"""Agent-to-agent (A2A) link: another AI agent on this PC or the home network can ask ALFRED what Telegram can.

Owner request 2026-11-25, outside sensitive finance. Shape follows OpenJarvis `a2a/` (Apache-2.0, 86f75ef): an agent
card at /.well-known/agent.json and JSON-RPC 2.0 `tasks/send` (also `message/send`) at /a2a/tasks. Built independently
and stricter: a bearer token made in Settings is always required (upstream allows none), only loopback or private
network addresses are served, and answers are the read-only Telegram set (next trip, due follow-ups, non-money
notices, public questions). Tokens are stored only as SHA-256 hashes and shown once.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import secrets
import threading
from pathlib import Path

from django.conf import settings

_lock = threading.Lock()
PREFIX = "alfred_a2a_"
# Home and office ranges only; Python also calls documentation and other reserved ranges private.
HOME_NETWORKS = tuple(ipaddress.ip_network(net) for net in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7"))


def _path() -> Path:
    return Path(os.environ.get("ALFRED_DATA_DIR") or settings.BASE_DIR) / "config" / "agent-tokens.json"


def _load() -> dict:
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
        return {str(k): int(v) for k, v in data.items()} if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _save(data) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data), encoding="utf-8")
    temporary.replace(path)


def _hash(token) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token(user) -> str:
    token = PREFIX + secrets.token_urlsafe(32)
    with _lock:
        data = _load()
        if sum(owner == user.pk for owner in data.values()) >= 5:
            raise ValueError("You have 5 agent tokens; remove them before making another.")
        data[_hash(token)] = user.pk
        _save(data)
    return token


def count(user) -> int:
    return sum(owner == user.pk for owner in _load().values())


def revoke(user) -> None:
    with _lock:
        _save({key: owner for key, owner in _load().items() if owner != user.pk})


def user_for(token):
    if not isinstance(token, str) or not token.startswith(PREFIX):
        return None
    owner = _load().get(_hash(token))
    if owner is None:
        return None
    from django.contrib.auth import get_user_model
    return get_user_model().objects.filter(pk=owner, is_active=True).first()


def nearby(address) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    if getattr(ip, "ipv4_mapped", None):
        ip = ip.ipv4_mapped
    return ip.is_loopback or any(ip in network for network in HOME_NETWORKS if network.version == ip.version)


def card(base_url) -> dict:
    return {"name": "ALFRED", "description": "Read-only answers from this PC: next trip, career follow-ups that are due, "
            "Home notices without money, and public questions. Money, documents and saved history are never shared.",
            "url": base_url.rstrip("/") + "/a2a/tasks", "version": "1.0", "capabilities": {"streaming": False},
            "authentication": {"schemes": ["bearer"]}, "defaultInputModes": ["text"], "defaultOutputModes": ["text"],
            "skills": [{"id": "trip", "name": "Next trip", "description": "Send /trip"},
                       {"id": "followups", "name": "Career follow-ups due", "description": "Send /followups"},
                       {"id": "notices", "name": "Home notices without money", "description": "Send /notices"},
                       {"id": "public", "name": "Public questions", "description": "Ask any public question"}]}


def _error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle(user, request) -> dict:
    """One JSON-RPC request; nothing is saved, so tasks/get and tasks/cancel are not offered."""
    from alfred_ai.services.telegram_bot import answer_for
    if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
        return _error(None, -32600, "Send one JSON-RPC 2.0 request.")
    request_id = request.get("id")
    if request.get("method") not in ("tasks/send", "message/send"):
        return _error(request_id, -32601, "Only tasks/send and message/send are offered.")
    params = request.get("params") if isinstance(request.get("params"), dict) else {}
    message = params.get("message") if isinstance(params.get("message"), dict) else {}
    parts = message.get("parts") if isinstance(message.get("parts"), list) else []
    text = " ".join(str(part.get("text")) for part in parts if isinstance(part, dict) and isinstance(part.get("text"), str))
    if not text.strip():
        return _error(request_id, -32602, "Send the question as a text part.")
    answer = answer_for(user, text)
    task_id = str(params.get("id") or secrets.token_hex(8))[:64]
    return {"jsonrpc": "2.0", "id": request_id, "result": {
        "id": task_id, "status": {"state": "completed"},
        "artifacts": [{"parts": [{"type": "text", "kind": "text", "text": answer}]}]}}
