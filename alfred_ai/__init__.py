import os

if os.environ.get("ALFRED_TASK_BACKEND") != "huey":
    from .celery_app import app as celery_app
else:
    celery_app = None

__all__ = ("celery_app",)
