# Native runtime and recovery proof

This is the historical 16 September development-server proof. The subsequently
implemented Waitress/Huey runtime, installer and verification commands are in
[Native Windows](NATIVE_WINDOWS.md). Docker is optional for that runtime.

Run date: 16 September 2026. Runtime: Windows, project Python 3.12.2,
Django, SQLite, and process-local memory cache.

## Result

The native application passed runtime checks, a backup and isolated restore,
and persistence after a Django process restart. Full hosted-stack verification
is still blocked: Docker Desktop/CLI, WSL, PostgreSQL and Redis are absent on
this machine. No PostgreSQL, Redis, Celery worker or beat operation is claimed.

`scripts/local_stack_ops.py verify` exited with status 1 and recorded the missing
Docker prerequisite in `artifacts/ops/local_stack_verification.json`.

## Native runtime checks

- `manage.py check` passed with no issues.
- `manage.py migrate --check` passed; all migrations are applied.
- `manage.py makemigrations --check --dry-run` found no model drift.
- The restarted server returned HTTP 200 for `/health/live/`, `/health/ready/`,
  `/login/`, and `/static/js/app.js?v=2.8`.
- The app is available at `http://127.0.0.1:8000/`. Startup training was disabled
  for the restarted verification process to avoid initiating a training cycle.

Evidence: `artifacts/ops/native_runtime_verification.json`.

## Backup and isolated restore

Backup directory on this host:

```text
F:\ALFRED-backups\20260916T173656Z-native-1a8bf13e
```

The native Django processes were stopped while capturing a SQLite backup plus
`media/`, `ml_models/`, and `artifacts/`. The source database and file hashes
remained stable during capture. The server was then restarted. The backup
contains `database.sqlite3`, `files.tar.gz`, and `manifest.json`; runtime secrets
and rebuildable static files are excluded.

| Check | Result |
| --- | --- |
| Database integrity and foreign keys | Passed |
| Database schema and all table contents | All 55 tables matched the source snapshot |
| Restored files | All 8,188 file sizes and SHA-256 hashes matched |
| Restored accounts | 13 accounts retained; an existing account profile and main pages loaded |
| File references | All three database-referenced uploads were present |
| Password login/logout | Passed using a temporary user in the restored copy |
| Expense persistence | Created and read an expense of 275.50; retained after reconnecting to the restored database |
| Latest Settings changes | Data removal button in Settings; no old navbar button or Manual Dependents section |
| Restored HTTP application | Liveness, readiness and login returned HTTP 200 |
| Temporary restore cleanup | Passed; temporary database, files and test user removed |

The restored app used a generated temporary directory under `F:\ALFRED-backups`.
The live database and live file roots were never restoration targets. The
temporary user and expense were created only in the restored database.

Evidence: `restore_check.json` in the backup directory and
`artifacts/ops/native_restore_verification.json`. The one-off drill code is
retained in `artifacts/ops/native_recovery_drill.py` and included in the backup.

## Restart persistence and limits

After restarting Django, all 54 non-session tables matched the backup and all
8,084 media/model files retained their hashes. Only session contents changed
as the live browser resumed dashboard polling and session heartbeat requests.
Evidence: `artifacts/ops/native_restart_persistence.json`.

This proves native process restart and isolated SQLite recovery. It does not
prove a host reboot, second-device LAN access, PostgreSQL recovery, Redis
operation, scheduled jobs, or recovery from disk failure. The backup is on the
same drive as the application. Secrets and matching application code still
need separate protected retention for a complete recovery set.
