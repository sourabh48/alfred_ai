"""The backup key and its passphrase-locked copy in Google Drive or Cloudflare R2 (owner decisions 2026-11-19 and 2026-11-26,
SYNC-09 and RUNTIME-08).

ALFRED's encrypted backups (scripts/cloud_backup.py, to Cloudflare R2) open only with the backup key, a plain Fernet key
file that never leaves this PC. If the PC is lost, the key must come from somewhere else: ALFRED locks a copy with a
passphrase the person remembers (scrypt, then Fernet) and keeps only that locked copy in the hidden app folder of their
Google Drive (drive.appdata: ALFRED sees only its own file, the person's other Drive files stay out of reach). On a new
PC: sign in to Google, fetch the locked copy, type the passphrase. Google alone cannot open it, and the passphrase is
never stored or sent.

The owner may keep the locked copy in their Cloudflare R2 bucket instead (2026-11-26, "use auto backup... to cloudflare"),
next to the encrypted backups. Then the passphrase alone protects the key (scrypt makes each guess slow), so it must be long.
"""
from __future__ import annotations

import base64
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from django.conf import settings

from alfred_ai.services import public_http
from alfred_ai.services.public_http import PublicHTTPError

SCOPE = "https://www.googleapis.com/auth/drive.appdata"
NAME = "alfred-backup-key.json"
FILES, UPLOAD = "https://www.googleapis.com/drive/v3/files", "https://www.googleapis.com/upload/drive/v3/files"
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 17, 8, 1  # about 128 MB and a second per try, so guessing a passphrase is slow
MIN_PASSPHRASE = 12
R2_NAME = "alfred-backup-key-v1/sealed.json"


class BackupKeyError(Exception):
    """A message safe to show the person."""


def folder() -> Path:
    return Path(os.environ.get("ALFRED_DATA_DIR") or settings.BASE_DIR) / "artifacts" / "backup-key"


def key_path() -> Path:
    """The key file to pass to scripts/cloud_backup.py --key-file."""
    return folder() / "backup.key"


def _sealed_path() -> Path:
    return folder() / "sealed.json"


def _status_path() -> Path:
    return folder() / "status.json"


def _write(path: Path, data: bytes) -> None:
    from alfred_private_storage import private_directory
    private_directory(path.parent)
    temporary = path.with_suffix(".saving")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def _derive(passphrase: str, salt: bytes, n: int, r: int, p: int) -> Fernet:
    raw = Scrypt(salt=salt, length=32, n=n, r=r, p=p).derive(passphrase.encode("utf-8"))
    return Fernet(base64.urlsafe_b64encode(raw))


def seal(key: bytes, passphrase: str) -> dict:
    salt = secrets.token_bytes(16)
    token = _derive(passphrase, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P).encrypt(key)
    return {"alfred_backup_key": 1, "kdf": "scrypt", "n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P,
            "salt": base64.b64encode(salt).decode(), "token": token.decode()}


def _valid(doc) -> bool:
    return (isinstance(doc, dict) and doc.get("alfred_backup_key") == 1 and doc.get("kdf") == "scrypt"
            and all(type(doc.get(k)) is int for k in ("n", "r", "p")) and 2 ** 10 <= doc["n"] <= 2 ** 20
            and 1 <= doc["r"] <= 16 and 1 <= doc["p"] <= 4 and isinstance(doc.get("salt"), str) and isinstance(doc.get("token"), str)
            and len(doc["token"]) < 4096)


def unseal(doc: dict, passphrase: str) -> bytes:
    if not _valid(doc):
        raise BackupKeyError("That is not an ALFRED backup key copy.")
    try:
        key = _derive(passphrase, base64.b64decode(doc["salt"]), doc["n"], doc["r"], doc["p"]).decrypt(doc["token"].encode())
        Fernet(key)  # it really is a backup key
    except (InvalidToken, ValueError):
        raise BackupKeyError("That passphrase does not open the backup key.") from None
    return key


def _saved() -> dict:
    try:
        saved = json.loads(_status_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    return saved if isinstance(saved, dict) else {}


def _remember(**fields) -> None:
    _write(_status_path(), json.dumps({**_saved(), **fields}).encode())


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def status() -> dict:
    saved = _saved()
    return {"key": key_path().is_file(), "key_file": str(key_path()), "locked_copy": _sealed_path().is_file(),
            "in_drive": bool(saved.get("drive_file_id")), "saved_on": saved.get("saved_on", ""), "google": saved.get("google", ""),
            "in_r2": bool(saved.get("r2_saved_on")), "r2_saved_on": saved.get("r2_saved_on", ""), "auto": _auto()}


def _auto() -> dict:
    """What alfred_ai/services/auto_backup.py last did, for Settings."""
    try:
        saved = json.loads((folder() / "auto-backup.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: saved.get(k) for k in ("last_ok", "last_try", "error", "kept")} if isinstance(saved, dict) else {}


def make(passphrase: str, repeat: str) -> dict:
    """Make the backup key if there is none (an existing key is never replaced) and lock a copy with the passphrase."""
    if not isinstance(passphrase, str) or len(passphrase) < MIN_PASSPHRASE:
        raise BackupKeyError(f"Use a passphrase of at least {MIN_PASSPHRASE} characters, for example four unrelated words.")
    if passphrase != repeat:
        raise BackupKeyError("The two passphrases differ.")
    if key_path().is_file():
        key = key_path().read_bytes().strip()
        try:
            Fernet(key)
        except ValueError:
            raise BackupKeyError("The backup key file on this PC is damaged; it was left as it is.") from None
    else:
        key = Fernet.generate_key()
        _write(key_path(), key)
    _write(_sealed_path(), json.dumps(seal(key, passphrase)).encode())
    return status()


def _call(method, url, token, **kwargs):
    try:
        return public_http.request(method, url, headers={"Authorization": f"Bearer {token}", **kwargs.pop("headers", {})}, **kwargs)
    except PublicHTTPError as exc:
        raise BackupKeyError("Google Drive refused ALFRED's access. Turn on the Google Drive API in your Google project and try again."
                             if exc.code in ("authorization_failed", "api_error") else "Could not reach Google Drive. Try again later.") from None


def _find(token) -> str:
    listing = _call("GET", FILES, token, params={"spaces": "appDataFolder", "q": f"name = '{NAME}' and trashed = false",
                                                 "fields": "files(id)", "pageSize": 10}).json()
    files = listing.get("files") if isinstance(listing, dict) else None
    return str(files[0]["id"]) if files and isinstance(files[0], dict) and files[0].get("id") else ""


def upload(token: str, google_email: str) -> dict:
    """Put the locked copy in the person's Drive app folder, then read it back to prove it arrived whole."""
    try:
        body = _sealed_path().read_bytes()
    except OSError:
        raise BackupKeyError("Make the locked copy first: choose a passphrase above.") from None
    old = _find(token)
    boundary = "alfred" + secrets.token_hex(8)
    meta = json.dumps({"name": NAME, "parents": ["appDataFolder"], "mimeType": "application/json"})
    multipart = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta}\r\n"
                 f"--{boundary}\r\nContent-Type: application/json\r\n\r\n").encode() + body + f"\r\n--{boundary}--\r\n".encode()
    created = _call("POST", UPLOAD, token, params={"uploadType": "multipart", "fields": "id"}, data=multipart,
                    headers={"Content-Type": f"multipart/related; boundary={boundary}"}).json()
    found = str(created.get("id") or "") if isinstance(created, dict) else ""
    back = _call("GET", f"{FILES}/{found}", token, params={"alt": "media"}, content_types=("application/json", "")).content if found else b""
    if back != body:
        raise BackupKeyError("Google Drive did not keep the locked copy intact. Try again.")
    if old and old != found:  # the new copy is checked first, so Drive never holds none
        _call("DELETE", f"{FILES}/{old}", token, accepted_statuses=(204,), content_types=("",))
    _remember(drive_file_id=found, google=google_email, saved_on=_today())
    return status()


def fetch(token: str, google_email: str) -> dict:
    """On a new PC: bring the locked copy down from Drive; the passphrase opens it in restore()."""
    found = _find(token)
    if not found:
        raise BackupKeyError(f"No ALFRED backup key copy is in the Google Drive of {google_email}. Sign in with the Google account you used to save it.")
    data = _call("GET", f"{FILES}/{found}", token, params={"alt": "media"}, content_types=("application/json", "")).content
    try:
        doc = json.loads(data)
    except ValueError:
        doc = None
    if not _valid(doc):
        raise BackupKeyError("The copy in Google Drive is not an ALFRED backup key copy.")
    _write(_sealed_path(), json.dumps(doc).encode())
    _remember(drive_file_id=found, google=google_email, saved_on="")
    return status()


def restore(passphrase: str) -> dict:
    """Open the fetched locked copy with the passphrase and write the backup key; a different existing key is never replaced."""
    try:
        doc = json.loads(_sealed_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise BackupKeyError("Fetch the locked copy from Google Drive or Cloudflare R2 first.") from None
    key = unseal(doc, passphrase if isinstance(passphrase, str) else "")
    if key_path().is_file():
        if key_path().read_bytes().strip() != key:
            raise BackupKeyError("This PC already has a different backup key; it was left as it is.")
    else:
        _write(key_path(), key)
    return status()


def _r2(client, method, **kwargs):
    """One request for the locked copy in the owner's R2 bucket; the bucket is the one cloud backups use."""
    from apps.ml_engine.services.memory_sync import SyncUnavailable
    from scripts import cloud_backup
    try:
        client = client or cloud_backup.bucket()
        return client._send(method, R2_NAME, deadline=cloud_backup.seconds(), maximum=64 * 1024, **kwargs)
    except cloud_backup.GateError:
        raise BackupKeyError("Cloudflare R2 is not set up yet. Add your bucket's four ALFRED_MEMORY_R2_ values and "
                             "ALFRED_CLOUD_BACKUP_AUTHORIZED=true to config/local.env, then restart ALFRED.") from None
    except SyncUnavailable:
        raise BackupKeyError("Could not reach Cloudflare R2. Try again later.") from None


def save_to_r2(client=None) -> dict:
    """Put the locked copy in the R2 bucket, then read it back to prove it arrived whole."""
    try:
        body = _sealed_path().read_bytes()
    except OSError:
        raise BackupKeyError("Make the locked copy first: choose a passphrase above.") from None
    _r2(client, "PUT", data=body)
    if _r2(client, "GET").content != body:
        raise BackupKeyError("Cloudflare R2 did not keep the locked copy intact. Try again.")
    _remember(r2_saved_on=_today())
    return status()


def fetch_from_r2(client=None) -> dict:
    """On a new PC with the same R2 settings: bring the locked copy down; the passphrase opens it in restore()."""
    response = _r2(client, "GET", statuses=(200, 404))
    try:
        doc = json.loads(response.content) if response.status == 200 else None
    except ValueError:
        doc = None
    if response.status == 404:
        raise BackupKeyError("No ALFRED backup key copy is in this Cloudflare R2 bucket.")
    if not _valid(doc):
        raise BackupKeyError("The copy in Cloudflare R2 is not an ALFRED backup key copy.")
    _write(_sealed_path(), json.dumps(doc).encode())
    _remember(r2_saved_on=_today())  # the copy is there
    return status()
