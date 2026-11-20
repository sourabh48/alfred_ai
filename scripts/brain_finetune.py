"""Nightly fine-tuning of a small local model from ALFRED's central brain (owner approval 2026-11-20).

ALFRED exports one owner's brain examples to a private file, then starts this script in a separate Python that has the
CPU PyTorch stack (the owner's AMD GPU has no PyTorch support on Windows). This script never imports Django, never
downloads anything (the base model must already be on disk) and deletes the exported examples when it ends. The result is
imported into the local Ollama as `alfred-brain`; ALFRED keeps its current models until the owner names alfred-brain in
config/local.env after checking it.

Setup, once, with the owner's approval (2026-11-20). The app never installs these; they live only in that Python:
    py -3.12 -m venv F:/ALFRED/brain/venv
    F:/ALFRED/brain/venv/Scripts/python -m pip install <TORCH> --index-url https://download.pytorch.org/whl/cpu
    F:/ALFRED/brain/venv/Scripts/python -m pip install <PACKAGES>
requirements-brain.txt names the same packages; TORCH and PACKAGES below are the exact versions installed and tested.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

TORCH = "torch==2.15.0"  # CPU build, from download.pytorch.org/whl/cpu
PACKAGES = ("transformers==5.23.0", "peft==0.22.0", "accelerate==1.16.0", "safetensors==0.8.0", "huggingface_hub==2.4.0",
            "sentencepiece==0.2.3")
# GGUF converter: llama.cpp v1.0.0 (MIT) source archive sha256 b8d90ec2be080e8834d05e4449793160d68d62518f614be4248d380f3b7c118b;
# keep convert_hf_to_gguf.py, conversion/ and gguf-py/ (pip install gguf-py, gguf 0.19.0) and name the script in
# ALFRED_BRAIN_CONVERTER.
MODEL_NAME = "alfred-brain"
EPOCHS = 2
MAX_TOKENS = 1024


def write_status(path, **values):
    Path(path).write_text(json.dumps({"at": datetime.now(timezone.utc).isoformat(), **values}, indent=1), encoding="utf-8")


def train(chats, base, out_dir, *, epochs=EPOCHS):  # pragma: no cover - needs the separate PyTorch stack
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
    for _ in range(epochs):
        for chat in chats:
            text = tokenizer.apply_chat_template(chat["messages"], tokenize=False)
            batch = tokenizer(text, return_tensors="pt", truncation=True, max_length=MAX_TOKENS)
            loss = model(**batch, labels=batch["input_ids"]).loss
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            losses.append(float(loss))
    merged = model.merge_and_unload().to(torch.float16)  # half the size on disk; Ollama keeps f16
    merged.save_pretrained(out_dir, safe_serialization=True)
    tokenizer.save_pretrained(out_dir)
    return round(sum(losses[-len(chats):]) / max(1, len(chats)), 4)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("--chats", "--base", "--out", "--status", "--ollama", "--converter"):
        parser.add_argument(name, required=True)
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    args = parser.parse_args(argv)
    chats_file, out = Path(args.chats), Path(args.out)
    merged, gguf = out / "merged", out / f"{args.model}.gguf"
    try:
        chats = [json.loads(line) for line in chats_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        write_status(args.status, state="training", examples=len(chats))
        loss = train(chats, args.base, merged, epochs=args.epochs)
        # Ollama 0.40.16 refused Qwen2 safetensors ("unsupported MLX architecture"); llama.cpp's GGUF imports (2026-11-20).
        subprocess.run([sys.executable, args.converter, str(merged), "--outtype", "f16", "--outfile", str(gguf)],
                       check=True, capture_output=True, encoding="utf-8", errors="replace", timeout=3600)
        shutil.rmtree(merged, ignore_errors=True)  # the GGUF replaces it; about 3 GB
        (out / "Modelfile").write_text(f"FROM {gguf.resolve()}\n", encoding="utf-8")
        created = subprocess.run([args.ollama, "create", args.model, "-f", str(out / "Modelfile")],
                                 capture_output=True, encoding="utf-8", errors="replace", timeout=3600)
        write_status(args.status, state="ready" if created.returncode == 0 else "ollama_import_failed", examples=len(chats),
                     loss=loss, model=args.model if created.returncode == 0 else None, detail=(created.stderr or "")[-300:])
        return 0 if created.returncode == 0 else 4
    except Exception as exc:
        write_status(args.status, state="failed", detail=type(exc).__name__)
        return 5
    finally:
        chats_file.unlink(missing_ok=True)  # the private examples stay only in the encrypted vault


if __name__ == "__main__":
    sys.exit(main())
