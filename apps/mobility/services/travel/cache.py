"""One cache/budget boundary for every travel adapter. No network in transactions."""
from copy import deepcopy
from datetime import timedelta
import hashlib
import json
from time import monotonic
from uuid import uuid4

import requests
from django.db.models import Avg, Count, Max, Q
from django.utils import timezone

from apps.integrations.models import VerifiedExternalInsight
from apps.mobility.models import TravelProviderRequest, TravelProviderState
from .providers.base import ProviderError, ProviderResult


def _cache_result(record, error=""):
    data = deepcopy(record.payload)
    stale = record.stale_after <= timezone.now()
    data.update(cached=True, stale=stale, error=error,
                status="stale" if stale else "ok",
                freshness="CACHED" if stale else "RECENTLY_VERIFIED")
    if stale:
        data["confidence"] = "UNKNOWN"
    return ProviderResult(**data)


def query(provider, parameters, *, force=False):
    try:
        parameters = provider.parameters(parameters)
    except (ValueError, TypeError, ProviderError):
        return ProviderResult(provider.name, provider.category, error="invalid_parameters")
    digest = hashlib.sha256((provider.cache_partition+json.dumps(parameters, sort_keys=True, allow_nan=False)).encode()).hexdigest()
    key = f"{provider.name}:{provider.category}:{provider.version}:{digest}"
    record = VerifiedExternalInsight.objects.filter(scope="travel_provider", cache_key=key, is_active=True).first()

    def log(status, network=False, latency=0, error=""):
        TravelProviderRequest.objects.create(provider=provider.name, category=provider.category,
            cache_key=key, parameters=parameters, status=status if len(status) <= 32 else "failed", network_call=network,
            latency_ms=latency, error=error)

    if record and record.is_fresh and not force:
        log("cache_hit")
        return _cache_result(record)

    def unavailable(code):
        log("unavailable", error=code)
        if record:
            return _cache_result(record, code)
        return ProviderResult(provider.name, provider.category, request_parameters=parameters,
            source_url=provider.source_url, attribution=provider.attribution, error=code)

    reason = provider.unavailable_reason()
    if reason:
        return unavailable(reason)
    now = timezone.now()
    state, _ = TravelProviderState.objects.get_or_create(provider=provider.name)
    token = str(uuid4())
    claimed = TravelProviderState.objects.filter(pk=state.pk).filter(
        Q(lease_until__isnull=True) | Q(lease_until__lte=now)).filter(
        Q(next_allowed_at__isnull=True) | Q(next_allowed_at__lte=now)).update(
        lease_token=token, lease_until=now+timedelta(seconds=90))
    if not claimed:
        return unavailable("provider_busy_or_backoff")
    start = monotonic()
    delay = provider.min_interval
    called = False
    event = None
    try:
        requests_qs = TravelProviderRequest.objects.filter(provider=provider.name, network_call=True)
        starts = {"minute": now-timedelta(minutes=1), "hour": now-timedelta(hours=1),
                  "day": now.replace(hour=0, minute=0, second=0, microsecond=0),
                  "month": now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)}
        for period, limit in provider.limits.items():
            if requests_qs.filter(created_at__gte=starts[period]).count() >= limit:
                return unavailable("local_quota_exhausted")
        called = True
        event = TravelProviderRequest.objects.create(provider=provider.name, category=provider.category,
            cache_key=key, parameters=parameters, status="in_progress", network_call=True)
        raw, response_hash = provider.fetch(parameters)
        payload = provider.normalize(raw, parameters)
        if not isinstance(payload, dict) or not payload:
            raise ProviderError("malformed_response")
        json.dumps(payload, allow_nan=False)
        retrieved = timezone.now()
        expires = provider.expires_at(payload, parameters, retrieved)
        result = ProviderResult(provider.name, provider.category, success=True, status="ok",
            freshness="LIVE", confidence="LIKELY", payload=payload,
            source_url=provider.source_url, attribution=provider.attribution,
            retrieved_at=retrieved.isoformat(), verified_at=retrieved.isoformat(),
            expires_at=expires.isoformat(),
            response_hash=response_hash, request_parameters=parameters)
        VerifiedExternalInsight.objects.update_or_create(scope="travel_provider", cache_key=key,
            defaults={"title": f"{provider.category} from {provider.name}", "source_name": provider.name,
                "source_url": provider.source_url, "payload": result.as_dict(), "checksum": response_hash,
                "status": "fresh", "fetched_at": retrieved, "verified_at": retrieved,
                "stale_after": expires, "is_active": True})
        TravelProviderRequest.objects.filter(pk=event.pk).update(status="ok", latency_ms=round((monotonic()-start)*1000))
        return result
    except requests.Timeout:
        code = "timeout"
    except requests.RequestException:
        code = "network_error"
    except ProviderError as exc:
        code, delay = exc.code, exc.retry_after
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError):
        code = "malformed_response"
    except Exception:
        # Adapter bugs are visible as failures, but don't discard other research.
        # Do not log raw exceptions that can include credentials or private URLs.
        code = "provider_fault"
    finally:
        TravelProviderState.objects.filter(pk=state.pk, lease_token=token).update(
            lease_until=None, lease_token="", next_allowed_at=timezone.now()+timedelta(seconds=delay))
    if event:
        TravelProviderRequest.objects.filter(pk=event.pk).update(status=code if len(code) <= 32 else "failed", error=code, latency_ms=round((monotonic()-start)*1000))
    else:
        log(code, called, round((monotonic()-start)*1000), code)
    if record:
        return _cache_result(record, code)
    return ProviderResult(provider.name, provider.category, status="failed", error=code,
        source_url=provider.source_url, request_parameters=parameters)


def query_with_fallback(providers, parameters, *, force=False):
    attempts, stale = [], None
    for provider in providers:
        result = query(provider, parameters, force=force)
        if result.success and not result.stale:
            result.fallback = attempts
            return result
        if result.success and stale is None:
            stale = result
        attempts.append({"provider": result.provider, "status": result.status, "error": result.error})
    result = stale or ProviderResult("none", providers[0].category if providers else "unknown", error="no_available_provider")
    result.fallback = attempts
    return result


def usage_summary():
    now = timezone.now()
    rows = TravelProviderRequest.objects.filter(created_at__date=now.date()).values("provider").annotate(
        calls_today=Count("id", filter=Q(network_call=True)), requests=Count("id"),
        cache_hits=Count("id", filter=Q(status="cache_hit")),
        failures=Count("id", filter=Q(network_call=True) & ~Q(status="ok")),
        last_call=Max("created_at", filter=Q(network_call=True)),
        average_latency_ms=Avg("latency_ms", filter=Q(network_call=True)))
    remaining = dict(TravelProviderState.objects.values_list("provider", "quota_remaining"))
    return [{**row, "cache_hit_ratio": round(row["cache_hits"]/row["requests"], 3),
             "quota_remaining": remaining.get(row["provider"])} for row in rows]
