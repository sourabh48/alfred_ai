"""Settings for the Windows launcher. Writable data lives outside the bundle."""
import os
from pathlib import Path

from .settings import *  # noqa: F403

ALFRED_NATIVE_RUNTIME = True
ASSET_DIR = BASE_DIR
BASE_DIR = Path(os.environ["ALFRED_DATA_DIR"]).resolve()
LOCAL_RUNTIME = True
DEBUG = False
SECRET_KEY_FALLBACKS = env.json("DJANGO_SECRET_KEY_FALLBACKS", default=[])
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
CORS_ALLOW_ALL_ORIGINS = False
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_PROXY_SSL_HEADER = None
USE_X_FORWARDED_HOST = False
ALFRED_AUTO_TRAIN_ON_STARTUP = False

DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": BASE_DIR / "db.sqlite3",
    "CONN_MAX_AGE": 0,
    "OPTIONS": {"timeout": 30, "transaction_mode": "IMMEDIATE"},
}}
MEDIA_ROOT = BASE_DIR / "media"
STATIC_ROOT = BASE_DIR / "artifacts" / "native" / "static"
CACHES = {"default": {
    "BACKEND": "diskcache.DjangoCache",
    "LOCATION": str(BASE_DIR / "artifacts" / "native" / "cache"),
    "DATABASE_TIMEOUT": 10,
    "SHARDS": 4,
    "KEY_PREFIX": "alfred",
    "TIMEOUT": 300,
    "OPTIONS": {"size_limit": 256 * 1024 * 1024},
}}
INSTALLED_APPS = [*INSTALLED_APPS, "huey.contrib.djhuey"]
HUEY = {
    "name": "alfred-native",
    "huey_class": "alfred_ai.durable_queue.DurableSqliteHuey",
    "filename": str(BASE_DIR / "artifacts" / "native" / "jobs.sqlite3"),
    "immediate": False,
    "utc": True,
    "results": True,
    "store_none": True,
    "fsync": True,
    "consumer": {"workers": 2, "worker_type": "thread", "periodic": True},
}
