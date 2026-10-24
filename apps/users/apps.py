from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from pathlib import Path
import os

from alfred_private_storage import guard_sqlite_storage, private_directory, PrivateStorageUnavailable

class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    label = "users"  # important: app label must match AUTH_USER_MODEL

    def ready(self):
        try:
            guard_sqlite_storage(settings.DATABASES)
            if os.name == "nt":
                private_directory(Path(settings.MEDIA_ROOT).absolute())
                for config in settings.CACHES.values():
                    if config["BACKEND"] in {"diskcache.DjangoCache", "django.core.cache.backends.filebased.FileBasedCache"}:
                        private_directory(Path(config["LOCATION"]).absolute())
        except (OSError, ValueError, PrivateStorageUnavailable):
            raise ImproperlyConfigured("Private storage requires verified owner permissions; review the authorized repair procedure.") from None
