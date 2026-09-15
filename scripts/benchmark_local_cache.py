"""Measure synthetic, sequential dashboard traffic in disposable local storage.

Run in a fresh Python process. This is SQLite/local-memory evidence, not a Redis,
multi-user, concurrent, live-network, or production performance claim.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from contextlib import ExitStack, chdir
from datetime import timedelta
import importlib
import json
import math
import os
from pathlib import Path
import platform
from statistics import median
import sys
import tempfile
from time import perf_counter
from unittest.mock import patch
import uuid


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def latency_summary(values):
    values = sorted(values)
    if not values:
        return {"samples": 0}
    return {
        "samples": len(values),
        "median_ms": round(median(values), 3),
        "p95_ms": round(values[math.ceil(len(values) * 0.95) - 1], 3),
        "max_ms": round(values[-1], 3),
    }


def configure_isolated_settings(storage):
    from django.conf import settings

    if settings.configured:
        raise RuntimeError("Use a fresh Python process; existing Django settings are not accepted")
    # Import code configuration only. Never load local credentials or let its
    # database/cache choices initialize Django before our overrides are applied.
    with patch("environ.Env.read_env"):
        base = importlib.import_module("alfred_ai.settings")
    configured = {name: getattr(base, name) for name in dir(base) if name.isupper()}
    configured.update(
        BASE_DIR=storage,
        DEBUG=False,
        ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
        DATABASES={"default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(storage / "benchmark.sqlite3"),
            "CONN_MAX_AGE": 0,
        }},
        CACHES={"default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "alfred-synthetic-benchmark-" + uuid.uuid4().hex,
            "OPTIONS": {"MAX_ENTRIES": 10000},
        }},
        MEDIA_ROOT=str(storage / "media"),
        STATIC_ROOT=str(storage / "staticfiles"),
        ALFRED_AUTO_TRAIN_ON_STARTUP=False,
        CELERY_BROKER_URL="memory://",
        CELERY_RESULT_BACKEND="cache+memory://",
        CELERY_TASK_ALWAYS_EAGER=False,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    )
    (storage / "media").mkdir()
    (storage / "staticfiles").mkdir()
    settings.configure(**configured)


def run_benchmark(*, expense_rows=3000, repetitions=10):
    if expense_rows < 3000 or repetitions < 10:
        raise ValueError("Use at least 3000 synthetic expense rows and 10 repetitions")
    network_attempts = []

    def block_network(*args, **kwargs):
        network_attempts.append("blocked")
        raise RuntimeError("Network access is disabled in the synthetic cache benchmark")

    with tempfile.TemporaryDirectory(prefix="alfred-cache-benchmark-") as temporary:
        storage = Path(temporary).resolve()
        forced_environment = {
            "ALFRED_LOCAL_RUNTIME": "true",
            "ALFRED_AUTO_TRAIN_ON_STARTUP": "false",
            "DJANGO_SETTINGS_MODULE": "alfred_ai.settings",
            "DJANGO_SECRET_KEY": "synthetic-cache-benchmark-only",
            "DATABASE_URL": "",
            "DB_ENGINE": "django.db.backends.sqlite3",
            "DB_NAME": str(storage / "benchmark.sqlite3"),
            "DB_USER": "", "DB_PASSWORD": "", "DB_HOST": "", "DB_PORT": "",
            "CACHE_BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "CACHE_LOCATION": "synthetic-cache-benchmark",
            "REDIS_URL": "",
            "CELERY_BROKER_URL": "memory://",
            "CELERY_RESULT_BACKEND": "cache+memory://",
            "CELERY_TASK_ALWAYS_EAGER": "false",
            "ALFRED_MATERIALIZED_CACHE_TRAFFIC_PROOF": str(storage / "traffic.json"),
        }
        with ExitStack() as isolated:
            isolated.enter_context(patch.dict(os.environ, forced_environment))
            isolated.enter_context(chdir(storage))
            for target in ("socket.socket.connect", "socket.socket.connect_ex",
                           "socket.create_connection", "socket.getaddrinfo"):
                isolated.enter_context(patch(target, side_effect=block_network))
            configure_isolated_settings(storage)

            import django
            django.setup()

            from django.conf import settings
            from django.contrib.auth import get_user_model
            from django.core.cache import caches
            from django.core.management import call_command
            from django.db import connections
            from django.test import Client
            from django.utils import timezone

            from apps.expenses.models import Expense
            from scripts.exercise_materialized_cache_traffic import run_materialized_cache_traffic_exercise

            try:
                call_command("migrate", verbosity=0, interactive=False)
                user = get_user_model().objects.create_user(
                    username="synthetic_cache_benchmark", monthly_income=110000,
                    rent_or_emi=28000, city="Bengaluru",
                )
                today = timezone.localdate()
                categories = ("food", "groceries", "fuel", "utilities", "shopping", "travel")
                Expense.objects.bulk_create([
                    Expense(
                        user=user, amount=80 + (index * 37) % 4200,
                        category=categories[index % len(categories)],
                        classification="expense", direction="debit", source="manual",
                        merchant="Synthetic benchmark merchant",
                        description="Explicitly synthetic cache workload",
                        transaction_date=today - timedelta(days=index % 1095),
                        external_reference=f"synthetic-benchmark-{index:06d}",
                    ) for index in range(expense_rows)
                ], batch_size=250)

                request_samples = defaultdict(list)

                class TimedClient(Client):
                    def get(self, path, *args, **kwargs):
                        started = perf_counter()
                        response = super().get(path, *args, **kwargs)
                        elapsed = (perf_counter() - started) * 1000
                        metadata = response.json().get("_materialized", {}) if response.status_code == 200 else {}
                        request_samples[path].append({
                            "elapsed_ms": elapsed,
                            "status_code": response.status_code,
                            "cache_status": metadata.get("cache_status", "unreported"),
                        })
                        return response

                started = perf_counter()
                traffic = run_materialized_cache_traffic_exercise(
                    user=user, client=TimedClient(), proof_path=storage / "traffic.json",
                    repetitions=repetitions, offline_fixtures=True,
                )
                elapsed = perf_counter() - started
                endpoints = []
                for target in traffic["endpoint_targets"]:
                    samples = request_samples[target["path"]]
                    endpoints.append({
                        "namespace": target["namespace"], "path": target["path"],
                        "all_requests": latency_summary([sample["elapsed_ms"] for sample in samples]),
                        "initial_request_ms": round(samples[0]["elapsed_ms"], 3),
                        "subsequent_requests": latency_summary([sample["elapsed_ms"] for sample in samples[1:]]),
                        "cache_hit_requests": latency_summary([
                            sample["elapsed_ms"] for sample in samples if sample["cache_status"] == "hit"
                        ]),
                        "status_codes": [sample["status_code"] for sample in samples],
                        "cache_statuses": [sample["cache_status"] for sample in samples],
                    })
                result = {
                    "summary_version": 1,
                    "kind": "isolated_synthetic_cache_benchmark",
                    "generated_at_utc": timezone.now().isoformat(),
                    "accepted": traffic["validation"]["accepted"] and not network_attempts,
                    "production_proof": False,
                    "workload": {
                        "synthetic": True, "users": 1, "seeded_expense_rows": expense_rows,
                        "total_expense_rows_including_fixtures": Expense.objects.count(),
                        "history_days": 1095, "repetitions_per_target": repetitions,
                        "execution": "single-process sequential Django test client",
                        "external_evidence": "offline fixtures", "network_attempts_blocked": len(network_attempts),
                        "trained_models": "absent; isolated fallback paths",
                    },
                    "isolation": {
                        "database_engine": settings.DATABASES["default"]["ENGINE"],
                        "database_temporary": Path(settings.DATABASES["default"]["NAME"]).parent == storage,
                        "cache_backend": settings.CACHES["default"]["BACKEND"],
                        "media_temporary": Path(settings.MEDIA_ROOT).parent == storage,
                        "working_directory_temporary": Path.cwd() == storage,
                        "startup_training_enabled": settings.ALFRED_AUTO_TRAIN_ON_STARTUP,
                        "local_environment_files_loaded": False,
                    },
                    "runtime": {"python": platform.python_version(), "django": django.get_version(),
                                "platform": platform.system(), "architecture": platform.machine()},
                    "exercise_duration_seconds": round(elapsed, 3),
                    "endpoint_latency": endpoints,
                    "namespace_telemetry": traffic["namespaces"],
                    "validation": {key: value for key, value in traffic["validation"].items()
                                   if key not in {"path", "proof_path", "namespaces", "source"}},
                    "limits": [
                        "Synthetic single-user sequential workload; no concurrency or throughput claim",
                        "SQLite and process-local memory cache; no Redis or Docker runtime measurement",
                        "First endpoint requests may reuse internal data warmed by earlier endpoints",
                        "Small latency samples include middleware/serialization; p95 uses nearest rank",
                        "Namespace generation latency comes from existing materialization telemetry",
                        "Fixture network evidence and absent trained models are not real-world quality proof",
                    ],
                }
            finally:
                connections.close_all()
                caches.close_all()
    result["isolation"]["temporary_storage_removed"] = not storage.exists()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expense-rows", type=int, default=3000)
    parser.add_argument("--repetitions", type=int, default=10)
    parser.add_argument("--proof-path", type=Path,
                        default=PROJECT_ROOT / "artifacts/cache/isolated_synthetic_benchmark.json")
    args = parser.parse_args()
    proof_path = args.proof_path.resolve()
    summary = run_benchmark(expense_rows=args.expense_rows, repetitions=args.repetitions)
    proof_path.parent.mkdir(parents=True, exist_ok=True)
    proof_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "accepted": summary["accepted"], "proof_path": str(proof_path),
        "workload": summary["workload"], "validation": summary["validation"],
        "exercise_duration_seconds": summary["exercise_duration_seconds"],
        "temporary_storage_removed": summary["isolation"]["temporary_storage_removed"],
    }, indent=2))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
