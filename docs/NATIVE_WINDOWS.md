# ALFRED on Windows

See the [dated verification report](NATIVE_WINDOWS_VERIFICATION.md) for test
results, executable proof, backup location and remaining validation limits.

The native application uses **Waitress + Huey + SQLite**. Docker, WSL, Redis
and a Celery service are unnecessary for this runtime. The interface opens in
your browser; two hidden processes handle web requests and background jobs.

## Start and stop

For the existing checkout, double-click **Start ALFRED.cmd** in `F:\ALFRED`.
It uses the existing account database, uploads and models. First startup may
take a minute while it applies migrations and prepares static assets.
Double-click **Stop ALFRED.cmd** to stop after current work finishes.

For a separate installation, run `dist\ALFRED-Setup.exe` and use the ALFRED
desktop shortcut. The installer includes Python and the application libraries.
It creates a separate data folder at `%LOCALAPPDATA%\ALFRED`; existing checkout
data is not silently copied into a new installation.

The default address is `http://127.0.0.1:8000/`. If another program occupies
that port, the launcher chooses the next available port and opens it. Starting
ALFRED again opens the same running instance. Closing the browser keeps jobs
running; Stop ALFRED closes the server and worker.

Command-line controls:

```powershell
.\.venv\Scripts\python.exe alfred_native.py status
.\.venv\Scripts\python.exe alfred_native.py start --no-browser
.\.venv\Scripts\python.exe alfred_native.py stop
# Installed/portable executable, explicitly using the existing checkout data:
.\dist\ALFRED\ALFRED.exe start --data-dir F:\ALFRED
```

The native launcher binds to this computer only. LAN service and Windows
auto-start are separate configurations, not enabled by this installer.

## Data and secrets

All writable state stays in the selected data folder:

| Path | Content |
| --- | --- |
| `db.sqlite3` | Accounts and application records |
| `media` | Retained private uploads |
| `ml_models` | Locally trained artifacts |
| `config/native.env` | Automatically generated local secret; keep private |
| `config/alfred_ui.json` | Optional UI overrides |
| `artifacts/native/jobs.sqlite3` | Persistent background queue and results |
| `artifacts/native/cache` | Shared local cache |
| `artifacts/native/server.log`, `worker.log` | Startup and background diagnostics |

First adoption of an existing database records the previous Django signing key
as a fallback. Existing encrypted email tokens remain readable and new tokens
use the new key. Keep `config/native.env` with backups. An explicit
`--data-dir` wins over `ALFRED_DATA_DIR`; otherwise the source launcher uses its
repository and the executable uses `%LOCALAPPDATA%\ALFRED`.

The installer contains code, libraries, OCR engine assets and static files.
It excludes your database, uploads, learned models, local settings and secrets.
Uninstalling the application retains the separate data folder.

## Background processing

One Huey consumer runs two thread workers and a scheduler. The queue uses its
own SQLite file; the shared cache also uses SQLite. Startup waits for a real
queued probe to complete before opening the browser.

| Job | Schedule while running (UTC) |
| --- | --- |
| Scheduler heartbeat | Every minute |
| Low-confidence statement retry | Every 20 minutes, up to 3 documents |
| Verified evidence refresh | Every 6 hours, up to 75 records |
| Evidence cleanup | Daily at 02:15 |
| Eligible model training | Daily at 03:00, subject to existing consent/data gates |

Shutdown waits for in-flight work; queued jobs survive restart. The native
SQLite adapter now records a claim before removing a queued job and acknowledges
it only after completion. Queue/schedule transfers are atomic and SQLite uses
full synchronous writes. An exclusive worker lock prevents concurrent recovery.
After an abrupt stop, repeatable maintenance jobs are replayed up to three times.
Interrupted imports, training and unknown jobs retain their payload for review;
their application changes cannot share the queue transaction, so automatic
replay could repeat partially completed changes. This is not exactly-once
execution or a hardware power-loss certification.

```powershell
.\ALFRED.exe jobs
.\ALFRED.exe retry-job --job-id <ID-from-jobs>
```

Check partial changes before explicitly retrying a retained job. Project Details
flags jobs awaiting review. Job outcomes and timing are retained for 30 days in
`artifacts/native/jobs.sqlite3`; document contents and task arguments are not
copied into the operational history. Unfinished claims are never aged out.

Schedules do not run while the application/computer is off. External source
refreshes still need internet access. Charts and controls use bundled assets;
optional Google fonts fall back to system fonts offline.

## Backup and restore

1. Stop ALFRED and wait for shutdown to finish.
2. Copy `db.sqlite3`, `media`, `ml_models`, `config`, and
   `artifacts/native/jobs.sqlite3` to a private backup folder. Include any
   `db.sqlite3-wal`/`db.sqlite3-shm` sidecars still present, or use SQLite's
   backup API as in the verification script. Keep the folder together.
3. Restore into a **new empty data folder** and start with `--data-dir` pointing
   there. Sign in, check totals, and download a retained document before adopting
   it. Do not overwrite a running data folder.

The verification script demonstrates a SQLite backup-API snapshot, restored
login/session, financial totals and private file download over real HTTP.
It uses synthetic records in disposable folders, never the live account.

## Reproduce verification and build

```powershell
.\.venv\Scripts\python.exe scripts/verify_native_runtime.py --browser
.\.venv\Scripts\python.exe scripts/verify_native_runtime.py --browser --extended
.\.venv\Scripts\python.exe manage.py test --noinput
.\.venv\Scripts\python.exe -m PyInstaller packaging/ALFRED.spec --noconfirm
.\.venv\Scripts\python.exe scripts/verify_native_runtime.py --executable dist/ALFRED/ALFRED.exe --browser
& 'F:\ALFRED-tools\InnoSetup\ISCC.exe' packaging/ALFRED.iss
```

Build tools are listed in `requirements-build.txt`. Inno Setup 6.7.3 builds the
installer. `artifacts/ops/native_huey_verification.json` and
`native_exe_verification.json` record integration results. The executable is
built for Windows x64; validation on a clean second PC remains a separate check.

The existing Docker/Celery configuration is retained as an optional alternative.

The extended check needs the official axe-core 4.13.0 npm package extracted to
`artifacts/tools/package`; see the pinned download/hash in the CI workflow.
It checks 12 concurrent users, five pages at four widths, automated WCAG checks,
keyboard navigation and an executing worker killed during a test job.
See [Windows acceptance](WINDOWS_ACCEPTANCE.md) for the separate-PC/reboot kit.

For actual elapsed-time observation, keep Windows awake and ALFRED running:

```powershell
.\.venv\Scripts\python.exe scripts/observe_native_runtime.py --data-dir F:\ALFRED --hours 8 --report artifacts/ops/native_overnight_verification.json
```

An interrupted observation or missed schedule remains a failed/incomplete proof.
In India, refresh runs at 05:30, 11:30, 17:30 and 23:30; cleanup at 07:45 and
eligible training at 08:30. A scheduled training cycle can legitimately skip
models because consent, data, freshness or runtime approval gates are unmet.
