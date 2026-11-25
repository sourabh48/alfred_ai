"""Anonymous usage counts to the owner's own PostHog project (owner request 2026-11-25).

ALFRED decides, not each person (owner 2026-11-25): it sends whenever a project key is set, and the allowlist below
decides what may go. ALFRED_USAGE_ANALYTICS=false in config/local.env stops it.

Only the events and values allowed below can leave the PC: which page was opened (its route name, never the address,
so no record IDs or search text) and how a local AI answer went (topic, fast or main model, rounded seconds). Never
amounts, names, emails, questions, answers, document text, file names or keys. Everyone on this PC shares one random
ID, so no person can be told apart, and PostHog is asked to skip location lookup and person profiles.
"""
from __future__ import annotations

import logging
import os
import queue
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings

LOGGER = logging.getLogger(__name__)
SWITCH = "ALFRED_USAGE_ANALYTICS"
KEY, HOST = "ALFRED_POSTHOG_PROJECT_KEY", "ALFRED_POSTHOG_HOST"
HOSTS = ("https://eu.i.posthog.com", "https://us.i.posthog.com")  # PostHog Cloud only; EU first
ROUTE = re.compile(r"^[a-z][\w:.-]{0,79}$", re.I)
SCOPES = {"general", "finance", "travel", "career", "documents", "bank_statements", "financial_records", "financial_document"}
MODELS = re.compile(r"^[\w.:-]{1,100}$")
# event: {property: check}; anything else is dropped before sending.
EVENTS = {
    "page_viewed": {"page": lambda value: isinstance(value, str) and bool(ROUTE.match(value))},
    "assistant_answered": {
        "scope": lambda value: value in SCOPES,
        "model": lambda value: value in ("fast", "main"),
        "seconds": lambda value: isinstance(value, (int, float)) and 0 <= value <= 3600,
        "thinking": lambda value: isinstance(value, bool),
        "web_results": lambda value: isinstance(value, bool),
    },
}
_queue: "queue.Queue[dict]" = queue.Queue(maxsize=500)
_worker = None
_lock = threading.Lock()


def enabled() -> bool:
    return os.environ.get(SWITCH) != "false" and bool(os.environ.get(KEY)) and _host() is not None


def _host():
    host = (os.environ.get(HOST) or HOSTS[0]).rstrip("/")
    return host if host in HOSTS else None


def _install_id() -> str:
    path = Path(os.environ.get("ALFRED_DATA_DIR") or settings.BASE_DIR) / "config" / "analytics-id"
    try:
        found = path.read_text(encoding="ascii").strip()
        return str(uuid.UUID(found))
    except (OSError, ValueError):
        new = str(uuid.uuid4())
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new, encoding="ascii")
        except OSError:
            pass  # a fresh ID each start is still anonymous
        return new


def clean(event, properties) -> dict | None:
    """The event with only its allowed properties and values, or None for an event not on the list."""
    checks = EVENTS.get(event)
    if checks is None:
        return None
    kept = {name: value for name, value in (properties or {}).items() if name in checks and checks[name](value)}
    if "seconds" in kept:
        kept["seconds"] = round(float(kept["seconds"]), 1)
    return kept


def model_tier(model) -> str | None:
    """'fast' or 'main' instead of the model's name, which could be one the owner named themselves."""
    if not isinstance(model, str) or not MODELS.match(model):
        return None
    return "fast" if model == settings.ALFRED_QUICK_OLLAMA_MODEL else "main"


def record(event, properties=None) -> None:
    """Queue one event; never raises and never slows the page. Dropped when switched off or the queue is full."""
    if not enabled():
        return
    kept = clean(event, properties)
    if kept is None:
        return
    try:
        _queue.put_nowait({"event": event, "properties": kept, "timestamp": datetime.now(timezone.utc).isoformat()})
    except queue.Full:
        return
    _start()


def _start():
    global _worker
    with _lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_run, name="alfred-usage-analytics", daemon=True)
            _worker.start()


def _run():
    while True:
        batch = [_queue.get()]
        while len(batch) < 50:
            try:
                batch.append(_queue.get(timeout=5))
            except queue.Empty:
                break
        send(batch)


def send(batch) -> bool:
    from alfred_ai.services import public_http
    if not enabled() or not batch:
        return False
    distinct = _install_id()
    body = {"api_key": os.environ[KEY], "batch": [
        {"event": item["event"], "timestamp": item["timestamp"], "distinct_id": distinct,
         "properties": {**item["properties"], "$process_person_profile": False, "$geoip_disable": True, "$lib": "alfred"}}
        for item in batch]}
    try:
        public_http.request("POST", _host() + "/batch/", json_body=body, content_types=("application/json", "text/plain"),
                            max_bytes=10_000)
        return True
    except Exception:  # analytics must never break ALFRED; the key is not logged
        LOGGER.warning("Usage analytics batch was not sent.")
        return False
