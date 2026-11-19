"""Each person's own keys for paid services and for free services with a usage limit (owner decision 2026-11-19).

Any signed-in person may save their own key for these in Settings. ALFRED uses it for that person's pages and background
jobs, and otherwise falls back to the PC-wide key (config/local.env, or a built-in free key). Free keys without a
practical limit (sign-in clients, FRED, Reddit) are built in, never shown and never changed in Settings.
Keys are encrypted in one private file per person under ALFRED's data folder and never sent back to the browser.
"""
from __future__ import annotations

import contextlib
import contextvars
import json
import os
from pathlib import Path

from django.conf import settings

PERSONAL = ("TRAVEL_GOOGLE_MAPS_API_KEY", "TRAVEL_SKYSCANNER_API_KEY", "ALFRED_ALPHA_VANTAGE_API_KEY")
# Who the current page or background job works for; a page request always sets it, a new thread starts with none.
_person = contextvars.ContextVar("alfred_key_person", default=None)
_cache: dict[int, tuple[int, dict]] = {}


def _folder() -> Path:
    return Path(os.environ.get("ALFRED_DATA_DIR") or settings.BASE_DIR) / "artifacts" / "personal-keys"


def _path(pk: int) -> Path:
    return _folder() / f"user-{int(pk)}.json"


def _own(pk: int) -> dict:
    """{name: encrypted value} for one person, re-read only when the file changes (map tiles ask for the key often)."""
    path = _path(pk)
    try:
        stamp = path.stat().st_mtime_ns
    except OSError:
        return {}
    cached = _cache.get(pk)
    if cached and cached[0] == stamp:
        return cached[1]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data = {k: v for k, v in data.items() if k in PERSONAL and isinstance(v, str)} if isinstance(data, dict) else {}
    _cache[pk] = (stamp, data)
    return data


def own(user, name: str) -> str:
    from apps.integrations.models import _decrypt_token
    pk = getattr(user, "pk", user)
    return _decrypt_token(_own(pk).get(name)) if pk and name in PERSONAL else ""


def get(name: str) -> str:
    """The key to use now: the current person's own key for a personal service, else the PC-wide one."""
    mine = own(_person.get(), name) if name in PERSONAL else ""
    return (mine or os.environ.get(name, "")).strip()


def save(user, changes: dict) -> None:
    """{name: value or ''}; '' removes that person's own key so the PC-wide one applies again."""
    from alfred_private_storage import private_directory
    from apps.integrations.models import _encrypt_token
    if not changes:
        return
    data = dict(_own(user.pk))
    for name, value in changes.items():
        if name not in PERSONAL:
            raise ValueError("Unknown service.")
        if value:
            data[name] = _encrypt_token(value)
        else:
            data.pop(name, None)
    path = _path(user.pk)
    private_directory(path.parent)
    temporary = path.with_suffix(".saving")
    temporary.write_text(json.dumps(data), encoding="utf-8")
    os.replace(temporary, path)
    _cache.pop(user.pk, None)


def use_for(user) -> None:
    """Set who this page request works for; every request sets it, so nothing carries over to the next one."""
    _person.set(getattr(user, "pk", None) if getattr(user, "is_authenticated", False) else None)


def forget(**_signal) -> None:
    """No person once a page request has finished (connected to Django's request_finished)."""
    _person.set(None)


@contextlib.contextmanager
def acting_for(user):
    """A background job working for one person (a user or their id) uses that person's own keys."""
    token = _person.set(getattr(user, "pk", user))
    try:
        yield
    finally:
        _person.reset(token)
