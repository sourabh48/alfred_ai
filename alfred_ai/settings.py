"""
Django settings for alfred_ai project.
"""

import environ
import os
import sys
from pathlib import Path
from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env.read_env(os.path.join(BASE_DIR, ".env"))


def _is_local_runtime(argv: list[str] | None = None) -> bool:
    argv = list(argv or sys.argv)
    command = argv[1] if len(argv) > 1 else ""
    return command in {
        "check",
        "createsuperuser",
        "flush",
        "loaddata",
        "makemigrations",
        "migrate",
        "runserver",
        "shell",
        "showmigrations",
        "bootstrap_training_samples",
        "test",
    }


def _default_secret_key(local_runtime: bool) -> str:
    if local_runtime:
        return "alfred-local-development-key"
    return ""


def _default_allowed_hosts(local_runtime: bool) -> list[str]:
    if local_runtime:
        return ["127.0.0.1", "localhost", "[::1]", "testserver"]
    return []


def _default_cors_allow_all(local_runtime: bool) -> bool:
    return bool(local_runtime)


def _default_ssl_redirect(local_runtime: bool) -> bool:
    return not local_runtime


def _default_secure_cookie(local_runtime: bool) -> bool:
    return not local_runtime


def _default_hsts_seconds(local_runtime: bool) -> int:
    return 0 if local_runtime else 31536000


def _is_postgresql_engine(engine: str) -> bool:
    engine_lower = str(engine or "").lower()
    return "postgresql" in engine_lower or "postgis" in engine_lower


def _is_redis_cache_backend(backend: str) -> bool:
    return "redis" in str(backend or "").lower()


def _is_redis_url(value: str) -> bool:
    return str(value or "").strip().lower().startswith(("redis://", "rediss://"))


def _is_local_redis_url(value: str) -> bool:
    lowered = str(value or "").strip().lower()
    return "localhost" in lowered or "127.0.0.1" in lowered


def _require_production(condition: bool, message: str) -> None:
    if not LOCAL_RUNTIME and not condition:
        raise ImproperlyConfigured(message)


# ---------------------------------------------------------
# CORE
# ---------------------------------------------------------

LOCAL_RUNTIME = env.bool("ALFRED_LOCAL_RUNTIME", default=_is_local_runtime())
DEBUG = env.bool("DEBUG", default=LOCAL_RUNTIME)
SECRET_KEY = env("DJANGO_SECRET_KEY", default=_default_secret_key(LOCAL_RUNTIME))
if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when local runtime mode is disabled.")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=_default_allowed_hosts(LOCAL_RUNTIME))

# ---------------------------------------------------------
# INSTALLED APPS
# ---------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "corsheaders",
    "environ",

    "apps.users",
    "apps.expenses",
    "apps.budgets",
    "apps.loans",
    "apps.investments",
    "apps.family",
    "apps.career",
    "apps.behavioral",
    "apps.relationship",
    "apps.risk",
    "apps.reports",
    "apps.mobility",
    "apps.ml_engine.apps.MlEngineConfig",
    "apps.integrations",
]

AUTH_USER_MODEL = "users.User"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"


# ---------------------------------------------------------
# MIDDLEWARE
# ---------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",

    "corsheaders.middleware.CorsMiddleware",

    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=_default_cors_allow_all(LOCAL_RUNTIME))
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=_default_ssl_redirect(LOCAL_RUNTIME))
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=_default_secure_cookie(LOCAL_RUNTIME))
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=_default_secure_cookie(LOCAL_RUNTIME))
SESSION_COOKIE_HTTPONLY = env.bool("SESSION_COOKIE_HTTPONLY", default=True)
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", default="Lax")
CSRF_COOKIE_SAMESITE = env("CSRF_COOKIE_SAMESITE", default="Lax")
SESSION_COOKIE_AGE = env.int("ALFRED_SESSION_TIMEOUT_SECONDS", default=3600 if LOCAL_RUNTIME else 1800)
ALFRED_SESSION_WARNING_SECONDS = env.int(
    "ALFRED_SESSION_WARNING_SECONDS",
    default=min(300, max(60, SESSION_COOKIE_AGE // 6)),
)
SESSION_SAVE_EVERY_REQUEST = env.bool("SESSION_SAVE_EVERY_REQUEST", default=True)
SESSION_EXPIRE_AT_BROWSER_CLOSE = env.bool("SESSION_EXPIRE_AT_BROWSER_CLOSE", default=not LOCAL_RUNTIME)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=_default_hsts_seconds(LOCAL_RUNTIME))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=bool(SECURE_HSTS_SECONDS),
)
SECURE_HSTS_PRELOAD = env.bool(
    "SECURE_HSTS_PRELOAD",
    default=bool(SECURE_HSTS_SECONDS),
)
SECURE_CONTENT_TYPE_NOSNIFF = env.bool("SECURE_CONTENT_TYPE_NOSNIFF", default=True)
SECURE_REFERRER_POLICY = env("SECURE_REFERRER_POLICY", default="same-origin")
SECURE_PROXY_SSL_HEADER_ENABLED = env.bool(
    "SECURE_PROXY_SSL_HEADER_ENABLED",
    default=not LOCAL_RUNTIME,
)
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https") if SECURE_PROXY_SSL_HEADER_ENABLED else None
)
USE_X_FORWARDED_HOST = env.bool("USE_X_FORWARDED_HOST", default=not LOCAL_RUNTIME)
X_FRAME_OPTIONS = env("X_FRAME_OPTIONS", default="DENY")


# ---------------------------------------------------------
# URL CONFIG
# ---------------------------------------------------------

ROOT_URLCONF = "alfred_ai.urls"


# ---------------------------------------------------------
# TEMPLATES
# ---------------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "alfred_ai.context_processors.global_ui_config",
            ],
        },
    },
]


WSGI_APPLICATION = "alfred_ai.wsgi.application"
ASGI_APPLICATION = "alfred_ai.asgi.application"


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

DB_CONN_MAX_AGE = env.int("DB_CONN_MAX_AGE", default=60 if not LOCAL_RUNTIME else 0)
DATABASE_URL = env("DATABASE_URL", default="")
if DATABASE_URL:
    DATABASES = {"default": env.db_url("DATABASE_URL")}
else:
    DATABASES = {
        "default": {
            "ENGINE": env("DB_ENGINE", default="django.db.backends.sqlite3"),
            "NAME": env("DB_NAME", default=str(BASE_DIR / "db.sqlite3")),
            "USER": env("DB_USER", default=""),
            "PASSWORD": env("DB_PASSWORD", default=""),
            "HOST": env("DB_HOST", default=""),
            "PORT": env("DB_PORT", default=""),
        }
    }

DATABASES["default"]["CONN_MAX_AGE"] = DB_CONN_MAX_AGE
DATABASES["default"]["CONN_HEALTH_CHECKS"] = env.bool(
    "DB_CONN_HEALTH_CHECKS",
    default=not LOCAL_RUNTIME,
)
_require_production(
    _is_postgresql_engine(DATABASES["default"].get("ENGINE", "")),
    "Production mode requires PostgreSQL. Set DATABASE_URL or DB_ENGINE=django.db.backends.postgresql.",
)
if not DATABASE_URL:
    _require_production(
        all(str(DATABASES["default"].get(key) or "").strip() for key in ("NAME", "USER", "PASSWORD", "HOST")),
        "Production PostgreSQL configuration requires DB_NAME, DB_USER, DB_PASSWORD, and DB_HOST.",
    )


# ---------------------------------------------------------
# STATIC & MEDIA
# ---------------------------------------------------------

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ---------------------------------------------------------
# REST FRAMEWORK
# ---------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}


# ---------------------------------------------------------
# CACHE
# ---------------------------------------------------------

REDIS_URL = env("REDIS_URL", default="")
CACHE_BACKEND = env(
    "CACHE_BACKEND",
    default="django.core.cache.backends.redis.RedisCache"
    if (not LOCAL_RUNTIME and REDIS_URL)
    else "django.core.cache.backends.locmem.LocMemCache",
)
CACHE_LOCATION = env("CACHE_LOCATION", default=REDIS_URL if (not LOCAL_RUNTIME and REDIS_URL) else "alfred-local-cache")
CACHE_KEY_PREFIX = env("CACHE_KEY_PREFIX", default="alfred")
CACHE_DEFAULT_TIMEOUT = env.int("CACHE_DEFAULT_TIMEOUT", default=300)

_require_production(
    _is_redis_cache_backend(CACHE_BACKEND),
    "Production mode requires a Redis-backed shared Django cache. Set CACHE_BACKEND and CACHE_LOCATION/REDIS_URL.",
)
_require_production(
    _is_redis_url(CACHE_LOCATION),
    "Production mode requires CACHE_LOCATION to be a redis:// or rediss:// URL.",
)

CACHES = {
    "default": {
        "BACKEND": CACHE_BACKEND,
        "LOCATION": CACHE_LOCATION,
        "KEY_PREFIX": CACHE_KEY_PREFIX,
        "TIMEOUT": CACHE_DEFAULT_TIMEOUT,
    }
}


# ---------------------------------------------------------
# CELERY FOR CONTINUOUS LEARNING
# ---------------------------------------------------------

# ---------------------------------------------
# Celery Configuration
# ---------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL or "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL or "redis://localhost:6379/0")
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = env.bool("CELERY_TASK_EAGER_PROPAGATES", default=False)

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

CELERY_TIMEZONE = "UTC"

_require_production(
    _is_redis_url(CELERY_BROKER_URL) and _is_redis_url(CELERY_RESULT_BACKEND),
    "Production mode requires Redis Celery broker and result backend URLs.",
)
_require_production(
    not _is_local_redis_url(CELERY_BROKER_URL) and not _is_local_redis_url(CELERY_RESULT_BACKEND),
    "Production mode cannot use localhost Redis for Celery.",
)
_require_production(
    not CELERY_TASK_ALWAYS_EAGER,
    "Production mode cannot enable CELERY_TASK_ALWAYS_EAGER.",
)

CELERY_BEAT_SCHEDULE = {
    "alfred-nightly-training": {
        "task": "apps.ml_engine.continual.tasks.run_global_training_cycle",
        "schedule": timedelta(hours=24),
    },
    "statement-review-retry": {
        "task": "apps.expenses.tasks.retry_low_confidence_statement_uploads",
        "schedule": timedelta(minutes=20),
        "args": (3,),
    },
    "verified-intelligence-refresh": {
        "task": "apps.integrations.tasks.refresh_verified_external_intelligence",
        "schedule": timedelta(hours=6),
        "args": (75,),
    },
    "verified-intelligence-cleanup": {
        "task": "apps.integrations.tasks.cleanup_verified_external_intelligence",
        "schedule": timedelta(hours=24),
        "args": (90,),
    },
    "production-readiness-heartbeat": {
        "task": "alfred_ai.tasks.production_beat_heartbeat",
        "schedule": timedelta(minutes=5),
    },
}

ALFRED_CELERY_PROBE_TIMEOUT_SECONDS = env.int("ALFRED_CELERY_PROBE_TIMEOUT_SECONDS", default=10)
ALFRED_CELERY_BEAT_HEARTBEAT_MAX_AGE_SECONDS = env.int(
    "ALFRED_CELERY_BEAT_HEARTBEAT_MAX_AGE_SECONDS",
    default=900,
)

ALFRED_AUTO_TRAIN_ON_STARTUP = env.bool("ALFRED_AUTO_TRAIN_ON_STARTUP", default=True)
ALFRED_AUTO_TRAIN_COOLDOWN_MINUTES = env.int("ALFRED_AUTO_TRAIN_COOLDOWN_MINUTES", default=45)
ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION = env.bool(
    "ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION",
    default=not LOCAL_RUNTIME,
)
ALFRED_FAMILY_LINK_CODE_TTL_HOURS = env.int("ALFRED_FAMILY_LINK_CODE_TTL_HOURS", default=24)


# ---------------------------------------------------------
# LOGGING
# ---------------------------------------------------------

LOG_LEVEL = env("LOG_LEVEL", default="INFO").upper()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": "ts=%(asctime)s level=%(levelname)s logger=%(name)s msg=%(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",
        }
    },
    "filters": {
        "redact_routes": {
            "()": "alfred_ai.services.logging_filters.RedactRouteFilter",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
            "filters": ["redact_routes"],
        }
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}



# ---------------------------------------------------------
# AWS (Model Storage)
# ---------------------------------------------------------

AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
AWS_REGION = env("AWS_REGION", default="us-east-1")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="alfred-models")
