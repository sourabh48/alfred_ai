"""M21: actual native/browser promotion and rollback in newly created synthetic storage."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import signal

from cryptography.fernet import Fernet
from alfred_private_storage import private_directory
from alfred_native import write_json
from scripts import release_gate as release
from scripts import release_recovery as recovery
from scripts import release_promotion as promotion


def native_fixture(repo, manifest):
    run = manifest.get("native_run", "")
    proof = Path(repo) / "artifacts/ops/native_huey_verification.json"
    if not re.fullmatch(r"[a-f0-9]{10}", run) or not proof.is_file():
        raise release.GateError("completed_synthetic_native_fixture_required")
    evidence = manifest["gates"]["native"]["evidence"]
    record = json.loads(proof.read_text())
    if (release.sha256(proof) != evidence.get("report_sha256") or record.get("run") != run
            or record.get("passed") is not True):
        raise release.GateError("native_fixture_proof_changed")
    expected = (Path(repo) / "artifacts/native-tests" / run).resolve()
    if Path(record["data_dir"]).resolve() != expected:
        raise release.GateError("native_fixture_runtime_mismatch")
    return recovery.no_links(expected)


def synthetic_session(port):
    import requests
    from tests.user_acceptance_scenario import PASSWORD
    base = f"http://127.0.0.1:{port}"
    session = requests.Session()
    session.trust_env = False
    session.get(base + "/login/", timeout=15).raise_for_status()
    response = session.post(base + "/login/", data={"username": "acceptance_demo", "password": PASSWORD},
        headers={"X-CSRFToken": session.cookies["csrftoken"], "Referer": base + "/login/"},
        timeout=30, allow_redirects=False)
    if response.status_code != 302:
        raise release.GateError("synthetic_acceptance_login_failed")
    return base, session


def memory_roundtrip(port, memory_id=None):
    base, session = synthetic_session(port)
    path = base + "/api/ai/memories/"
    headers = {"X-CSRFToken": session.cookies["csrftoken"], "Referer": base + "/settings/"}
    if memory_id is None:
        response = session.post(path, json={"content": {"statement": "I prefer quiet mountain hiking holidays."},
            "provenance": {"source": "SYNTHETIC-M21-RELEASE-REHEARSAL"}, "sensitivity": "sensitive", "verified": True},
            headers=headers, timeout=75)
        if response.status_code != 201:
            raise release.GateError("synthetic_memory_save_failed")
        memory_id = response.json()["id"]
    response = session.post(path + "retrieve/", json={"query": "What kind of holiday do I enjoy?"}, headers=headers, timeout=75)
    if response.status_code != 200 or memory_id not in [row["id"] for row in response.json()["memories"]]:
        raise release.GateError("synthetic_restart_memory_retrieval_failed")
    cloud = session.get(path + "reason/", timeout=15).json()
    sync = session.get(path + "sync/", timeout=15).json()
    if cloud["real_provider_enabled"] or cloud["provider_available"] or sync["provider"] != "disabled" or sync["available"]:
        raise release.GateError("external_provider_unexpectedly_enabled")
    return memory_id


def browser_acceptance(port, output):
    from tests.user_acceptance_scenario import PASSWORD
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    options = webdriver.ChromeOptions()
    for option in ("--headless=new", "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage", "--window-size=1440,1100"):
        options.add_argument(option)
    browser = webdriver.Chrome(options=options)
    checks = []
    base = f"http://127.0.0.1:{port}"
    try:
        wait = WebDriverWait(browser, 60)
        browser.get(base + "/login/")
        browser.find_element(By.NAME, "username").send_keys("acceptance_demo")
        browser.find_element(By.NAME, "password").send_keys(PASSWORD)
        browser.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        wait.until(lambda d: "80,000" in d.find_element(By.ID, "dashboardSummaryCards").text)
        checks.append("synthetic_login_canonical_dashboard")
        for name, path, selector in (
            ("finance", "/expenses/", "#bankAccountsPanel"),
            ("loans", "/loans/", "#loanTableBody"),
            ("investments", "/investments/", "#investmentPositionsBodySearch"),
            ("travel", "/mobility/", "main"),
            ("documents", "/documents/", "main"),
            ("memory", "/settings/#privateMemoryPanel", "#privateMemoryPanel"),
            ("conversation", "/ai/insights/", "#intelligenceQuery"),
        ):
            browser.get(base + path)
            wait.until(lambda d: d.find_element(By.CSS_SELECTOR, selector))
            if name == "conversation":
                wait.until(lambda d: d.find_element(By.ID, "intelligenceCloudStatus").text == "OpenAI disabled")
            browser.save_screenshot(str(output / (name + ".png")))
            checks.append(name)
        theme = browser.find_element(By.ID, "workspaceTheme")
        before = browser.execute_script("return document.documentElement.dataset.theme")
        theme.click()
        if browser.execute_script("return document.documentElement.dataset.theme") == before:
            raise release.GateError("synthetic_theme_switch_failed")
        browser.set_window_size(390, 844)
        browser.save_screenshot(str(output / "responsive.png"))
        checks.append("responsive_and_theme")
    finally:
        browser.quit()
    write_json(output / "browser.json", {"status": "PASS", "checks": checks, "scope": "synthetic_account_only"})
    return checks


class RehearsalNative(promotion.NativeOperator):
    def __init__(self, *args, crash_worker=False):
        super().__init__(*args)
        self.crash_worker = crash_worker
        self.browser_checks = []

    def acceptance(self):
        super().acceptance()
        if self.crash_worker:
            self.crash_worker = False
            state = json.loads((self.runtime / "artifacts/native/runtime.json").read_text())
            worker = state.get("worker_pid")
            if not isinstance(worker, int) or worker <= 0 or worker == os.getpid():
                raise release.GateError("synthetic_worker_binding_invalid")
            os.kill(worker, signal.SIGTERM)  # Only this newly created rehearsal runtime's checked child.
            raise release.GateError("synthetic_worker_crash_injected")
        self.browser_checks = browser_acceptance(self.port, self.output / "browser")


def attach_backup(manifest, receipt, directory):
    release.gate(manifest, "local_backup", "PASS", "synthetic_independent_restore", **receipt)
    release.gate(manifest, "financial", "PASS", "synthetic_typed_financial_reconciliation")
    manifest["backup"] = {"directory": str(directory), "archive_sha256": receipt["archive_sha256"],
                          "runtime_reference": receipt["runtime_reference"]}


def sandbox_approval(manifest, target, runtime, output):
    output = private_directory(recovery.no_links(output))
    write_json(runtime / ".alfred-release-rehearsal.json", promotion.core_binding(manifest, target, runtime, "rehearsal"))
    approval = output / "synthetic-authorization.json"
    write_json(approval, {"decision": "YES", "binding": promotion.binding(manifest, target, runtime, "rehearsal"),
        "authorized_by": "automated disposable M21 acceptance",
        "authorization_evidence": "User requested controlled test-environment promotion only; no production authorization",
        "expires_utc": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "actions": ["stop_writers", "backup", "promote", "restart", "rollback_source", "restart_previous"]})
    return approval


def rehearse(repo, manifest, output, directory, port=8150):
    release.source_checks(repo, manifest)
    required = tuple(name for name in release.TECHNICAL if name not in ("financial", "rollback"))
    if release.decision(manifest, required)["status"] != "PASS":
        raise release.GateError("complete_technical_validation_before_rehearsal")
    fixture = native_fixture(repo, manifest)
    directory = recovery.no_links(directory)
    if directory.is_relative_to(Path(repo).resolve()) or Path(repo).resolve().is_relative_to(directory):
        raise release.GateError("rehearsal_must_be_outside_candidate_source")
    directory = recovery.private_root(directory)
    result = {"status": "NOT_RUN", "candidate_sha": manifest["candidate_sha"], "directory": str(directory),
              "scope": "new_disposable_synthetic_runtime_only", "human_acceptance": "NOT_RUN"}
    manifest["rehearsal"] = result
    original = deepcopy(manifest)
    target, runtime = directory / "source", directory / "runtime"
    ops = None
    try:
        release.git(repo, "clone", "--quiet", "--no-hardlinks", str(Path(repo).resolve()), str(target))
        release.git(target, "switch", "--detach", manifest["production_baseline_sha"])
        key = directory / "synthetic-test-key.protected"
        # This new synthetic fixture key cannot decrypt any existing ALFRED backup.
        key.write_bytes(b"M15DPAPI1\0" + recovery.protect_key(Fernet.generate_key()) if os.name == "nt" else Fernet.generate_key())
        seed = directory / "fixture-backup"
        recovery.create(fixture, seed, key, manifest["release_id"], manifest["candidate_sha"],
                        manifest["production_baseline_sha"], target)
        recovery.restore(seed, key, runtime)
        baseline = promotion.NativeOperator(target, runtime, directory / "baseline", port)
        ops = baseline
        baseline.start()
        baseline.health()
        memory_id = memory_roundtrip(port)
        baseline.stop()
        release.gate(manifest, "rollback", "PASS", "baseline_source_bundle_and_restored_native_runtime_boot_verified",
                     scope="same_host_synthetic_runtime_only")
        release.source_checks(repo, manifest, target_repo=target)
        backup = directory / "prepromotion-backup"
        receipt = recovery.create(runtime, backup, key, manifest["release_id"], manifest["candidate_sha"],
                                  manifest["production_baseline_sha"], target)
        attach_backup(manifest, receipt, backup)
        child = deepcopy(manifest)
        approval = sandbox_approval(child, target, runtime, directory)
        ops = RehearsalNative(target, runtime, directory / "promotion", port)
        promotion.promote(repo, child, directory / "promotion", target, runtime, key, approval,
                          execute=True, operator=ops)
        if child["deployment"].get("stage") != "COMPLETE":
            raise release.GateError("synthetic_promotion_not_complete")
        result["promotion"] = "PASS"
        result["browser_checks"] = len(ops.browser_checks)
        before = promotion.canonical_snapshot(runtime / "db.sqlite3")
        ops.stop()
        ops.start()
        ops.health()
        memory_roundtrip(port, memory_id)
        ops.stop()
        if promotion.canonical_snapshot(runtime / "db.sqlite3") != before:
            raise release.GateError("synthetic_restart_financial_difference")
        result["restart_persistence"] = "PASS"

        # A second promotion exercises an actual synthetic worker crash and authorized rollback.
        release.git(target, "switch", "--detach", manifest["production_baseline_sha"])
        rollback = deepcopy(original)
        rollback["release_id"] = manifest["release_id"][:60] + "-rollback"
        rollback["deployment"] = {"stage": "PREFLIGHT"}
        release.gate(rollback, "rollback", "PASS", "baseline_restore_boot_verified")
        release.source_checks(repo, rollback, target_repo=target)
        backup = directory / "rollback-prepromotion-backup"
        receipt = recovery.create(runtime, backup, key, rollback["release_id"], rollback["candidate_sha"],
                                  rollback["production_baseline_sha"], target)
        attach_backup(rollback, receipt, backup)
        approval = sandbox_approval(rollback, target, runtime, directory / "failure-injection")
        ops = RehearsalNative(target, runtime, directory / "failure-injection", port, crash_worker=True)
        try:
            promotion.promote(repo, rollback, directory / "failure-injection", target, runtime, key, approval,
                              execute=True, operator=ops)
        except release.GateError as exc:
            if str(exc) != "synthetic_worker_crash_injected" or rollback["deployment"].get("rollback") != "PASS":
                raise release.GateError("actual_native_rollback_failed") from None
        else:
            raise release.GateError("synthetic_failure_injection_not_observed")
        if release.git(target, "rev-parse", "HEAD") != manifest["production_baseline_sha"]:
            raise release.GateError("rollback_baseline_head_not_restored")
        memory_roundtrip(port, memory_id)
        browser_acceptance(port, directory / "after-rollback-browser")
        result.update(status="PASS", rollback="PASS", worker_crash_recovery="PASS", local_restore="PASS")
        release.gate(manifest, "rollback", "PASS", "actual_native_source_rollback_and_preserved_data_verified",
                     scope="same_host_synthetic_runtime_only", evidence_directory=str(directory))
    except BaseException as exc:
        result.update(status="FAIL", code=str(exc) if isinstance(exc, release.GateError) else "synthetic_rehearsal_failed",
                      exception_type=type(exc).__name__)
        release.gate(manifest, "rollback", "FAIL", "synthetic_release_rehearsal_failed")
        raise release.GateError(result["code"]) from None
    finally:
        if ops:
            try:
                ops.stop()
            except Exception:
                result["shutdown"] = "BLOCKED"
                result["status"] = "FAIL"
        write_json(directory / "rehearsal.json", result)
        release.report(manifest, output)
    if result["status"] != "PASS":
        raise release.GateError("synthetic_rehearsal_shutdown_failed")
    return result
