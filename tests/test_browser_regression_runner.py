import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import TestCase

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
        )

        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["runner_return_code"], 0)
        self.assertEqual(summary["skipped_count"], 0)
        self.assertEqual(summary["tests_run_count"], 2)
        self.assertTrue(summary["driver_backed_success"])

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
        )

        self.assertEqual(summary["status"], "skipped")
        self.assertEqual(summary["runner_return_code"], 2)
        self.assertEqual(summary["skipped_count"], 2)
        self.assertFalse(summary["driver_backed_success"])

    def test_summary_file_is_written_to_browser_artifact_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_dir = Path(tmpdir)
            summary_path = run_browser_regressions.write_summary(
                artifact_dir,
                {"status": "passed", "skipped_count": 0},
            )

            self.assertEqual(summary_path.name, run_browser_regressions.SUMMARY_FILENAME)
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "passed")
            self.assertEqual(payload["skipped_count"], 0)
