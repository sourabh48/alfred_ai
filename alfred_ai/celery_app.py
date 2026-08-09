import logging
import os
from importlib import import_module

from celery import Celery
from django.apps import apps as django_apps

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alfred_ai.settings")

app = Celery("alfred_ai")
LOGGER = logging.getLogger(__name__)

# Load config from Django settings with CELERY_ prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks across all installed apps
app.autodiscover_tasks(lambda: [config.name for config in django_apps.get_app_configs()])
import_module("alfred_ai.tasks")

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")

@app.task(name="alfred_ai.celery_app.cleanup_memory_task")
def cleanup_memory_task():
    try:
        memory_module = import_module("apps.ml_engine.memory.memory_engine")
    except ModuleNotFoundError as exc:
        if (exc.name or "").startswith("apps.ml_engine.memory"):
            LOGGER.info("Skipping memory cleanup task because the optional memory engine module is unavailable.")
            return {"status": "skipped", "reason": "memory_engine_unavailable"}
        raise

    alfred_memory = getattr(memory_module, "alfred_memory", None)
    cleanup = getattr(alfred_memory, "cleanup", None)
    if cleanup is None:
        LOGGER.warning("Skipping memory cleanup task because the loaded memory engine has no cleanup() hook.")
        return {"status": "skipped", "reason": "memory_cleanup_unavailable"}

    return cleanup()
