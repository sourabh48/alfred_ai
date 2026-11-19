"""Keep the local model running: start the installed Ollama app when Ollama on this PC stops answering (owner, 2026-11-20)."""
import os
import socket
import subprocess
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
