"""
Optional local overrides for ALFRED development.

This file is intentionally safe-by-default and should not contain production
secrets in source control. Use environment variables for real credentials.

Common local overrides:

    DEBUG = True
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

    DATABASES["default"]["NAME"] = BASE_DIR / "db.sqlite3"
    MEDIA_ROOT = BASE_DIR / "media"

Backup note:
For the default SQLite setup, the minimum recoverable local backup set is:
1. db.sqlite3
2. media/
3. ml_models/

See docs/BACKUP_AND_RESTORE.md for the operational backup and recovery steps.
"""
