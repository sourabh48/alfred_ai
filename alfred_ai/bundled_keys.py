"""Free service keys built into the installer (owner decision 2026-11-19).

Only keys that can never charge anyone are allowed (sign-in clients, FRED, Alpha Vantage, Finnhub, Reddit, OpenRouteService).
The builder's own config/local.env supplies them at build time; they are never committed. A person's own saved key
always wins, and Settings shows "Built in" instead of any part of a built-in key.

shortcut: the file is encrypted with a key that ships beside it, so it keeps the keys out of plain text and out of
casual search, not away from someone who unpacks the installer and reads this code; a free key that leaks can only be
rate-limited or revoked, never billed. Upgrade to a sign-in relay server if a key ever needs to stay truly secret.
"""
import base64
import hashlib
import json
import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

FREE = ("ALFRED_GOOGLE_CLIENT_ID", "ALFRED_GOOGLE_CLIENT_SECRET", "ALFRED_GITHUB_CLIENT_ID", "ALFRED_GITHUB_CLIENT_SECRET",
        "ALFRED_MICROSOFT_CLIENT_ID", "ALFRED_MICROSOFT_CLIENT_SECRET", "ALFRED_FRED_API_KEY", "ALFRED_ALPHA_VANTAGE_API_KEY",
        "ALFRED_REDDIT_CLIENT_ID", "ALFRED_REDDIT_CLIENT_SECRET", "TRAVEL_ORS_API_KEY", "ALFRED_FINNHUB_API_KEY")
FILE_NAME = "alfred_keys.bin"
_built_in = {}


def _cipher(salt: bytes) -> Fernet:
    return Fernet(base64.urlsafe_b64encode(hashlib.pbkdf2_hmac("sha256", b"ALFRED built-in free keys", salt, 200_000)))


def read_env_file(path: Path) -> dict:
    """NAME=value lines of a local.env file, quotes removed; only this file, never the builder's environment."""
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        name, sep, value = line.strip().removeprefix("export ").partition("=")
        if sep and name.strip().isidentifier():
            values[name.strip()] = value.strip().strip("'\"")
    return values


def seal(values: dict) -> bytes:
    """Encrypt the free keys among values; anything not in FREE is dropped, so a paid key can never be bundled."""
    chosen = {name: str(values[name]).strip() for name in FREE if str(values.get(name) or "").strip()}
    salt = os.urandom(16)
    return salt + _cipher(salt).encrypt(json.dumps(chosen).encode("utf-8"))


def unseal(blob: bytes) -> dict:
    try:
        data = json.loads(_cipher(blob[:16]).decrypt(blob[16:]))
    except (InvalidToken, ValueError):
        return {}
    return {name: value for name, value in data.items() if name in FREE and isinstance(value, str) and value}


def load(path: Path | None = None) -> None:
    """Fill in each built-in key the environment does not already have (call after reading config/local.env)."""
    if path is None and getattr(sys, "_MEIPASS", None):
        path = Path(sys._MEIPASS) / FILE_NAME  # only an installed copy carries the file
    if path and path.is_file():
        _built_in.clear()
        _built_in.update(unseal(path.read_bytes()))
    for name, value in _built_in.items():
        os.environ.setdefault(name, value)


def is_built_in(name: str) -> bool:
    return bool(_built_in.get(name)) and os.environ.get(name) == _built_in[name]


def restore(name: str) -> None:
    """After a person removes their own key, fall back to the built-in one."""
    if _built_in.get(name):
        os.environ[name] = _built_in[name]
