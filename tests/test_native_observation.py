"""Business failures must not become a successful overnight proof."""
import unittest

from scripts.observe_native_runtime import job_failed, observation_status


class NativeObservationTests(unittest.TestCase):
    def test_stale_observer_cannot_still_be_reported_as_running(self):
        report = {"status": "observing", "passed": False, "samples": [{"time": 1000}], "jobs": []}
        self.assertEqual(observation_status(report, now=1180)["status"], "observing")
        result = observation_status(report, now=1181)
        self.assertEqual(result["status"], "interrupted")
        self.assertFalse(result["passed"])
        self.assertEqual(report["status"], "observing")  # Preserve historical evidence.

    def test_finished_pass_is_not_expired_by_status_check(self):
        result = observation_status({"status": "finished", "passed": True, "samples": [{"time": 1000}]}, now=90000)
        self.assertEqual(result["status"], "finished")
        self.assertTrue(result["passed"])

    def test_completed_refresh_with_failed_sources_is_a_failure(self):
        self.assertTrue(job_failed({"outcome": "complete", "summary": {
            "processed": 33, "refreshed": 32, "failed": 1,
        }}))

    def test_failed_training_counts_and_status_are_failures(self):
        for summary in ({"failed_count": 1}, {"failed_models": 2}, {"status": "failed"}):
            with self.subTest(summary=summary):
                self.assertTrue(job_failed({"outcome": "complete", "summary": summary}))

    def test_ineligible_training_is_a_valid_completed_cycle(self):
        self.assertFalse(job_failed({"outcome": "complete", "summary": {
            "status": "skipped", "skipped_count": 7, "failed_count": 0,
        }}))
        self.assertFalse(job_failed({"outcome": "complete", "summary": {"failed": 0}}))

    def test_worker_error_and_interrupted_review_are_failures(self):
        for outcome in ("error", "interrupted_needs_review"):
            with self.subTest(outcome=outcome):
                self.assertTrue(job_failed({"outcome": outcome, "summary": {}}))
