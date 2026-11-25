"""ALFRED on Telegram (owner request 2026-11-25): trips, career follow-ups, non-money notices and public questions.

Telegram's servers see every message, so the bot never reads or sends finance, documents or saved private history
(memories, chats). Only a private chat linked with a code shown in Settings on this PC gets answers, and each linked
chat sees only its own person's records. Replies are plain text; nothing is booked, sent, paid or changed.
The bot token lives in config/local.env as ALFRED_TELEGRAM_BOT_TOKEN and is never logged.
"""
from __future__ import annotations

import json
import logging
import os
import re
import secrets
import threading
import time
from pathlib import Path

from django.conf import settings
from django.core.cache import cache

LOGGER = logging.getLogger(__name__)
TOKEN_ENV = "ALFRED_TELEGRAM_BOT_TOKEN"
TOKEN_FORMAT = re.compile(r"^\d{5,15}:[\w-]{30,60}$")
CODE_SECONDS, WRONG_CODES_PER_HOUR = 600, 5
# Home notices that point here are about money or documents and never go to Telegram.
SENSITIVE_PATHS = ("/expenses", "/loans", "/budgets", "/investments", "/income", "/banking", "/documents", "/tax", "/reports",
                   "/wealth", "/goals", "/ai/insights")
HELP = ("I can tell you:\n/trip - your next trip\n/followups - career follow-ups that are due\n/notices - Home notices (no money)\n"
        "Or ask any public question, such as \"What is the capital of Peru?\".\n"
        "Money, documents and your saved history stay on your PC and are never shown here. /unlink stops this chat.")
_lock = threading.Lock()


def configured() -> bool:
    return bool(TOKEN_FORMAT.match(os.environ.get(TOKEN_ENV, "")))


def _path() -> Path:
    return Path(os.environ.get("ALFRED_DATA_DIR") or settings.BASE_DIR) / "config" / "telegram-links.json"


def _load() -> dict:
    try:
        state = json.loads(_path().read_text(encoding="utf-8"))
        return {"links": {str(k): int(v) for k, v in state.get("links", {}).items()}, "offset": int(state.get("offset", 0))}
    except (OSError, ValueError, TypeError, AttributeError):
        return {"links": {}, "offset": 0}


def _save(state) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state), encoding="utf-8")
    temporary.replace(path)


def new_code(user) -> str:
    """A one-time 8-digit code, valid 10 minutes, that links the chat it is sent from to this person."""
    code = f"{secrets.randbelow(10**8):08d}"
    cache.set(f"telegram:code:{code}", user.pk, CODE_SECONDS)
    return code


def links_for(user) -> list:
    return [chat for chat, owner in _load()["links"].items() if owner == user.pk]


def unlink(user, chat=None) -> int:
    with _lock:
        state = _load()
        gone = [key for key, owner in state["links"].items() if owner == user.pk and (chat is None or key == str(chat))]
        for key in gone:
            del state["links"][key]
        _save(state)
    return len(gone)


def _call(method, body, *, deadline=None):
    from alfred_ai.services import public_http
    reply = public_http.request("POST", f"https://api.telegram.org/bot{os.environ[TOKEN_ENV]}/{method}", json_body=body,
                                max_bytes=2_000_000, deadline=deadline).json()
    if reply.get("ok") is not True:
        raise ValueError("Telegram refused the request.")
    return reply.get("result")


def send(chat, text) -> None:
    _call("sendMessage", {"chat_id": int(chat), "text": text[:4000] or "-", "disable_web_page_preview": True})


def _link(chat, code) -> str:
    tries = f"telegram:wrong:{chat}"
    if cache.get(tries, 0) >= WRONG_CODES_PER_HOUR:
        return "Too many wrong codes. Try again in an hour."
    owner = cache.get(f"telegram:code:{code}") if re.fullmatch(r"\d{8}", code or "") else None
    if owner is None:
        cache.set(tries, cache.get(tries, 0) + 1, 3600)
        return "That code is wrong or has expired. Get a new one in ALFRED: Settings, Telegram."
    cache.delete(f"telegram:code:{code}")
    with _lock:
        state = _load()
        state["links"][str(chat)] = owner
        _save(state)
    return "Linked. " + HELP


def _user(owner):
    from django.contrib.auth import get_user_model
    return get_user_model().objects.filter(pk=owner, is_active=True).first()


def next_trip(user) -> str:
    from django.utils import timezone
    from apps.mobility.models import TravelPlan
    trip = (TravelPlan.objects.filter(user=user, start_date__gte=timezone.localdate()).exclude(status__in=("completed", "cancelled"))
            .order_by("start_date").first())
    if not trip:
        return "No upcoming trip is saved."
    where = f" to {trip.destination}" if trip.destination else ""
    return f"Your next trip: {trip.title}{where}, from {trip.start_date:%A %d %B}" + (f" to {trip.end_date:%d %B}." if trip.end_date else ".")


def follow_ups(user) -> str:
    from django.utils import timezone
    from apps.career.models import CareerJobAnalysis
    from apps.career.services import application_tracker
    today, rows = timezone.localdate(), []
    for analysis in CareerJobAnalysis.objects.filter(user=user).order_by("-updated_at", "-id")[:300]:
        payload = analysis.extracted_payload if isinstance(analysis.extracted_payload, dict) else {}
        status = application_tracker.follow_up_status(payload.get("application"), today=today)
        if status["status"] == "due":
            rows.append(f"- {analysis.job_title} at {analysis.company} (due {status['due_on']})")
    return "Career follow-ups due:\n" + "\n".join(rows[:20]) if rows else "No career follow-ups are due."


def notices(user) -> str:
    from alfred_ai.views import _attention_items
    from alfred_ai.services.data_sources import data_sources_snapshot
    items = [item["text"] for item in _attention_items(user, data_sources_snapshot(user)["sources"])
             if item.get("spent") is None and not str(item.get("url", "")).startswith(SENSITIVE_PATHS) and "₹" not in item["text"]]
    return "Home notices:\n" + "\n".join(f"- {text}" for text in items) if items else "Nothing needs you right now (money notices stay on your PC)."


def public_answer(question) -> str:
    """A public question answered by the local model from public web results only; never memories, records or chats."""
    from apps.ml_engine.services import web_lookup
    from apps.ml_engine.services.hybrid_intelligence import OllamaReasoner, easy_question
    from apps.ml_engine.services.local_ai_limits import deadline, max_output_tokens
    from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
    try:
        web_lookup.check_public(question)
    except web_lookup.PrivateQuestion:
        return "That looks personal, so ask it in ALFRED on your PC. Here I answer only public questions."
    sources = web_lookup.search(question)
    try:
        reasoner = OllamaReasoner()
        if easy_question(question, "general"):
            reasoner.use_quick_model()
        answer = reasoner.reason({"query": question, "sources": sources, "response_style": "concise"},
                                 max_output_tokens=max_output_tokens(), deadline=deadline())
    except (EmbeddingUnavailable, ValueError):
        return "The local AI on your PC is not answering right now. Try again in a few minutes."
    cited = sorted({item["url"] for item in sources if f"[{item['ref']}]" in answer})
    return answer.strip() + ("\n\nSources:\n" + "\n".join(cited) if cited else "")


def reply_to(chat, text) -> str:
    text = " ".join(str(text or "").split())[:500]
    command, _, rest = text.partition(" ")
    command = command.split("@")[0].lower()
    if command in ("/start", "/link") and rest:
        return _link(chat, rest.strip())
    owner = _load()["links"].get(str(chat))
    user = _user(owner) if owner is not None else None
    if user is None:
        return "This chat is not linked. In ALFRED on your PC open Settings, Telegram, get a code and send: /link <code>"
    if command == "/unlink":
        unlink(user, chat)
        return "Unlinked. This chat gets no more answers."
    return answer_for(user, text)


def answer_for(user, text) -> str:
    """The safe answers Telegram and linked agents share: never money, documents or saved history."""
    text = " ".join(str(text or "").split())[:500]
    command = text.partition(" ")[0].split("@")[0].lower()
    if command in ("/start", "/help"):
        return HELP
    if command == "/trip":
        return next_trip(user)
    if command == "/followups":
        return follow_ups(user)
    if command == "/notices":
        return notices(user)
    if command.startswith("/"):
        return HELP
    return public_answer(text) if text else HELP


def poll_once(wait=15) -> int:
    """Read new messages once and answer each; returns how many were handled."""
    from django.db import close_old_connections
    with _lock:
        offset = _load()["offset"]
    updates = _call("getUpdates", {"offset": offset, "timeout": wait, "allowed_updates": ["message"]},
                    deadline=time.monotonic() + wait + 4) or []
    handled = 0
    for update in updates:
        with _lock:  # saved first, so a message that fails is never answered twice
            state = _load()
            state["offset"] = max(state["offset"], int(update["update_id"]) + 1)
            _save(state)
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        if chat.get("type") != "private" or not isinstance(message.get("text"), str):
            continue  # groups and channels are never answered
        close_old_connections()
        try:
            send(chat["id"], reply_to(chat["id"], message["text"]))
            handled += 1
        except Exception:
            LOGGER.warning("A Telegram message was not answered.")
        finally:
            close_old_connections()
    return handled


def start_polling(keep_running) -> threading.Thread:
    """Background listener in the worker process; idle while no token is set."""
    def run():
        while keep_running():
            if not configured():
                time.sleep(30)
                continue
            try:
                poll_once()
            except Exception:  # offline or Telegram down: retried shortly; the token is never logged
                LOGGER.info("Telegram is not reachable; retrying.")
                time.sleep(10)
    thread = threading.Thread(target=run, name="alfred-telegram", daemon=True)
    thread.start()
    return thread
