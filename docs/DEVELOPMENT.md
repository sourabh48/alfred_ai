# Development and verification

Use Python 3.12 for the currently tested development environment. Packaged
Windows users can follow [Native Windows](NATIVE_WINDOWS.md) directly.
Run these commands from the repository root in PowerShell.

## Set up a fresh checkout

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe alfred_native.py start
```

The native launcher creates local configuration, applies migrations, prepares
static assets and starts the server, worker and scheduler. It uses the checkout
as its data folder by default. Keep an existing `.venv` if it is already set up.

For Django's development server, set `ALFRED_LOCAL_RUNTIME=true` and use
`python manage.py runserver` with the selected environment. `runserver` is one
word; it starts only the development web server. Use the native launcher to
exercise background jobs too. Runtime secrets belong in untracked local files;
see [native configuration and data](NATIVE_WINDOWS.md#data-and-secrets).

## Backend checks

```powershell
$env:ALFRED_LOCAL_RUNTIME = 'true'
$env:ALFRED_AUTO_TRAIN_ON_STARTUP = 'false'
$env:ALFRED_RUN_BROWSER_TESTS = 'false'
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test --noinput
```

Use a disposable checkout/data folder for wider integration work. Browser tests
are intentionally separate from the normal backend run; skipped browser cases
in that run are not browser verification.

## Browser checks

```powershell
.\.venv\Scripts\python.exe scripts/run_browser_regressions.py --browser Chrome --require-browser --proof-label local-chrome
```

Use `--browser Edge --proof-label local-edge` for Edge. The runner enables
`ALFRED_RUN_BROWSER_TESTS=true`; `--require-browser` rejects an unavailable or
skipped browser run. Summaries, screenshots, HTML and supported browser logs go
to `artifacts/browser`, including `browser_regression_summary.json` and a labeled
summary. `--artifact-dir` or `ALFRED_BROWSER_ARTIFACT_DIR` can select another folder.
The CI workflow is `.github/workflows/browser-regression.yml`.

## Native runtime and recovery

```powershell
.\.venv\Scripts\python.exe scripts/verify_native_runtime.py --browser --extended
.\.venv\Scripts\python.exe scripts/verify_native_runtime.py --executable dist/ALFRED/ALFRED.exe --browser --extended
```

These checks create isolated synthetic accounts and data. Extended verification
includes concurrent users, responsive pages and automated accessibility; it
requires the pinned axe-core package described in [Native Windows](NATIVE_WINDOWS.md).
Build instructions and the real overnight observer are also documented there.
Keep real Windows sign-in/reboot and [clean-PC acceptance](WINDOWS_ACCEPTANCE.md)
separate from a process restart test.

## Additional diagnostics

```powershell
.\.venv\Scripts\python.exe scripts/refresh_verified_evidence.py --require-healthy
.\.venv\Scripts\python.exe scripts/exercise_materialized_cache_traffic.py
```

The refresh command contacts configured sources and updates due evidence; it is
not a read-only check. Its proof is written under `artifacts/evidence`.
The cache exercise creates deterministic staging proof under `artifacts/cache`
for all 21 registered materialized namespaces. Staging proof does not establish
capacity under real workloads. See [recorded verification](NATIVE_HARDENING_VERIFICATION.md)
and the [completion audit](COMPLETION_AUDIT.md) for results and limits.

The optional PostgreSQL/Redis/Celery runtime has its own
[Compose instructions](LOCAL_HOSTING.md). Native Windows runs use Huey.
