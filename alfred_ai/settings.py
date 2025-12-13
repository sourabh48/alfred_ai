"""
Django settings for alfred_ai project.
"""

import environ
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env.read_env(os.path.join(BASE_DIR, ".env"))


# ---------------------------------------------------------
# CORE
# ---------------------------------------------------------

SECRET_KEY = env("DJANGO_SECRET_KEY", default="CHANGEME")
DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "192.168.0.108", "[::1]"]

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
    "apps.ml_engine",
]

AUTH_USER_MODEL = "users.User"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


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
]

CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=True)


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
    }
}



# ---------------------------------------------------------
# AWS (Model Storage)
# ---------------------------------------------------------

AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
AWS_REGION = env("AWS_REGION", default="us-east-1")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="alfred-models")
