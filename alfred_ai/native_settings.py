"""Settings for the Windows launcher. Writable data lives outside the bundle."""
import os
import socket
from pathlib import Path

from .settings import *  # noqa: F403

ALFRED_NATIVE_RUNTIME = True
ASSET_DIR = BASE_DIR
BASE_DIR = Path(os.environ["ALFRED_DATA_DIR"]).resolve()
LOCAL_RUNTIME = True
DEBUG = False
SECRET_KEY_FALLBACKS = env.json("DJANGO_SECRET_KEY_FALLBACKS", default=[])
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
# Opt-in home Wi-Fi access: other devices open http://<this PC's address>:<port>/ (see docs/NATIVE_WINDOWS.md).
ALFRED_LAN_ACCESS = env.bool("ALFRED_LAN_ACCESS", default=False)
if ALFRED_LAN_ACCESS:
    from alfred_ai.services.native_web import lan_addresses
    ALLOWED_HOSTS += [*lan_addresses(), socket.gethostname().lower()]
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
from alfred_ai.safe_cache import SafeDisk

CACHES = {"default": {
    "BACKEND": "diskcache.DjangoCache",
    # A new folder: rows written before this format are pickled, and are never opened.
    "LOCATION": str(BASE_DIR / "artifacts" / "native" / "cache" / "json-v1"),
    "DATABASE_TIMEOUT": 10,
    "SHARDS": 4,
    "KEY_PREFIX": "alfred",
    "TIMEOUT": 300,
    "OPTIONS": {"size_limit": 256 * 1024 * 1024, "disk": SafeDisk},
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
