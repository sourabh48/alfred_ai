import os
from celery import Celery

from celery import shared_task
from apps.ml_engine.memory.memory_engine import alfred_memory

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alfred_ai.settings")

app = Celery("alfred_ai")

# Load config from Django settings with CELERY_ prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks across all installed apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")

@shared_task
def cleanup_memory_task():
    return alfred_memory.cleanup()
