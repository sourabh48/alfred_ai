"""Nightly fine-tuning of a small local model from ALFRED's central brain (owner approval 2026-11-20).

Runs only on this PC, for one configured owner, on the CPU (the owner's AMD GPU has no PyTorch support on Windows).
It never downloads anything: the base model must already be in ALFRED_BRAIN_BASE_MODEL_DIR and PyTorch, transformers and
peft must be installed in the separate Python named by ALFRED_BRAIN_FINETUNE_PYTHON (see requirements-brain.txt), so the
app's own environment is not changed. The result is imported into the local Ollama as `alfred-brain`; ALFRED keeps using
its current models until the owner names alfred-brain in config/local.env after checking it.

    python scripts/brain_finetune.py --user <username>
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MODEL_NAME = "alfred-brain"
EPOCHS = 2
MAX_TOKENS = 1024


def records(user):
    """The owner's brain examples as chat records, oldest first; private data never leaves this PC."""
    from apps.ml_engine.services.brain import examples
    from apps.mobility.services.travel.understanding import SYSTEM
    out = []
    for item in reversed(examples(user, "travel_reading")):
        if isinstance(item.get("message"), str) and isinstance(item.get("meant"), dict):
            out.append({"messages": [{"role": "system", "content": SYSTEM.split(" Today is ")[0]},
                                     {"role": "user", "content": json.dumps({"message": item["message"]}, ensure_ascii=False)},
                                     {"role": "assistant", "content": json.dumps(item["meant"], ensure_ascii=False)}]})
    for item in reversed(examples(user, "public_answer")):
        if isinstance(item.get("question"), str) and isinstance(item.get("answer"), str):
            out.append({"messages": [{"role": "user", "content": item["question"]},
                                     {"role": "assistant", "content": item["answer"]}]})
    return out


def status_file(data_dir):
    return Path(data_dir) / "artifacts" / "brain-training" / "status.json"


def write_status(data_dir, **values):
    path = status_file(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"at": datetime.now(timezone.utc).isoformat(), **values}, indent=1), encoding="utf-8")


def train(chats, base, out_dir):  # pragma: no cover - needs the optional PyTorch stack; run by hand after install
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.set_num_threads(max(1, (os.cpu_count() or 2) - 1))  # leave a core for the owner
    tokenizer = AutoTokenizer.from_pretrained(base, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(base, local_files_only=True, torch_dtype=torch.float32)
    model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, task_type="CAUSAL_LM",
                                             target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]))
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=2e-4)
    model.train()
    losses = []
    for _ in range(EPOCHS):
        for chat in chats:
            text = tokenizer.apply_chat_template(chat["messages"], tokenize=False)
            batch = tokenizer(text, return_tensors="pt", truncation=True, max_length=MAX_TOKENS)
            loss = model(**batch, labels=batch["input_ids"]).loss
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            losses.append(float(loss))
    merged = model.merge_and_unload()
    merged.save_pretrained(out_dir, safe_serialization=True)
    tokenizer.save_pretrained(out_dir)
    return round(sum(losses[-len(chats):]) / max(1, len(chats)), 4)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--user", required=True)
    args = parser.parse_args(argv)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alfred_ai.settings")
    import django
    django.setup()
    from django.conf import settings
    from django.contrib.auth import get_user_model

    data_dir = os.environ.get("ALFRED_DATA_DIR") or str(ROOT)
    user = get_user_model().objects.filter(username=args.user).first()
    if user is None:
        write_status(data_dir, state="no_such_user")
        return 2
    chats = records(user)
    if len(chats) < settings.ALFRED_BRAIN_FINETUNE_MIN_EXAMPLES:
        write_status(data_dir, state="too_few_examples", examples=len(chats))
        return 0
    base = Path(settings.ALFRED_BRAIN_BASE_MODEL_DIR)
    if not (base / "config.json").is_file():
        write_status(data_dir, state="base_model_missing", examples=len(chats))
        return 3
    try:
        import peft, torch, transformers  # noqa: F401
    except ImportError:
        write_status(data_dir, state="dependencies_missing", examples=len(chats))
        return 3
    out_dir = Path(data_dir) / "artifacts" / "brain-model"
    write_status(data_dir, state="training", examples=len(chats))
    loss = train(chats, base, out_dir)
    (out_dir / "Modelfile").write_text(f"FROM {out_dir}\n", encoding="utf-8")
    created = subprocess.run(["ollama", "create", MODEL_NAME, "-f", str(out_dir / "Modelfile")], capture_output=True, text=True, timeout=3600)
    write_status(data_dir, state="ready" if created.returncode == 0 else "ollama_import_failed", examples=len(chats),
                 loss=loss, model=MODEL_NAME if created.returncode == 0 else None, detail=created.stderr[-300:])
    return 0 if created.returncode == 0 else 4


if __name__ == "__main__":
    sys.exit(main())
