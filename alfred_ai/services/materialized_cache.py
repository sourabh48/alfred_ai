from __future__ import annotations

import hashlib

from django.core.cache import cache
from django.utils import timezone


MATERIALIZED_INDEX_TTL = 60 * 60 * 24 * 30


def _user_index_key(user_id: int) -> str:
    return f"alfred:materialized-index:{user_id}"


def _track_user_cache_key(user_id: int, cache_key: str) -> None:
    index_key = _user_index_key(user_id)
    tracked_keys = set(cache.get(index_key) or [])
    if cache_key in tracked_keys:
        return
    tracked_keys.add(cache_key)
    cache.set(index_key, sorted(tracked_keys), MATERIALIZED_INDEX_TTL)


def _legacy_locmem_user_keys(user_id: int) -> list[str]:
    backing_store = getattr(cache, "_cache", None)
    if not isinstance(backing_store, dict):
        return []
    token = f":{user_id}:"
    keys = []
    for raw_key in list(backing_store.keys()):
        key = str(raw_key or "")
        if "alfred:materialized:" in key and token in key:
            keys.append(raw_key)
    return keys


def _delete_legacy_locmem_keys(keys: list[str]) -> None:
    backing_store = getattr(cache, "_cache", None)
    expire_info = getattr(cache, "_expire_info", None)
    if not isinstance(backing_store, dict):
        return
    for raw_key in keys:
        backing_store.pop(raw_key, None)
        if isinstance(expire_info, dict):
            expire_info.pop(raw_key, None)


def invalidate_user_materialized_payloads(user_id: int) -> None:
    index_key = _user_index_key(user_id)
    tracked_keys = set(cache.get(index_key) or [])
    legacy_locmem_keys = _legacy_locmem_user_keys(user_id)
    if tracked_keys:
        delete_many = getattr(cache, "delete_many", None)
        if callable(delete_many):
            delete_many(list(tracked_keys))
        else:
            for cache_key in tracked_keys:
                cache.delete(cache_key)
    if legacy_locmem_keys:
        _delete_legacy_locmem_keys(legacy_locmem_keys)
    cache.delete(index_key)


def materialize_payload(*, namespace: str, user_id: int, revision: str, ttl_seconds: int, builder):
    revision_hash = hashlib.sha256((revision or "empty").encode("utf-8")).hexdigest()[:16]
    cache_key = f"alfred:materialized:{namespace}:{user_id}:{revision_hash}"
    _track_user_cache_key(user_id, cache_key)
    cached = cache.get(cache_key)
    if cached is not None:
        payload = dict(cached)
        payload["_materialized"] = {
            **dict(payload.get("_materialized") or {}),
            "cached": True,
            "cache_key": cache_key,
        }
        return payload

    payload = dict(builder() or {})
    payload["_materialized"] = {
        "namespace": namespace,
        "cached": False,
        "revision": revision_hash,
        "generated_at": timezone.now().isoformat(),
        "ttl_seconds": int(ttl_seconds),
        "cache_key": cache_key,
    }
    cache.set(cache_key, payload, ttl_seconds)
    return payload
