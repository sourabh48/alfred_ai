from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from django.conf import settings


PRODUCTION_DEPLOYMENT_PROOF_ENV = "ALFRED_PRODUCTION_DEPLOYMENT_PROOF"
PRODUCTION_DEPLOYMENT_PROOF_DEFAULT_PATH = "artifacts/ops/production_readiness_summary.json"
PRODUCTION_DEPLOYMENT_PROOF_SOURCE = "production_deployment_probe"
REQUIRED_CELERY_SCHEDULE = {
    "alfred-nightly-training": "apps.ml_engine.continual.tasks.run_global_training_cycle",
    "statement-review-retry": "apps.expenses.tasks.retry_low_confidence_statement_uploads",
    "verified-intelligence-refresh": "apps.integrations.tasks.refresh_verified_external_intelligence",
    "verified-intelligence-cleanup": "apps.integrations.tasks.cleanup_verified_external_intelligence",
}
REQUIRED_PRODUCTION_ENV_VARS = (
    "ALFRED_LOCAL_RUNTIME=false",
    "DEBUG=false",
    "DJANGO_SECRET_KEY",
    "ALLOWED_HOSTS",
    "CSRF_TRUSTED_ORIGINS",
    "DB_ENGINE",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "DB_HOST",
    "CACHE_BACKEND",
    "CACHE_LOCATION",
    "REDIS_URL",
)


def _project_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return Path(settings.BASE_DIR) / path


def production_deployment_proof_path() -> Path:
    configured_path = os.environ.get(PRODUCTION_DEPLOYMENT_PROOF_ENV, "").strip()
    if configured_path:
        return _project_path(configured_path)
    return _project_path(PRODUCTION_DEPLOYMENT_PROOF_DEFAULT_PATH)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "ok", "ready", "passed"}


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _env_value(name: str) -> str:
    return str(os.environ.get(name) or "").strip()


def _is_sqlite_backend(engine: str) -> bool:
    return "sqlite" in str(engine or "").lower()


def _is_shared_cache_backend(backend: str) -> bool:
    backend_lower = str(backend or "").lower()
    if not backend_lower:
        return False
    local_backends = ("locmem", "dummy", "filebased")
    return not any(token in backend_lower for token in local_backends)


def _is_redis_url(value: str) -> bool:
    return str(value or "").strip().lower().startswith(("redis://", "rediss://"))


def _is_localhost_url(value: str) -> bool:
    lowered = str(value or "").lower()
    return "localhost" in lowered or "127.0.0.1" in lowered


def _check_item(*, key: str, label: str, ready: bool, detail: str, manual_task: str) -> dict:
    return {
        "key": key,
        "label": label,
        "ready": bool(ready),
        "status": "ready" if ready else "blocked",
        "detail": detail,
        "manual_task": "" if ready else manual_task,
    }


def _default_deployment_proof(*, path: str = "", recorded: bool = False, blockers: list[str] | None = None) -> dict:
    return {
        "path": path,
        "recorded": recorded,
        "accepted": False,
        "state": "missing" if not recorded else "failed",
        "blockers": blockers or ["production deployment proof artifact missing"],
        "summary_version": 0,
        "source": "",
        "generated_at_utc": "",
        "sections": {
            "database": {"ready": False},
            "cache": {"ready": False},
            "celery": {"ready": False},
            "security": {"ready": False},
            "browser_ci": {"ready": False},
            "cache_traffic": {"ready": False},
        },
        "summary": "No accepted production deployment proof has been recorded.",
    }


def validate_production_deployment_proof(payload: dict, *, proof_path: str = "") -> dict:
    if not isinstance(payload, dict):
        return _default_deployment_proof(
            path=proof_path,
            recorded=True,
            blockers=["production deployment proof artifact is not a JSON object"],
        )

    blockers: list[str] = []
    source = str(payload.get("source") or "")
    summary_version = _as_int(payload.get("summary_version"))
    generated_at_utc = str(payload.get("generated_at_utc") or "")
    environment = str(payload.get("environment") or "").lower()

    if source != PRODUCTION_DEPLOYMENT_PROOF_SOURCE:
        blockers.append(f"source is not {PRODUCTION_DEPLOYMENT_PROOF_SOURCE}")
    if summary_version < 1:
        blockers.append("summary_version is missing or unsupported")
    if not generated_at_utc:
        blockers.append("generated_at_utc is missing")
    if environment != "production":
        blockers.append("environment is not production")

    database = dict(payload.get("database") or {})
    database_engine = str(database.get("engine") or "")
    database_ready = (
        bool(database_engine)
        and not _is_sqlite_backend(database_engine)
        and _as_bool(database.get("connection_usable"))
        and _as_bool(database.get("migrations_current"))
    )
    if not database_ready:
        blockers.append("database proof must use a non-sqlite backend with usable connection and current migrations")

    cache = dict(payload.get("cache") or {})
    cache_backend = str(cache.get("backend") or "")
    cache_ready = (
        _is_shared_cache_backend(cache_backend)
        and _as_bool(cache.get("shared_backend"))
        and _as_bool(cache.get("read_write_ok"))
    )
    if not cache_ready:
        blockers.append("cache proof must use a shared backend with read/write health")

    celery = dict(payload.get("celery") or {})
    celery_broker = str(celery.get("broker_url") or "")
    celery_ready = (
        _is_redis_url(celery_broker)
        and _as_bool(celery.get("worker_ping_ok"))
        and _as_bool(celery.get("beat_schedule_ok"))
        and _as_int(celery.get("scheduled_task_count")) >= len(REQUIRED_CELERY_SCHEDULE)
    )
    if not celery_ready:
        blockers.append("Celery proof must show Redis broker, worker ping, beat schedule, and required task count")

    security = dict(payload.get("security") or {})
    security_ready = (
        _as_bool(security.get("debug")) is False
        and _as_bool(security.get("allowed_hosts_configured"))
        and _as_bool(security.get("secret_key_configured"))
        and _as_bool(security.get("secure_cookies"))
        and _as_bool(security.get("ssl_redirect"))
        and _as_int(security.get("hsts_seconds")) > 0
    )
    if not security_ready:
        blockers.append("security proof must show DEBUG=false, hosts, secret key, HTTPS redirect, secure cookies, and HSTS")

    browser_ci = dict(payload.get("browser_ci") or {})
    browser_ready = _as_bool(browser_ci.get("ci_chrome_no_skip"))
    if not browser_ready:
        blockers.append("browser CI proof must show Chrome required-browser execution with zero skipped Selenium tests")

    cache_traffic = dict(payload.get("cache_traffic") or {})
    cache_traffic_ready = (
        _as_bool(cache_traffic.get("production_like"))
        and _as_int(cache_traffic.get("registered_namespace_count")) > 0
        and _as_int(cache_traffic.get("observed_namespace_count"))
        >= _as_int(cache_traffic.get("registered_namespace_count"))
        and _as_bool(cache_traffic.get("shared_cache_backend"))
    )
    if not cache_traffic_ready:
        blockers.append("cache traffic proof must be production-like, shared-cache backed, and cover every namespace")

    sections = {
        "database": {"ready": database_ready, **database},
        "cache": {"ready": cache_ready, **cache},
        "celery": {"ready": celery_ready, **celery},
        "security": {"ready": security_ready, **security},
        "browser_ci": {"ready": browser_ready, **browser_ci},
        "cache_traffic": {"ready": cache_traffic_ready, **cache_traffic},
    }
    accepted = not blockers
    return {
        "path": proof_path,
        "recorded": True,
        "accepted": accepted,
        "state": "accepted" if accepted else "failed",
        "blockers": blockers,
        "summary_version": summary_version,
        "source": source,
        "generated_at_utc": generated_at_utc,
        "sections": sections,
        "summary": (
            "Accepted production deployment proof covers database, cache, Celery, security, browser CI, and cache traffic."
            if accepted
            else f"Production deployment proof is present but not accepted: {'; '.join(blockers[:3])}."
        ),
    }


def load_production_deployment_proof() -> dict:
    path = production_deployment_proof_path()
    path_label = str(path)
    if not path.exists():
        return _default_deployment_proof(path=path_label)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _default_deployment_proof(
            path=path_label,
            recorded=True,
            blockers=[f"production deployment proof artifact is unreadable: {exc}"],
        )
    return validate_production_deployment_proof(payload, proof_path=path_label)


def _database_config_check() -> dict:
    database = dict(settings.DATABASES.get("default") or {})
    engine = str(database.get("ENGINE") or "")
    name = str(database.get("NAME") or "")
    ready = bool(engine and name) and not _is_sqlite_backend(engine) and bool(_env_value("DB_ENGINE"))
    return _check_item(
        key="database_config",
        label="Production database config",
        ready=ready,
        detail=f"Database engine is {engine or 'not configured'}; local sqlite is not production-ready.",
        manual_task="Configure PostgreSQL or another production database through DB_ENGINE, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, and DB_PORT, then run migrations.",
    )


def _cache_config_check() -> dict:
    cache_config = dict(settings.CACHES.get("default") or {})
    backend = str(cache_config.get("BACKEND") or "")
    location = str(cache_config.get("LOCATION") or "")
    ready = _is_shared_cache_backend(backend) and bool(_env_value("CACHE_BACKEND")) and bool(_env_value("CACHE_LOCATION"))
    return _check_item(
        key="shared_cache_config",
        label="Shared cache config",
        ready=ready,
        detail=f"Cache backend is {backend or 'not configured'} at {location or 'not configured'}; local-memory cache is development-only.",
        manual_task="Configure a shared cache backend such as django.core.cache.backends.redis.RedisCache with CACHE_BACKEND and CACHE_LOCATION.",
    )


def _celery_config_check() -> dict:
    broker_url = str(getattr(settings, "CELERY_BROKER_URL", "") or "")
    result_backend = str(getattr(settings, "CELERY_RESULT_BACKEND", "") or "")
    schedule = dict(getattr(settings, "CELERY_BEAT_SCHEDULE", {}) or {})
    missing_tasks = [
        key
        for key, task_name in REQUIRED_CELERY_SCHEDULE.items()
        if str((schedule.get(key) or {}).get("task") or "") != task_name
    ]
    ready = (
        _is_redis_url(broker_url)
        and _is_redis_url(result_backend)
        and not _is_localhost_url(broker_url)
        and not _is_localhost_url(result_backend)
        and bool(_env_value("REDIS_URL"))
        and not missing_tasks
    )
    detail = (
        f"Celery broker/result backend: {broker_url or 'not configured'}; "
        f"missing schedules: {', '.join(missing_tasks) if missing_tasks else 'none'}."
    )
    return _check_item(
        key="celery_config",
        label="Celery config",
        ready=ready,
        detail=detail,
        manual_task="Configure REDIS_URL to a deployed Redis instance and keep the training, retry, refresh, and cleanup beat schedules present.",
    )


def _security_config_check() -> dict:
    allowed_hosts = list(getattr(settings, "ALLOWED_HOSTS", []) or [])
    secret_key = str(getattr(settings, "SECRET_KEY", "") or "")
    local_secret = secret_key == "alfred-local-development-key"
    ready = (
        not bool(getattr(settings, "LOCAL_RUNTIME", False))
        and not bool(getattr(settings, "DEBUG", True))
        and bool(_env_value("DJANGO_SECRET_KEY"))
        and not local_secret
        and bool(allowed_hosts)
        and "*" not in allowed_hosts
        and bool(getattr(settings, "SECURE_SSL_REDIRECT", False))
        and bool(getattr(settings, "SESSION_COOKIE_SECURE", False))
        and bool(getattr(settings, "CSRF_COOKIE_SECURE", False))
        and _as_int(getattr(settings, "SECURE_HSTS_SECONDS", 0)) > 0
        and not bool(getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False))
        and bool(getattr(settings, "CSRF_TRUSTED_ORIGINS", []) or [])
    )
    return _check_item(
        key="security_config",
        label="Production security config",
        ready=ready,
        detail=(
            f"LOCAL_RUNTIME={getattr(settings, 'LOCAL_RUNTIME', None)}, DEBUG={getattr(settings, 'DEBUG', None)}, "
            f"hosts={len(allowed_hosts)}, HSTS={getattr(settings, 'SECURE_HSTS_SECONDS', 0)}."
        ),
        manual_task="Set ALFRED_LOCAL_RUNTIME=false, DEBUG=false, DJANGO_SECRET_KEY, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, HTTPS redirect, secure cookies, and HSTS.",
    )


def production_readiness_snapshot(*, cache_health: dict | None = None, browser_coverage: dict | None = None) -> dict:
    cache_health = dict(cache_health or {})
    browser_coverage = dict(browser_coverage or {})
    proof = load_production_deployment_proof()
    proof_sections = dict(proof.get("sections") or {})

    browser_summary = dict(browser_coverage.get("proof_summary") or {})
    browser_ci_ready = bool(browser_summary.get("ci_gate_recorded")) or bool(
        (proof_sections.get("browser_ci") or {}).get("ready")
    )
    cache_traffic_ready = bool(cache_health.get("production_mature")) or bool(
        (proof_sections.get("cache_traffic") or {}).get("ready")
    )

    checks = [
        _database_config_check(),
        _cache_config_check(),
        _celery_config_check(),
        _security_config_check(),
        _check_item(
            key="database_runtime_proof",
            label="Database runtime proof",
            ready=bool((proof_sections.get("database") or {}).get("ready")),
            detail=proof.get("summary", ""),
            manual_task="Run the production deployment probe after migrations and record database connection plus migration health.",
        ),
        _check_item(
            key="cache_runtime_proof",
            label="Shared cache runtime proof",
            ready=bool((proof_sections.get("cache") or {}).get("ready")),
            detail=proof.get("summary", ""),
            manual_task="Run the production deployment probe against the shared cache and record read/write health.",
        ),
        _check_item(
            key="celery_runtime_proof",
            label="Celery worker and beat proof",
            ready=bool((proof_sections.get("celery") or {}).get("ready")),
            detail=proof.get("summary", ""),
            manual_task="Run Celery worker and Celery beat with Redis, verify worker ping and beat schedule, then record deployment proof.",
        ),
        _check_item(
            key="cache_traffic_proof",
            label="Production cache traffic proof",
            ready=cache_traffic_ready,
            detail=(
                f"Cache telemetry source is {cache_health.get('telemetry_source', 'not recorded')}; "
                f"production mature={bool(cache_health.get('production_mature'))}."
            ),
            manual_task="Collect shared-cache telemetry for every materialized namespace under production-like traffic and record it as production deployment proof.",
        ),
        _check_item(
            key="browser_ci_proof",
            label="Browser CI proof",
            ready=browser_ci_ready,
            detail=str(browser_summary.get("summary") or "Browser CI proof not recorded."),
            manual_task="Run the browser-regression GitHub Actions job and keep browser_regression_summary.ci-chrome.json at zero skipped Selenium tests.",
        ),
    ]
    ready_count = sum(1 for item in checks if item["ready"])
    total_count = len(checks)
    progress = int(round((ready_count / total_count) * 100)) if total_count else 0
    blockers = [item["label"] for item in checks if not item["ready"]]
    manual_tasks = [item["manual_task"] for item in checks if item["manual_task"]]
    ready = ready_count == total_count
    return {
        "progress": max(0, min(100, progress)),
        "ready": ready,
        "maturity_status": "Production ready" if ready else "Deployment proof gated",
        "ready_check_count": ready_count,
        "total_check_count": total_count,
        "blockers": blockers,
        "manual_tasks": manual_tasks,
        "required_env_vars": list(REQUIRED_PRODUCTION_ENV_VARS),
        "deployment_proof": proof,
        "deployment_proof_path": proof.get("path") or str(production_deployment_proof_path()),
        "checks": checks,
        "summary": (
            f"{ready_count}/{total_count} production readiness check(s) are ready; "
            f"{len(blockers)} deployment blocker(s) remain."
        ),
    }
