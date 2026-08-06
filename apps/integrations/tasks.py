from celery import shared_task

from apps.integrations.services import verified_intelligence


@shared_task
def refresh_verified_external_intelligence(batch_size: int | None = None):
    return verified_intelligence.refresh_due_records(batch_size=batch_size)


@shared_task
def cleanup_verified_external_intelligence(retention_days: int = 90):
    verified_intelligence.cleanup_stale(retention_days=retention_days)
    return {"status": "ok", "retention_days": retention_days}
