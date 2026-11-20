"""ALFRED starts the installed Ollama app again when the local model stops answering (owner, 2026-11-20)."""
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from alfred_ai.services import ollama_keeper


class OllamaKeeperTests(SimpleTestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory(prefix="alfred-ollama-keeper-synthetic-")))
        self.enterContext(patch.dict(os.environ, {"LOCALAPPDATA": str(self.root)}))
        self.start = self.enterContext(patch.object(ollama_keeper.subprocess, "Popen"))
        self.enterContext(patch.object(ollama_keeper.os, "name", "nt"))
        self.enterContext(patch.object(ollama_keeper.subprocess, "DETACHED_PROCESS", 8, create=True))
        self.enterContext(patch.object(ollama_keeper.subprocess, "CREATE_NEW_PROCESS_GROUP", 512, create=True))

    def test_a_stopped_local_ollama_is_started_and_a_running_one_is_left_alone(self):
        app = self.root / "Programs" / "Ollama" / "ollama app.exe"
        with patch.object(ollama_keeper, "answering", return_value=False):
            self.assertEqual(ollama_keeper.ensure_running(), "not_installed")
            app.parent.mkdir(parents=True); app.write_bytes(b"synthetic")
            self.assertEqual(ollama_keeper.ensure_running(), "started")
        self.assertEqual(self.start.call_args.args[0], [str(app)])
        self.start.reset_mock()
        with patch.object(ollama_keeper, "answering", return_value=True):
            self.assertEqual(ollama_keeper.ensure_running(), "running")
        self.start.assert_not_called()

    @override_settings(ALFRED_TRAVEL_LOCAL_READING=True, ALFRED_TRAVEL_READING_MODEL="qwen3.5:9b")
    def test_the_travel_reading_model_is_kept_loaded_when_installed(self):
        with patch("apps.ml_engine.services.local_embeddings.OllamaEmbeddings._request") as ollama:
            ollama.return_value = {"models": [{"name": "qwen3.5:9b"}]}
            self.assertEqual(ollama_keeper.warm_reading_model(), "warm")
            self.assertEqual(ollama.call_args.args[1:], ("/api/generate", {"model": "qwen3.5:9b", "keep_alive": "60m", "stream": False}))
            ollama.reset_mock(return_value=True)
            ollama.return_value = {"models": [{"name": "all-minilm:latest"}]}
            self.assertEqual(ollama_keeper.warm_reading_model(), "not_installed")
            self.assertEqual(ollama.call_count, 1)  # nothing is downloaded or loaded
        with override_settings(ALFRED_TRAVEL_LOCAL_READING=False):
            self.assertEqual(ollama_keeper.warm_reading_model(), "off")

    @override_settings(ALFRED_OLLAMA_HOST="192.168.0.50")
    def test_an_ollama_on_another_lan_pc_is_never_started_from_here(self):
        with patch.object(ollama_keeper, "answering") as probe:
            self.assertEqual(ollama_keeper.ensure_running(), "remote")
        probe.assert_not_called()
        self.start.assert_not_called()
