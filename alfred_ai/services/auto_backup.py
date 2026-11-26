"""Nightly encrypted backup of the whole ALFRED to the owner's Cloudflare R2 bucket (owner 2026-11-26, SYNC-09 and RUNTIME-08).

Done "like most financial applications": one archive of everything, made while ALFRED runs, encrypted with the backup key
before it leaves the PC, then read back from R2 and hash-checked. Each person's data stays theirs because a restored ALFRED
keeps its sign-in and owner checks. R2 keeps the newest 7 nightly archives and this PC the newest one; an older one is
removed only after a newer one is verified in R2, and archives uploaded by hand are never touched. Nothing runs until R2 is
set up, the owner turned cloud backup on, and the backup key's locked copy is saved off this PC: an archive that only this
PC could open would be lost with it.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.cache import cache

from alfred_ai.background import shared_task
from alfred_ai.services import backup_key

logger = logging.getLogger(__name__)
KEEP = 7
FREE_BYTES = 9 * 1024 ** 3  # stays inside R2's 10 GB free storage
STAMP = re.compile(r"\d{8}T\d{6}Z")


def runtime() -> Path:
    return Path(os.environ.get("ALFRED_DATA_DIR") or settings.BASE_DIR)


def nightly_folder() -> Path:
    """Beside the data folder, never inside it: a backup must not contain itself."""
    data = runtime()
    return data.parent / f"{data.name}-backups" / "nightly"


def _status_path() -> Path:
    return backup_key.folder() / "auto-backup.json"


def status() -> dict:
    try:
        saved = json.loads(_status_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    return saved if isinstance(saved, dict) else {}


def _record(**fields) -> None:
    backup_key._write(_status_path(), json.dumps({**status(), **fields}).encode())


def run(client=None) -> dict:
    if not cache.add("alfred:auto-backup:running", 1, timeout=2 * 3600):
        return {"status": "busy"}
    try:
        return _run(client)
    finally:
        cache.delete("alfred:auto-backup:running")


def _run(client):
    from apps.ml_engine.services.memory_sync import SyncUnavailable
    from scripts import cloud_backup
    now = datetime.now(timezone.utc)
    key = backup_key.status()
    if not key["key"] or not (key["in_r2"] or (key["in_drive"] and key["saved_on"])):
        _record(error="Make the backup key and save its locked copy first (above).")
        return {"status": "not_set_up"}
    try:
        client = client or cloud_backup.bucket()
    except cloud_backup.GateError:
        _record(error="Cloudflare R2 is not set up yet (config/local.env).")
        return {"status": "not_set_up"}
    root = nightly_folder()
    destination = root / now.strftime("%Y%m%dT%H%M%SZ")
    try:
        cloud_backup.create(runtime(), destination, backup_key.key_path(), live=True)
        shutil.rmtree(destination / "independent-local-restore")  # the check's plain copy is not kept
        receipt = cloud_backup.upload(destination, backup_key.key_path(), recovery_copy_confirmed=True, client=client)
        digest = receipt["archive_sha256"]
        history = [digest] + [d for d in status().get("history", []) if d != digest]
        keep = max(1, min(KEEP, FREE_BYTES // max(receipt["archive_bytes"], 1)))
        remote = cloud_backup.listing(client)
        for old in history[keep:]:
            if old in remote:
                client._send("DELETE", cloud_backup.PREFIX + old + ".zip", deadline=cloud_backup.seconds(),
                             maximum=64 * 1024, statuses=(204,))
        history = [d for d in history[:keep] if d in remote]
    except Exception as exc:
        if destination.parent == root and destination.exists():  # this run's own unfinished folder, with any plain scratch copy
            shutil.rmtree(destination, ignore_errors=True)
        reason = str(exc) if isinstance(exc, (cloud_backup.GateError, SyncUnavailable)) else type(exc).__name__  # never raw paths or data
        _record(last_try=now.strftime("%Y-%m-%d %H:%M UTC"), error=f"{reason.rstrip('.')}. ALFRED tries again within the hour.")
        logger.warning("Nightly backup failed (%s)", type(exc).__name__)
        raise
    for folder in root.iterdir():  # only after R2 verified the new one: earlier nightly folders, finished or not
        if folder != destination and folder.is_dir() and STAMP.fullmatch(folder.name):
            shutil.rmtree(folder)
    _record(last_ok=now.strftime("%Y-%m-%d %H:%M UTC"), last_try=now.strftime("%Y-%m-%d %H:%M UTC"), error="",
            history=history, kept=len(history), bytes=receipt["archive_bytes"])
    return {"status": "saved", "archive_sha256": digest, "kept": len(history)}


@shared_task
def backup_now():
    """Settings > Backup key: "Back up now", for the first upload and restore drills."""
    try:
        return run()
    except Exception as exc:  # already recorded for Settings
        return {"status": "failed", "error": type(exc).__name__}
