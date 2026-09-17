"""Schedules used by the single native Huey consumer (times are UTC)."""
from huey import crontab
import os
from huey.contrib.djhuey import db_periodic_task, db_task
from django.core.cache import cache
from django.utils import timezone

from alfred_ai.tasks import production_probe_task  # register the end-to-end probe
from apps.expenses.tasks import retry_low_confidence_statement_uploads, retry_statement_upload_task
from apps.integrations.tasks import (
    cleanup_verified_external_intelligence, refresh_verified_external_intelligence,
)
from apps.ml_engine.continual.tasks import run_global_training_cycle


@db_periodic_task(crontab(minute="*"))
def native_scheduler_heartbeat():
    cache.set("native:scheduler-heartbeat", {
        "time": timezone.now().timestamp(), "instance": os.environ.get("ALFRED_NATIVE_INSTANCE"),
    }, timeout=180)


@db_task(retries=2, retry_delay=1)
def native_runtime_probe(probe_id, fail_once=False):
    """A harmless queue/retry diagnostic, also used by the verification script."""
    key = f"native:probe:{probe_id}"
    cache.add(key, 0, timeout=300)
    attempts = cache.incr(key)
    if fail_once and attempts == 1:
        raise RuntimeError("Intentional transient failure for the native retry diagnostic")
    return {"probe_id": probe_id, "attempts": attempts, "worker_pid": os.getpid()}


@db_periodic_task(crontab(minute="*/20"))
def native_document_retry():
    return retry_low_confidence_statement_uploads(batch_size=3)


@db_periodic_task(crontab(minute="0", hour="*/6"))
def native_intelligence_refresh():
    return refresh_verified_external_intelligence(batch_size=75)


@db_periodic_task(crontab(minute="15", hour="2"))
def native_intelligence_cleanup():
    return cleanup_verified_external_intelligence(retention_days=90)


@db_periodic_task(crontab(minute="0", hour="3"))
def native_nightly_training():
    return run_global_training_cycle()
