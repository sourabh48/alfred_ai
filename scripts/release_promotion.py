"""Approval-bound local promotion; dry run by default, no pushes or schema application."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import uuid

from alfred_native import InstanceLock
from scripts import release_gate as release
from scripts import release_recovery as recovery
from scripts.release_validation import safe_log

STAGES = ("PREFLIGHT", "BACKUP", "APPROVAL", "STOP_WRITERS", "VERIFY", "PROMOTE", "RESTART", "ACCEPTANCE", "COMPLETE")
FINANCIAL_PREFIXES = ("expenses_", "loans_", "investments_", "family_", "mobility_", "users_", "budgets_")
REHEARSAL_REQUIRED = release.TECHNICAL + ("operators", "local_backup")
BEFORE_PRODUCTION = release.TECHNICAL + tuple(name for name in release.OPERATIONAL if name != "real_account")


def core_binding(manifest, target, runtime, environment):
    return {"release_id": manifest["release_id"], "candidate_sha": manifest["candidate_sha"],
            "production_baseline_sha": manifest["production_baseline_sha"],
            "target_repo": str(Path(target).resolve()), "runtime": str(Path(runtime).resolve()),
            "environment": environment}


def binding(manifest, target, runtime, environment):
    result = core_binding(manifest, target, runtime, environment)
    evidence = {"gates": manifest["gates"], "policy": manifest.get("change_policy", {}), "waivers": manifest.get("waivers", [])}
    result["gate_evidence_sha256"] = hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()
    result["backup_archive_sha256"] = manifest.get("backup", {}).get("archive_sha256")
    return result


def authorization(path, manifest, target, runtime, environment):
    if not path:
        raise release.GateError("explicit_deployment_authorization_required")
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    expected = binding(manifest, target, runtime, environment)
    required = {"stop_writers", "backup", "promote", "restart"}
    if (document.get("decision") != "YES" or document.get("binding") != expected
            or not required <= set(document.get("actions", []))
            or not all(isinstance(document.get(key), str) and document[key].strip()
                       for key in ("authorized_by", "authorization_evidence"))):
        raise release.GateError("deployment_authorization_scope_mismatch")
    expiry = datetime.fromisoformat(document.get("expires_utc", ""))
    remaining = expiry.timestamp() - datetime.now(timezone.utc).timestamp()
    if expiry.tzinfo is None or not 0 < remaining <= 86400:
        raise release.GateError("deployment_authorization_expired_or_unbounded")
    if environment == "rehearsal":
        marker = Path(runtime) / ".alfred-release-rehearsal.json"
        if not marker.is_file() or json.loads(marker.read_text()) != core_binding(manifest, target, runtime, environment):
            raise release.GateError("rehearsal_sandbox_binding_missing")
    return document


def canonical_snapshot(path):
    # Signing in changes last_login; income, ownership, consent and all financial columns remain covered.
    return {table: record for table, record in recovery.database_snapshot(path, {"users_user": ("last_login",)}).items()
            if (table.startswith(FINANCIAL_PREFIXES) or table == "django_migrations")
            and table != 'mobility_travelproviderrequest'}  # Expiring telemetry stays in full recovery snapshots.


class NativeOperator:
    def __init__(self, target, runtime, output, port):
        self.target, self.runtime, self.output = map(Path, (target, runtime, output))
        self.port = port
        if not 1024 <= port <= 65534:
            raise release.GateError("invalid_native_port")
        config = self.runtime / "config/native.env"
        if not config.is_file():
            raise release.GateError("existing_native_secret_file_required")
        for line in config.read_text(encoding="utf-8-sig").splitlines():
            name, separator, value = line.removeprefix("export ").partition("=")
            if separator and name.strip() in ("ALFRED_MEMORY_OPENAI_AUTHORIZED", "ALFRED_MEMORY_CLOUD_AUTHORIZED",
                                              "ALFRED_MEMORY_SYNC_PROVIDER", "ALFRED_MEMORY_SYNC_MOCK_DIR"):
                value = value.strip().strip("\"'").lower()
                allowed_value = (value in ("", "false", "0", "no", "off") if name.strip().endswith("AUTHORIZED") else value == "")
                if not allowed_value:
                    raise release.GateError("external_provider_config_must_be_disabled")
        # Preserve the existing native secret/configuration. Never inject a test signing key.
        allowed = {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "USERPROFILE",
                   "LOCALAPPDATA", "APPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMDATA", "HOME"}
        self.env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
        self.env.update(ALFRED_DATA_DIR=str(self.runtime), ALFRED_LOCAL_RUNTIME="true",
                        ALFRED_AUTO_TRAIN_ON_STARTUP="false", DJANGO_SETTINGS_MODULE="alfred_ai.native_settings",
                        ALFRED_TASK_BACKEND="huey",
                        ALFRED_MEMORY_OPENAI_AUTHORIZED="false", ALFRED_MEMORY_CLOUD_AUTHORIZED="false",
                        ALFRED_MEMORY_SYNC_PROVIDER="", ALFRED_MEMORY_SYNC_MOCK_DIR="", PYTHONDONTWRITEBYTECODE="1")

    def command(self, name, arguments):
        result = subprocess.run([sys.executable, *arguments], cwd=self.target, env=self.env,
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
        self.output.mkdir(parents=True, exist_ok=True)
        (self.output / (name + ".log")).write_text(safe_log(result.stdout + result.stderr), encoding="utf-8")
        if result.returncode:
            raise release.GateError("native_" + name + "_failed")
        return result.stdout

    def migration_check(self):
        self.command("migration_check", [str(self.target / "manage.py"), "migrate", "--check", "--noinput"])

    def stop(self):
        self.command("stop", [str(self.target / "alfred_native.py"), "stop", "--data-dir", str(self.runtime)])

    def start(self):
        self.migration_check()  # The launcher must have nothing to apply before startup.
        self.command("start", [str(self.target / "alfred_native.py"), "start", "--data-dir", str(self.runtime),
                               "--port", str(self.port), "--no-browser"])

    def health(self):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://127.0.0.1:{self.port}/health/native/", timeout=10) as response:
            payload = json.loads(response.read(8192))
        if payload.get("status") != "ok":
            raise release.GateError("native_worker_health_failed")
        state = json.loads((self.runtime / "artifacts/native/runtime.json").read_text())
        if payload.get("instance") != state.get("instance"):
            raise release.GateError("native_health_instance_mismatch")
        self.env["ALFRED_NATIVE_INSTANCE"] = state["instance"]
        code = ("import json; from alfred_ai.services.native_readiness import native_readiness_snapshot; "
                "s=native_readiness_snapshot(); print(json.dumps({'ready':s['ready_check_count']==s['total_check_count']}))")
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            output = self.command("readiness", [str(self.target / "manage.py"), "shell", "-c", code])
            if json.loads(output.splitlines()[-1]).get("ready"):
                return
            time.sleep(1)
        raise release.GateError("native_scheduler_or_runtime_not_ready")

    def acceptance(self):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for path in ("/login/", "/static/js/intelligence.js", "/static/css/workspace.css"):
            with opener.open(f"http://127.0.0.1:{self.port}" + path, timeout=15) as response:
                if response.status != 200:
                    raise release.GateError("public_runtime_acceptance_failed")


def promote(candidate_repo, manifest, output, target, runtime, key_file=None, approval_file=None,
            execute=False, environment="rehearsal", port=8150, operator=None):
    target, runtime, output = map(recovery.no_links, (target, runtime, output))
    if environment not in ("rehearsal", "production") or target == Path(candidate_repo).resolve():
        raise release.GateError("invalid_promotion_target")
    state = manifest["deployment"]
    if execute and state.get("started"):
        if (state.get("target_repo") != str(target) or state.get("runtime") != str(runtime)
                or state.get("environment") != environment):
            raise release.GateError("deployment_checkpoint_target_mismatch")
        if state.get("stage") == "COMPLETE" and release.git(target, "rev-parse", "HEAD") == manifest["candidate_sha"]:
            return state  # Idempotent completion never stops or reapplies a release.
        raise release.GateError("interrupted_promotion_requires_review")
    release.source_checks(candidate_repo, manifest, target_repo=target)
    if environment == "production":
        release.remote_check(candidate_repo, manifest)
    state.update(stage="PREFLIGHT", environment=environment, plan=list(STAGES), execute=bool(execute),
                 target_repo=str(target), runtime=str(runtime))
    required = REHEARSAL_REQUIRED if environment == "rehearsal" else BEFORE_PRODUCTION
    readiness = release.decision(manifest, required)
    state["readiness"] = readiness
    if not execute:
        state["status"] = "BLOCKED" if readiness["status"] != "PASS" else "NOT_RUN"
        state["code"] = "dry_run_no_production_mutation"
        release.report(manifest, output)
        return state
    if readiness["status"] != "PASS":
        raise release.GateError("required_promotion_gates_unsatisfied")
    if not key_file or not manifest.get("backup", {}).get("directory"):
        raise release.GateError("verified_local_backup_and_existing_key_required")
    if manifest["backup"].get("runtime_reference") != recovery.runtime_reference(runtime):
        raise release.GateError("approved_backup_runtime_mismatch")
    # Bind to evidence AFTER the target's operator-file recheck; no older waiver or YES is inherited.
    approved = authorization(approval_file, manifest, target, runtime, environment)
    operator_hashes = dict(manifest["gates"]["operators"]["evidence"]["sha256"])
    old_backup = Path(manifest["backup"]["directory"])
    if release.sha256(old_backup / "recovery.zip") != manifest["backup"]["archive_sha256"]:
        raise release.GateError("approved_backup_changed")
    ops = operator or NativeOperator(target, runtime, output, port)
    if operator is not None and environment != "rehearsal":
        raise release.GateError("test_operator_forbidden_for_production")
    manifest["approval"] = {"status": "PASS", "binding": approved["binding"],
                            "authorization_reference": hashlib.sha256(approved["authorization_evidence"].encode()).hexdigest()}

    def checkpoint(stage, status="PASS", code="stage_verified"):
        state.update(stage=stage, status=status, code=code)
        state.setdefault("history", []).append({"stage": stage, "status": status, "utc": release.now(), "code": code})
        release.report(manifest, output)

    checkpoint("BACKUP", code="existing_verified_archive_unchanged")
    checkpoint("APPROVAL", code="exact_release_and_environment_approved")
    state["started"] = True
    baseline = manifest["production_baseline_sha"]
    fresh_backup = None
    expected = None
    with InstanceLock(runtime, "promotion.lock"):
        try:
            checkpoint("STOP_WRITERS", "NOT_RUN", "shutdown_about_to_begin")
            ops.stop()
            checkpoint("STOP_WRITERS", code="graceful_shutdown_returned")
            fresh = old_backup.parent / (manifest["release_id"] + "-quiesced-" + uuid.uuid4().hex)
            receipt = recovery.create(runtime, fresh, key_file, manifest["release_id"], manifest["candidate_sha"], baseline, target)
            fresh_backup = fresh
            state["fresh_backup"] = {"directory": str(fresh), "archive_sha256": receipt["archive_sha256"]}
            expected = canonical_snapshot(fresh / "independent-local-restore/db.sqlite3")
            checkpoint("VERIFY", code="fresh_quiesced_backup_and_restore_verified")
            ops.migration_check()
            if manifest["gates"]["migrations"]["evidence"].get("paths"):
                raise release.GateError("schema_change_requires_separate_migration_workflow")
            release.source_checks(candidate_repo, manifest, target_repo=target)
            if manifest["gates"]["operators"]["evidence"]["sha256"] != operator_hashes:
                raise release.GateError("operator_file_changed_after_approval")
            for path, digest in operator_hashes.items():
                if release.sha256(target / path) != digest:
                    raise release.GateError("operator_file_changed_before_promotion")
            checkpoint("PROMOTE", "NOT_RUN", "fast_forward_about_to_begin")
            release.git(target, "merge", "--ff-only", manifest["candidate_sha"])
            if release.git(target, "rev-parse", "HEAD") != manifest["candidate_sha"]:
                raise release.GateError("promoted_head_mismatch")
            checkpoint("PROMOTE", code="exact_fast_forward_verified")
            checkpoint("RESTART", "NOT_RUN", "restart_about_to_begin")
            ops.start()
            ops.health()
            ops.acceptance()
            snapshot = fresh / "after-start.sqlite3"
            recovery.sqlite_copy(runtime / "db.sqlite3", snapshot)
            if canonical_snapshot(snapshot) != expected:
                raise release.GateError("post_start_financial_difference")
            retained = json.loads((fresh / "independent-local-restore/manifest.json").read_text())
            for record in retained["files"]:
                if record["backup_path"].startswith(("config/", "media/")):
                    if release.sha256(runtime / record["backup_path"]) != record["sha256"]:
                        raise release.GateError("durable_file_changed_after_start")
            for path, digest in operator_hashes.items():
                if release.sha256(target / path) != digest:
                    raise release.GateError("operator_file_changed_after_promotion")
            checkpoint("RESTART", code="native_runtime_and_reconciliation_verified")
            checkpoint("ACCEPTANCE", code="native_worker_scheduler_financial_and_source_verified")
            if environment == "production" and release.decision(manifest, release.TECHNICAL + release.OPERATIONAL)["status"] != "PASS":
                checkpoint("ACCEPTANCE", "BLOCKED", "real_account_acceptance_pending")
            else:
                checkpoint("COMPLETE", code="rehearsal_complete" if environment == "rehearsal" else "release_complete")
        except BaseException as exc:
            code = str(exc) if isinstance(exc, release.GateError) else "promotion_interrupted" if isinstance(exc, KeyboardInterrupt) else "promotion_failed"
            state["exception_type"] = type(exc).__name__
            checkpoint(state["stage"], "FAIL", code)
            state["rollback"] = "NOT_AUTHORIZED"
            if "rollback_source" in approved["actions"]:
                try:
                    ops.stop()
                    evidence = old_backup.parent / (manifest["release_id"] + "-failure-" + uuid.uuid4().hex)
                    state["failure_source_head"] = release.git(target, "rev-parse", "HEAD")
                    recovery.create(runtime, evidence, key_file, manifest["release_id"], manifest["candidate_sha"], baseline, source_repo=None)
                    state["failure_backup"] = str(evidence)
                    current = evidence / "independent-local-restore/db.sqlite3"
                    if expected is None or canonical_snapshot(current) != expected:
                        raise release.GateError("data_or_schema_difference_manual_recovery_required")
                    head = release.git(target, "rev-parse", "HEAD")
                    if head not in (baseline, manifest["candidate_sha"]):
                        raise release.GateError("rollback_source_head_unexpected")
                    if head != baseline:
                        release.git(target, "switch", "--detach", baseline)
                    ops.migration_check()
                    if "restart_previous" in approved["actions"]:
                        ops.start()
                        ops.health()
                    state["rollback"] = "PASS"
                except BaseException as rollback_error:
                    state["rollback"] = "BLOCKED"
                    state["rollback_error"] = (str(rollback_error) if isinstance(rollback_error, release.GateError)
                                                else "rollback_failed")
                    try:
                        ops.stop()
                    except BaseException:
                        state["shutdown_after_failed_rollback"] = "BLOCKED"
            release.report(manifest, output)
            raise release.GateError(code) from None
    return state
