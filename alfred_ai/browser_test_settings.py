"""Isolated storage for driver-backed tests of concurrent dashboard requests."""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from .settings import *  # noqa: F403


# Django shares one SQLite connection between live-server threads when its
# default in-memory test database is used. Real pages issue parallel requests;
# a temporary file gives each request its own connection and avoids API misuse.
_browser_storage = TemporaryDirectory(prefix="alfred-browser-tests-")
DATABASES = deepcopy(DATABASES)  # noqa: F405
if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
    DATABASES["default"].setdefault("TEST", {})["NAME"] = str(
        Path(_browser_storage.name) / "browser.sqlite3"
    )
    DATABASES["default"].setdefault("OPTIONS", {}).update(
        timeout=30,
        transaction_mode="IMMEDIATE",
    )
MEDIA_ROOT = str(Path(_browser_storage.name) / "media")
ALFRED_AUTO_TRAIN_ON_STARTUP = False
