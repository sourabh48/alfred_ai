"""Persistent atomic rolling-window quotas, shared by invitation and runtime guards."""
import json
import logging
from math import isfinite
from pathlib import Path
import time

from diskcache import Cache
from django.utils import timezone

from alfred_ai.safe_cache import CacheIntegrityError, StrictDisk
from alfred_private_storage import private_directory, verify_cache_storage

logger = logging.getLogger(__name__)
# A new folder: rows written before this format are pickled, and are never opened.
STORE = "json-v1"
# Every API request passes here and a permission check costs tens of milliseconds, so a process rechecks a store only
# this often, and startup always checks. shortcut: a folder loosened, or replaced by a link or a new folder, passes
# for up to this long, which is fine while planted rows cannot run code; shorten it if the store guards more than counts.
CHECK_SECONDS = 30
_checked = {}


def _private_store(directory):
    store_path = Path(directory) / STORE
    last = _checked.get(store_path)
    if last is not None and time.monotonic() - last < CHECK_SECONDS and store_path.is_dir():
        return store_path
    # Refuses a location other accounts can write to, including a configured external one.
    private_directory(private_directory(Path(directory)) / STORE)
    verify_cache_storage(store_path)
    _checked[store_path] = time.monotonic()
    return store_path


def _history(store, key):
    """Return the recorded times, or None if the row is not what this code writes."""
    try:
        history = store.get(key, [])
    except CacheIntegrityError:
        return None
    valid = isinstance(history, list) and all(type(stamp) is float and isfinite(stamp) for stamp in history)
    return history if valid else None


def reserve_attempts(directory, buckets):
    if not directory or not Path(directory).is_absolute():
        raise ValueError('Protection requires an absolute persistent directory')
    if any(limit < 1 or window < 1 for _, limit, window in buckets):
        raise ValueError('Limits must be positive')
    with Cache(str(_private_store(directory)), disk=StrictDisk, timeout=5, eviction_policy='none', cull_limit=0) as store, store.transact():
        now = timezone.now().timestamp()
        store.expire()
        reservations, retry = [], 0
        for key, limit, window in buckets:
            key = json.dumps(key, sort_keys=True)
            history = _history(store, key)
            if history is None:
                # Fail closed for this window, and drop the row so the quota can recover.
                logger.warning('A rate limit record was unreadable and has been reset.')
                store.delete(key)
                retry = max(retry, window)
                continue
            # A time over a window ahead means the clock moved back or the row is forged. Neither should block anyone.
            history = [stamp for stamp in history if now - window < stamp <= now + window]
            if len(history) >= limit:
                retry = max(retry, min(history) + window - now)
            reservations.append((key, history, window))
        if retry:
            return retry
        for key, history, window in reservations:
            store.set(key, history + [now], expire=window)
    return 0
