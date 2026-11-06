"""One-time, owner-approved download of the offline speech models (AI-18).

Files are pinned to a Hugging Face revision and checked by size and hash before
they are kept. After this runs, speech works offline; nothing here runs at startup.
"""
from __future__ import annotations

import hashlib
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = Path(os.environ.get("ALFRED_SPEECH_MODEL_DIR") or ROOT / "ml_models" / "speech")

WHISPER = ("openai/whisper-base", "e37978b90ca9030d5170a5c07aadb050351a65bb", "whisper-base")
PIPER = ("rhasspy/piper-voices", "e7229f7d33a10e145e109b886d661984201ac3c4", "piper")
# (source, path in repository, size, sha256 for large files or git blob sha1 for small ones)
FILES = [
    (WHISPER, "added_tokens.json", 34604, "e3d256c988462aa153dcabe2aa38b8e9b436c06f"),
    (WHISPER, "config.json", 1983, "708cca09e7e8a9364e444efe8b4f9c2691fc5f51"),
    (WHISPER, "generation_config.json", 3807, "38eda87a0b22fdb85af5dfa14cf065147337137a"),
    (WHISPER, "merges.txt", 493869, "6038932a2a1f09a66991b1c2adae0d14066fa29e"),
    (WHISPER, "model.safetensors", 290403936, "07cadb9f25677c8d50df603e66a98fbd842cce45047139baeb16e6219a1e807b"),
    (WHISPER, "normalizer.json", 52666, "dd6ae819ad738ac1a546e9f9282ef325c33b9ea0"),
    (WHISPER, "preprocessor_config.json", 184990, "c2048dfa9fd94a052e62e908d2c4dfb18534b4d2"),
    (WHISPER, "special_tokens_map.json", 2194, "bf69932dca4b3719b59fdd8f6cc1978109509f6c"),
    (WHISPER, "tokenizer.json", 2480466, "1e95340ff836fad1b5932e800fb7b8c5e6d78a74"),
    (WHISPER, "tokenizer_config.json", 282683, "d13b786c04765fb1a06492b53587752cd67665ea"),
    (WHISPER, "vocab.json", 835550, "d7016e21da8776c8a9d577d0f559600f09a240eb"),
    (PIPER, "en/en_GB/vctk/medium/en_GB-vctk-medium.onnx", 76952753,
     "4e9fc85ab9009385319fc6bae7f55577f8a2d7ee77fd9159a5500eb6531f41e6"),
    (PIPER, "en/en_GB/vctk/medium/en_GB-vctk-medium.onnx.json", 6637, "8b9509fc9e58d214f0092a662441b57de1427225"),
]


def digest(data: bytes, expected: str) -> str:
    if len(expected) == 64:
        return hashlib.sha256(data).hexdigest()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def fetch(source, path: str, size: int, expected: str) -> str:
    repo, revision, folder = source
    out = TARGET / folder / Path(path).name
    if out.exists() and out.stat().st_size == size and digest(out.read_bytes(), expected) == expected:
        return f"kept {out.name}"
    url = f"https://huggingface.co/{repo}/resolve/{revision}/{path}"
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read()
    if len(data) != size or digest(data, expected) != expected:
        raise SystemExit(f"{path}: size or hash mismatch; nothing kept")
    out.parent.mkdir(parents=True, exist_ok=True)
    part = out.with_suffix(out.suffix + ".part")
    part.write_bytes(data)
    part.replace(out)
    return f"downloaded {out.name}"


def main() -> int:
    for row in FILES:
        print(fetch(*row))
    print(f"Speech models ready in {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
