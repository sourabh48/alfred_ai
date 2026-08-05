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

    def test_cleanup_memory_task_skips_when_optional_memory_engine_is_missing(self):
        result = cleanup_memory_task()

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "memory_engine_unavailable")
