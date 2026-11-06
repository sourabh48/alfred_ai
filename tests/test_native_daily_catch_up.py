"""Daily native jobs run again after their scheduled time passed while ALFRED was off."""
import time
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from alfred_ai import native_tasks as tasks


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                                       "LOCATION": "native-daily-catch-up"}})
class DailyCatchUpTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.jobs = {name: Mock(return_value={"status": "completed"}) for name in tasks.DAILY_JOBS}
        patcher = patch.dict(tasks.DAILY_JOBS, self.jobs)
        patcher.start()
        self.addCleanup(patcher.stop)

    def mark(self, name, kind, seconds_ago):
        cache.set(f"native:daily:{name}:{kind}", time.time() - seconds_ago, timeout=None)

    def calls(self):
        return {name for name, job in self.jobs.items() if job.called}

    def test_jobs_that_never_ran_are_caught_up_once(self):
        self.assertEqual(tasks.native_daily_catch_up.call_local(), {"status": "completed", "processed": 4})
        self.assertEqual(self.calls(), set(tasks.DAILY_JOBS))
        self.assertEqual(tasks.native_daily_catch_up.call_local()["processed"], 0)
        for job in self.jobs.values():
            job.assert_called_once_with()

    def test_only_missed_jobs_run(self):
        for name in tasks.DAILY_JOBS:
            self.mark(name, "success", 3600)
        self.mark("private-memory-cleanup", "success", 26 * 3600)
        self.mark("private-memory-cleanup", "attempt", 26 * 3600)
        tasks.native_daily_catch_up.call_local()
        self.assertEqual(self.calls(), {"private-memory-cleanup"})

    def test_failure_is_retried_after_an_hour_and_does_not_block_other_jobs(self):
        self.jobs["budget-publication-check"].side_effect = RuntimeError("offline")
        with self.assertLogs("alfred_ai.native_tasks", "WARNING"):
            self.assertEqual(tasks.native_daily_catch_up.call_local()["processed"], 3)
        self.assertIsNone(cache.get("native:daily:budget-publication-check:success"))
        tasks.native_daily_catch_up.call_local()
        self.assertEqual(self.jobs["budget-publication-check"].call_count, 1, "no retry within the hour")
        self.mark("budget-publication-check", "attempt", 3601)
        self.jobs["budget-publication-check"].side_effect = None
        self.assertEqual(tasks.native_daily_catch_up.call_local()["processed"], 1)
        self.assertIsNotNone(cache.get("native:daily:budget-publication-check:success"))

    def test_scheduled_run_records_success_so_catch_up_skips_it(self):
        self.assertEqual(tasks.native_private_memory_cleanup.call_local(), {"status": "completed"})
        tasks.native_daily_catch_up.call_local()
        self.assertEqual(self.jobs["private-memory-cleanup"].call_count, 1)

    def test_a_running_job_is_never_started_twice(self):
        cache.set("native:daily:nightly-training:running", 1)
        self.assertEqual(tasks.native_nightly_training.call_local(), {"status": "busy"})
        self.assertEqual(tasks.native_daily_catch_up.call_local()["processed"], 3)
        self.jobs["nightly-training"].assert_not_called()
        self.assertIsNone(cache.get("native:daily:nightly-training:success"))

    def test_scheduled_failure_still_raises_and_releases_its_lock(self):
        self.jobs["intelligence-cleanup"].side_effect = RuntimeError("disk")
        with self.assertRaises(RuntimeError):
            tasks.native_intelligence_cleanup.call_local()
        self.assertIsNone(cache.get("native:daily:intelligence-cleanup:running"))
        self.assertIsNone(cache.get("native:daily:intelligence-cleanup:success"))

    def test_real_job_bindings_are_unchanged(self):
        with patch.object(tasks, "cleanup_verified_external_intelligence", return_value={"status": "ok"}) as cleanup, \
                patch.object(tasks, "run_global_training_cycle", return_value={"status": "completed"}) as train, \
                patch("django.core.management.call_command") as command:
            real = self.real_jobs  # read at class definition, before setUp swaps in mocks
            real["intelligence-cleanup"]()
            real["nightly-training"]()
            real["private-memory-cleanup"]()
        cleanup.assert_called_once_with(retention_days=90)
        train.assert_called_once_with()
        command.assert_called_once_with("prune_private_memory", verbosity=0)

    real_jobs = dict(tasks.DAILY_JOBS)
