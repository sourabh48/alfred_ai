# Backup And Restore

## Scope

This document defines the minimum recovery set for ALFRED as it exists in this repository today.

The current local/default runtime uses:

- SQLite for application data
- `media/` for uploaded documents and images
- `ml_models/` for trained model artifacts and registry state

## Minimum Backup Set

Back up these paths together:

| Item | Why it matters |
| --- | --- |
| `db.sqlite3` | Primary application data: users, expenses, loans, document metadata, training state, evidence cache |
| `media/` | Uploaded source documents, trip photos, vehicle files, resumes, bureau reports |
| `ml_models/` | Persisted model artifacts, registry data, and training outputs |

## Recommended Local Backup Procedure

1. Stop the Django server and any Celery worker/beat process to avoid partial writes.
2. Copy `db.sqlite3` to a dated backup location.
3. Copy `media/` to the same dated backup location.
4. Copy `ml_models/` to the same dated backup location.
5. Keep the three copies together under one timestamped folder.

Example layout:

```text
backups/
  2026-04-01_2030/
    db.sqlite3
    media/
    ml_models/
```

## Restore Procedure

1. Stop the Django server and Celery processes.
2. Move the current `db.sqlite3`, `media/`, and `ml_models/` out of the way if they exist.
3. Restore the backed-up `db.sqlite3` to the project root.
4. Restore the backed-up `media/` directory.
5. Restore the backed-up `ml_models/` directory.
6. Run:

```bash
python manage.py check
python manage.py migrate
```

7. Start the Django server.
8. If Celery is used, restart worker and beat after the app passes checks.

## Validation After Restore

Validate these paths before treating the restore as complete:

1. `/health/`
2. login page
3. document center
4. expenses dashboard
5. credit score page
6. project details for a superuser

## Current Limitations

- No automated snapshot scheduler is evidenced in the repo.
- No managed cloud backup target is evidenced in the repo.
- SQLite file-copy backups are safe only when the app and workers are stopped.
- Redis-backed cache state is not part of the default local backup story because the default cache is local-memory.
