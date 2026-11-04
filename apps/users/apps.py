from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from pathlib import Path
import logging
import os

from alfred_private_storage import guard_sqlite_storage, private_directory, PrivateStorageUnavailable, verify_cache_storage, verify_pickle_storage

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
                        verify_cache_storage(private_directory(Path(config["LOCATION"]).absolute()))
                for directory in (settings.ALFRED_ABUSE_THROTTLE_DIR, settings.ALFRED_FAMILY_INVITE_THROTTLE_DIR):
                    if directory and Path(directory).is_absolute():
                        verify_cache_storage(private_directory(Path(directory)))
                # Only the native runtime has this queue; a source checkout keeps models beside the code.
                if huey := getattr(settings, "HUEY", None):
                    verify_pickle_storage(Path(huey["filename"]), Path(settings.BASE_DIR) / "ml_models")
        except (OSError, ValueError, PrivateStorageUnavailable):
            raise ImproperlyConfigured("Private storage requires verified owner permissions; review the authorized repair procedure.") from None
        if settings.TIME_ZONE_WARNING:
            logging.getLogger(__name__).warning(settings.TIME_ZONE_WARNING)
        from alfred_ai.services.live_version import connect
        connect()
