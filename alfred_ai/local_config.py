"""Read local runtime configuration without overriding process environment."""
from pathlib import Path

import environ


def load_local_environment(data_dir):
    root = Path(data_dir)
    # The documented local file takes precedence over legacy .env values.
    # Explicit process variables still win; never read another runtime's files.
    for path in (root / "config" / "local.env", root / ".env"):
        if path.is_file():
            environ.Env.read_env(path, overwrite=False)
