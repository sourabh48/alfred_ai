"""Adapters for existing ALFRED test runners; child environments contain no operator secrets."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

from scripts import release_gate as release

# This is the established M15 combined scope, plus the release engine's own tests.
BACKEND = tuple("tests." + name for name in (
    "test_alfred_brain", "test_api_session_security", "test_auth_pages", "test_bank_statement_grounding", "test_bike_document_parser",
    "test_budget_money", "test_budget_money_migration", "test_canonical_evidence", "test_canonical_grounding", "test_closure_citations",
    "test_career_api_errors", "test_career_job_http", "test_career_recruiter_and_evidence",
    "test_career_resume_upload", "test_career_money", "test_conversation_history", "test_credit_report_upload", "test_document_center_and_statement_import",
    "test_document_corpus", "test_document_extraction", "test_document_grounding_acceptance", "test_document_knowledge", "test_document_questions", "test_document_retry_integrity",
    "test_document_review_and_retry", "test_expense_corrections", "test_expense_export", "test_expense_money_identity", "test_expense_money_runtime", "test_experimental_retirement",
    "test_family_account_links", "test_family_api_errors", "test_family_consent_migration",
    "test_family_invitation_atomic", "test_family_invitation_throttling", "test_file_uploader_persistence",
    "test_financial_baseline_alignment", "test_global_abuse_limits", "test_hybrid_intelligence",
    "test_intelligence_currency", "test_intelligence_ui", "test_investment_and_relationship_advisory",
    "test_investment_evidence", "test_investment_evidence_migration", "test_investment_grounding", "test_financial_source_selection",
    "test_investment_money", "test_loan_diagnostics", "test_loan_evidence", "test_loan_evidence_migration", "test_loan_grounding", "test_loan_payment_sources", "test_loan_foreclosure_money",
    "test_loan_lifecycle_and_reports", "test_loan_money_field", "test_loan_money_runtime",
    "test_loan_related_money_runtime", "test_loan_verification", "test_loan_verification_api",
    "test_memory_checkpoint", "test_memory_cloud", "test_memory_learning", "test_memory_privacy", "test_memory_platform",
    "test_memory_reasoning", "test_memory_evaluation", "test_memory_sync", "test_memory_sync_runtime", "test_native_launcher", "test_retrieval_quality",
    "test_mobility_money", "test_native_observation", "test_native_runtime", "test_native_tray", "test_operational_hardening",
    "test_password_security", "test_persistent_memory", "test_profile_money_boundary",
    "test_private_storage", "test_source_storage", "test_private_media_profiles", "test_local_config",
    "test_platform_hardening.EmailConnectionTokenSecurityTests", "test_remaining_public_http",
    "test_retention_release_boundary", "test_statement_columns", "test_statement_evidence", "test_statement_evidence_migration", "test_token_rotation",
    "test_travel_http", "test_travel_retention", "test_travel_refresh", "test_upload_limits", "test_upload_privacy_retention", "test_user_data_reset", "test_user_money",
    "test_release_gate", "test_release_validation", "test_release_recovery", "test_private_recovery_verifier",
    "test_release_promotion", "test_release_acceptance", "test_browser_regression_runner", "test_live_ui_contracts", "test_windows_build_provenance"))

SECRET = re.compile(rb"sk-(?:proj-|svcacct-|ant-api[0-9]-)?[A-Za-z0-9_-]{30,}|"
                    rb"github_pat_[A-Za-z0-9_]{35,}|gh[pousr]_[A-Za-z0-9]{30,}|"
                    rb"AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|"
                    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
                    rb"['\"]?(?:SECRET_KEY|AWS_SECRET_ACCESS_KEY|OPENAI_API_KEY|api_key|password|"
                    rb"access_token|refresh_token|client_secret|secret_key|token)['\"]?"
                    rb"\s*[:=]\s*['\"][A-Za-z0-9_+/=-]{24,}['\"]", re.IGNORECASE)
PRIVATE = re.compile(r"(?i)(^|/)(?:\.env(?:\..+)?|native\.env|local\.env|"
                     r"[^/]+\.(?:sqlite3?|db|key|pem|p12|pfx|wal|shm|zip|7z|enc)|"
                     r"media|uploads|statement_uploads|career_resumes|credit_reports|"
                     r"backups|restored-runtime|embeddings_store|private-memory-v2)(?:/|$)")
PUBLIC_TEST_IDENTIFIERS = {
    # AWS documentation example and a mocked OpenAI key, reviewed at the M15 baseline.
    ("tests/memory_s3_fixture.py", "1a5d44a2dca19669d72edf4c4f1c27c4c1ca4b4408fbb17f6ce4ad452d78ddb3"),
    ("tests/memory_s3_fixture.py", "099ffd0e4ccd9ca5a43a7ff4255d0ce24231fa1776f934dd60361dfa0499c431"),
    ("tests/test_memory_reasoning.py", "3de18efc58026cb49080132b1b2c2a55776401162062b9d6c060951ddb93e626"),
    # Explicit synthetic signing keys in local generated-data drills, never runtime credentials.
    ("scripts/benchmark_local_cache.py", "5dbfc784c7dd91de820790aecc08e0a09248acf4aceb858175544c73b6e270b7"),
    ("scripts/rehearse_money_migrations.py", "8c55aea836191192e8d863229227c32585de62f669d245e5383490ed6d125431"),
    ("tests/test_global_abuse_limits.py", "c3e1e29fc822d0b9a3e12bb120c19b9aeccdc5ea47169a4f4ff6b123e3a6ec22"),
}
SOURCE_SCAN_BATCH_BYTES = 64 * 1024 * 1024
SOURCE_SCAN_TOTAL_BYTES = 128 * 1024 * 1024


def privacy(repo, manifest):
    """Inspect pinned blobs, including intermediate history, without printing content."""
    release.gate(manifest, "privacy", "NOT_RUN", "source_scan_pending")
    candidate, baseline = manifest["candidate_sha"], manifest["production_baseline_sha"]
    release.exact_commit(repo, candidate)
    release.exact_commit(repo, baseline)
    commits = release.git(repo, "rev-list", baseline + ".." + candidate).splitlines()
    if len(commits) > 1000:
        raise release.GateError("source_scan_object_budget")
    objects = {}
    sizes = {}
    total_bytes = 0
    findings = []
    paths = set()
    for commit in sorted(set(commits + [candidate])):
        for entry in release.git(repo, "ls-tree", "-r", "-l", "-z", commit).split("\0"):
            if not entry:
                continue
            fields, path = entry.split("\t", 1)
            mode, kind, oid, size = fields.split()
            paths.add(path)
            ref = hashlib.sha256(path.encode()).hexdigest()[:16]
            if (kind != "blob" or mode == "120000" or "\n" in path or "\r" in path
                    or (PRIVATE.search(path) and not path.endswith((".env.example", ".example.env")))):
                findings.append({"code": "private_or_unsafe_tracked_path", "path_reference": ref})
            elif int(size) > 16 * 1024 * 1024:
                findings.append({"code": "source_blob_exceeds_scan_budget", "path_reference": ref})
            else:
                if oid not in objects:
                    total_bytes += int(size)
                    sizes[oid] = int(size)
                objects.setdefault(oid, set()).add(path)
                if len(objects) > 10000 or total_bytes > SOURCE_SCAN_TOTAL_BYTES:
                    raise release.GateError("source_scan_object_budget")
    # Bound each captured response, including framing, while retaining all history.
    batches, batch, batch_bytes = [], [], 0
    for oid in sorted(objects):
        cost = len(f"{oid} blob {sizes[oid]}\n".encode()) + sizes[oid] + 1
        if cost > SOURCE_SCAN_BATCH_BYTES:
            raise release.GateError("source_scan_object_budget")
        if batch and batch_bytes + cost > SOURCE_SCAN_BATCH_BYTES:
            batches.append(batch)
            batch, batch_bytes = [], 0
        batch.append(oid)
        batch_bytes += cost
    if batch:
        batches.append(batch)
    reviewed = 0
    deadline = time.monotonic() + 120
    for batch in batches:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise release.GateError("source_blob_scan_failed")
        try:
            result = subprocess.run(["git", "-C", str(repo), "cat-file", "--batch"],
                                    input="".join(oid + "\n" for oid in batch).encode(),
                                    capture_output=True, timeout=remaining)
        except (OSError, subprocess.TimeoutExpired):
            raise release.GateError("source_blob_scan_failed") from None
        if result.returncode:
            raise release.GateError("source_blob_scan_failed")
        if len(result.stdout) > SOURCE_SCAN_BATCH_BYTES:
            raise release.GateError("source_blob_identity_mismatch")
        position = 0
        for oid in batch:
            if time.monotonic() >= deadline:
                raise release.GateError("source_blob_scan_failed")
            names = objects[oid]
            end = result.stdout.find(b"\n", position)
            header = result.stdout[position:end].split() if end >= 0 else []
            if header != [oid.encode(), b"blob", str(sizes[oid]).encode()]:
                raise release.GateError("source_blob_identity_mismatch")
            stop = end + 1 + sizes[oid]
            if stop >= len(result.stdout) or result.stdout[stop:stop + 1] != b"\n":
                raise release.GateError("source_blob_identity_mismatch")
            content = result.stdout[end + 1:stop]
            position = stop + 1
            for match in SECRET.finditer(content):
                value = match.group()
                known_fixture = (len(names) == 1 and (next(iter(names)), hashlib.sha256(value).hexdigest())
                                 in PUBLIC_TEST_IDENTIFIERS)
                known_rehearsal = (names == {"scripts/rehearse_money_migrations.py"}
                                   and b"disposable-rehearsal-key-only" in value
                                   and b"Django DB is not disposable" in content)
                if known_fixture or known_rehearsal:
                    reviewed += 1
                else:
                    findings.append({"code": "credential_pattern", "blob_reference": oid[:16]})
        if position != len(result.stdout):
            raise release.GateError("source_blob_identity_mismatch")
        del result
    if time.monotonic() >= deadline:
        raise release.GateError("source_blob_scan_failed")
    release.gate(manifest, "privacy", "FAIL" if findings else "PASS",
                 "source_privacy_findings" if findings else "pinned_source_privacy_verified",
                 paths=len(paths), blobs=len(objects), history_commits=len(commits),
                 reviewed_synthetic_identifiers=reviewed, findings=findings,
                 scanned_bytes=total_bytes, batches=len(batches))
    source = manifest["gates"]["source"].get("evidence", {})
    source["changed_paths"] = ["redacted-path-" + hashlib.sha256(path.encode()).hexdigest()[:16]
                               if PRIVATE.search(path) else path for path in source.get("changed_paths", [])]
    return manifest["gates"]["privacy"]


def environment(sandbox):
    sandbox = Path(sandbox).resolve()
    sandbox.mkdir(parents=True, exist_ok=False)
    allowed = {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "USERPROFILE",
               "LOCALAPPDATA", "APPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMDATA",
               "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "HOME", "LANG", "LC_ALL",
               "CHROME_BINARY", "CHROMEDRIVER", "GITHUB_ACTIONS", "GITHUB_WORKFLOW", "GITHUB_RUN_ID",
               "GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_EVENT_NAME", "GITHUB_REF", "GITHUB_HEAD_REF",
               "GITHUB_REF_NAME"}
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    env.update(ALFRED_LOCAL_RUNTIME="true", ALFRED_AUTO_TRAIN_ON_STARTUP="false",
               ALFRED_DATA_DIR=str(sandbox), ALFRED_LOCAL_ENV_FILE=str(sandbox / "absent.env"),
               ALFRED_MEDIA_ROOT=str(sandbox / "media"),
               ALFRED_REGISTRY_PATH=str(sandbox / "registry"),
               ALFRED_MEMORY_CLOUD_AUTHORIZED="false", ALFRED_MEMORY_SYNC_PROVIDER="",
               ALFRED_MEMORY_OPENAI_AUTHORIZED="false", ALFRED_MEMORY_SYNC_MOCK_DIR="",
               ALFRED_RUN_BROWSER_TESTS="false", DJANGO_SECRET_KEY=uuid.uuid4().hex,
               DATABASE_URL="sqlite:///" + (sandbox / "db.sqlite3").as_posix(),
               CACHE_BACKEND="django.core.cache.backends.locmem.LocMemCache", CACHE_LOCATION="release-synthetic",
               PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    return env


def safe_log(text):
    """Retain test identifiers/counts, never raw tracebacks, payloads or exception messages."""
    lines = []
    for line in text.splitlines():
        failure = re.fullmatch(r"(FAIL|ERROR): ([A-Za-z_][A-Za-z0-9_.]*) "
                               r"\(([A-Za-z_][A-Za-z0-9_.]*)\)(?: .*)?", line.strip())
        if failure:
            # Subtest parameters can contain document text; retain identifiers only.
            lines.append(f"{failure[1]}: {failure[2]} ({failure[3]})")
        elif re.fullmatch(r"(?:Ran \d+ tests? in [\d.]+s|OK(?: \(skipped=\d+\))?|"
                        r"FAILED \([\w=, ]+\)|[.sEFx!]+|Found \d+ test\(s\)\.)", line.strip()):
            lines.append(line.strip())
        elif re.match(r"PASS [a-zA-Z0-9_]+:", line):
            lines.append(line.split(":", 1)[0])
    return "\n".join(lines) + "\nOther output omitted to protect diagnostic privacy.\n"


def run(repo, command, env, output, name, timeout):
    try:
        process = subprocess.run(command, cwd=repo, env=env, capture_output=True,
                                 text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        result = {"status": "FAIL", "code": "suite_timeout", "tests": 0, "skips": 0}
        text = ""
    else:
        text = process.stdout + "\n" + process.stderr
        counts = re.findall(r"Ran (\d+) tests? in", text)
        skips = re.findall(r"skipped=(\d+)", text)
        result = {"status": "PASS" if process.returncode == 0 else "FAIL", "code": "suite_exit",
                  "exit": process.returncode, "tests": int(counts[-1]) if counts else 0,
                  "skips": int(skips[-1]) if skips else 0}
    path = Path(output) / (name + ".log")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(safe_log(text), encoding="utf-8")
    result.update(log=path.name, log_sha256=release.sha256(path))
    return result


def validate(repo, manifest, output, profile, labels=(), with_ollama=False, bundle=None, package_manifest=None):
    repo, output = Path(repo).resolve(), Path(output).resolve()
    release.source_checks(repo, manifest)
    privacy(repo, manifest)
    if decision_failed(manifest):
        return
    run_id = uuid.uuid4().hex[:12]
    manifest.setdefault("validation_history", []).append({"run": run_id, "profile": profile,
        "previous": {name: manifest["gates"][name] for name in ("configuration", "backend", "browser", "native", "ollama", "packaged")}})
    env = environment(output / ("synthetic-" + uuid.uuid4().hex))
    configuration = []
    for index, args in enumerate((("check",), ("makemigrations", "--check", "--dry-run"))):
        configuration.append(run(repo, [sys.executable, "manage.py", *args], env, output,
                                 "configuration-" + run_id + "-" + str(index), 120))
    release.gate(manifest, "configuration", "PASS" if all(r["status"] == "PASS" for r in configuration) else "FAIL",
                 "isolated_configuration_checks", results=configuration, cloud_enabled=False, paid_openai_enabled=False)
    if manifest["gates"]["configuration"]["status"] != "PASS":
        return
    if profile in ("targeted", "backend", "full"):
        selected = tuple(labels) if profile == "targeted" else BACKEND
        if not selected or any(not re.fullmatch(r"(?:tests|apps)\.[A-Za-z0-9_.]+", label) for label in selected):
            raise release.GateError("invalid_targeted_test_labels")
        result = run(repo, [sys.executable, "manage.py", "test", *selected, "--noinput"], env, output, "backend-" + run_id, 1800)
        if result["status"] == "PASS" and (not result["tests"] or result["skips"]):
            result["status"] = "NOT_RUN"
            result["code"] = "tests_missing_or_skipped"
        if profile == "targeted":
            manifest.setdefault("targeted_runs", []).append(result)
            manifest["last_validation"] = {"profile": profile, "status": result["status"]}
        else:
            release.gate(manifest, "backend", result["status"], "combined_backend", **result_evidence(result), labels=list(selected))
        if result["status"] != "PASS":
            return
    if profile in ("browser", "full"):
        result = run(repo, [sys.executable, "scripts/run_browser_regressions.py", "--browser", "Chrome",
                           "--require-browser", "--artifact-dir", str(output / "browser"),
                           "--proof-label", "release"], env, output, "browser-" + run_id, 1800)
        if result["status"] == "PASS" and (not result["tests"] or result["skips"]):
            result["status"] = "NOT_RUN"
        release.gate(manifest, "browser", result["status"], "house_chrome_suite", **result_evidence(result))
        if result["status"] != "PASS":
            return
    if profile in ("native", "full"):
        args = [sys.executable, "scripts/verify_native_runtime.py", "--browser", "--port", "8140"]
        if with_ollama:
            args.append("--memory")
        native_path = repo / "artifacts/ops/native_huey_verification.json"
        previous = release.sha256(native_path) if native_path.is_file() else None
        result = run(repo, args, env, output, "native-" + run_id, 1800)
        # The house report provides per-check evidence; a zero exit alone is insufficient.
        native = {}
        if native_path.is_file():
            import json
            native = json.loads(native_path.read_text(encoding="utf-8"))
        passed = (result["status"] == "PASS" and native.get("passed") is True and bool(native.get("checks"))
                  and release.sha256(native_path) != previous)
        release.gate(manifest, "native", "PASS" if passed else "FAIL", "house_native_suite",
                     **result_evidence(result), checks=len(native.get("checks", {})),
                     report_sha256=release.sha256(native_path) if native_path.is_file() else None)
        manifest["native_run"] = native.get("run")
        if with_ollama:
            release.gate(manifest, "ollama", "PASS" if passed else "FAIL", "local_model_native_acceptance")
    if profile == "packaged":
        packaged(repo, manifest, output, env, bundle, package_manifest, with_ollama)
    # Tests must not silently change tracked source or advance the selected SHA.
    release.source_checks(repo, manifest)


def result_evidence(result):
    return {key: value for key, value in result.items() if key not in ("status", "code")}


def decision_failed(manifest):
    return any(manifest["gates"][name]["status"] == "FAIL" for name in ("source", "dependencies", "migrations", "privacy"))


def packaged(repo, manifest, output, env, bundle, package_manifest, with_ollama=False):
    import json
    if not bundle or not package_manifest:
        release.gate(manifest, "packaged", "NOT_RUN", "fresh_bundle_and_source_manifest_required")
        return
    from scripts.package_windows_release import inspect_bundle
    bundle, package_manifest = Path(bundle).resolve(), Path(package_manifest).resolve()
    receipt = json.loads(package_manifest.read_text(encoding="utf-8"))
    if receipt.get("source_commit") != manifest["candidate_sha"] or receipt.get("source_dirty") is not False:
        raise release.GateError("packaged_source_identity_mismatch")
    for name in ("ALFRED.exe", "ALFRED Launcher.exe"):
        if receipt.get("artifacts", {}).get(name, {}).get("sha256") != release.sha256(bundle / name):
            raise release.GateError("packaged_executable_hash_mismatch")
    files = inspect_bundle(bundle)
    report = Path(repo) / "artifacts/ops/native_exe_verification.json"
    previous = release.sha256(report) if report.is_file() else None
    args = [sys.executable, "scripts/verify_native_runtime.py", "--executable", str(bundle / "ALFRED.exe"),
            "--launcher", str(bundle / "ALFRED Launcher.exe"), "--browser", "--port", "8160"]
    if with_ollama:
        args.append("--memory")
    result = run(repo, args, env, output, "packaged-" + uuid.uuid4().hex[:12], 1800)
    record = json.loads(report.read_text()) if report.is_file() else {}
    passed = (result["status"] == "PASS" and record.get("passed") is True and bool(record.get("checks"))
              and release.sha256(report) != previous)
    release.gate(manifest, "packaged", "PASS" if passed else "FAIL", "house_packaged_native_and_chrome",
        **result_evidence(result), checks=len(record.get("checks", {})), inspected_files=len(files),
        source_manifest_sha256=release.sha256(package_manifest), scope="same_host_portable_package_only")
