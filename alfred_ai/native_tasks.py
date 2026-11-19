"""Schedules used by the single native Huey consumer (times are UTC)."""
from huey import crontab
import logging
import os
import time
from huey.contrib.djhuey import db_periodic_task, db_task
from django.core.cache import cache
from django.utils import timezone

from alfred_ai.tasks import production_probe_task  # register the end-to-end probe
from apps.expenses.tasks import retry_low_confidence_statement_uploads, retry_statement_upload_task
from apps.integrations.tasks import (
    cleanup_verified_external_intelligence, refresh_verified_external_intelligence,
)
from apps.ml_engine.continual.tasks import run_global_training_cycle
from apps.mobility.tasks import research_travel, resume_travel_research, cleanup_travel_request_history

logger = logging.getLogger(__name__)


@db_periodic_task(crontab(minute="*"))
def native_travel_reminders():
    from apps.mobility.services.travel.reminders import sweep_due
    return sweep_due()


@db_periodic_task(crontab(minute="*/15"))
def native_travel_request_cleanup():
    return cleanup_travel_request_history()


@db_periodic_task(crontab(minute="*/2"))
def native_travel_research_recovery():
    return resume_travel_research()


@db_periodic_task(crontab(hour="2", minute="30"))
def native_brain_finetune():
    """Owner approval 2026-11-20: fine-tune a small local model overnight from the central brain, on this PC only."""
    from alfred_ai.services.ollama_keeper import start_brain_finetune
    return start_brain_finetune()


@db_periodic_task(crontab(minute="*/2"))
def native_ollama_keeper():
    """Ollama stopped on the owner PC on 2026-11-20 and local answers failed until it was started again."""
    from alfred_ai.services.ollama_keeper import ensure_running
    from alfred_ai.services.ollama_keeper import warm_reading_model
    state = ensure_running()
    if state == "started":
        logger.warning("Local Ollama was not answering; started it again.")
    elif state == "running":
        try:
            return state, warm_reading_model()
        except Exception as exc:  # a busy or slow Ollama is retried two minutes later
            logger.info("Travel reading model not warmed: %s", type(exc).__name__)
    return state


@db_periodic_task(crontab(minute="*"))
def native_scheduler_heartbeat():
    cache.set("native:scheduler-heartbeat", {
        "time": timezone.now().timestamp(), "instance": os.environ.get("ALFRED_NATIVE_INSTANCE"),
    }, timeout=180)


@db_task(retries=2, retry_delay=1)
def native_runtime_probe(probe_id, fail_once=False, hold_seconds=0):
    """A harmless queue/retry diagnostic, also used by the verification script."""
    key = f"native:probe:{probe_id}"
    cache.add(key, 0, timeout=300)
    attempts = cache.incr(key)
    if hold_seconds:
        # Bounded pause lets the isolated recovery drill kill an executing job.
        time.sleep(min(max(float(hold_seconds), 0), 30))
    if fail_once and attempts == 1:
        raise RuntimeError("Intentional transient failure for the native retry diagnostic")
    return {"probe_id": probe_id, "attempts": attempts, "worker_pid": os.getpid()}


@db_periodic_task(crontab(minute="*/20"))
def native_document_retry():
    return retry_low_confidence_statement_uploads(batch_size=3)


@db_periodic_task(crontab(minute="0", hour="*/6"))
def native_intelligence_refresh():
    return refresh_verified_external_intelligence(batch_size=75)


@db_periodic_task(crontab(minute="30", hour="7,23"))
def native_fund_value_refresh():
    # AMFI publishes the day's NAVs late in the evening; the morning run catches a late file.
    from apps.investments.services.fund_prices import refresh_fund_values
    return refresh_fund_values()


@db_periodic_task(crontab(minute="45", hour="*/4"))
def native_crypto_value_refresh():
    # One CoinGecko request for every held coin; the public API needs no key at this rate.
    from apps.investments.services.crypto_prices import refresh_crypto_values
    return refresh_crypto_values()


@db_periodic_task(crontab(minute="*"))
def native_private_memory_sync():
    from django.core.management import call_command
    call_command('sync_private_memory', seconds=2, verbosity=0)
    call_command('checkpoint_knowledge_hub', seconds=2, verbosity=0)


def _budget_publication_check():
    # Daily, notice-only: reads which Budget the official site lists; never changes tax rules.
    from apps.integrations.services import verified_intelligence
    return verified_intelligence.budget_publication_check().payload


def _private_memory_cleanup():
    from django.core.management import call_command
    call_command('prune_private_memory', verbosity=0)


def _task_bots():
    # Proposals only; nothing changes until the owner confirms in the app (AI-17).
    from apps.ml_engine.services.task_bots import run_scheduled
    return run_scheduled()


def _research_desk():
    # Suggestions only; the owner accepts or rejects each one, and nothing is ever bought or sold.
    from apps.investments.services.research_desk import run_scheduled
    return run_scheduled()


def _retrieval_quality():
    from django.conf import settings
    from apps.ml_engine.services.retrieval_quality import weekly_check, weekly_due
    # Daily slot, weekly work: catch-up still runs it when the PC was off on the day.
    return weekly_check() if settings.ALFRED_WEEKLY_QUALITY_CHECK and weekly_due() else {"status": "not_due"}


DAILY_JOBS = {
    "budget-publication-check": _budget_publication_check,
    "intelligence-cleanup": lambda: cleanup_verified_external_intelligence(retention_days=90),
    "private-memory-cleanup": _private_memory_cleanup,
    "nightly-training": lambda: run_global_training_cycle(),
    "task-bots": _task_bots,
    "research-desk": _research_desk,
    "retrieval-quality": _retrieval_quality,
}
MISSED_AFTER = 25 * 3600  # A daily job with no success for this long missed its slot, usually because the PC was off.
RETRY_AFTER = 3600


def _run_daily(name):
    """Run one daily job at a time and record when it last succeeded."""
    if not cache.add(f"native:daily:{name}:running", 1, timeout=2 * 3600):
        return {"status": "busy"}
    try:
        # timeout=None keeps these across restarts; if the cache evicts one, the job just runs again.
        cache.set(f"native:daily:{name}:attempt", time.time(), timeout=None)
        result = DAILY_JOBS[name]()
        cache.set(f"native:daily:{name}:success", time.time(), timeout=None)
        return result
    finally:
        cache.delete(f"native:daily:{name}:running")


@db_periodic_task(crontab(minute="45", hour="1"))
def native_budget_publication_check():
    return _run_daily("budget-publication-check")


@db_periodic_task(crontab(minute="15", hour="2"))
def native_intelligence_cleanup():
    return _run_daily("intelligence-cleanup")


@db_periodic_task(crontab(minute="0", hour="3"))
def native_private_memory_cleanup():
    return _run_daily("private-memory-cleanup")


@db_periodic_task(crontab(minute="0", hour="3"))
def native_nightly_training():
    return _run_daily("nightly-training")


@db_periodic_task(crontab(minute="*/15"))
def native_daily_catch_up():
    """Run daily jobs whose scheduled time passed while ALFRED was not running."""
    now, ran = time.time(), []
    for name in DAILY_JOBS:
        success = cache.get(f"native:daily:{name}:success") or 0
        attempt = cache.get(f"native:daily:{name}:attempt") or 0
        if now - success < MISSED_AFTER or now - attempt < RETRY_AFTER:
            continue
        try:
            if _run_daily(name) != {"status": "busy"}:
                ran.append(name)
        except Exception as error:  # One failing job must not stop the others; it is retried after RETRY_AFTER.
            logger.warning("Daily job %s failed during catch-up (%s)", name, type(error).__name__)
    return {"status": "completed", "processed": len(ran)}


@db_periodic_task(crontab(minute="0", hour="13"))  # after Indian markets close (UTC)
def native_research_desk():
    return _run_daily("research-desk")


@db_periodic_task(crontab(minute="30", hour="4"))
def native_retrieval_quality():
    return _run_daily("retrieval-quality")


@db_periodic_task(crontab(minute="*/5"))
def native_research_debate():
    """The local AI debates new research calls in the background, a few minutes at a time (owner request 2026-11-18)."""
    from apps.investments.services.research_debate import debate_due
    return debate_due()


@db_periodic_task(crontab(minute="30"))  # every hour; see task_bots.NETWORK_BOTS for what stays daily
def native_task_bots():
    return _run_daily("task-bots")


@db_periodic_task(crontab(minute="*/30"))
def native_google_sync():
    """Phone sync to Google Calendar and Tasks for owners who connected it (owner decision 2026-11-18)."""
    from alfred_ai.services.google_sync import sync_everyone
    try:
        sync_everyone()
    except Exception:  # never let one bad run stop the scheduler; each owner's error is kept for Settings
        logging.getLogger(__name__).warning("Google phone sync run failed.", exc_info=True)
