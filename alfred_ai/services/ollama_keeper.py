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


def start_brain_finetune():
    """Export the owner's brain examples and start scripts/brain_finetune.py at low priority in its own Python."""
    import json
    from django.contrib.auth import get_user_model
    from apps.ml_engine.services.brain import held_back, training_chats
    from apps.mobility.services.travel.understanding import SCHEMA
    from apps.ml_engine.services.memory_key import private_directory
    name, python, base = settings.ALFRED_BRAIN_FINETUNE_USER, settings.ALFRED_BRAIN_FINETUNE_PYTHON, Path(settings.ALFRED_BRAIN_BASE_MODEL_DIR)
    if not name or not python:
        return "off"
    if not Path(python).is_file():
        return "python_missing"
    if not (base / "config.json").is_file():
        return "base_model_missing"
    converter = Path(settings.ALFRED_BRAIN_CONVERTER)
    if not settings.ALFRED_BRAIN_CONVERTER or not converter.is_file():
        return "converter_missing"
    user = get_user_model().objects.filter(username=name).first()
    if user is None:
        return "no_such_user"
    chats = training_chats(user)
    work = Path(settings.ALFRED_MEMORY_DIR).parent / "brain-training"
    private_directory(work.absolute())
    status = work / "status.json"
    try:
        last = json.loads(status.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        last = {}
    if len(chats) < settings.ALFRED_BRAIN_FINETUNE_MIN_EXAMPLES:
        return "too_few_examples"
    if last.get("state") in ("training", "scoring") or (last.get("state") == "ready" and last.get("examples") == len(chats)):
        return "nothing_new"
    exported = work / "chats.jsonl"  # deleted by the script when it ends; the vault keeps the encrypted copy
    exported.write_text("".join(json.dumps(chat, ensure_ascii=False) + "\n" for chat in chats), encoding="utf-8")
    scoring = work / "held_back.json"  # deleted with the examples; the new model must match the current one on these
    scoring.write_text(json.dumps({"current_model": settings.ALFRED_TRAVEL_READING_MODEL, "format": SCHEMA,
                                   "items": held_back(user)}, ensure_ascii=False), encoding="utf-8")
    ollama = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    flags = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.BELOW_NORMAL_PRIORITY_CLASS
             if os.name == "nt" else 0)
    subprocess.Popen([python, str(Path(settings.BASE_DIR) / "scripts" / "brain_finetune.py"), "--chats", str(exported),
                      "--base", str(base), "--out", str(work.parent / "brain-model"), "--status", str(status),
                      "--ollama", str(ollama) if ollama.is_file() else "ollama", "--converter", str(converter),
                      "--held-back", str(scoring), "--ollama-url", f"http://{settings.ALFRED_OLLAMA_HOST}:{settings.ALFRED_OLLAMA_PORT}"],
                     cwd=work, creationflags=flags, close_fds=True)
    return "started"


WARM_FOR = "60m"  # refreshed every two minutes while ALFRED runs, so the model stays loaded


def warm_reading_model():
    """Keep the Travel models loaded: a cold load took about 20 s on the owner PC, a warm reading about 3 s. The configured
    model answers trip questions; a fine-tuned reader that tested better (understanding.reading_model) is kept loaded too."""
    if not settings.ALFRED_TRAVEL_LOCAL_READING:
        return "off"
    from apps.ml_engine.services.local_embeddings import OllamaEmbeddings
    from apps.mobility.services.travel.understanding import reading_model
    client, deadline = OllamaEmbeddings(), time.monotonic() + 90
    installed = {item.get("name") for item in client._request("GET", "/api/tags", deadline=deadline).get("models", [])}
    models = [model for model in dict.fromkeys((settings.ALFRED_TRAVEL_READING_MODEL, reading_model()))
              if model in installed or f"{model}:latest" in installed]
    for model in models:
        client._request("POST", "/api/generate", {"model": model, "keep_alive": WARM_FOR, "stream": False}, deadline=deadline)
    return "warm" if models else "not_installed"
