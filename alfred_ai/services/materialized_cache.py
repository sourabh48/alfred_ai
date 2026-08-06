from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from datetime import timedelta
import hashlib
from time import perf_counter

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


MATERIALIZED_INDEX_TTL = 60 * 60 * 24 * 30
MATERIALIZED_TELEMETRY_TTL = MATERIALIZED_INDEX_TTL
MATERIALIZED_NAMESPACE_INDEX_KEY = "alfred:materialized:namespaces"
MATERIALIZED_TRAFFIC_PROOF_ENV = "ALFRED_MATERIALIZED_CACHE_TRAFFIC_PROOF"
MATERIALIZED_TRAFFIC_PROOF_DEFAULT_PATH = "artifacts/cache/materialized_cache_traffic_summary.json"
MATERIALIZED_TRAFFIC_PROOF_SOURCE = "staging_cache_exercise"
MATERIALIZED_TRAFFIC_PROOF_MIN_REQUESTS_PER_NAMESPACE = 2

MATERIALIZED_PAYLOAD_REGISTRY = (
    {
        "namespace": "budget-dashboard",
        "path": "/api/budgets/dashboard/",
        "owner": "budgets",
        "ttl_seconds": 60,
    },
    {
        "namespace": "loan-summary",
        "path": "/api/loans/summary/",
        "owner": "loans",
        "ttl_seconds": 60,
    },
    {
        "namespace": "loan-metrics",
        "path": "/api/loans/metrics/",
        "owner": "loans",
        "ttl_seconds": 60,
    },
    {
        "namespace": "loan-networth",
        "path": "/api/loans/networth/",
        "owner": "loans",
        "ttl_seconds": 60,
    },
    {
        "namespace": "financial-intelligence",
        "path": "/api/expenses/dashboard/ and /api/ai/financial-intelligence/",
        "owner": "expenses",
        "ttl_seconds": 45,
    },
    {
        "namespace": "financial-baseline",
        "path": "internal canonical baseline service",
        "owner": "expenses",
        "ttl_seconds": 45,
    },
    {
        "namespace": "behavioral-fingerprint",
        "path": "/api/behavioral/fingerprint/",
        "owner": "behavioral",
        "ttl_seconds": 60,
    },
    {
        "namespace": "behavioral-stress",
        "path": "/api/behavioral/stress/",
        "owner": "behavioral",
        "ttl_seconds": 60,
    },
    {
        "namespace": "career-dashboard",
        "path": "/api/career/dashboard/",
        "owner": "career",
        "ttl_seconds": 45,
    },
    {
        "namespace": "family-growth",
        "path": "/api/family/growth/",
        "owner": "family",
        "ttl_seconds": 60,
    },
    {
        "namespace": "recommendation-overview",
        "path": "/api/integrations/recommendations/overview/",
        "owner": "integrations",
        "ttl_seconds": 120,
    },
    {
        "namespace": "tax-optimizer-overview",
        "path": "/api/integrations/tax/overview/",
        "owner": "integrations",
        "ttl_seconds": 120,
    },
    {
        "namespace": "investments-summary",
        "path": "/api/investments/summary/",
        "owner": "investments",
        "ttl_seconds": 45,
    },
    {
        "namespace": "investments-allocation",
        "path": "/api/investments/allocation/",
        "owner": "investments",
        "ttl_seconds": 60,
    },
    {
        "namespace": "investments-growth",
        "path": "/api/investments/growth/",
        "owner": "investments",
        "ttl_seconds": 90,
    },
    {
        "namespace": "bike-service-dashboard",
        "path": "internal vehicle service intelligence",
        "owner": "mobility",
        "ttl_seconds": 45,
    },
    {
        "namespace": "bike-service-risk-snapshot",
        "path": "internal vehicle risk snapshot",
        "owner": "mobility",
        "ttl_seconds": 30,
    },
    {
        "namespace": "mobility-dashboard",
        "path": "/api/mobility/dashboard/",
        "owner": "mobility",
        "ttl_seconds": 45,
    },
    {
        "namespace": "bike-service-dashboard-view",
        "path": "/api/mobility/bike-service-dashboard/",
        "owner": "mobility",
        "ttl_seconds": 45,
    },
    {
        "namespace": "relationship-alignment",
        "path": "/api/relationship/alignment/",
        "owner": "relationship",
        "ttl_seconds": 30,
    },
    {
        "namespace": "risk-outlook",
        "path": "/api/risk/outlook/",
        "owner": "risk",
        "ttl_seconds": 60,
    },
)


def _registry_by_namespace() -> dict[str, dict]:
    return {item["namespace"]: dict(item) for item in MATERIALIZED_PAYLOAD_REGISTRY}


def _project_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return Path(settings.BASE_DIR) / path


def materialized_cache_traffic_proof_path() -> Path:
    configured_path = os.environ.get(MATERIALIZED_TRAFFIC_PROOF_ENV, "").strip()
    if configured_path:
        return _project_path(configured_path)
    return _project_path(MATERIALIZED_TRAFFIC_PROOF_DEFAULT_PATH)


def _should_load_default_traffic_proof() -> bool:
    if os.environ.get(MATERIALIZED_TRAFFIC_PROOF_ENV, "").strip():
        return True
    return "test" not in {Path(arg).name for arg in sys.argv[1:]}


def _as_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _user_index_key(user_id: int) -> str:
    return f"alfred:materialized-index:{user_id}"


def _namespace_stats_key(namespace: str) -> str:
    return f"alfred:materialized-stats:{namespace}"


def _tracked_user_cache_keys(user_id: int) -> set[str]:
    return set(cache.get(_user_index_key(user_id)) or [])


def _track_user_cache_key(user_id: int, cache_key: str) -> None:
    index_key = _user_index_key(user_id)
    tracked_keys = _tracked_user_cache_keys(user_id)
    if cache_key in tracked_keys:
        return
    tracked_keys.add(cache_key)
    cache.set(index_key, sorted(tracked_keys), MATERIALIZED_INDEX_TTL)


def _track_namespace(namespace: str) -> None:
    namespaces = set(cache.get(MATERIALIZED_NAMESPACE_INDEX_KEY) or [])
    if namespace in namespaces:
        return
    namespaces.add(namespace)
    cache.set(MATERIALIZED_NAMESPACE_INDEX_KEY, sorted(namespaces), MATERIALIZED_TELEMETRY_TTL)


def _namespace_from_cache_key(cache_key: str) -> str:
    parts = str(cache_key or "").split(":")
    for index, part in enumerate(parts[:-2]):
        if part == "alfred" and parts[index + 1] == "materialized":
            return parts[index + 2]
    return ""


def _has_prior_namespace_key(cache_keys: set[str], namespace: str, current_cache_key: str) -> bool:
    for tracked_key in cache_keys:
        if tracked_key == current_cache_key:
            continue
        if _namespace_from_cache_key(tracked_key) == namespace:
            return True
    return False


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


def invalidate_user_materialized_payloads(user_id: int, *, reason: str = "user_data_reset") -> None:
    index_key = _user_index_key(user_id)
    tracked_keys = _tracked_user_cache_keys(user_id)
    legacy_locmem_keys = _legacy_locmem_user_keys(user_id)
    invalidated_namespaces: dict[str, int] = {}
    for cache_key in list(tracked_keys) + [str(item) for item in legacy_locmem_keys]:
        namespace = _namespace_from_cache_key(cache_key)
        if not namespace:
            continue
        invalidated_namespaces[namespace] = invalidated_namespaces.get(namespace, 0) + 1
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
    for namespace, deleted_count in invalidated_namespaces.items():
        _record_cache_invalidation(namespace, reason=reason, deleted_key_count=deleted_count)


def materialize_payload(*, namespace: str, user_id: int, revision: str, ttl_seconds: int, builder):
    revision_hash = hashlib.sha256((revision or "empty").encode("utf-8")).hexdigest()[:16]
    cache_key = f"alfred:materialized:{namespace}:{user_id}:{revision_hash}"
    tracked_keys = _tracked_user_cache_keys(user_id)
    cached = cache.get(cache_key)
    now = timezone.now()
    _track_namespace(namespace)
    _track_user_cache_key(user_id, cache_key)
    if cached is not None:
        payload = dict(cached)
        previous_meta = dict(payload.get("_materialized") or {})
        payload["_materialized"] = {
            **previous_meta,
            "cached": True,
            "cache_status": "hit",
            "cache_key": cache_key,
            "revision": previous_meta.get("revision") or revision_hash,
            "revision_key": previous_meta.get("revision_key") or revision_hash,
            "ttl_seconds": int(previous_meta.get("ttl_seconds") or ttl_seconds),
            "expires_at": previous_meta.get("expires_at") or (now + timedelta(seconds=int(ttl_seconds))).isoformat(),
            "generation_latency_ms": float(previous_meta.get("generation_latency_ms") or 0),
            "invalidation_reason": previous_meta.get("invalidation_reason") or "cache_hit",
            "served_at": now.isoformat(),
        }
        _record_cache_event(namespace, payload["_materialized"], event="hit")
        return payload

    stale_regenerated = _has_prior_namespace_key(tracked_keys, namespace, cache_key)
    if cache_key in tracked_keys:
        invalidation_reason = "expired"
    elif stale_regenerated:
        invalidation_reason = "revision_changed"
    else:
        invalidation_reason = "cold_start"
    started = perf_counter()
    payload = dict(builder() or {})
    generation_latency_ms = round((perf_counter() - started) * 1000, 2)
    generated_at = timezone.now()
    ttl_seconds = int(ttl_seconds)
    payload["_materialized"] = {
        "namespace": namespace,
        "cached": False,
        "cache_status": "miss",
        "revision": revision_hash,
        "revision_key": revision_hash,
        "generated_at": generated_at.isoformat(),
        "expires_at": (generated_at + timedelta(seconds=ttl_seconds)).isoformat(),
        "ttl_seconds": ttl_seconds,
        "cache_key": cache_key,
        "invalidation_reason": invalidation_reason,
        "generation_latency_ms": generation_latency_ms,
        "served_at": generated_at.isoformat(),
        "stale_regenerated": stale_regenerated,
    }
    cache.set(cache_key, payload, ttl_seconds)
    _record_cache_event(namespace, payload["_materialized"], event="miss")
    return payload


def _record_cache_event(namespace: str, metadata: dict, *, event: str) -> None:
    _track_namespace(namespace)
    stats = dict(cache.get(_namespace_stats_key(namespace)) or {})
    now = timezone.now()
    requests = int(stats.get("requests") or 0) + 1
    hits = int(stats.get("hits") or 0) + (1 if event == "hit" else 0)
    misses = int(stats.get("misses") or 0) + (1 if event != "hit" else 0)
    stale_regenerations = int(stats.get("stale_regenerations") or 0) + (
        1 if metadata.get("stale_regenerated") else 0
    )
    generation_count = int(stats.get("generation_count") or 0)
    total_generation_latency_ms = float(stats.get("total_generation_latency_ms") or 0)
    if event != "hit":
        generation_count += 1
        total_generation_latency_ms += float(metadata.get("generation_latency_ms") or 0)
    ttl_seconds_values = sorted(
        {
            int(value)
            for value in list(stats.get("ttl_seconds_values") or []) + [int(metadata.get("ttl_seconds") or 0)]
            if int(value) > 0
        }
    )
    stats.update(
        {
            "namespace": namespace,
            "requests": requests,
            "hits": hits,
            "misses": misses,
            "stale_regenerations": stale_regenerations,
            "generation_count": generation_count,
            "total_generation_latency_ms": round(total_generation_latency_ms, 2),
            "ttl_seconds_values": ttl_seconds_values,
            "last_cache_status": metadata.get("cache_status") or event,
            "last_cache_key": metadata.get("cache_key") or "",
            "last_revision_key": metadata.get("revision_key") or metadata.get("revision") or "",
            "last_generated_at": metadata.get("generated_at") or "",
            "last_served_at": metadata.get("served_at") or now.isoformat(),
            "last_invalidation_reason": metadata.get("invalidation_reason") or "",
        }
    )
    cache.set(_namespace_stats_key(namespace), stats, MATERIALIZED_TELEMETRY_TTL)


def _record_cache_invalidation(namespace: str, *, reason: str, deleted_key_count: int) -> None:
    _track_namespace(namespace)
    stats = dict(cache.get(_namespace_stats_key(namespace)) or {})
    now = timezone.now()
    stats.update(
        {
            "namespace": namespace,
            "invalidations": int(stats.get("invalidations") or 0) + 1,
            "last_invalidation_at": now.isoformat(),
            "last_invalidation_reason": reason or "unspecified",
            "last_invalidated_key_count": int(deleted_key_count or 0),
        }
    )
    cache.set(_namespace_stats_key(namespace), stats, MATERIALIZED_TELEMETRY_TTL)


def _default_traffic_proof_snapshot(*, path: str = "", blockers: list[str] | None = None, recorded: bool = False) -> dict:
    return {
        "path": path,
        "recorded": recorded,
        "accepted": False,
        "state": "missing" if not recorded else "failed",
        "blockers": blockers or ["traffic proof artifact missing"],
        "summary_version": 0,
        "source": "",
        "generated_at_utc": "",
        "registered_namespace_count": len(MATERIALIZED_PAYLOAD_REGISTRY),
        "observed_namespace_count": 0,
        "unobserved_namespace_count": len(MATERIALIZED_PAYLOAD_REGISTRY),
        "total_requests": 0,
        "hits": 0,
        "misses": 0,
        "hit_rate_pct": 0.0,
        "average_generation_latency_ms": 0.0,
        "stale_regeneration_count": 0,
        "invalidation_count": 0,
        "last_invalidation_at": "",
        "last_invalidation_namespace": "",
        "last_invalidation_reason": "",
        "last_generated_at": "",
        "last_served_at": "",
        "observed_ttl_coverage_pct": 0.0,
        "configured_ttl_coverage_pct": 0.0,
        "observed_namespaces": [],
        "namespaces": [],
        "summary": "No accepted materialized cache traffic proof has been recorded.",
    }


def validate_materialized_cache_traffic_proof(payload: dict, *, proof_path: str = "") -> dict:
    registry = _registry_by_namespace()
    registered_namespaces = set(registry)
    if not isinstance(payload, dict):
        return _default_traffic_proof_snapshot(
            path=proof_path,
            recorded=True,
            blockers=["traffic proof artifact is not a JSON object"],
        )

    blockers: list[str] = []
    source = str(payload.get("source") or payload.get("exercise_source") or "")
    summary_version = _as_int(payload.get("summary_version"))
    namespace_rows = [dict(item) for item in payload.get("namespaces") or [] if isinstance(item, dict)]
    rows_by_namespace = {
        str(item.get("namespace") or ""): item
        for item in namespace_rows
        if str(item.get("namespace") or "")
    }
    observed_namespaces = {
        str(item or "")
        for item in payload.get("observed_namespaces") or []
        if str(item or "")
    }
    if not observed_namespaces:
        observed_namespaces = {
            namespace
            for namespace, row in rows_by_namespace.items()
            if _as_int(row.get("requests")) > 0
        }
    observed_registered = observed_namespaces & registered_namespaces
    missing_namespaces = sorted(registered_namespaces - observed_registered)

    if summary_version < 1:
        blockers.append("summary_version is missing or unsupported")
    if source != MATERIALIZED_TRAFFIC_PROOF_SOURCE:
        blockers.append(f"source is not {MATERIALIZED_TRAFFIC_PROOF_SOURCE}")
    if _as_int(payload.get("registered_namespace_count")) != len(registered_namespaces):
        blockers.append("registered namespace count does not match the current registry")
    if missing_namespaces:
        blockers.append(f"missing namespace telemetry: {', '.join(missing_namespaces[:6])}")
    if _as_int(payload.get("observed_namespace_count")) < len(registered_namespaces):
        blockers.append("observed namespace count does not cover the full registry")

    required_request_count = len(registered_namespaces) * MATERIALIZED_TRAFFIC_PROOF_MIN_REQUESTS_PER_NAMESPACE
    total_requests = _as_int(payload.get("total_requests"))
    if total_requests < required_request_count:
        blockers.append(f"total request sample is below {required_request_count}")
    if _as_float(payload.get("hit_rate_pct")) <= 0:
        blockers.append("cache hit telemetry is missing")
    if _as_float(payload.get("observed_ttl_coverage_pct")) < 100.0:
        blockers.append("observed TTL coverage is incomplete")
    if _as_int(payload.get("stale_regeneration_count")) <= 0:
        blockers.append("stale regeneration telemetry is missing")
    if _as_int(payload.get("invalidation_count")) <= 0:
        blockers.append("cache invalidation telemetry is missing")
    if not str(payload.get("last_invalidation_reason") or "").strip():
        blockers.append("last invalidation reason is missing")
    if _as_float(payload.get("average_generation_latency_ms"), -1.0) < 0:
        blockers.append("average generation latency is missing")

    for namespace in sorted(registered_namespaces):
        row = rows_by_namespace.get(namespace)
        if not row:
            blockers.append(f"{namespace} row is missing")
            continue
        if _as_int(row.get("requests")) < MATERIALIZED_TRAFFIC_PROOF_MIN_REQUESTS_PER_NAMESPACE:
            blockers.append(f"{namespace} has fewer than {MATERIALIZED_TRAFFIC_PROOF_MIN_REQUESTS_PER_NAMESPACE} requests")
        if _as_int(row.get("hits")) < 1:
            blockers.append(f"{namespace} has no cache hit")
        if _as_int(row.get("misses")) < 1:
            blockers.append(f"{namespace} has no cache miss")
        if _as_int(row.get("configured_ttl_seconds")) <= 0:
            blockers.append(f"{namespace} configured TTL is missing")
        if _as_int(row.get("observed_ttl_seconds")) <= 0 or not bool(row.get("ttl_observed")):
            blockers.append(f"{namespace} observed TTL is missing")
        if not str(row.get("last_revision_key") or "").strip():
            blockers.append(f"{namespace} revision key is missing")
        if not str(row.get("last_generated_at") or "").strip():
            blockers.append(f"{namespace} generated_at is missing")
        if not str(row.get("last_served_at") or "").strip():
            blockers.append(f"{namespace} served_at is missing")
        if _as_float(row.get("average_generation_latency_ms"), -1.0) < 0:
            blockers.append(f"{namespace} generation latency is missing")

    accepted = not blockers
    return {
        "path": proof_path,
        "recorded": True,
        "accepted": accepted,
        "state": "accepted" if accepted else "failed",
        "blockers": blockers,
        "summary_version": summary_version,
        "source": source,
        "generated_at_utc": str(payload.get("generated_at_utc") or ""),
        "registered_namespace_count": len(registered_namespaces),
        "observed_namespace_count": len(observed_registered),
        "unobserved_namespace_count": max(len(registered_namespaces) - len(observed_registered), 0),
        "total_requests": total_requests,
        "hits": _as_int(payload.get("hits")),
        "misses": _as_int(payload.get("misses")),
        "hit_rate_pct": round(_as_float(payload.get("hit_rate_pct")), 1),
        "average_generation_latency_ms": round(_as_float(payload.get("average_generation_latency_ms")), 2),
        "stale_regeneration_count": _as_int(payload.get("stale_regeneration_count")),
        "invalidation_count": _as_int(payload.get("invalidation_count")),
        "last_invalidation_at": str(payload.get("last_invalidation_at") or ""),
        "last_invalidation_namespace": str(payload.get("last_invalidation_namespace") or ""),
        "last_invalidation_reason": str(payload.get("last_invalidation_reason") or ""),
        "last_generated_at": str(payload.get("last_generated_at") or ""),
        "last_served_at": str(payload.get("last_served_at") or ""),
        "observed_ttl_coverage_pct": round(_as_float(payload.get("observed_ttl_coverage_pct")), 1),
        "configured_ttl_coverage_pct": round(_as_float(payload.get("configured_ttl_coverage_pct")), 1),
        "observed_namespaces": sorted(observed_registered),
        "namespaces": [rows_by_namespace[namespace] for namespace in sorted(registered_namespaces) if namespace in rows_by_namespace],
        "summary": (
            f"Accepted materialized cache traffic proof covers {len(observed_registered)}/{len(registered_namespaces)} "
            f"namespace(s) across {total_requests} request(s)."
            if accepted
            else f"Materialized cache traffic proof is present but not accepted: {'; '.join(blockers[:3])}."
        ),
    }


def load_materialized_cache_traffic_proof() -> dict:
    path = materialized_cache_traffic_proof_path()
    path_label = str(path)
    if not _should_load_default_traffic_proof():
        return _default_traffic_proof_snapshot(path=path_label, blockers=["traffic proof loading is disabled for default Django test runs"])
    if not path.exists():
        return _default_traffic_proof_snapshot(path=path_label)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _default_traffic_proof_snapshot(
            path=path_label,
            recorded=True,
            blockers=[f"traffic proof artifact is unreadable: {exc}"],
        )
    return validate_materialized_cache_traffic_proof(payload, proof_path=path_label)


def materialized_cache_health_snapshot(*, include_traffic_proof: bool = True) -> dict:
    registry = _registry_by_namespace()
    observed_namespaces = set(cache.get(MATERIALIZED_NAMESPACE_INDEX_KEY) or [])
    namespaces = sorted(set(registry) | observed_namespaces)
    namespace_rows = []
    total_requests = 0
    total_hits = 0
    total_misses = 0
    stale_regeneration_count = 0
    invalidation_count = 0
    total_generation_latency_ms = 0.0
    generation_count = 0
    observed_ttl_count = 0
    configured_ttl_count = 0
    last_invalidation = {"namespace": "", "at": "", "reason": ""}
    last_generated_at = ""
    last_served_at = ""

    for namespace in namespaces:
        registered = registry.get(namespace, {"namespace": namespace, "path": "unknown", "owner": "unknown", "ttl_seconds": 0})
        stats = dict(cache.get(_namespace_stats_key(namespace)) or {})
        requests = int(stats.get("requests") or 0)
        hits = int(stats.get("hits") or 0)
        misses = int(stats.get("misses") or 0)
        invalidations = int(stats.get("invalidations") or 0)
        namespace_generation_count = int(stats.get("generation_count") or 0)
        namespace_generation_latency = float(stats.get("total_generation_latency_ms") or 0)
        ttl_seconds_values = [int(value) for value in stats.get("ttl_seconds_values") or [] if int(value) > 0]
        configured_ttl = int(registered.get("ttl_seconds") or 0)
        ttl_observed = bool(ttl_seconds_values)
        if ttl_observed:
            observed_ttl_count += 1
        if configured_ttl > 0:
            configured_ttl_count += 1
        total_requests += requests
        total_hits += hits
        total_misses += misses
        stale_regeneration_count += int(stats.get("stale_regenerations") or 0)
        invalidation_count += invalidations
        generation_count += namespace_generation_count
        total_generation_latency_ms += namespace_generation_latency
        if stats.get("last_generated_at") and stats["last_generated_at"] > last_generated_at:
            last_generated_at = stats["last_generated_at"]
        if stats.get("last_served_at") and stats["last_served_at"] > last_served_at:
            last_served_at = stats["last_served_at"]
        if stats.get("last_invalidation_at") and stats["last_invalidation_at"] > last_invalidation["at"]:
            last_invalidation = {
                "namespace": namespace,
                "at": stats["last_invalidation_at"],
                "reason": stats.get("last_invalidation_reason") or "",
            }
        namespace_rows.append(
            {
                "namespace": namespace,
                "path": registered.get("path") or "unknown",
                "owner": registered.get("owner") or "unknown",
                "configured_ttl_seconds": configured_ttl,
                "observed_ttl_seconds": ttl_seconds_values[-1] if ttl_seconds_values else 0,
                "ttl_observed": ttl_observed,
                "requests": requests,
                "hits": hits,
                "misses": misses,
                "hit_rate_pct": round((hits / requests) * 100, 1) if requests else 0.0,
                "stale_regenerations": int(stats.get("stale_regenerations") or 0),
                "invalidations": invalidations,
                "average_generation_latency_ms": round(namespace_generation_latency / namespace_generation_count, 2)
                if namespace_generation_count
                else 0.0,
                "last_cache_status": stats.get("last_cache_status") or "unobserved",
                "last_revision_key": stats.get("last_revision_key") or "",
                "last_generated_at": stats.get("last_generated_at") or "",
                "last_served_at": stats.get("last_served_at") or "",
                "last_invalidation_at": stats.get("last_invalidation_at") or "",
                "last_invalidation_reason": stats.get("last_invalidation_reason") or "",
            }
        )

    registered_count = len(registry)
    live_observed_count = sum(1 for item in namespace_rows if item["requests"] > 0)
    live_unobserved_count = max(registered_count - live_observed_count, 0)
    live_hit_rate_pct = round((total_hits / total_requests) * 100, 1) if total_requests else 0.0
    live_average_generation_latency_ms = round(total_generation_latency_ms / generation_count, 2) if generation_count else 0.0
    live_configured_ttl_coverage_pct = round((configured_ttl_count / registered_count) * 100, 1) if registered_count else 0.0
    live_observed_ttl_coverage_pct = round((observed_ttl_count / registered_count) * 100, 1) if registered_count else 0.0
    configured_ttl_ready = registered_count > 0 and configured_ttl_count == registered_count
    live_runtime_telemetry_ready = registered_count > 0 and live_observed_count == registered_count
    live_traffic_sample_ready = live_runtime_telemetry_ready and total_requests >= registered_count * 2
    traffic_proof = (
        load_materialized_cache_traffic_proof()
        if include_traffic_proof
        else _default_traffic_proof_snapshot(blockers=["traffic proof loading was not requested"])
    )
    traffic_proof_ready = bool(traffic_proof.get("accepted"))
    use_traffic_proof = traffic_proof_ready and _as_int(traffic_proof.get("observed_namespace_count")) >= live_observed_count
    effective_namespace_rows = list(traffic_proof["namespaces"]) if use_traffic_proof else namespace_rows
    observed_count = _as_int(traffic_proof.get("observed_namespace_count")) if use_traffic_proof else live_observed_count
    unobserved_count = max(registered_count - observed_count, 0)
    effective_total_requests = _as_int(traffic_proof.get("total_requests")) if use_traffic_proof else total_requests
    effective_hits = _as_int(traffic_proof.get("hits")) if use_traffic_proof else total_hits
    effective_misses = _as_int(traffic_proof.get("misses")) if use_traffic_proof else total_misses
    effective_hit_rate_pct = _as_float(traffic_proof.get("hit_rate_pct")) if use_traffic_proof else live_hit_rate_pct
    effective_stale_regeneration_count = (
        _as_int(traffic_proof.get("stale_regeneration_count")) if use_traffic_proof else stale_regeneration_count
    )
    effective_invalidation_count = _as_int(traffic_proof.get("invalidation_count")) if use_traffic_proof else invalidation_count
    effective_average_generation_latency_ms = (
        _as_float(traffic_proof.get("average_generation_latency_ms")) if use_traffic_proof else live_average_generation_latency_ms
    )
    effective_observed_ttl_coverage_pct = (
        _as_float(traffic_proof.get("observed_ttl_coverage_pct")) if use_traffic_proof else live_observed_ttl_coverage_pct
    )
    effective_last_invalidation_at = (
        str(traffic_proof.get("last_invalidation_at") or "") if use_traffic_proof else last_invalidation["at"]
    )
    effective_last_invalidation_reason = (
        str(traffic_proof.get("last_invalidation_reason") or "") if use_traffic_proof else last_invalidation["reason"]
    )
    effective_last_invalidation_namespace = (
        str(traffic_proof.get("last_invalidation_namespace") or "") if use_traffic_proof else last_invalidation["namespace"]
    )
    effective_last_generated_at = str(traffic_proof.get("last_generated_at") or "") if use_traffic_proof else last_generated_at
    effective_last_served_at = str(traffic_proof.get("last_served_at") or "") if use_traffic_proof else last_served_at
    runtime_telemetry_ready = live_runtime_telemetry_ready or traffic_proof_ready
    traffic_sample_ready = live_traffic_sample_ready or traffic_proof_ready
    maturity_blockers = []
    if not configured_ttl_ready:
        maturity_blockers.append("not every registered namespace has a configured TTL")
    if unobserved_count:
        maturity_blockers.append(f"{unobserved_count} registered namespace(s) do not have runtime telemetry")
    if not traffic_sample_ready:
        maturity_blockers.append("namespace traffic sample is not broad enough for production cache sizing")
    maturity_blockers.append("sustained production cache sizing and TTL tuning still need real traffic before full maturity")
    telemetry_source = "traffic_proof" if use_traffic_proof else "live_cache"
    if use_traffic_proof:
        summary = (
            f"Accepted materialized cache traffic proof covers {observed_count}/{registered_count} namespace(s); "
            f"{effective_hit_rate_pct}% hit rate across {effective_total_requests} request(s), "
            f"{effective_stale_regeneration_count} stale regeneration(s), and "
            f"{effective_invalidation_count} invalidation(s)."
        )
    else:
        summary = (
            f"{live_observed_count}/{registered_count} materialized namespace(s) have runtime telemetry; "
            f"{live_hit_rate_pct}% hit rate across {total_requests} request(s), {stale_regeneration_count} "
            f"stale regeneration(s), and {invalidation_count} invalidation(s)."
        )
    return {
        "registered_namespace_count": registered_count,
        "observed_namespace_count": observed_count,
        "unobserved_namespace_count": unobserved_count,
        "live_observed_namespace_count": live_observed_count,
        "live_unobserved_namespace_count": live_unobserved_count,
        "total_requests": effective_total_requests,
        "hits": effective_hits,
        "misses": effective_misses,
        "hit_rate_pct": round(effective_hit_rate_pct, 1),
        "stale_regeneration_count": effective_stale_regeneration_count,
        "invalidation_count": effective_invalidation_count,
        "average_generation_latency_ms": round(effective_average_generation_latency_ms, 2),
        "configured_ttl_coverage_pct": live_configured_ttl_coverage_pct,
        "observed_ttl_coverage_pct": round(effective_observed_ttl_coverage_pct, 1),
        "last_invalidation_at": effective_last_invalidation_at,
        "last_invalidation_reason": effective_last_invalidation_reason,
        "last_invalidation_namespace": effective_last_invalidation_namespace,
        "last_generated_at": effective_last_generated_at,
        "last_served_at": effective_last_served_at,
        "configured_ttl_ready": configured_ttl_ready,
        "observability_ready": configured_ttl_ready and observed_count > 0,
        "runtime_telemetry_ready": runtime_telemetry_ready,
        "traffic_sample_ready": traffic_sample_ready,
        "live_runtime_telemetry_ready": live_runtime_telemetry_ready,
        "live_traffic_sample_ready": live_traffic_sample_ready,
        "traffic_proof_ready": traffic_proof_ready,
        "traffic_proof": traffic_proof,
        "telemetry_source": telemetry_source,
        "maturity_blockers": maturity_blockers,
        "production_mature": False,
        "summary": summary,
        "namespaces": effective_namespace_rows,
        "live_namespaces": namespace_rows,
    }
