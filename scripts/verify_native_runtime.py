"""Exercise real HTTP, worker, retries and restarts in a fresh disposable folder.

Use --executable dist/ALFRED/ALFRED.exe to verify the packaged application.
The report contains synthetic data only. This never opens the live database.
"""
from __future__ import annotations
import argparse
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--port", type=int, default=8030)
    parser.add_argument("--browser", action="store_true", help="Check the real UI using headless Chrome")
    parser.add_argument("--extended", action="store_true", help="Concurrent users, mobile and accessibility checks")
    args = parser.parse_args()
    run = uuid.uuid4().hex[:10]
    data = ROOT / "artifacts" / "native-tests" / run
    data.mkdir(parents=True)
    report = {"run": run, "data_dir": str(data), "executable": str(args.executable or sys.executable), "passed": False, "checks": {}}
    prefix = [str(args.executable.resolve())] if args.executable else [sys.executable, str(ROOT / "alfred_native.py")]

    def command(action):
        result = subprocess.run([*prefix, action, "--data-dir", str(data), "--port", str(args.port), "--no-browser"],
                                capture_output=True, text=True, timeout=240)
        assert result.returncode == 0, (action, result.stdout, result.stderr)
        return result.stdout

    def passed(name, detail=True):
        report["checks"][name] = detail
        print(f"PASS {name}: {detail}", flush=True)

    from alfred_native import configure, read_state
    import requests

    try:
        command("start")
        state = read_state(data)
        base = f"http://127.0.0.1:{state['port']}"
        session = requests.Session()
        session.trust_env = False
        assert session.get(base + "/health/native/", timeout=10).status_code == 200
        passed("startup")
        command("start")
        assert read_state(data)["instance"] == state["instance"]
        passed("duplicate_start_reuses_instance")
        configure(data)
        from django.contrib.auth import get_user_model
        from django.core.cache import cache
        from django.core.files.base import ContentFile
        from alfred_ai.native_tasks import native_runtime_probe
        from huey.contrib.djhuey import HUEY
        from apps.expenses.models import StatementUpload
        from tests.user_acceptance_scenario import PASSWORD, seed_acceptance_user

        # Adapt the existing scenario to real network requests, with CSRF enabled.
        class HttpClient:
            def post(self, path, payload, content_type=None):
                if not session.cookies.get("csrftoken"):
                    session.get(base + "/signup/", timeout=30).raise_for_status()
                headers = {"X-CSRFToken": session.cookies["csrftoken"], "Referer": base + path}
                kwargs = {"json": payload} if content_type else {"data": payload}
                return session.post(base + path, headers=headers, allow_redirects=False, timeout=90, **kwargs)

            def force_login(self, user):
                result = self.post("/login/", {"username": user.username, "password": PASSWORD})
                assert result.status_code == 302, result.content[:1000]

        scenario = seed_acceptance_user(HttpClient())
        dashboard = session.get(base + "/api/expenses/dashboard/", timeout=90)
        dashboard.raise_for_status()
        summary = dashboard.json()["summary"]
        expected = {"current_month_income": 80000, "current_month_expense": 30000,
                    "current_month_loans": 10000, "current_month_outflow": 47000,
                    "current_month_net": 33000, "current_month_review_required": 60000}
        for key, value in expected.items():
            assert Decimal(str(summary[key])) == value, (key, summary[key], value)
        passed("signup_api_arithmetic", expected)
        expenses = session.get(base + "/api/expenses/", timeout=30).json()
        rows = expenses if isinstance(expenses, list) else expenses["results"]
        assert rows and all(row.get("category_label") and row.get("direction_label") for row in rows)
        passed("readable_transaction_labels")
        for page in ("/dashboard/", "/expenses/", "/settings/"):
            response = session.get(base + page, timeout=90)
            assert response.status_code == 200, (page, response.status_code, response.text[:300])
        for asset in ("/static/js/app.js", "/static/css/style.css", "/static/favicon.svg",
                      "/static/vendor/bootstrap.min.css", "/static/vendor/bootstrap.bundle.min.js",
                      "/static/vendor/chart.umd.min.js"):
            assert session.get(base + asset, timeout=30).status_code == 200, asset
        passed("pages_and_static_files")
        assert session.get(base + "/project-details/", timeout=30).status_code == 403
        passed("admin_page_access_control")
        if args.browser:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1440,1200")
            browser = webdriver.Chrome(options=options)
            try:
                # Confirm charts and controls work with all external assets blocked.
                browser.execute_cdp_cmd("Network.enable", {})
                browser.execute_cdp_cmd("Network.setBlockedURLs", {"urls": ["*://fonts.googleapis.com/*", "*://fonts.gstatic.com/*", "*://cdn.jsdelivr.net/*"]})
                browser.get(base + "/login/")
                browser.find_element(By.NAME, "username").send_keys(scenario["user"].username)
                browser.find_element(By.NAME, "password").send_keys(PASSWORD)
                browser.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
                wait = WebDriverWait(browser, 60)
                wait.until(lambda driver: "80,000" in driver.find_element(By.ID, "dashboardSummaryCards").text)
                text = browser.find_element(By.ID, "dashboardSummaryCards").text
                browser.save_screenshot(str(data / "dashboard.png"))
                assert all(value in text.lower() for value in ("30,000", "47,000", "confirmed outflow")), text
                notice = browser.find_element(By.ID, "dashboardReviewNotice").text
                assert "60,000" in notice and "excluded" in notice
                charts = browser.execute_script("return Chart.getChart(document.getElementById('dashboardMonthlyChart')).data.datasets.map(d => ({label:d.label, last:d.data.at(-1)}));")
                amounts = {item["label"]: item["last"] for item in charts}
                assert amounts["Investments"] == 5000 and amounts["Card payments"] == 2000
                browser.save_screenshot(str(data / "dashboard.png"))
                browser.get(base + "/settings/")
                wait.until(lambda driver: "remove my data" in driver.find_element(By.TAG_NAME, "body").text.lower())
                browser.save_screenshot(str(data / "settings.png"))
                passed("chrome_browser_totals_charts_and_settings_without_cdn", amounts)
            finally:
                browser.quit()

        user = scenario["user"]
        user.is_superuser = True
        user.save(update_fields=["is_superuser"])
        try:
            operations = session.get(base + "/project-details/", timeout=90)
            assert operations.status_code == 200, operations.status_code
            assert "5/5 local runtime checks passed" in operations.text, "Native readiness was not ready"
            passed("native_readiness_in_admin_page")
        finally:
            user.is_superuser = False
            user.save(update_fields=["is_superuser"])
        upload = StatementUpload.objects.create(user=user, file_name="native-proof.txt",
            original_file=ContentFile(b"Private synthetic document", name="native-proof.txt"))
        file_url = base + upload.original_file.url
        owner = session.get(file_url, timeout=10)
        assert owner.status_code == 200 and owner.content == b"Private synthetic document"
        anonymous = requests.get(file_url, allow_redirects=False, timeout=10)
        assert anonymous.status_code == 302
        stranger = get_user_model().objects.create_user(username="other_native_user", password=PASSWORD)
        other = requests.Session()
        other.get(base + "/login/", timeout=10)
        other.post(base + "/login/", data={"username": stranger.username, "password": PASSWORD},
            headers={"X-CSRFToken": other.cookies["csrftoken"]}, timeout=10)
        assert other.get(file_url, timeout=10).status_code == 404
        passed("private_upload_ownership")

        probe = native_runtime_probe(run)
        result = probe.get(blocking=True, timeout=30)
        assert result["worker_pid"] != os.getpid() and result["attempts"] == 1
        passed("separate_worker_execution", result)
        simultaneous = [native_runtime_probe(run + "-atomic") for _ in range(20)]
        counts = sorted(item.get(blocking=True, timeout=30)["attempts"] for item in simultaneous)
        assert counts == list(range(1, 21)), counts
        passed("shared_cache_atomic_increments", counts[-1])
        retry = native_runtime_probe(run + "-retry", fail_once=True)
        deadline = time.monotonic() + 30
        retry_result = None
        while time.monotonic() < deadline:
            try:
                retry_result = HUEY.result(retry.id, blocking=False)
            except Exception:
                pass  # Huey exposes the first attempt's error before retrying.
            if retry_result:
                break
            time.sleep(0.2)
        assert retry_result and retry_result["attempts"] == 2, retry_result
        passed("transient_failure_retry", retry_result)
        (data / "artifacts" / "native" / f"worker-stop-{state['instance']}").touch()
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and read_state(data).get("worker_pid") == state["worker_pid"]:
            time.sleep(0.25)
        recovered = native_runtime_probe(run + "-recovered").get(blocking=True, timeout=30)
        assert recovered["worker_pid"] != state["worker_pid"]
        passed("supervisor_restarts_stopped_worker", recovered["worker_pid"])
        crash_probe = native_runtime_probe(run + "-crash", hold_seconds=8)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and cache.get(f"native:probe:{run}-crash") != 1:
            time.sleep(0.1)
        assert cache.get(f"native:probe:{run}-crash") == 1, "Crash probe never started"
        # Kill only the child identified by this isolated data folder's supervisor.
        import signal
        os.kill(read_state(data)["worker_pid"], signal.SIGTERM)
        crash_result = crash_probe.get(blocking=True, timeout=60)
        assert crash_result["attempts"] == 2, crash_result
        assert HUEY.storage.sql("SELECT COUNT(*) FROM native_history WHERE outcome='recovered'", results=True)[0][0] >= 1
        passed("inflight_job_recovers_after_worker_kill", crash_result)
        heartbeat = cache.get("native:scheduler-heartbeat")
        assert heartbeat and heartbeat["instance"] == state["instance"]
        passed("scheduler_executed_heartbeat")
        if args.extended:
            from scripts.verify_native_extended import verify_extended
            verify_extended(base, session, scenario, data, passed)
        if args.executable:
            import fitz
            pdf_path = data / "ocr-proof.pdf"
            with fitz.open() as document:
                page = document.new_page()
                page.insert_text((72, 120), "ALFRED NATIVE OCR PROOF", fontsize=24)
                page.insert_text((72, 170), "Invoice total 275.50", fontsize=24)
                document.save(pdf_path)
            for kind in ("document", "statement"):
                process = subprocess.run([*prefix, "--ocr-worker", kind, str(pdf_path), "1"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
                assert process.returncode == 0, (kind, process.stdout[-1000:], process.stderr[-2000:])
                payload = json.loads(process.stdout.strip().splitlines()[-1])
                assert "ALFRED" in payload["text"] and "275.50" in payload["text"], payload
            passed("bundled_document_and_statement_ocr")
        command("stop")
        pending = native_runtime_probe(run + "-persist")
        time.sleep(1)
        assert pending.get() is None
        command("start")
        persisted = pending.get(blocking=True, timeout=30)
        assert persisted["probe_id"] == run + "-persist"
        assert read_state(data)["instance"] != state["instance"]
        # The same signed-in browser session and all entered data survive restart.
        restored_summary = session.get(base + "/api/expenses/dashboard/", timeout=90).json()["summary"]
        assert all(restored_summary[key] == summary[key] for key in expected)
        assert session.get(file_url, timeout=10).content == owner.content
        passed("queued_job_and_account_persist_after_restart")
        command("stop")

        backup_probe = native_runtime_probe(run + "-backup-queue")
        backup = data.parent / f"{run}-backup"
        restored = data.parent / f"{run}-restored"
        backup.mkdir()
        with sqlite3.connect(data / "db.sqlite3") as source, sqlite3.connect(backup / "db.sqlite3") as target:
            source.backup(target)
        queue_copy = backup / "artifacts" / "native" / "jobs.sqlite3"
        queue_copy.parent.mkdir(parents=True)
        with sqlite3.connect(data / "artifacts" / "native" / "jobs.sqlite3") as source, sqlite3.connect(queue_copy) as target:
            source.backup(target)
        shutil.copytree(data / "media", backup / "media")
        shutil.copytree(data / "config", backup / "config")
        shutil.copytree(backup, restored)
        assert hashlib.sha256((data / "media" / upload.original_file.name).read_bytes()).digest() == hashlib.sha256((restored / "media" / upload.original_file.name).read_bytes()).digest()
        result = subprocess.run([*prefix, "start", "--data-dir", str(restored), "--port", str(args.port + 1), "--no-browser"],
                                capture_output=True, text=True, timeout=240)
        assert result.returncode == 0, result.stderr
        restore_base = f"http://127.0.0.1:{read_state(restored)['port']}"
        try:
            restored_response = session.get(restore_base + "/api/expenses/dashboard/", timeout=90)
            restored_response.raise_for_status()
            assert all(restored_response.json()["summary"][key] == summary[key] for key in expected)
            assert session.get(restore_base + upload.original_file.url, timeout=10).content == owner.content
            passed("backup_restore_http_data_and_upload")
            deadline = time.monotonic() + 30
            restored_job = None
            while time.monotonic() < deadline:
                with sqlite3.connect(restored / "artifacts" / "native" / "jobs.sqlite3") as queue:
                    row = queue.execute("SELECT value FROM kv WHERE queue=? AND key=?",
                                        (HUEY.storage.name, backup_probe.id)).fetchone()
                if row:
                    restored_job = HUEY.serializer.deserialize(row[0])
                    break
                time.sleep(.2)
            assert restored_job and restored_job["probe_id"] == run + "-backup-queue", restored_job
            passed("backup_restore_pending_job")
        finally:
            subprocess.run([*prefix, "stop", "--data-dir", str(restored)], timeout=180, check=True)
        report["passed"] = True
    finally:
        subprocess.run([*prefix, "stop", "--data-dir", str(data)], timeout=180)
        filename = "native_exe_verification.json" if args.executable else "native_huey_verification.json"
        if args.extended:
            filename = filename.replace("_verification", "_extended_verification")
        report_path = ROOT / "artifacts" / "ops" / filename
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Report: {report_path}", flush=True)


if __name__ == "__main__":
    main()
