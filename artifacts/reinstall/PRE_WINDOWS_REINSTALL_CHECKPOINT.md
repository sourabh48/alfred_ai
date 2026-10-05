# Pre-Windows-reinstall checkpoint

Prepared 2026-10-05 (Asia/Kolkata). This is preparation only; no Windows reinstall or private-data restore has been performed.

## Repository and engineering state

- Actual repository root: `F:\ALFRED`; `alfred_ai/` is the Django package, not a second Git checkout.
- Repository: https://github.com/sourabh48/alfred_ai (public).
- Branch: `codex/native-runtime-hardening-20260918`.
- Starting HEAD: `b4e89742717d0f4ce1d8b6e49ccb7b6b6abde525`, also verified on origin at task start.
- Starting worktree: intended Phase 0/1, M12A/B/C and M13A/B source, migrations, tests and documentation were uncommitted. Preserve these before formatting.
- Engineering checkpoint: M13A/B Loan currency complete; M13C Investment currency remains the next engineering stage. Reinstall preparation supersedes that continuation for this task.
- Current documented published preview: `v1.1.0-preview.1` (installer AppVersion `1.1.0`); existing frozen binaries do not contain this newer engineering work. No installer promotion is part of this checkpoint.
- Latest prior full backend gate: 688 run, 671 passed, 17 browser skips, zero failures/errors, 641.053 seconds, exit 0; completed 2026-10-05 15:40:05 +05:30. Two distinct Chrome workflows also passed. See `docs/MASTER_M13B_VERIFICATION_20261005.md`.

## Environment

- Windows; PowerShell is the setup-script shell.
- Configured interpreter: `F:\ALFRED\.venv\Scripts\python.exe`, CPython 3.12.2, 64 bit.
- Git: 2.52.0.windows.1; GitHub CLI: 2.97.0.
- Django: 6.0.8; pip: 25.1.1; NumPy: 1.26.4; pandas: 2.2.3; PyTorch: 2.2.0+cpu; scikit-learn: 1.4.1.post1; cryptography: 43.0.3; PyInstaller: 6.22.3.
- Native application uses SQLite, diskcache and Huey; it needs no Redis/PostgreSQL service, Node or Java.
- Node/npm are agent-tool dependencies, not native application dependencies. Actual tooling versions and reinstall commands are in `AGENT_TOOLS_REINSTALL.md`.
- Java exists on this machine; no application requirement has been established, so it is not a Windows setup prerequisite.
- `requirements.txt` and `constraints/windows-py312.txt` preserve the tested Windows Python 3.12 runtime dependency versions. Constraints contain package versions only.

## Actual private runtime paths

Two separate installations were discovered; neither is tracked by Git:

| Root | Valuable state |
|---|---|
| `F:\ALFRED` | `db.sqlite3`, `media/`, private `config/local.env` and `config/native.env`, durable `artifacts/native/jobs.sqlite3`, valuable model state and application backup archives |
| `C:\Users\soura\AppData\Local\ALFRED` | separate `db.sqlite3`, `config/native.env`, and any existing media, durable queue, model state or application backup archives |

The main native runtime was running at inventory time. Stop it cleanly before backing up; SQLite snapshots alone do not make concurrent media/model changes coherent. The packaged-user runtime was stopped.

`config/local.env` contains a legacy Compose PostgreSQL configuration. The active native runtime overrides it with SQLite. No Docker CLI/service or PostgreSQL/Redis process was found; historical Docker/WSL data coverage must be resolved before asserting that all private data is backed up.

## Inventory and secret handling

Initial inventory: 591 tracked files, 757 untracked files, 124,613 ignored files and five tracked-but-ignored safe audit documents. The exact requested `git ls-files --ignored --exclude-standard` requires `--cached` or `--others`; both corrected forms were used.

There were no tracked database, PDF, executable, archive or application image files. Largest tracked files are required offline browser libraries (Bootstrap, Chart.js, Leaflet), all below 250 KB; preserve them. Raw inventories, secret-scanner reports and logs stay outside Git.

Gitleaks 8.30.1 scanned all available local Git refs/history. Four generic-key alerts were reviewed: all are public motorcycle `catalog_key` identifiers, not credentials. A separate intended-source scan is required immediately before commit/push. Those scanner false positives do not require rotation. The additional private-value comparison below found a separate real signing-key concern that the scanner missed.

## Reinstall gate

Private backup destination and confirmation that it will remain untouched are pending. GitHub/SSH recovery, independent secret recovery and installation media are also operator confirmations. Until the verified backup and final Git/remote checks are complete:

`SAFE TO REINSTALL WINDOWS = NO`

See `PRE_REINSTALL_FINAL_STATUS.md` for the final verification state and `../../docs/WINDOWS_REINSTALL_CHECKLIST.md` for the operator checklist. The final status is an ignored generated receipt written after the final push, so it can record the actual final local/remote HEAD without a self-referential documentation commit; the reusable recovery instructions are versioned.

## Environment variable names (no values)

Names/state below were read from each installation's private files and process environment. No credential values are recorded. Names not configured here may be supported optional integrations.

| Name | Main native/source configuration | Packaged-user configuration |
|---|---|---|
| ALFRED_AUTO_TRAIN_ON_STARTUP | CONFIGURED | NOT CONFIGURED |
| ALFRED_BROWSER_CI_CHROME_SUMMARY | CONFIGURED | NOT CONFIGURED |
| ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION | CONFIGURED | NOT CONFIGURED |
| ALFRED_LOCAL_RUNTIME | CONFIGURED | NOT CONFIGURED |
| ALFRED_MATERIALIZED_CACHE_TRAFFIC_PROOF | CONFIGURED | NOT CONFIGURED |
| ALFRED_PRODUCTION_DEPLOYMENT_PROOF | CONFIGURED | NOT CONFIGURED |
| ALFRED_SESSION_TIMEOUT_SECONDS | CONFIGURED | NOT CONFIGURED |
| ALFRED_SESSION_WARNING_SECONDS | CONFIGURED | NOT CONFIGURED |
| ALLOWED_HOSTS | CONFIGURED | NOT CONFIGURED |
| ANTHROPIC_API_KEY | NOT CONFIGURED | NOT CONFIGURED |
| BRAVE_API_KEY | NOT CONFIGURED | NOT CONFIGURED |
| CACHE_BACKEND | CONFIGURED | NOT CONFIGURED |
| CACHE_LOCATION | CONFIGURED | NOT CONFIGURED |
| CELERY_BROKER_URL | CONFIGURED | NOT CONFIGURED |
| CELERY_RESULT_BACKEND | CONFIGURED | NOT CONFIGURED |
| CELERY_TASK_ALWAYS_EAGER | CONFIGURED | NOT CONFIGURED |
| CORS_ALLOW_ALL_ORIGINS | CONFIGURED | NOT CONFIGURED |
| CORS_ALLOWED_ORIGINS | CONFIGURED | NOT CONFIGURED |
| CSRF_COOKIE_SAMESITE | CONFIGURED | NOT CONFIGURED |
| CSRF_COOKIE_SECURE | CONFIGURED | NOT CONFIGURED |
| CSRF_TRUSTED_ORIGINS | CONFIGURED | NOT CONFIGURED |
| DB_CONN_HEALTH_CHECKS | CONFIGURED | NOT CONFIGURED |
| DB_CONN_MAX_AGE | CONFIGURED | NOT CONFIGURED |
| DB_ENGINE | CONFIGURED | NOT CONFIGURED |
| DB_HOST | CONFIGURED | NOT CONFIGURED |
| DB_NAME | CONFIGURED | NOT CONFIGURED |
| DB_PASSWORD | CONFIGURED | NOT CONFIGURED |
| DB_PORT | CONFIGURED | NOT CONFIGURED |
| DB_USER | CONFIGURED | NOT CONFIGURED |
| DEBUG | CONFIGURED | NOT CONFIGURED |
| DJANGO_SECRET_KEY | CONFIGURED | CONFIGURED |
| DJANGO_SECRET_KEY_FALLBACKS | CONFIGURED | NOT CONFIGURED |
| GEMINI_API_KEY | NOT CONFIGURED | NOT CONFIGURED |
| GOOGLE_API_KEY | NOT CONFIGURED | NOT CONFIGURED |
| GOOGLE_MAPS_API_KEY | NOT CONFIGURED | NOT CONFIGURED |
| LOG_LEVEL | CONFIGURED | NOT CONFIGURED |
| OPENAI_API_KEY | NOT CONFIGURED | NOT CONFIGURED |
| REDIS_URL | CONFIGURED | NOT CONFIGURED |
| SECURE_HSTS_SECONDS | CONFIGURED | NOT CONFIGURED |
| SECURE_SSL_REDIRECT | CONFIGURED | NOT CONFIGURED |
| SESSION_COOKIE_HTTPONLY | CONFIGURED | NOT CONFIGURED |
| SESSION_COOKIE_SAMESITE | CONFIGURED | NOT CONFIGURED |
| SESSION_COOKIE_SECURE | CONFIGURED | NOT CONFIGURED |
| SESSION_EXPIRE_AT_BROWSER_CLOSE | CONFIGURED | NOT CONFIGURED |
| SESSION_SAVE_EVERY_REQUEST | CONFIGURED | NOT CONFIGURED |
| TRAVEL_BRAVE_API_KEY | NOT CONFIGURED | NOT CONFIGURED |
| TRAVEL_DUFFEL_API_KEY | NOT CONFIGURED | NOT CONFIGURED |
| TRAVEL_ORS_API_KEY | NOT CONFIGURED | NOT CONFIGURED |

Configured optional API provider names: none found in the inspected files/process environment. Provider OAuth state stored in databases is private and belongs in the database backup.

Historical Docker disk discovered: `%LOCALAPPDATA%\Docker\wsl\main\ext4.vhdx`, 100,663,296 bytes. Preserve this private disk as a precaution; absence of a Docker service does not prove its contents are disposable.

Current documented published preview: `v1.1.0-preview.1`; installer source AppVersion `1.1.0`. The current engineering source is newer than that package.

Observed PowerShell: 5.1.26100.9549. Tesseract is absent from PATH; scanned credit-report OCR may require installation or an explicitly restored local TESSERACT_CMD. General document OCR has bundled Python/ONNX fallback dependencies.

## Dependency rebuild finding

The original environment's `pip check` reported three Google API dependency conflicts caused by Protobuf 7.34.1. The isolated fresh environment resolved compatible Protobuf 6.33.6, now pinned in the Windows constraints. Fresh dependency installation and `pip check` passed. The running installation was not modified. Full application verification of this rebuilt environment is recorded in the final receipt.

## Exposed historical signing fallback

A blind comparison against private configuration found the public development signing key actively retained as a legacy fallback in the main installation. Its plaintext was removed from current source and tests; a fingerprint preserves readiness rejection. Fresh local profiles now persist a unique private key once. Retained databases without a known key fail safely. Existing private primary/fallback files were preserved.

The exposed value still exists in public Git history and older packaged releases. Removing current plaintext does not revoke it. Preserve the key in the verified private backup for decryption recovery, then deliberately re-encrypt affected credentials and retire the old signing fallback/sessions. Do not simply delete the fallback and lose encrypted data. History cleanup is a separate action; no history rewrite was performed. The inactive Compose example password is a public placeholder; change it before activating/restoring that service.

Focused key/config/native/readiness/setup validation passed 28 tests in 5.345 seconds. No private configuration was changed. The final full gates supersede this focused evidence when complete.
