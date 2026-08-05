import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from scripts import run_browser_regressions


class BrowserRegressionRunnerTests(TestCase):
    def test_summary_records_driver_backed_success_when_required_suite_runs_without_skips(self):
        summary = run_browser_regressions.build_run_summary(
            command=["python", "manage.py", "test", "tests.test_document_review_browser"],
            output="Found 2 test(s).\nRan 2 tests in 12.34s\nOK\n",
            return_code=0,
            require_browser=True,
            browser="Chrome",
            artifact_dir=Path("artifacts/browser"),
            test_labels=("tests.test_document_review_browser",),
            started_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
            finished_at=datetime(2026, 8, 5, 0, 0, 13, tzinfo=timezone.utc),
            duration_seconds=12.7,
            run_browser_tests_env="true",
            run_context="local",
            proof_label="local-chrome",
            github_actions={},
        )

        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["runner_return_code"], 0)
        self.assertEqual(summary["skipped_count"], 0)
        self.assertEqual(summary["tests_run_count"], 2)
        self.assertTrue(summary["driver_backed_success"])
        self.assertEqual(summary["run_context"], "local")
        self.assertEqual(summary["proof_label"], "local-chrome")
        self.assertEqual(summary["artifact_contract"]["labeled_summary_filename"], "browser_regression_summary.local-chrome.json")
        self.assertEqual(summary["github_actions"], {})

    def test_required_browser_summary_fails_when_selenium_suite_is_skipped(self):
        summary = run_browser_regressions.build_run_summary(
            command=["python", "manage.py", "test", "tests.test_document_review_browser"],
            output="Found 2 test(s).\nRan 2 tests in 0.01s\nOK (skipped=2)\n",
            return_code=0,
            require_browser=True,
            browser="Chrome",
            artifact_dir=Path("artifacts/browser"),
            test_labels=("tests.test_document_review_browser",),
            started_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
            finished_at=datetime(2026, 8, 5, 0, 0, 1, tzinfo=timezone.utc),
            duration_seconds=0.5,
            run_browser_tests_env="true",
            run_context="ci",
            proof_label="ci-chrome",
        )

        self.assertEqual(summary["status"], "skipped")
        self.assertEqual(summary["runner_return_code"], 2)
        self.assertEqual(summary["skipped_count"], 2)
        self.assertFalse(summary["driver_backed_success"])
        self.assertEqual(summary["run_context"], "ci")

    def test_ci_summary_records_github_actions_metadata(self):
        github_actions = {
            "enabled": True,
            "event_name": "pull_request",
            "workflow": "Browser Regression",
            "run_id": "987654321",
            "run_attempt": "1",
            "repository": "sourabh48/alfred_ai",
            "sha": "f12d062614f87fbc9be411245d28563e60ef8193",
            "ref": "refs/pull/1/merge",
            "ref_name": "1/merge",
            "head_ref": "agent/browser-regression-maturity-gate",
            "base_ref": "master",
            "server_url": "https://github.com",
            "run_url": "https://github.com/sourabh48/alfred_ai/actions/runs/987654321",
        }
        summary = run_browser_regressions.build_run_summary(
            command=["python", "manage.py", "test", "tests.test_document_review_browser"],
            output="Found 2 test(s).\nRan 2 tests in 12.34s\nOK\n",
            return_code=0,
            require_browser=True,
            browser="Chrome",
            artifact_dir=Path("artifacts/browser"),
            test_labels=("tests.test_document_review_browser",),
            started_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
            finished_at=datetime(2026, 8, 5, 0, 0, 13, tzinfo=timezone.utc),
            duration_seconds=12.7,
            run_browser_tests_env="true",
            run_context="ci",
            proof_label="ci-chrome",
            github_actions=github_actions,
        )

        self.assertEqual(summary["status"], "passed")
        self.assertTrue(summary["driver_backed_success"])
        self.assertTrue(summary["github_actions"]["enabled"])
        self.assertEqual(summary["github_actions"]["event_name"], "pull_request")
        self.assertEqual(summary["github_actions"]["run_url"], "https://github.com/sourabh48/alfred_ai/actions/runs/987654321")

    def test_github_actions_metadata_builds_run_url_from_environment(self):
        with patch.dict(
            os.environ,
            {
                "GITHUB_ACTIONS": "true",
                "GITHUB_EVENT_NAME": "workflow_dispatch",
                "GITHUB_WORKFLOW": "Browser Regression",
                "GITHUB_RUN_ID": "123",
                "GITHUB_RUN_ATTEMPT": "2",
                "GITHUB_REPOSITORY": "sourabh48/alfred_ai",
                "GITHUB_SHA": "abc123",
                "GITHUB_REF": "refs/heads/agent/browser-regression-maturity-gate",
                "GITHUB_REF_NAME": "agent/browser-regression-maturity-gate",
                "GITHUB_SERVER_URL": "https://github.com",
            },
            clear=False,
        ):
            metadata = run_browser_regressions.github_actions_metadata()

        self.assertTrue(metadata["enabled"])
        self.assertEqual(metadata["event_name"], "workflow_dispatch")
        self.assertEqual(metadata["workflow"], "Browser Regression")
        self.assertEqual(metadata["run_id"], "123")
        self.assertEqual(metadata["run_url"], "https://github.com/sourabh48/alfred_ai/actions/runs/123")

    def test_summary_file_is_written_to_browser_artifact_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_dir = Path(tmpdir)
            summary_path = run_browser_regressions.write_summary(
                artifact_dir,
                {"status": "passed", "skipped_count": 0, "proof_label": "ci-chrome"},
            )

            self.assertEqual(summary_path.name, run_browser_regressions.SUMMARY_FILENAME)
            self.assertTrue((artifact_dir / "browser_regression_summary.ci-chrome.json").exists())
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "passed")
            self.assertEqual(payload["skipped_count"], 0)

    def test_ci_summary_contract_names_failure_artifacts_uploaded_from_same_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_dir = Path(tmpdir)
            for name in (
                "failed-test.png",
                "failed-test.html",
                "failed-test.browser.log",
                "failed-test.json",
            ):
                (artifact_dir / name).write_text("artifact", encoding="utf-8")

            summary = run_browser_regressions.build_run_summary(
                command=["python", "manage.py", "test", "tests.test_document_review_browser"],
                output="Found 2 test(s).\nRan 2 tests in 12.34s\nFAILED (failures=1)\n",
                return_code=1,
                require_browser=True,
                browser="Chrome",
                artifact_dir=artifact_dir,
                test_labels=("tests.test_document_review_browser",),
                started_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
                finished_at=datetime(2026, 8, 5, 0, 0, 13, tzinfo=timezone.utc),
                duration_seconds=12.7,
                run_browser_tests_env="true",
                run_context="ci",
                proof_label="ci-chrome",
            )

            self.assertEqual(summary["status"], "failed")
            self.assertEqual(summary["runner_return_code"], 1)
            self.assertEqual(summary["artifact_contract"]["summary_filename"], "browser_regression_summary.json")
            self.assertEqual(summary["artifact_contract"]["upload_path"], str(artifact_dir))
            for suffix in (".png", ".html", ".browser.log", ".json"):
                self.assertIn(suffix, summary["artifact_contract"]["failure_artifact_suffixes"])
            inventory_names = {item["file_name"] for item in summary["artifact_inventory"]}
            self.assertIn("failed-test.png", inventory_names)
            self.assertIn("failed-test.browser.log", inventory_names)
