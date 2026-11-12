"""Owner-configurable local AI limits (owner decision 2026-11-12): set in config/local.env, generous defaults.

Nothing here allows a cloud host: Ollama must run on this PC or a private LAN address the owner controls.
"""
import ipaddress
import json
import time

from django.conf import settings

# Characters per token is about 4 for English JSON; 3 keeps a safety margin for numbers and non-Latin text.
BYTES_PER_TOKEN = 3
SYSTEM_PROMPT_TOKENS = 1024
FALLBACK_CONTEXT_TOKENS = 8192
_windows = {}


def ollama_address():
    """(host, port) of the owner's Ollama listener; refuses anything that is not loopback or a private LAN address."""
    host = str(settings.ALFRED_OLLAMA_HOST).strip()
    port = settings.ALFRED_OLLAMA_PORT
    try:
        address = ipaddress.ip_address('127.0.0.1' if host == 'localhost' else host)
    except ValueError:
        address = None
    if (address is None or not (address.is_loopback or address.is_private) or address.is_link_local
            or address.is_unspecified or type(port) is not int or not 0 < port < 65536):
        from .local_embeddings import EmbeddingUnavailable
        raise EmbeddingUnavailable('ALFRED_OLLAMA_HOST must be this PC or a private LAN IP address.')
    return str(address), port


def timeout_seconds():
    return max(1, int(settings.ALFRED_LOCAL_AI_TIMEOUT_SECONDS))


def deadline():
    return time.monotonic() + timeout_seconds()


def max_output_tokens():
    return max(64, int(settings.ALFRED_LOCAL_AI_MAX_OUTPUT_TOKENS))


def learn_window(client, digest, *, deadline=None):
    """Remember the model's own context window, read once per installed model digest from Ollama /api/show.

    Called from the reasoner's model check, so a failed lookup costs nothing and is retried next time.
    """
    model = getattr(client, 'model', None)
    if _windows.get(model, (None,))[0] == digest:
        return
    try:
        limit = time.monotonic() + 10
        info = client._request('POST', '/api/show', {'model': model},
                               deadline=limit if deadline is None else min(deadline, limit)).get('model_info', {})
        window = next((value for key, value in info.items()
                       if key.endswith('.context_length') and type(value) is int and value > 0), None)
    except Exception:
        return  # unknown window: callers use the safe fallback, never a guess above it
    if window:
        _windows[model] = (digest, window)


def context_tokens(client):
    """num_ctx for the client's model: its real window once known, capped by the owner's setting."""
    cap = max(2048, int(settings.ALFRED_LOCAL_AI_MAX_CONTEXT_TOKENS))
    model = getattr(client, 'model', None)
    window = _windows.get(model)[1] if isinstance(model, str) and model in _windows else None
    return min(cap, window or FALLBACK_CONTEXT_TOKENS)


def context_bytes(num_ctx, output_tokens):
    """Prompt bytes that fit num_ctx after the system prompt and the answer budget."""
    return max(4096, (num_ctx - output_tokens - SYSTEM_PROMPT_TOKENS) * BYTES_PER_TOKEN)


def payload_bytes(payload):
    return len(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode())
