"""Offline speech for the assistant (AI-18).

Speech-to-text runs Whisper base in process through the installed transformers.
Text-to-speech runs Piper as a separate program: Piper is GPL-3.0, so ALFRED
never imports it. Audio is processed in memory and never stored.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import threading
import wave
from pathlib import Path

import numpy as np
from django.conf import settings

RATE = 16000
MAX_SECONDS = 30
MAX_AUDIO_BYTES = 44 + RATE * 2 * MAX_SECONDS
MAX_SPEAK_CHARS = 600
VOICE = "en_GB-vctk-medium.onnx"
SPEAKER = "p254"  # VCTK Southern English male; the deepest of the British male voices checked
DEEPER = 0.96  # play slightly slower and lower than the stock voice for a calm, measured tone

# Steers Whisper toward money words: without it, "1 lakh by March" came back as "1-Lac by much".
HINT = "Add a savings goal of 1 lakh by March 2027. Update Emergency fund saved to 25000."
_lock = threading.Lock()
_whisper = None


class SpeechError(ValueError):
    pass


class SpeechUnavailable(RuntimeError):
    pass


def _root() -> Path:
    return Path(settings.SPEECH_MODEL_DIR)


def status() -> dict:
    voice = _root() / "piper" / VOICE
    # shortcut: the frozen installer build does not bundle Piper; speaking works from a checkout only.
    piper = not getattr(sys, "frozen", False) and importlib.util.find_spec("piper") is not None
    return {
        "listen": (_root() / "whisper-base" / "model.safetensors").is_file(),
        "speak": piper and voice.is_file() and voice.with_suffix(".onnx.json").is_file(),
    }


def read_wav(data: bytes) -> np.ndarray:
    if len(data) > MAX_AUDIO_BYTES:
        raise SpeechError(f"Recordings are limited to {MAX_SECONDS} seconds.")
    try:
        with wave.open(io.BytesIO(data)) as audio:
            if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, RATE):
                raise SpeechError("Send 16 kHz mono 16-bit audio.")
            frames = audio.readframes(audio.getnframes())
    except (wave.Error, EOFError) as error:
        raise SpeechError("The recording is not valid WAV audio.") from error
    if not frames:
        raise SpeechError("No audio was recorded.")
    return np.frombuffer(frames, "<i2").astype(np.float32) / 32768.0


def _load_whisper():
    global _whisper
    if _whisper is None:
        path = _root() / "whisper-base"
        if not status()["listen"]:
            raise SpeechUnavailable("The offline speech-to-text model is not installed.")
        from transformers import WhisperForConditionalGeneration, WhisperProcessor

        processor = WhisperProcessor.from_pretrained(path, local_files_only=True)
        model = WhisperForConditionalGeneration.from_pretrained(path, local_files_only=True, use_safetensors=True)
        _whisper = (processor, model.eval(), processor.get_prompt_ids(HINT, return_tensors="pt"))
    return _whisper


def transcribe(data: bytes) -> str:
    audio = read_wav(data)
    import torch

    with _lock:
        processor, model, hint = _load_whisper()
        features = processor(audio, sampling_rate=RATE, return_tensors="pt").input_features
        with torch.inference_mode():
            tokens = model.generate(features, language="en", task="transcribe", prompt_ids=hint)
    return processor.batch_decode(tokens, skip_special_tokens=True)[0].strip()


def speak(text) -> bytes:
    text = " ".join(str(text or "").split())[:MAX_SPEAK_CHARS]
    if not text:
        raise SpeechError("There is nothing to read aloud.")
    if not status()["speak"]:
        raise SpeechUnavailable("The offline voice is not installed.")
    voice = _root() / "piper" / VOICE
    config = json.loads(voice.with_suffix(".onnx.json").read_text(encoding="utf-8"))
    command = [sys.executable, "-m", "piper", "-m", str(voice), "-s", str(config["speaker_id_map"][SPEAKER]), "--output-raw"]
    try:
        result = subprocess.run(
            command, input=text.encode("utf-8"), capture_output=True, timeout=60, check=True,
            env={**os.environ, "PYTHONUTF8": "1"}, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise SpeechUnavailable("The offline voice could not run.") from error
    if not result.stdout:
        raise SpeechUnavailable("The offline voice produced no audio.")
    out = io.BytesIO()
    with wave.open(out, "wb") as target:  # raw 16-bit mono PCM, played back slightly slower and lower
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(int(config["audio"]["sample_rate"] * DEEPER))
        target.writeframes(result.stdout)
    return out.getvalue()
