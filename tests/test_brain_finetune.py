"""Nightly fine-tuning starts only when set up, exports one owner's examples and the trainer deletes them (2026-11-20)."""
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from alfred_ai.services import ollama_keeper
from apps.ml_engine.services import brain
from scripts import brain_finetune


class StartTests(TestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory(prefix="alfred-finetune-synthetic-")))
        (root / "base").mkdir()
        (root / "base" / "config.json").write_text("{}")
        self.root = root
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root / "artifacts" / "private-memory-v2"),
                                            ALFRED_BRAIN_BASE_MODEL_DIR=str(root / "base"), ALFRED_BRAIN_FINETUNE_MIN_EXAMPLES=2))
        self.owner = get_user_model().objects.create_user("synthetic-finetune-owner")

    def test_it_starts_only_when_set_up_and_there_is_something_new(self):
        ready = dict(ALFRED_BRAIN_FINETUNE_USER="synthetic-finetune-owner", ALFRED_BRAIN_FINETUNE_PYTHON=sys.executable)
        with patch("subprocess.Popen") as start:
            self.assertEqual(ollama_keeper.start_brain_finetune(), "off")
            with override_settings(**{**ready, "ALFRED_BRAIN_FINETUNE_PYTHON": "Z:/missing/python.exe"}):
                self.assertEqual(ollama_keeper.start_brain_finetune(), "python_missing")
            with override_settings(**{**ready, "ALFRED_BRAIN_FINETUNE_USER": "nobody"}):
                self.assertEqual(ollama_keeper.start_brain_finetune(), "no_such_user")
            with override_settings(**ready):
                brain.remember(self.owner, "public_answer", {"question": "What is a dosa?", "answer": "A crepe."})
                self.assertEqual(ollama_keeper.start_brain_finetune(), "too_few_examples")
                brain.remember(self.owner, "travel_reading", {"message": "me n the gang", "meant": {"travellers": 5}})
                self.assertEqual(ollama_keeper.start_brain_finetune(), "started")
                command = start.call_args.args[0]
                work = self.root / "artifacts" / "brain-training"
                self.assertEqual(command[:2], [sys.executable, str(Path(settings.BASE_DIR) / "scripts" / "brain_finetune.py")])
                self.assertEqual(command[command.index("--base") + 1], str(self.root / "base"))
                chats = [json.loads(line) for line in (work / "chats.jsonl").read_text(encoding="utf-8").splitlines()]
                self.assertEqual(len(chats), 2)
                (work / "status.json").write_text(json.dumps({"state": "ready", "examples": 2}))
                self.assertEqual(ollama_keeper.start_brain_finetune(), "nothing_new")
            with override_settings(**{**ready, "ALFRED_BRAIN_BASE_MODEL_DIR": str(self.root / "absent")}):
                self.assertEqual(ollama_keeper.start_brain_finetune(), "base_model_missing")
        self.assertEqual(start.call_count, 1)

    def test_the_trainer_deletes_the_exported_examples_and_records_the_outcome(self):
        chats, status = self.root / "chats.jsonl", self.root / "status.json"
        chats.write_text(json.dumps({"messages": []}) + "\n", encoding="utf-8")
        arguments = ["--chats", str(chats), "--base", "b", "--out", str(self.root), "--status", str(status), "--ollama", "ollama"]
        with patch.object(brain_finetune, "train", side_effect=ImportError("no torch")):
            self.assertEqual(brain_finetune.main(arguments), 5)
        self.assertFalse(chats.exists())
        self.assertEqual(json.loads(status.read_text())["state"], "failed")
        chats.write_text(json.dumps({"messages": []}) + "\n", encoding="utf-8")
        with patch.object(brain_finetune, "train", return_value=0.5), patch("subprocess.run") as run:
            run.return_value.returncode, run.return_value.stderr = 0, ""
            self.assertEqual(brain_finetune.main(arguments), 0)
        self.assertEqual(run.call_args.args[0][:3], ["ollama", "create", "alfred-brain"])
        self.assertEqual(json.loads(status.read_text())["state"], "ready")
        self.assertFalse(chats.exists())
