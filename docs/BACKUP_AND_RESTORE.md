# Backup and restore

Keep application data and its related files in one dated recovery set. The
Docker Compose runtime uses PostgreSQL and named volumes; native development
may use SQLite and directories in the checkout. Select the procedure for the
runtime that actually contains your data.

## Docker Compose recovery set

Run the helper from the repository root using Python 3.12 or later. The examples
use the project's Windows virtual environment. Docker Desktop, Compose, the
local environment file, a running PostgreSQL service, and the built web image
are required.

```powershell
.\.venv\Scripts\python.exe scripts/local_stack_ops.py backup
```

This command pauses running web, worker, and beat services while it captures:

| File | Contents |
| --- | --- |
| `database.dump` | PostgreSQL custom-format dump of the configured application database |
| `files.tar.gz` | The `media`, `ml_models`, and `artifacts` volumes mounted by the web service |
| `manifest.json` | Backup version, table row counts, file sizes and SHA-256 hashes, archive hashes, completion and service restart status |

Backups default to `artifacts/backups/<UTC timestamp>-<random suffix>/` on the
host. To place them on another local disk:

```powershell
.\.venv\Scripts\python.exe scripts/local_stack_ops.py backup --output-root 'E:\ALFRED-backups'
```

The helper attempts to restart only services that were running at the start,
including after a failed dump or stop. Allow a maintenance window: requests and
scheduled processing are unavailable while those services are stopped. External
writers using the same database or volumes must also be stopped separately.
Avoid overlapping backup runs or changing services during the operation.

Accept a backup only when the command succeeds and `manifest.json` has
`complete: true`. Confirm `writers_resumed: true` and check service health
afterward. A successful dump can remain usable even if restarting a service
fails; the command still fails and the manifest records that restart failure.
Incomplete backup folders are retained for diagnosis and cannot pass a restore
check.

### Test the backup without replacing live data

Use the exact directory printed by the backup command:

```powershell
.\.venv\Scripts\python.exe scripts/local_stack_ops.py restore-check 'E:\ALFRED-backups\<backup-directory>'
```

The check validates the manifest and archive checksums, rejects unsafe or
duplicate archive paths, and extracts files into a temporary host directory
before connecting to Docker. It restores PostgreSQL into a generated database
named `alfred_restore_check_<random id>` on the existing server, compares every
public table's row count, and drops that temporary database. Existing application
tables and mounted files are not restore targets.

`restore_check.json` in the backup folder must report both `accepted: true` and
`cleanup_complete: true`. If cleanup fails, acceptance remains false and the
temporary database name is recorded for investigation. The server needs enough
free disk space for a second database, and the host needs space for extracted
files. Treat these backups as trusted local recovery material; checksums detect
accidental changes, not a maliciously rewritten backup and manifest.

For a nondefault environment file, place the option before the command:

```powershell
.\.venv\Scripts\python.exe scripts/local_stack_ops.py --env-file 'config\recovery.local.env' restore-check 'E:\ALFRED-backups\<backup-directory>'
```

The helper applies that environment file to Compose interpolation and the app
containers. Keep all real environment files untracked.

### Recovery scope and limitations

- Keep a protected copy on a different disk. A backup under the checkout does
  not protect against loss of that disk.
- Store the runtime environment/secrets separately in a protected local backup;
  the helper intentionally excludes them. Also retain the matching code version
  and image/build inputs needed to recreate the application.
- Redis queues, task results, and cache state are excluded. Review pending jobs
  and retry/rebuild work as appropriate after an actual recovery. Static files
  can be regenerated with `collectstatic`.
- Uploads already deleted by the configured retention policy cannot be recovered
  from a later backup.
- The isolated check verifies restoration, row counts, and file integrity. It
  does not boot a second application, compare every database value, or prove
  recovery after a host restart.
- There is no automated backup scheduler or command that overwrites the live
  database. A full recovery requires a planned maintenance procedure: retain the
  old database and volumes, restore the dump and all three file roots into an
  empty replacement stack, validate the application there, then resume work.
  Keep the old stack stopped while the replacement is active.

Do not pass a binary dump or tar archive through PowerShell text redirection or
`Get-Content`. The helper uses binary subprocess streams to preserve the bytes.

## Native SQLite recovery set

For a native runtime configured to use SQLite, stop Django and all worker/beat
processes before copying anything. Back up these together:

| Path | Contents |
| --- | --- |
| `db.sqlite3` and any remaining `db.sqlite3-wal` / `db.sqlite3-shm` sidecars | Application data and any outstanding SQLite write-ahead log state |
| `media/` | Retained documents, photos, reports, and resumes |
| `ml_models/` | Trained models and registry state |
| `artifacts/` | Runtime evidence, training outputs, and scheduler state |

Keep the dated backup outside those source directories to avoid copying a
backup into itself. Securely retain the native runtime's local environment file
separately. These file-copy instructions do not apply to a native runtime that
has been configured to use PostgreSQL.

To restore, keep all application processes stopped, move the current database,
its sidecars, and the three directories into a separate recovery folder, then
copy the entire saved set back. Do not merge an old file tree into a newer one
or leave the newer database's sidecars alongside the restored database.

Run checks with the restored application's matching code version:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate --check
```

If a code upgrade requires migrations, preserve the restored copy before
applying them. Start Django and validate the application before starting workers
and beat.

## Application validation after recovery

Check `/health/live/`, login, the document center, expenses, credit reports,
linked files that were retained, and project details for a superuser. Confirm
that relevant schedules and background jobs resume. Record the date, backup
directory, command outcomes, and any missing retained files before treating a
full recovery drill as complete.
