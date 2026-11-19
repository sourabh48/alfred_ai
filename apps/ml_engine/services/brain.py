"""ALFRED's central brain (owner decision 2026-11-20): examples the local models learn from.

Each example is encrypted with the private memory vault's key and kept per owner in the vault database on this PC.
That folder is inside the encrypted recovery archive that scripts/cloud_backup.py copies to R2, so the brain is backed up
with it and never leaves the PC unencrypted. Only the owner's own examples are ever read back.
"""
import logging
from pathlib import Path
import time
from uuid import uuid4

from cryptography.fernet import InvalidToken
from django.conf import settings

from .persistent_memory import MemoryStore, _json, _owner

logger = logging.getLogger(__name__)
KINDS = ("travel_reading", "public_answer")
PER_KIND = 500  # shortcut: the oldest examples are dropped past this; raise it with a measured fine-tuning budget


def _store():
    return MemoryStore(Path(settings.ALFRED_MEMORY_DIR))


def remember(user, kind, example):
    """Save one example; a bounded JSON object, newest kept."""
    if kind not in KINDS or not isinstance(example, dict) or not example:
        raise ValueError("Choose a known example kind and a non-empty example.")
    owner, text, store = _owner(user), _json(example), _store()
    with store._transaction() as db:
        db.execute("INSERT INTO brain_examples(id,owner,kind,created,record) VALUES(?,?,?,?,?)",
                   (uuid4().hex, owner, kind, time.time(), store._cipher(db).encrypt(text.encode())))
        db.execute("DELETE FROM brain_examples WHERE owner=? AND kind=? AND id NOT IN "
                   "(SELECT id FROM brain_examples WHERE owner=? AND kind=? ORDER BY created DESC LIMIT ?)",
                   (owner, kind, owner, kind, PER_KIND))


def examples(user, kind, *, limit=PER_KIND):
    """This owner's examples of one kind, newest first; unreadable ones are skipped."""
    import json
    owner, store, found = _owner(user), _store(), []
    with store._transaction() as db:
        cipher = store._cipher(db)
        rows = db.execute("SELECT record FROM brain_examples WHERE owner=? AND kind=? ORDER BY created DESC LIMIT ?",
                          (owner, kind, int(limit))).fetchall()
        for (record,) in rows:
            try:
                found.append(json.loads(cipher.decrypt(record)))
            except (InvalidToken, ValueError):
                continue
    return found


def try_remember(user, kind, example):
    """remember(), but a closed or busy vault never stops the conversation that taught it."""
    try:
        remember(user, kind, example)
        return True
    except Exception as exc:
        logger.info("Brain example not saved: %s", type(exc).__name__)
        return False


def try_examples(user, kind, *, limit=PER_KIND):
    try:
        return examples(user, kind, limit=limit)
    except Exception as exc:
        logger.info("Brain examples not read: %s", type(exc).__name__)
        return []
