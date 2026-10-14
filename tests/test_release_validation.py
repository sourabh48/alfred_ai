"""Pinned source scanning and runner isolation; all data and repositories are synthetic."""
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import release_gate as release
from scripts import release_validation as validation
from tests.test_release_gate import ReleaseRepositoryFixture


class ReleasePrivacyTests(ReleaseRepositoryFixture, unittest.TestCase):
    def test_clean_source_passes_without_loading_runtime_configuration(self):
        result = validation.privacy(self.repo, self.manifest)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["evidence"]["history_commits"], 1)

    def test_private_database_and_memory_payload_paths_are_blocked(self):
        self.commit("artifacts/private-memory-v2/index.sqlite3", "synthetic private memory")
        self.manifest["candidate_sha"] = self.git("rev-parse", "HEAD")
        release.source_checks(self.repo, self.manifest)
        result = validation.privacy(self.repo, self.manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertNotIn("synthetic private memory", json.dumps(result))
        self.assertNotIn("index.sqlite3", json.dumps(result))
        self.assertNotIn("index.sqlite3", json.dumps(self.manifest))

    def test_secret_removed_in_later_commit_still_blocks_history_push(self):
        secret = "sk-proj-" + "a" * 40
        self.commit("settings.py", "credential = '" + secret + "'")
        self.commit("settings.py", "# removed synthetic credential")
        self.manifest["candidate_sha"] = self.git("rev-parse", "HEAD")
        result = validation.privacy(self.repo, self.manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertNotIn(secret, json.dumps(result))

    def test_test_filename_is_not_a_blanket_credential_exemption(self):
        self.commit("tests/memory_s3_fixture.py", "token='" + "sk-proj-" + "b" * 40 + "'")
        self.manifest["candidate_sha"] = self.git("rev-parse", "HEAD")
        self.assertEqual(validation.privacy(self.repo, self.manifest)["status"], "FAIL")

    def test_exact_public_examples_are_classified_without_a_blanket_test_exemption(self):
        for name in ("memory_s3_fixture.py", "test_memory_reasoning.py"):
            self.commit("tests/" + name, (Path(__file__).parent / name).read_text(encoding="utf-8"))
        self.manifest["candidate_sha"] = self.git("rev-parse", "HEAD")
        result = validation.privacy(self.repo, self.manifest)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["evidence"]["reviewed_synthetic_identifiers"], 2)

    def test_profile_environment_and_logs_never_include_operator_secrets(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic-secret", "AWS_SECRET_ACCESS_KEY": "synthetic-secret",
                    "ALFRED_DATA_DIR": "synthetic-production", "ALFRED_MEMORY_CLOUD_AUTHORIZED": "true"}):
            env = validation.environment(self.root / "sandbox")
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", env)
        self.assertEqual(env["ALFRED_MEMORY_CLOUD_AUTHORIZED"], "false")
        self.assertEqual(env["ALFRED_MEMORY_OPENAI_AUTHORIZED"], "false")
        self.assertEqual(env["ALFRED_MEMORY_SYNC_PROVIDER"], "")
        self.assertEqual(env["ALFRED_MEMORY_SYNC_MOCK_DIR"], "")
        self.assertNotIn("synthetic-production", json.dumps(env))
        raw = "FAIL: test_example (tests.synthetic.Case)\nC:\\private\\account.pdf amount=123456\nOCR synthetic-secret\nRan 2 tests in 1.2s\nFAILED (failures=1)"
        safe = validation.safe_log(raw)
        self.assertIn("test_example", safe)
        self.assertIn("Ran 2 tests", safe)
        self.assertNotIn("account.pdf", safe)
        self.assertNotIn("123456", safe)
        self.assertNotIn("synthetic-secret", safe)

    def test_runner_counts_and_timeout_are_explicit(self):
        completed = subprocess.CompletedProcess([], 1, "Ran 3 tests in 1.2s\nFAILED (failures=1)", "synthetic-secret")
        with patch.object(validation.subprocess, "run", return_value=completed):
            result = validation.run(self.repo, ["unused"], {}, self.root, "test", 1)
        self.assertEqual((result["status"], result["tests"]), ("FAIL", 3))
        self.assertNotIn("synthetic-secret", (self.root / "test.log").read_text())
        with patch.object(validation.subprocess, "run", side_effect=subprocess.TimeoutExpired("unused", 1)):
            result = validation.run(self.repo, ["unused"], {}, self.root, "timeout", 1)
        self.assertEqual(result["code"], "suite_timeout")

    def test_targeted_tests_do_not_satisfy_full_backend_gate(self):
        result = {"status": "PASS", "code": "suite_exit", "tests": 3, "skips": 0,
                  "log": "synthetic.log", "log_sha256": "a" * 64}
        with patch.object(validation, "run", return_value=result):
            validation.validate(self.repo, self.manifest, self.root / "output", "targeted", ["tests.synthetic"])
        self.assertEqual(self.manifest["gates"]["backend"]["status"], "NOT_RUN")
        self.assertEqual(self.manifest["targeted_runs"][-1]["tests"], 3)

    def test_failed_gate_can_be_explicitly_rerun_without_losing_prior_result(self):
        release.gate(self.manifest, "backend", "FAIL", "synthetic_prior_failure")
        result = {"status": "PASS", "code": "suite_exit", "tests": 3, "skips": 0,
                  "log": "synthetic.log", "log_sha256": "a" * 64}
        with patch.object(validation, "run", return_value=result):
            validation.validate(self.repo, self.manifest, self.root / "retry", "backend")
        self.assertEqual(self.manifest["gates"]["backend"]["status"], "PASS")
        self.assertEqual(self.manifest["validation_history"][-1]["previous"]["backend"]["status"], "FAIL")

    def test_skipped_or_zero_backend_tests_do_not_pass(self):
        for count, skips in ((0, 0), (3, 1)):
            result = {"status": "PASS", "code": "suite_exit", "tests": count, "skips": skips,
                      "log": "synthetic.log", "log_sha256": "a" * 64}
            with self.subTest(count=count, skips=skips), patch.object(validation, "run", return_value=result):
                validation.validate(self.repo, self.manifest, self.root / ("run-" + str(count)), "backend")
                self.assertEqual(self.manifest["gates"]["backend"]["status"], "FAIL")
                self.manifest = release.new_manifest("synthetic-1", self.candidate, self.baseline)

    def test_absent_package_is_not_run_instead_of_pass(self):
        validation.packaged(self.repo, self.manifest, self.root, {}, None, None)
        self.assertEqual(self.manifest["gates"]["packaged"]["status"], "NOT_RUN")

    def test_packaged_source_and_executable_identity_are_required_before_execution(self):
        manifest = self.root / "package.json"
        manifest.write_text(json.dumps({"source_commit": self.baseline, "source_dirty": False}))
        with self.assertRaisesRegex(release.GateError, "packaged_source_identity_mismatch"):
            validation.packaged(self.repo, self.manifest, self.root, {}, self.root, manifest)
        (self.root / "ALFRED.exe").write_bytes(b"synthetic executable")
        manifest.write_text(json.dumps({"source_commit": self.candidate, "source_dirty": False, "artifacts": {}}))
        with self.assertRaisesRegex(release.GateError, "packaged_executable_hash_mismatch"):
            validation.packaged(self.repo, self.manifest, self.root, {}, self.root, manifest)


if __name__ == "__main__":
    unittest.main()
