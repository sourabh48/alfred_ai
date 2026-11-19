"""Keep the local model running: start the installed Ollama app when Ollama on this PC stops answering (owner, 2026-11-20)."""
import os
import socket
import subprocess
import time
from pathlib import Path

from django.conf import settings


def answering(timeout=2):
    try:
        with socket.create_connection((settings.ALFRED_OLLAMA_HOST, settings.ALFRED_OLLAMA_PORT), timeout=timeout):
            return True
    except OSError:
        return False


def ensure_running():
    """'running', 'started', 'not_installed' or 'remote'; a LAN Ollama is someone else's to start."""
    if settings.ALFRED_OLLAMA_HOST not in ("127.0.0.1", "localhost", "::1"):
        return "remote"
    if answering():
        return "running"
    app = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama app.exe"
    if os.name != "nt" or not app.is_file():
        return "not_installed"
    subprocess.Popen([str(app)], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP, close_fds=True)
    return "started"


WARM_FOR = "60m"  # refreshed every two minutes while ALFRED runs, so the model stays loaded


def warm_reading_model():
    """Keep the Travel reading model loaded: a cold load took about 20 s on the owner PC, a warm reading about 3 s."""
    if not settings.ALFRED_TRAVEL_LOCAL_READING:
        return "off"
    from apps.ml_engine.services.local_embeddings import OllamaEmbeddings
    client, model, deadline = OllamaEmbeddings(), settings.ALFRED_TRAVEL_READING_MODEL, time.monotonic() + 90
    installed = {item.get("name") for item in client._request("GET", "/api/tags", deadline=deadline).get("models", [])}
    if model not in installed and f"{model}:latest" not in installed:
        return "not_installed"
    client._request("POST", "/api/generate", {"model": model, "keep_alive": WARM_FOR, "stream": False}, deadline=deadline)
    return "warm"
