from __future__ import annotations

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone


CELERY_PROBE_CACHE_PREFIX = "alfred:production-readiness:celery-probe"
CELERY_BEAT_HEARTBEAT_CACHE_KEY = "alfred:production-readiness:celery-beat-heartbeat"


@shared_task(name="alfred_ai.tasks.production_probe_task")
def production_probe_task(probe_id: str) -> dict:
    payload = {
        "probe_id": str(probe_id),
        "status": "ok",
        "executed_at": timezone.now().isoformat(),
    }
    cache.set(f"{CELERY_PROBE_CACHE_PREFIX}:{probe_id}", payload, timeout=300)
    return payload


@shared_task(name="alfred_ai.tasks.production_beat_heartbeat")
def production_beat_heartbeat() -> dict:
    payload = {
        "task": "alfred_ai.tasks.production_beat_heartbeat",
        "status": "ok",
        "worker_executed_at": timezone.now().isoformat(),
    }
    cache.set(CELERY_BEAT_HEARTBEAT_CACHE_KEY, payload, timeout=86400)
    return payload
