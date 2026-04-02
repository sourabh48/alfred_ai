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
LOGIN_REDIRECT_URL = "/dashboard/"
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

CACHES = {
    "default": {
        "BACKEND": env("CACHE_BACKEND", default="django.core.cache.backends.locmem.LocMemCache"),
        "LOCATION": env("CACHE_LOCATION", default="alfred-local-cache"),
    }
}


# ---------------------------------------------------------
# CELERY FOR CONTINUOUS LEARNING
# ---------------------------------------------------------

# ---------------------------------------------
# Celery Configuration
# ---------------------------------------------
CELERY_BROKER_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("REDIS_URL", default="redis://localhost:6379/0")

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

CELERY_TIMEZONE = "UTC"

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
        "args": (25,),
    },
    "verified-intelligence-cleanup": {
        "task": "apps.integrations.tasks.cleanup_verified_external_intelligence",
        "schedule": timedelta(hours=24),
        "args": (90,),
    },
}

ALFRED_AUTO_TRAIN_ON_STARTUP = env.bool("ALFRED_AUTO_TRAIN_ON_STARTUP", default=True)
ALFRED_AUTO_TRAIN_COOLDOWN_MINUTES = env.int("ALFRED_AUTO_TRAIN_COOLDOWN_MINUTES", default=45)


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
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
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
