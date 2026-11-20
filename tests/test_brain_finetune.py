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
from apps.mobility.services.travel import understanding
from scripts import brain_finetune


class StartTests(TestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory(prefix="alfred-finetune-synthetic-")))
        (root / "base").mkdir()
        (root / "base" / "config.json").write_text("{}")
        (root / "convert_hf_to_gguf.py").write_text("")
        self.root = root
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root / "artifacts" / "private-memory-v2"),
                                            ALFRED_BRAIN_CONVERTER=str(root / "convert_hf_to_gguf.py"),
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
                self.assertEqual(command[command.index("--converter") + 1], str(self.root / "convert_hf_to_gguf.py"))
                scoring = json.loads(Path(command[command.index("--held-back") + 1]).read_text(encoding="utf-8"))
                self.assertEqual((scoring["current_model"], scoring["items"]), (settings.ALFRED_TRAVEL_READING_MODEL, []))
                self.assertEqual(scoring["format"]["type"], "object")
                chats = [json.loads(line) for line in (work / "chats.jsonl").read_text(encoding="utf-8").splitlines()]
                self.assertEqual(len(chats), 2)
                (work / "status.json").write_text(json.dumps({"state": "ready", "examples": 2}))
                self.assertEqual(ollama_keeper.start_brain_finetune(), "nothing_new")
            with override_settings(**{**ready, "ALFRED_BRAIN_BASE_MODEL_DIR": str(self.root / "absent")}):
                self.assertEqual(ollama_keeper.start_brain_finetune(), "base_model_missing")
            with override_settings(**{**ready, "ALFRED_BRAIN_CONVERTER": ""}):
                self.assertEqual(ollama_keeper.start_brain_finetune(), "converter_missing")
        self.assertEqual(start.call_count, 1)

    def test_the_trainer_deletes_the_exported_examples_and_records_the_outcome(self):
        chats, status = self.root / "chats.jsonl", self.root / "status.json"
        chats.write_text(json.dumps({"messages": []}) + "\n", encoding="utf-8")
        arguments = ["--chats", str(chats), "--base", "b", "--out", str(self.root), "--status", str(status), "--ollama", "ollama",
                     "--converter", "convert_hf_to_gguf.py"]
        with patch.object(brain_finetune, "train", side_effect=ImportError("no torch")):
            self.assertEqual(brain_finetune.main(arguments), 5)
        self.assertFalse(chats.exists())
        self.assertEqual(json.loads(status.read_text())["state"], "failed")
        chats.write_text(json.dumps({"messages": []}) + "\n", encoding="utf-8")
        with patch.object(brain_finetune, "train", return_value=0.5), patch("subprocess.run") as run:
            run.return_value.returncode, run.return_value.stderr = 0, ""
            self.assertEqual(brain_finetune.main(arguments), 0)
        convert, create = (call.args[0] for call in run.call_args_list)
        self.assertEqual(convert[1:3], ["convert_hf_to_gguf.py", str(self.root / "merged")])
        self.assertEqual(convert[-2:], ["--outfile", str(self.root / "alfred-brain.gguf")])
        self.assertEqual(create[:3], ["ollama", "create", "alfred-brain"])
        self.assertIn("alfred-brain.gguf", (self.root / "Modelfile").read_text())
        self.assertEqual(json.loads(status.read_text())["state"], "ready")
        self.assertIsNone(json.loads(status.read_text())["scores"])
        self.assertFalse(chats.exists())

    def test_held_back_examples_score_both_models_and_are_deleted(self):
        chats, status, held = self.root / "chats.jsonl", self.root / "status.json", self.root / "held_back.json"
        chats.write_text(json.dumps({"messages": []}) + "\n", encoding="utf-8")
        items = [{"messages": [], "expected": {"destination": "Goa", "travellers": 4}},
                 {"messages": [], "expected": {"trip_styles": ["beach", "food"]}}]
        held.write_text(json.dumps({"current_model": "qwen3.5:9b", "format": {}, "items": items}), encoding="utf-8")
        answers = {"qwen3.5:9b": [{"destination": "goa", "travellers": 4, "food": None}, {"trip_styles": ["food"]}],
                   "alfred-brain": [{"destination": "Goa", "travellers": 4}, {"trip_styles": ["Food", "beach"], "avoid": []}]}

        def fake_ask(url, model, messages, schema):
            return answers[model].pop(0)
        arguments = ["--chats", str(chats), "--base", "b", "--out", str(self.root), "--status", str(status), "--ollama", "ollama",
                     "--converter", "c.py", "--held-back", str(held), "--ollama-url", "http://127.0.0.1:11434"]
        with patch.object(brain_finetune, "train", return_value=0.5), patch("subprocess.run") as run, \
                patch.object(brain_finetune, "ask", side_effect=fake_ask):
            run.return_value.returncode, run.return_value.stderr = 0, ""
            self.assertEqual(brain_finetune.main(arguments), 0)
        result = json.loads(status.read_text())
        self.assertEqual(result["scores"], {"current_model": "qwen3.5:9b", "held_back": 2, "current": 0.5, "new": 1.0})
        self.assertFalse(held.exists())


class SwitchTests(TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory(prefix="alfred-switch-synthetic-")))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(self.root / "artifacts" / "private-memory-v2"),
                                            ALFRED_TRAVEL_READING_MODEL="qwen3.5:9b"))
        (self.root / "artifacts" / "brain-training").mkdir(parents=True)

    def outcome(self, **scores):
        (self.root / "artifacts" / "brain-training" / "status.json").write_text(json.dumps(
            {"state": "ready", "model": "alfred-brain",
             "scores": {"current_model": "qwen3.5:9b", "held_back": 50, "current": 0.8, "new": 0.8, **scores}}))
        return understanding.reading_model()

    def test_the_reader_switches_only_when_the_new_model_scores_at_least_as_well(self):
        self.assertEqual(understanding.reading_model(), "qwen3.5:9b")  # never trained
        self.assertEqual(self.outcome(), "alfred-brain")
        self.assertEqual(self.outcome(new=0.79), "qwen3.5:9b")
        self.assertEqual(self.outcome(held_back=5), "qwen3.5:9b")  # too few to tell
        self.assertEqual(self.outcome(current_model="qwen3.5:35b-a3b"), "qwen3.5:9b")  # compared with another model
