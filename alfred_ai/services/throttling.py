"""Persistent atomic rolling-window quotas, shared by invitation and runtime guards."""
from pathlib import Path

from diskcache import Cache
from django.utils import timezone


def reserve_attempts(directory, buckets):
    if not directory or not Path(directory).is_absolute():
        raise ValueError('Protection requires an absolute persistent directory')
    if any(limit < 1 or window < 1 for _, limit, window in buckets):
        raise ValueError('Limits must be positive')
    with Cache(directory, timeout=5, eviction_policy='none', cull_limit=0) as store, store.transact():
        now = timezone.now().timestamp()
        store.expire()
        reservations, retry = [], 0
        for key, limit, window in buckets:
            history = [stamp for stamp in store.get(key, []) if stamp > now - window]
            if len(history) >= limit:
                retry = max(retry, min(history) + window - now)
            reservations.append((key, history, window))
        if retry:
            return retry
        for key, history, window in reservations:
            store.set(key, history + [now], expire=window)
    return 0
