"""Real Git/SQLite/crypto promotion rehearsal; native actions are explicit test doubles."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
from contextlib import closing
import unittest

from cryptography.fernet import Fernet
from scripts import release_gate as release
from scripts import release_promotion as promotion
from scripts import release_recovery as recovery
from tests.test_release_gate import ReleaseRepositoryFixture


class FakeNative:
    def __init__(self, fail=None, change_data=False):
        self.fail, self.change_data, self.calls = fail, change_data, []
        self.runtime = None

    def call(self, name):
        self.calls.append(name)
        if self.fail == name + "-interrupt":
            self.fail = None
            raise KeyboardInterrupt()
        if self.fail == name:
            self.fail = None
            raise release.GateError("synthetic_" + name + "_failure")

    def stop(self):
        self.call("stop")

    def migration_check(self):
        self.call("migration")

    def start(self):
        self.call("start")
        if self.change_data:
            with closing(sqlite3.connect(self.runtime / "db.sqlite3")) as db, db:
                db.execute("UPDATE expenses_expense SET amount=999")

    def health(self):
        self.call("health")

    def acceptance(self):
        self.call("acceptance")


class ReleasePromotionTests(ReleaseRepositoryFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.target = self.root / "target"
        release.git(self.root, "clone", "--quiet", str(self.repo), str(self.target))
        release.git(self.target, "switch", "--detach", self.baseline)
        self.runtime = self.root / "runtime"
        for path in ("config", "media", "artifacts/native"):
            (self.runtime / path).mkdir(parents=True, exist_ok=True)
        (self.runtime / "config/native.env").write_text("SYNTHETIC_ONLY=true")
        for name in ("db.sqlite3", "artifacts/native/jobs.sqlite3"):
            with closing(sqlite3.connect(self.runtime / name)) as db, db:
                db.execute("CREATE TABLE expenses_expense (id INTEGER PRIMARY KEY, amount NUMERIC, fingerprint TEXT)")
                db.execute("INSERT INTO expenses_expense VALUES (1,123.45,'synthetic-preserved')")
        self.key = self.root / "synthetic.key"
        self.key.write_bytes(Fernet.generate_key())
        self.output = self.root / "report"
        self.output.mkdir()
        self.ops = FakeNative()
        self.ops.runtime = self.runtime
        for name in release.TECHNICAL:
            release.gate(self.manifest, name, "PASS", "synthetic_test_evidence")
        release.source_checks(self.repo, self.manifest, target_repo=self.target)
        self.backup = self.root / "backup"
        self.receipt = recovery.create(self.runtime, self.backup, self.key,
            self.manifest["release_id"], self.candidate, self.baseline, self.target)
        release.gate(self.manifest, "local_backup", "PASS", "synthetic_local_restore")
        self.manifest["backup"] = {"directory": str(self.backup), "archive_sha256": self.receipt["archive_sha256"],
                                   "runtime_reference": self.receipt["runtime_reference"]}
        marker = promotion.core_binding(self.manifest, self.target, self.runtime, "rehearsal")
        (self.runtime / ".alfred-release-rehearsal.json").write_text(json.dumps(marker))
        self.approval = self.root / "synthetic-approval.json"
        self.approve()

    def approve(self, actions=None):
        self.approval.write_text(json.dumps({"decision": "YES", "authorized_by": "synthetic operator",
            "authorization_evidence": "Current task authorizes disposable M21 rehearsal only; never production",
            "binding": promotion.binding(self.manifest, self.target, self.runtime, "rehearsal"),
            "expires_utc": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
            "actions": actions or ["stop_writers", "backup", "promote", "restart", "rollback_source", "restart_previous"]}))

    def execute(self, **kwargs):
        return promotion.promote(self.repo, self.manifest, self.output, self.target, self.runtime,
            self.key, self.approval, operator=self.ops, execute=True, **kwargs)

    def test_default_dry_run_never_stops_promotes_or_decrypts(self):
        state = promotion.promote(self.repo, self.manifest, self.output, self.target, self.runtime)
        self.assertEqual(state["code"], "dry_run_no_production_mutation")
        self.assertEqual(release.git(self.target, "rev-parse", "HEAD"), self.baseline)
        self.assertFalse(self.ops.calls)

    def test_authorized_sandbox_fast_forwards_and_is_idempotent(self):
        before = recovery.database_snapshot(self.runtime / "db.sqlite3")
        state = self.execute()
        self.assertEqual(state["stage"], "COMPLETE")
        self.assertEqual(release.git(self.target, "rev-parse", "HEAD"), self.candidate)
        self.assertEqual(before, recovery.database_snapshot(self.runtime / "db.sqlite3"))
        self.assertTrue((self.backup / "recovery.zip").exists())
        calls = list(self.ops.calls)
        self.execute()
        self.assertEqual(calls, self.ops.calls)
        self.assertFalse(self.manifest.get("promotion", {}).get("ready"))

    def test_missing_authorization_never_stops_service(self):
        with self.assertRaisesRegex(release.GateError, "explicit_deployment_authorization_required"):
            promotion.promote(self.repo, self.manifest, self.output, self.target, self.runtime,
                              self.key, execute=True, operator=self.ops)
        self.assertFalse(self.ops.calls)

    def test_authorization_does_not_transfer_to_other_sha_or_production(self):
        document = json.loads(self.approval.read_text())
        document["binding"]["candidate_sha"] = "a" * 40
        self.approval.write_text(json.dumps(document))
        with self.assertRaisesRegex(release.GateError, "deployment_authorization_scope_mismatch"):
            self.execute()
        with self.assertRaises(release.GateError):
            self.execute(environment="production")
        self.assertFalse(self.ops.calls)

    def test_expired_authorization_and_missing_sandbox_marker_block(self):
        document = json.loads(self.approval.read_text())
        document["expires_utc"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        self.approval.write_text(json.dumps(document))
        with self.assertRaisesRegex(release.GateError, "deployment_authorization_expired"):
            self.execute()
        self.approve()
        (self.runtime / ".alfred-release-rehearsal.json").unlink()
        with self.assertRaisesRegex(release.GateError, "rehearsal_sandbox_binding_missing"):
            self.execute()
        self.assertFalse(self.ops.calls)

    def test_financial_gate_failure_cannot_be_bypassed_by_approval(self):
        release.gate(self.manifest, "financial", "FAIL", "synthetic_financial_difference")
        self.approve()
        with self.assertRaisesRegex(release.GateError, "required_promotion_gates_unsatisfied"):
            self.execute()
        self.assertFalse(self.ops.calls)

    def test_a_different_runtimes_backup_cannot_authorize_shutdown(self):
        self.manifest["backup"]["runtime_reference"] = "a" * 64
        self.approve()
        with self.assertRaisesRegex(release.GateError, "approved_backup_runtime_mismatch"):
            self.execute()
        self.assertFalse(self.ops.calls)

    def test_browser_ollama_privacy_and_backend_failures_block_promotion(self):
        for name in ("browser", "ollama", "privacy", "backend", "configuration", "local_backup"):
            with self.subTest(gate=name):
                previous = self.manifest["gates"][name]
                release.gate(self.manifest, name, "FAIL", "synthetic_failure_injection")
                self.approve()
                with self.assertRaisesRegex(release.GateError, "required_promotion_gates_unsatisfied"):
                    self.execute()
                self.assertFalse(self.ops.calls)
                self.manifest["gates"][name] = previous

    def test_failed_migration_check_never_promotes(self):
        self.ops.fail = "migration"
        with self.assertRaisesRegex(release.GateError, "synthetic_migration_failure"):
            self.execute()
        self.assertEqual(release.git(self.target, "rev-parse", "HEAD"), self.baseline)
        self.assertEqual(self.manifest["deployment"]["status"], "FAIL")

    def test_worker_or_browser_acceptance_failure_rolls_source_back_preserving_data(self):
        self.ops.fail = "health"
        before = recovery.database_snapshot(self.runtime / "db.sqlite3")
        with self.assertRaisesRegex(release.GateError, "synthetic_health_failure"):
            self.execute()
        self.assertEqual(release.git(self.target, "rev-parse", "HEAD"), self.baseline)
        self.assertEqual(self.manifest["deployment"]["rollback"], "PASS")
        self.assertEqual(before, recovery.database_snapshot(self.runtime / "db.sqlite3"))
        self.assertTrue(Path(self.manifest["deployment"]["failure_backup"]).is_dir())

    def test_browser_acceptance_failure_rolls_source_back(self):
        self.ops.fail = "acceptance"
        with self.assertRaisesRegex(release.GateError, "synthetic_acceptance_failure"):
            self.execute()
        self.assertEqual(self.manifest["deployment"]["rollback"], "PASS")
        self.assertEqual(release.git(self.target, "rev-parse", "HEAD"), self.baseline)

    def test_login_timestamp_is_expected_but_income_changes_are_not(self):
        with closing(sqlite3.connect(self.runtime / "db.sqlite3")) as db, db:
            db.execute("CREATE TABLE users_user (id INTEGER, monthly_income NUMERIC, last_login TEXT)")
            db.execute("INSERT INTO users_user VALUES (1,80000,NULL)")
        before = promotion.canonical_snapshot(self.runtime / "db.sqlite3")
        with closing(sqlite3.connect(self.runtime / "db.sqlite3")) as db, db:
            db.execute("UPDATE users_user SET last_login='2026-10-15'")
        self.assertEqual(before, promotion.canonical_snapshot(self.runtime / "db.sqlite3"))
        with closing(sqlite3.connect(self.runtime / "db.sqlite3")) as db, db:
            db.execute("UPDATE users_user SET monthly_income=999")
        self.assertNotEqual(before, promotion.canonical_snapshot(self.runtime / "db.sqlite3"))

    def test_unexplained_financial_writes_are_preserved_and_block_blind_data_rollback(self):
        self.ops.change_data = True
        with self.assertRaisesRegex(release.GateError, "post_start_financial_difference"):
            self.execute()
        self.assertEqual(self.manifest["deployment"]["rollback"], "BLOCKED")
        self.assertEqual(self.manifest["deployment"]["rollback_error"], "data_or_schema_difference_manual_recovery_required")
        with closing(sqlite3.connect(self.runtime / "db.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT amount FROM expenses_expense").fetchone()[0], 999)
        self.assertTrue(Path(self.manifest["deployment"]["failure_backup"]).is_dir())

    def test_interruption_is_checkpointed_and_never_automatically_resumed(self):
        self.manifest["deployment"].update(started=True, stage="PROMOTE", status="NOT_RUN",
            target_repo=str(self.target.resolve()), runtime=str(self.runtime.resolve()), environment="rehearsal")
        with self.assertRaisesRegex(release.GateError, "interrupted_promotion_requires_review"):
            self.execute()
        self.assertFalse(self.ops.calls)

    def test_checkpoint_from_another_target_never_resumes(self):
        self.manifest["deployment"].update(started=True, stage="COMPLETE", target_repo="another target")
        with self.assertRaisesRegex(release.GateError, "deployment_checkpoint_target_mismatch"):
            self.execute()
        self.assertFalse(self.ops.calls)

    def test_interrupt_after_fast_forward_keeps_evidence_and_recovers_source(self):
        self.ops.fail = "start-interrupt"
        with self.assertRaisesRegex(release.GateError, "promotion_interrupted"):
            self.execute()
        self.assertEqual(release.git(self.target, "rev-parse", "HEAD"), self.baseline)
        self.assertEqual(self.manifest["deployment"]["rollback"], "PASS")
        self.assertEqual(self.manifest["deployment"]["exception_type"], "KeyboardInterrupt")

    def test_rollback_failure_is_reported_and_does_not_claim_completion(self):
        def failed_health():
            raise release.GateError("synthetic_health_always_failed")
        self.ops.health = failed_health
        with self.assertRaisesRegex(release.GateError, "synthetic_health_always_failed"):
            self.execute()
        self.assertEqual(self.manifest["deployment"]["rollback"], "BLOCKED")
        self.assertEqual(self.manifest["deployment"]["status"], "FAIL")

    def test_native_operator_never_injects_new_signing_key_or_real_provider(self):
        native = promotion.NativeOperator(self.target, self.runtime, self.output, 8150)
        self.assertNotIn("DJANGO_SECRET_KEY", native.env)
        self.assertEqual(native.env["ALFRED_MEMORY_OPENAI_AUTHORIZED"], "false")
        self.assertEqual(native.env["ALFRED_MEMORY_CLOUD_AUTHORIZED"], "false")
        self.assertEqual(native.env["ALFRED_TASK_BACKEND"], "huey")
        (self.runtime / "config/native.env").write_text("ALFRED_MEMORY_OPENAI_AUTHORIZED=true")
        with self.assertRaisesRegex(release.GateError, "external_provider_config_must_be_disabled"):
            promotion.NativeOperator(self.target, self.runtime, self.output, 8150)


if __name__ == "__main__":
    unittest.main()
