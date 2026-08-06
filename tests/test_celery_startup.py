from django.conf import settings
from django.test import SimpleTestCase

from alfred_ai.celery_app import app, cleanup_memory_task


class CeleryStartupTests(SimpleTestCase):
    def test_default_task_modules_import_without_broken_references(self):
        app.loader.import_default_modules()

        self.assertIn("apps.expenses.tasks.retry_low_confidence_statement_uploads", app.tasks)
        self.assertIn("apps.integrations.tasks.refresh_verified_external_intelligence", app.tasks)
        self.assertIn("apps.ml_engine.continual.tasks.run_global_training_cycle", app.tasks)
        self.assertIn("alfred_ai.celery_app.cleanup_memory_task", app.tasks)

    def test_verified_intelligence_refresh_schedule_can_drain_current_backlog_size(self):
        schedule = settings.CELERY_BEAT_SCHEDULE["verified-intelligence-refresh"]

        self.assertEqual(schedule["task"], "apps.integrations.tasks.refresh_verified_external_intelligence")
        self.assertEqual(schedule["args"], (75,))

    def test_batch_job_schedule_covers_training_retry_refresh_and_cleanup(self):
        schedule = settings.CELERY_BEAT_SCHEDULE

        self.assertEqual(
            schedule["alfred-nightly-training"]["task"],
            "apps.ml_engine.continual.tasks.run_global_training_cycle",
        )
        self.assertEqual(
            schedule["statement-review-retry"]["task"],
            "apps.expenses.tasks.retry_low_confidence_statement_uploads",
        )
        self.assertEqual(schedule["statement-review-retry"]["args"], (3,))
        self.assertEqual(
            schedule["verified-intelligence-refresh"]["task"],
            "apps.integrations.tasks.refresh_verified_external_intelligence",
        )
        self.assertEqual(schedule["verified-intelligence-refresh"]["args"], (75,))
        self.assertEqual(
            schedule["verified-intelligence-cleanup"]["task"],
            "apps.integrations.tasks.cleanup_verified_external_intelligence",
        )
        self.assertEqual(schedule["verified-intelligence-cleanup"]["args"], (90,))

    def test_cleanup_memory_task_skips_when_optional_memory_engine_is_missing(self):
        result = cleanup_memory_task()

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "memory_engine_unavailable")
