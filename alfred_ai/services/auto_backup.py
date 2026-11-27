"""Nightly encrypted backup of the whole ALFRED to the owner's Cloudflare R2 bucket (owner 2026-11-26, SYNC-09 and RUNTIME-08).

Done "like most financial applications": one archive of everything, made while ALFRED runs, encrypted with the backup key
before it leaves the PC, then read back from R2 and hash-checked. Each person's data stays theirs because a restored ALFRED
keeps its sign-in and owner checks. R2 keeps the newest 7 nightly archives and this PC the newest one; an older one is
removed only after a newer one is verified in R2, and archives uploaded by hand are never touched. The bucket always stays
inside Cloudflare's free allowance (owner 2026-11-27, "keep under limit always"): before an upload the oldest nightly copies
make room, the newest verified one always stays, and an archive that still does not fit is not uploaded; tries are capped
each month so writes stay far below the free million. Nothing runs until R2 is
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
MONTHLY_TRIES = 60  # a try is at most 1,152 parts plus a few calls: about 70,000 of R2's free 1 million writes a month
FRIENDLY = {
    "free_storage_full": "This backup would take R2 past its free 9 GB, so it was not uploaded; the newest backup in R2 is kept",
    "another_cloud_upload_running": "Another upload to R2 is still running",
}
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
    month = now.strftime("%Y-%m")
    tries = status().get("tries") or {}
    count = tries.get("count", 0) if tries.get("month") == month else 0
    if count >= MONTHLY_TRIES:
        _record(error=f"{MONTHLY_TRIES} backup tries this month already, so ALFRED waits for next month to keep R2 free. "
                      "The newest backup in R2 is kept.")
        return {"status": "monthly_limit"}
    _record(tries={"month": month, "count": count + 1})
    root = nightly_folder()
    destination = root / now.strftime("%Y%m%dT%H%M%SZ")
    try:
        cloud_backup.create(runtime(), destination, backup_key.key_path(), live=True)
        shutil.rmtree(destination / "independent-local-restore")  # the check's plain copy is not kept
        public = json.loads((destination / "backup.json").read_text(encoding="utf-8"))
        _make_room(client, public["archive_sha256"], public["archive_bytes"])
        receipt = cloud_backup.upload(destination, backup_key.key_path(), recovery_copy_confirmed=True, client=client)
        digest = receipt["archive_sha256"]
        history = [digest] + [d for d in status().get("history", []) if d != digest]
        keep = max(1, min(KEEP, cloud_backup.FREE_STORAGE // max(receipt["archive_bytes"], 1)))
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
        if reason in FRIENDLY:  # refused before any part went up: not a try against the monthly cap
            reason = FRIENDLY[reason]
            _record(tries={"month": month, "count": count})
        _record(last_try=now.strftime("%Y-%m-%d %H:%M UTC"), error=f"{reason.rstrip('.')}. ALFRED tries again within the hour.")
        logger.warning("Nightly backup failed (%s)", type(exc).__name__)
        raise
    for folder in root.iterdir():  # only after R2 verified the new one: earlier nightly folders, finished or not
        if folder != destination and folder.is_dir() and STAMP.fullmatch(folder.name):
            shutil.rmtree(folder)
    _record(last_ok=now.strftime("%Y-%m-%d %H:%M UTC"), last_try=now.strftime("%Y-%m-%d %H:%M UTC"), error="",
            history=history, kept=len(history), bytes=receipt["archive_bytes"])
    return {"status": "saved", "archive_sha256": digest, "kept": len(history)}


def _make_room(client, digest, size):
    """Before an upload, the oldest nightly copies go until it fits R2's free storage; the newest verified one always stays."""
    from scripts import cloud_backup
    remote = cloud_backup.listing(client)
    if digest in remote:
        return
    history = [d for d in status().get("history", []) if d in remote]
    room = cloud_backup.FREE_STORAGE - cloud_backup.stored_bytes(client)
    while size > room and len(history) > 1:
        old = history.pop()
        client._send("DELETE", cloud_backup.PREFIX + old + ".zip", deadline=cloud_backup.seconds(), maximum=64 * 1024,
                     statuses=(204,))
        room += remote[old][0]
    _record(history=history)


@shared_task
def backup_now():
    """Settings > Backup key: "Back up now", for the first upload and restore drills."""
    try:
        return run()
    except Exception as exc:  # already recorded for Settings
        return {"status": "failed", "error": type(exc).__name__}


FIELDS = ("account_id", "bucket", "access_key", "secret_key")


def _apply(changes: dict) -> None:
    """Write the lines to config/local.env and use them in the running app at once."""
    from alfred_ai.services import online_services
    online_services.save(changes)
    for name, value in changes.items():
        setattr(settings, name, value == "true" if name == "ALFRED_CLOUD_BACKUP_AUTHORIZED" else value)


def connect(data: dict, client=None) -> None:
    """Settings > Backup key: the owner's bucket and its token. Cloudflare is asked first, so wrong values are never saved."""
    from apps.ml_engine.services.memory_r2 import R2Bucket, validate_profile
    from apps.ml_engine.services.memory_sync import SyncUnavailable
    from alfred_ai.services.online_services import VALUE
    from scripts import cloud_backup
    profile = {name: str((data or {}).get(name) or "").strip() for name in FIELDS} if isinstance(data, dict) else {}
    try:
        if len(profile) != len(FIELDS) or not all(VALUE.fullmatch(value) or name == "bucket" for name, value in profile.items()):
            raise ValueError("Fill in all four values, pasted without spaces or quotes.")
        checked = validate_profile({**profile, "jurisdiction": ""})
    except ValueError as exc:
        raise backup_key.BackupKeyError(str(exc)) from None
    try:
        cloud_backup.listing(client or R2Bucket(checked))
    except (SyncUnavailable, cloud_backup.GateError):
        raise backup_key.BackupKeyError("Cloudflare did not accept these values. Check them, and that the token may read and "
                                        "write this bucket.") from None
    _apply({**{"ALFRED_MEMORY_R2_" + name.upper(): profile[name] for name in FIELDS},
            "ALFRED_MEMORY_R2_JURISDICTION": "", "ALFRED_CLOUD_BACKUP_AUTHORIZED": "true"})


def turn_off() -> None:
    """Stops the nightly upload; the bucket values and every backup already in it stay."""
    _apply({"ALFRED_CLOUD_BACKUP_AUTHORIZED": ""})
