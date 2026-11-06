"""AI-18: offline speech checks audio before use, stores nothing and runs Piper as a separate program."""
import io
import json
import subprocess
import tempfile
import wave
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.ml_engine.services import speech


def wav_bytes(seconds=1.0, rate=16000, channels=1):
    out = io.BytesIO()
    with wave.open(out, "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(b"\x01\x00" * int(seconds * rate) * channels)
    return out.getvalue()


class SpeechTests(TestCase):
    def setUp(self):
        self.models = tempfile.TemporaryDirectory()
        self.addCleanup(self.models.cleanup)
        self.settings_override = override_settings(SPEECH_MODEL_DIR=self.models.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.client.force_login(get_user_model().objects.create_user(username="synthetic-speech-owner"))

    def test_audio_is_checked_before_any_model_runs(self):
        self.assertEqual(len(speech.read_wav(wav_bytes(0.5))), 8000)
        for data in (wav_bytes(rate=44100), wav_bytes(channels=2), wav_bytes(0), b"not audio", wav_bytes(31)):
            with self.subTest(size=len(data)), self.assertRaises(speech.SpeechError):
                speech.read_wav(data)

    def test_missing_models_are_reported_not_downloaded(self):
        self.assertEqual(speech.status(), {"listen": False, "speak": False})
        self.assertEqual(self.client.get("/api/ai/speech/status/").json(), {"listen": False, "speak": False})
        response = self.client.post("/api/ai/speech/transcribe/", wav_bytes(), content_type="audio/wav")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.client.post("/api/ai/speech/speak/", {"text": "Hello"}, content_type="application/json").status_code, 503)

    def test_transcribe_reads_recordings_above_the_form_limit_and_rejects_longer_ones(self):
        audio = wav_bytes(20)  # about 640 KB, above the 256 KB form-body limit
        with patch.object(speech, "transcribe", side_effect=lambda data: f"{len(data)} bytes") as run:
            response = self.client.post("/api/ai/speech/transcribe/", audio, content_type="audio/wav")
            self.assertEqual(response.json(), {"text": f"{len(audio)} bytes"})
            too_long = self.client.post("/api/ai/speech/transcribe/", wav_bytes(31), content_type="audio/wav")
        self.assertEqual(too_long.status_code, 413)
        run.assert_called_once()

    def test_speak_runs_piper_as_a_separate_program_and_returns_a_deeper_wav(self):
        voice = Path(self.models.name) / "piper" / speech.VOICE
        voice.parent.mkdir()
        voice.write_bytes(b"synthetic")
        voice.with_suffix(".onnx.json").write_text(json.dumps({"audio": {"sample_rate": 22050}, "speaker_id_map": {"p254": 76}}))
        done = subprocess.CompletedProcess([], 0, stdout=b"\x00\x01" * 100, stderr=b"")
        with patch.object(speech.importlib.util, "find_spec", return_value=object()), \
                patch.object(speech.subprocess, "run", return_value=done) as run:
            response = self.client.post("/api/ai/speech/speak/", {"text": "  Good   evening.  "}, content_type="application/json")
            blank = self.client.post("/api/ai/speech/speak/", {"text": "   "}, content_type="application/json")
        self.assertEqual((response.status_code, response["Content-Type"], response["Cache-Control"]), (200, "audio/wav", "no-store"))
        with wave.open(io.BytesIO(response.content)) as audio:
            self.assertEqual((audio.getframerate(), audio.getnframes()), (int(22050 * speech.DEEPER), 100))
        command = run.call_args.args[0]
        self.assertEqual(command[1:3], ["-m", "piper"])
        self.assertIn("--output-raw", command)
        self.assertEqual(command[command.index("-s") + 1], "76")
        self.assertEqual(run.call_args.kwargs["input"], b"Good evening.")
        self.assertEqual(blank.status_code, 400)
        run.assert_called_once()

    def test_speech_needs_a_signed_in_owner(self):
        self.client.logout()
        for method, url in (("get", "/api/ai/speech/status/"), ("post", "/api/ai/speech/transcribe/"), ("post", "/api/ai/speech/speak/")):
            with self.subTest(url=url):
                self.assertIn(getattr(self.client, method)(url).status_code, (401, 403))
