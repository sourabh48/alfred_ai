"""Runtime checks appropriate to the local Windows application."""
import os
import time
from math import isfinite
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.db import connection


def native_heartbeat_ready(heartbeat, maximum_age):
    instance = os.environ.get("ALFRED_NATIVE_INSTANCE")
    if not instance or not isinstance(heartbeat, dict) or heartbeat.get("instance") != instance:
        return False
    stamp = heartbeat.get("time")
    return (type(stamp) in (int, float) and isfinite(stamp)
            and 0 <= time.time() - stamp < maximum_age)


def native_readiness_snapshot():
    checks = []

    def check(key, label, ready, detail, action):
        checks.append({"key": key, "label": label, "ready": bool(ready),
                       "status": "ready" if ready else "blocked", "detail": detail,
                       "manual_task": "" if ready else action})

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database_ok = True
    except Exception:
        database_ok = False
    check("database", "Local database", database_ok, "Your account data is stored on this computer.",
          "Restart ALFRED and check the server log if this continues.")
    try:
        key = f"native:readiness:{uuid4().hex}"
        cache.set(key, "ok", timeout=15)
        cache_ok = cache.get(key) == "ok"
        cache.delete(key)
        worker = cache.get("native:worker-heartbeat", {})
        scheduler = cache.get("native:scheduler-heartbeat", {})
    except Exception:
        cache_ok, worker, scheduler = False, {}, {}
    check("cache", "Shared local cache", cache_ok, "Pages and background jobs share current data.", "Restart ALFRED.")
    review_count = 0
    try:
        from huey.contrib.djhuey import HUEY
        review_count = HUEY.storage.sql(
            "SELECT count(*) FROM native_claim WHERE queue=? AND state='review'",
            (HUEY.storage.name,), results=True)[0][0]
    except Exception:
        pass  # Worker/queue health below still determines readiness.
    for key, label, heartbeat, age, detail in (
        ("worker", "Background processing", worker, 15, "Document processing runs separately from the web pages."),
        ("scheduler", "Scheduled jobs", scheduler, 150, "A current scheduler heartbeat confirms automatic retries and scheduled updates."),
    ):
        ready = native_heartbeat_ready(heartbeat, age)
        action = "Allow a minute after startup; restart ALFRED if this persists."
        if key == "worker" and review_count:
            ready = False
            detail = f"{review_count} interrupted job(s) need review before retrying; other background work can continue."
            action = "Run ALFRED.exe jobs to inspect interrupted work; check partial changes before using retry-job."
        check(key, label, ready, detail, action)
    check("local_security", "Local access", not settings.DEBUG and len(settings.SECRET_KEY) >= 50,
          "Debug mode is off and a signing key is configured. Sign in to access your data.",
          "Start ALFRED using its native launcher.")
    ready_checks = [item for item in checks if item["ready"]]
    blocked = [item for item in checks if not item["ready"]]
    tasks = [item["manual_task"] for item in blocked]
    progress = round(100 * len(ready_checks) / len(checks))
    return {
        "progress": progress, "blocker_percent": 100 - progress,
        "ready": not blocked, "maturity_status": "Local runtime ready" if not blocked else "Local runtime needs attention",
        "ready_check_count": len(ready_checks), "total_check_count": len(checks),
        "blocker_count": len(blocked), "blockers": [item["label"] for item in blocked],
        "ready_checks": ready_checks, "blocked_checks": blocked, "checks": checks,
        "manual_tasks": tasks, "manual_task_count": len(tasks), "required_env_vars": [],
        "probe_command": "ALFRED.exe status", "deployment_proof": {}, "deployment_proof_path": "",
        "summary": f"{len(ready_checks)}/{len(checks)} local runtime checks passed. "
                   "ALFRED uses Waitress, Huey and SQLite on this computer.",
    }
