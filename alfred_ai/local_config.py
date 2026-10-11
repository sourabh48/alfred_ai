"""Read local runtime configuration without overriding process environment."""
import hashlib
import json
import os
from pathlib import Path
import secrets

import environ

# Fingerprint only: an exposed historical development key remains unsafe.
PUBLIC_DEFAULT_SECRET_SHA256 = "65056bf67be3ed0122fdbdf34850a71d74805949e7caea67fae0fe63462cb086"


def load_local_environment(data_dir):
    root = Path(data_dir)
    # The documented local file takes precedence over legacy .env values.
    # Explicit process variables still win; never read another runtime's files.
    for path in (root / "config" / "local.env", root / ".env"):
        if path.is_file():
            environ.Env.read_env(path, overwrite=False)


def native_secret_file(data_dir):
    """Persist a fresh signing key once; require a retained database's old key."""
    root = Path(data_dir)
    config = root / "config"
    config.mkdir(parents=True, exist_ok=True)
    path = config / "native.env"
    if not path.exists():
        previous = os.environ.get("DJANGO_SECRET_KEY")
        retained = (root / "db.sqlite3").exists()
        if retained and not previous:
            raise RuntimeError("Restore config/native.env or explicitly configure the retained database's previous DJANGO_SECRET_KEY.")
        try:
            with path.open("x", encoding="utf-8") as output:
                output.write(f"DJANGO_SECRET_KEY={secrets.token_urlsafe(64)}\n")
                if retained:
                    output.write(f"DJANGO_SECRET_KEY_FALLBACKS={json.dumps([previous])}\n")
        except FileExistsError:
            pass
    return path


def is_public_default_secret(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest() == PUBLIC_DEFAULT_SECRET_SHA256
