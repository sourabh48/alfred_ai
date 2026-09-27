"""Simulated timing tests; these are not evidence of an actual overnight run."""
from contextlib import ExitStack
from datetime import datetime
import io
import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from scripts import complete_native_observation as supervisor
from scripts import observe_native_runtime as observer


class ObservationLoopTests(unittest.TestCase):
    def run_window(self, *, gap=False, failed=False, cancel=False):
        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            data = Path(folder)
            report = data / "attempt.json"
            stop = data / "stop.requested"
            if cancel:
                stop.touch()
            clock = [1000.0]

            def sleep(seconds):
                clock[0] += 241 if gap else seconds

            jobs = [{"task": "tasks." + name, "outcome": "complete", "summary": {}}
                    for name in observer.REQUIRED]
            if failed:
                jobs[0]["summary"] = {"failed": 1}
            stack.enter_context(patch.object(observer.time, "time", side_effect=lambda: clock[0]))
            stack.enter_context(patch.object(observer.time, "monotonic", side_effect=lambda: clock[0]))
            stack.enter_context(patch.object(observer.time, "sleep", side_effect=sleep))
            stack.enter_context(patch.object(observer, "read_state", return_value={"instance": "test"}))
            stack.enter_context(patch.object(observer, "snapshot", return_value=(jobs, None)))
            opener = stack.enter_context(patch.object(observer.urllib.request, "build_opener"))
            opener.return_value.open.side_effect = lambda *a, **k: io.StringIO(
                '{"status": "ok", "instance": "test"}')
            code = observer.run_observation(data, 0.05, 60, report,
                                            restart_on_gap=True, stop_file=stop)
            return code, json.loads(report.read_text())

    def test_continuous_healthy_window_with_all_cycles_passes(self):
        code, report = self.run_window()
        self.assertEqual(code, 0)
        self.assertTrue(report["passed"])
        self.assertEqual(len(report["samples"]), 4)

    def test_gap_requires_fresh_window_even_if_duration_and_jobs_are_met(self):
        code, report = self.run_window(gap=True)
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "interrupted")
        self.assertFalse(report["passed"])

    def test_completed_business_failure_does_not_pass(self):
        code, report = self.run_window(failed=True)
        self.assertEqual(code, 1)
        self.assertEqual(report["failed_job_count"], 1)
        self.assertFalse(report["passed"])

    def test_cancellation_is_recorded_without_passing(self):
        code, report = self.run_window(cancel=True)
        self.assertEqual(code, 3)
        self.assertEqual(report["status"], "cancelled")
        self.assertFalse(report["passed"])


class ObservationSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.data = Path(self.temporary.name)
        self.evidence = self.data / "evidence"
        self.evidence.mkdir()
        self.executable = self.data / "ALFRED.exe"

    def save_attempt(self, status, passed=False, timestamp=None):
        report = self.evidence / "previous.json"
        supervisor.write_json(report, {"status": status, "passed": passed,
                              "samples": [{"time": time.time() if timestamp is None else timestamp}]})
        supervisor.write_json(self.evidence / "current.json", {
            "report": str(report), "attempts": [str(report)], "status": status, "passed": passed})
        return report

    def test_next_daily_cycles_are_covered_even_after_training(self):
        cases = (("2026-09-27T13:00:00+00:00", 14.5),
                 ("2026-09-27T03:01:00+00:00", 24 + 29 / 60),
                 ("2026-09-27T23:00:00+00:00", 10),
                 ("2026-09-27T02:30:00+00:00", 24.25))
        for value, hours in cases:
            with self.subTest(value=value):
                self.assertAlmostEqual(supervisor.required_hours(datetime.fromisoformat(value)), hours)

    def test_already_passed_and_completed_failed_runs_do_not_launch_again(self):
        for passed, expected in ((True, 0), (False, 1)):
            self.save_attempt("finished", passed)
            with patch.object(supervisor.subprocess, "run") as launch:
                self.assertEqual(supervisor.supervise(self.data, self.executable, self.evidence), expected)
                launch.assert_not_called()

    def test_interrupted_attempts_are_preserved_and_new_windows_are_distinct(self):
        old = self.save_attempt("observing")
        original = old.read_bytes()
        outcomes = iter((("interrupted", False, 2), ("finished", True, 0)))

        def observe(data, hours, interval, report, **kwargs):
            status, passed, code = next(outcomes)
            self.assertTrue(kwargs["restart_on_gap"])
            self.assertEqual(supervisor.load_manifest(self.evidence)["previous_attempt"]["status"], "interrupted")
            supervisor.write_json(report, {"status": status, "passed": passed,
                                          "samples": [{"time": time.time()}]})
            return code

        with patch.object(supervisor.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)), \
             patch.object(supervisor, "run_observation", side_effect=observe):
            self.assertEqual(supervisor.supervise(self.data, self.executable, self.evidence), 0)
        manifest = supervisor.load_manifest(self.evidence)
        self.assertEqual(len(set(manifest["attempts"])), 3)
        self.assertTrue(manifest["passed"])
        self.assertEqual(manifest["previous_attempt"]["status"], "interrupted")
        self.assertEqual(old.read_bytes(), original)
        self.assertTrue(all(Path(item).is_file() for item in manifest["attempts"]))

    def test_failed_business_run_is_retained_without_automatic_retry(self):
        def observe(data, hours, interval, report, **kwargs):
            supervisor.write_json(report, {"status": "finished", "passed": False})
            return 1

        with patch.object(supervisor.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as launch, \
             patch.object(supervisor, "run_observation", side_effect=observe) as observe_mock:
            self.assertEqual(supervisor.supervise(self.data, self.executable, self.evidence), 1)
            self.assertEqual(observe_mock.call_count, 1)
            self.assertEqual(launch.call_count, 1)

    def test_cancel_marker_prevents_starting_the_app(self):
        (self.evidence / "stop.requested").touch()
        with patch.object(supervisor.subprocess, "run") as launch:
            self.assertEqual(supervisor.supervise(self.data, self.executable, self.evidence), 3)
            launch.assert_not_called()

    def test_missing_report_is_interrupted_and_outside_report_is_rejected(self):
        supervisor.write_json(self.evidence / "current.json", {"report": str(self.evidence / "missing.json")})
        self.assertEqual(supervisor.latest_status(self.evidence)["status"], "interrupted")
        supervisor.write_json(self.evidence / "current.json", {"report": str(self.data / "outside.json")})
        with self.assertRaises(ValueError):
            supervisor.latest_status(self.evidence)


if __name__ == "__main__":
    unittest.main()
