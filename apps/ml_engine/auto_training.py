from __future__ import annotations

import logging
import os
import sys
import threading

from django.conf import settings
from django.core.cache import cache

from apps.ml_engine.runtime_control import training_bootstrap_allowed

LOGGER = logging.getLogger(__name__)


def should_bootstrap_training(argv: list[str] | None = None) -> bool:
    argv = list(argv or sys.argv)
    command = argv[1] if len(argv) > 1 else ""

    if not getattr(settings, "ALFRED_AUTO_TRAIN_ON_STARTUP", True):
        return False

    blocked_commands = {
        "check",
        "collectstatic",
        "createsuperuser",
        "dbshell",
        "dumpdata",
        "flush",
        "loaddata",
        "makemigrations",
        "migrate",
        "shell",
        "showmigrations",
        "test",
    }
    if command in blocked_commands:
        return False

    if command == "runserver" and os.environ.get("RUN_MAIN") not in {"true", "True"}:
        return False

    return True


def bootstrap_startup_training() -> bool:
    if not should_bootstrap_training():
        return False

    allowed, reason = training_bootstrap_allowed()
    if not allowed:
        LOGGER.info("ALFRED startup auto-training skipped. reason=%s", reason)
        return False

    cache_key = "alfred:auto-train:startup-debounce"
    timeout_seconds = max(60, int(getattr(settings, "ALFRED_AUTO_TRAIN_COOLDOWN_MINUTES", 45) * 60))
    if not cache.add(cache_key, "1", timeout=timeout_seconds):
        return False

    thread = threading.Thread(target=_run_startup_training, name="alfred-auto-training", daemon=True)
    thread.start()
    return True


def _run_startup_training():
    try:
        from apps.ml_engine.training.orchestrator import run_training_cycle

        run_training_cycle(trigger="startup")
    except Exception:
        LOGGER.exception("ALFRED startup auto-training failed.")
