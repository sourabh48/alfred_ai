"""ALFRED's central brain (owner decision 2026-11-20): examples the local models learn from.

Each example is encrypted with the private memory vault's key and kept per owner in the vault database on this PC.
That folder is inside the encrypted recovery archive that scripts/cloud_backup.py copies to R2, so the brain is backed up
with it and never leaves the PC unencrypted. Like a chat app (owner 2026-11-26, "like Claude and Codex"), general know-how is
shared and a person's own words are not: public answers and made-up practice messages teach ALFRED for everyone, while each
person's real travel messages and corrections are read back only for that person. A reset still removes all of a person's own.
"""
import logging
from pathlib import Path
import re
import time
from uuid import uuid4

from cryptography.fernet import InvalidToken
from django.conf import settings

from .persistent_memory import MemoryStore, _json, _owner

logger = logging.getLogger(__name__)
KINDS = ("travel_reading", "travel_practice", "public_answer")  # travel_practice: Gemini's made-up messages, never lessons
SHARED = ("public_answer", "travel_practice")  # never a person's own messages
PER_KIND = 500  # shortcut: the oldest examples are dropped past this; raise it with a measured fine-tuning budget


def _store():
    return MemoryStore(Path(settings.ALFRED_MEMORY_DIR))


def remember(user, kind, example, *, store=None):
    """Save one example; a bounded JSON object, newest kept."""
    if kind not in KINDS or not isinstance(example, dict) or not example:
        raise ValueError("Choose a known example kind and a non-empty example.")
    owner, text, store = _owner(user), _json(example), store or _store()
    with store._transaction() as db:
        db.execute("INSERT INTO brain_examples(id,owner,kind,created,record) VALUES(?,?,?,?,?)",
                   (uuid4().hex, owner, kind, time.time(), store._cipher(db).encrypt(text.encode())))
        db.execute("DELETE FROM brain_examples WHERE owner=? AND kind=? AND id NOT IN "
                   "(SELECT id FROM brain_examples WHERE owner=? AND kind=? ORDER BY created DESC LIMIT ?)",
                   (owner, kind, owner, kind, PER_KIND))


def examples(user, kind, *, limit=PER_KIND, store=None):
    """Examples of one kind, newest first: everyone's for a shared kind, else only this owner's; unreadable ones are skipped."""
    import json
    owner, store, found = _owner(user), store or _store(), []
    with store._transaction() as db:
        cipher = store._cipher(db)
        rows = (db.execute("SELECT record FROM brain_examples WHERE kind=? ORDER BY created DESC LIMIT ?", (kind, int(limit)))
                if kind in SHARED else
                db.execute("SELECT record FROM brain_examples WHERE owner=? AND kind=? ORDER BY created DESC LIMIT ?",
                           (owner, kind, int(limit)))).fetchall()
        for (record,) in rows:
            try:
                found.append(json.loads(cipher.decrypt(record)))
            except (InvalidToken, ValueError):
                continue
    return found


def try_remember(user, kind, example, *, store=None):
    """remember(), but a closed or busy vault never stops the conversation that taught it."""
    try:
        remember(user, kind, example, store=store)
        return True
    except Exception as exc:
        logger.info("Brain example not saved: %s", type(exc).__name__)
        return False


def try_examples(user, kind, *, limit=PER_KIND, store=None):
    try:
        return examples(user, kind, limit=limit, store=store)
    except Exception as exc:
        logger.info("Brain examples not read: %s", type(exc).__name__)
        return []


def reading_messages(message, today):
    """System and user turns exactly as the travel reader sends them (LocalChat.ask), so training matches use."""
    import json
    from apps.mobility.services.travel.understanding import SCHEMA, system_prompt
    return [{"role": "system", "content": system_prompt(today) + " Output schema: " + json.dumps(SCHEMA, separators=(",", ":"))},
            {"role": "user", "content": json.dumps({"message": message, "alfred_last_asked": None}, ensure_ascii=False)}]


def _readings(user, store):
    """(message, meant, held back) for corrections and practice, oldest first; every tenth practice example is held back."""
    for kind in ("travel_reading", "travel_practice"):
        for item in reversed(examples(user, kind, store=store)):
            if isinstance(item.get("message"), str) and isinstance(item.get("meant"), dict):
                yield item["message"], item["meant"], item.get("held_back") is True


def training_chats(user, *, store=None, today=None):
    """This owner's corrections and everyone's shared examples as chat records for fine-tuning, oldest first; held-back
    practice examples are left out."""
    import json
    from django.utils import timezone
    today, out = today or timezone.localdate(), []
    for message, meant, held_back in _readings(user, store):
        if not held_back:
            out.append({"messages": [*reading_messages(message, today),
                                     {"role": "assistant", "content": json.dumps(meant, ensure_ascii=False)}]})
    for item in reversed(examples(user, "public_answer", store=store)):
        if isinstance(item.get("question"), str) and isinstance(item.get("answer"), str):
            out.append({"messages": [{"role": "user", "content": item["question"]},
                                     {"role": "assistant", "content": item["answer"]}]})
    return out


def held_back(user, *, store=None, today=None):
    """Practice examples kept out of training, to score the fine-tuned model against the current one."""
    from django.utils import timezone
    today = today or timezone.localdate()
    return [{"messages": reading_messages(message, today), "expected": meant}
            for message, meant, kept_back in _readings(user, store) if kept_back]


STOP = set("the and for with from what which when where does how why who whose that this these those are was were has have "
           "can should would could about tell give explain mean means".split())


def _words(text):
    return set(re.findall(r"[^\W\d_]{3,}", str(text).casefold())) - STOP


def similar_public_answers(user, query, *, store=None, limit=2):
    """Earlier Gemini answers to questions sharing most of this one's words, for the local model to learn from."""
    words = _words(query)
    if len(words) < 2:
        return []
    scored = []
    for item in try_examples(user, "public_answer", limit=200, store=store):
        shared = words & _words(item.get("question", ""))
        if len(shared) >= max(2, (len(words) + 1) // 2) and isinstance(item.get("answer"), str):
            scored.append((len(shared), item))
    return [item for _, item in sorted(scored, key=lambda pair: -pair[0])[:limit]]
