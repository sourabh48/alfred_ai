# Windows source application setup

Prepared on 2026-10-05 for the pre-reinstall checkpoint. These are recovery
instructions to retain now; Windows has not been reinstalled and private data
has not been restored by this preparation. Read the
[reinstall checklist](WINDOWS_REINSTALL_CHECKLIST.md) before formatting.

The current Git checkout is **F:\ALFRED**, containing `manage.py`. Its
`alfred_ai` subdirectory is the Django package. A new clone may use a different
folder; run commands from the folder containing `manage.py`.

## Git

Install [Git for Windows](https://git-scm.com/install/windows), then verify
`git --version`. GitHub authentication recovery is separate from the source
checkout; keep account recovery or SSH key recovery available independently.

## Supported Python version

Use **64-bit CPython 3.12** with pip, venv and Tcl/Tk. The current validated
installation is 3.12.2; the bootstrap deliberately selects the 3.12 series,
because the pinned scientific packages have been validated on it. Django 6
requires Python 3.12 or newer, but newer Python series have not been validated
for the whole dependency set.

Use the [official Python Windows installation guide](https://docs.python.org/3.12/using/windows.html).
[Python 3.12.10](https://www.python.org/downloads/release/python-31210/) is the
last 3.12 release with the traditional Windows binary installers; subsequent
3.12 releases provide security fixes. Select the x64 installer, pip, Tcl/Tk,
the Python launcher and the long-path option. If using another distribution
of 3.12, verify its patch/security support and use `-PythonExecutable` below.

```powershell
py -3.12 --version
py -3.12 -c "import struct; print(struct.calcsize('P') * 8)"
```

The second command must print `64`. Use a supported Windows installation.

## PowerShell

Windows PowerShell 5.1 or PowerShell 7 works. The scripts do not require an
administrator account or a persistent execution-policy change. If local
policy blocks a reviewed script, use a process-scoped invocation:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
```

[Microsoft documents execution-policy scopes](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies).
Organization Group Policy may still apply.

## Browser required by Selenium

ALFRED opens the default browser for normal use. Install Chrome for the
existing Chrome regression workflow. Selenium is included in the Python
requirements; [Selenium Manager](https://www.selenium.dev/documentation/selenium_manager/)
can obtain the matching driver. The first browser test needs network access
for its driver unless already available. Browser profiles, cookies and caches
are private runtime data and are not source dependencies.

## OCR / Tesseract

RapidOCR, ONNX Runtime, its packaged model assets and PyMuPDF are installed by
the Python requirements for general document OCR. **Scanned credit-report
OCR also uses Tesseract** in `credit_report_parser.py`. For that feature,
follow the [Tesseract Windows installation instructions](https://tesseract-ocr.github.io/tessdoc/Installation.html)
(which link the Windows installer), install English language data, and set
this path privately in the selected data directory's `config/local.env`:

```text
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

Verify the installed executable with:

```powershell
& 'C:\Program Files\Tesseract-OCR\tesseract.exe' --version
```

## Visual C++ / build tools

Scientific, OCR and audio packages use native Windows DLLs. Install the
[Microsoft x64 Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)
if their imports report a missing MSVC runtime. The tested Python/x64
dependencies use wheels; Visual Studio C++ Build Tools are not a normal
application prerequisite. If pip tries to compile a pinned package, first
check that Python is 64-bit 3.12 and investigate the missing wheel rather
than silently changing packages.

## Node / npm and Java

Neither is required to run or rebuild this source application's web assets.
JavaScript libraries are checked into `static/vendor`; the application has
no Node build step or Java service. Node may be needed for agent tooling;
follow [agent tooling recovery](../artifacts/reinstall/AGENT_TOOLS_REINSTALL.md)
for that separate installation. The native runtime uses Waitress, Huey and
SQLite without a PostgreSQL, Redis, Docker or Celery service.

## Clone

The pre-reinstall branch is `codex/native-runtime-hardening-20260918`.
Use the verified commit recorded in the final checkpoint when choosing the
recovery revision, rather than assuming `master` contains the preparation.

```powershell
New-Item -ItemType Directory -Path F:\ALFRED -Force | Out-Null
Set-Location F:\ALFRED
git clone --branch codex/native-runtime-hardening-20260918 https://github.com/sourabh48/alfred_ai.git alfred_ai
Set-Location .\alfred_ai
git rev-parse HEAD
```

Do not clone over an existing checkout. If restoring the existing private
installation, use the separately verified backup manifest and the
post-reinstall recovery prompt before first startup. Preserve
`config/native.env` alongside its database; it protects encrypted credentials
and signed sessions. Bootstrap refuses an existing database without this
file. Fresh application setup does not restore accounts or private files.

## Fresh venv and dependencies

The bootstrap handles this, or run the equivalent dependency steps manually:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
```

Use a new venv; copying the old `.venv` is unnecessary. `requirements.txt` is
the dependency entry point and includes the CPU PyTorch index. Retain any
versioned constraints it references. These are large downloads; allow disk
space and network access. Do not mix Graphify or global agent-tool packages
into the application venv.

## Environment setup and bootstrap

`config/native.local.env.example` is the safe **native Windows** template.
`config/local.env.example` is the separate Compose/PostgreSQL template.
For a fresh native profile, copy only when the destination does not exist:

```powershell
if (-not (Test-Path .\config\local.env)) {
    Copy-Item .\config\native.local.env.example .\config\local.env
}
.\scripts\setup_windows.ps1
```

The script creates `.venv` if absent, checks Python/x64, installs dependencies,
runs `pip check`, preserves existing environment files, creates runtime
directories, and runs Django `manage.py check` in the actual native settings
context. It reuses the launcher's one-time `config/native.env` creation and
does not run migrations or start ALFRED by default. Stop ALFRED and let its
worker finish before rerunning setup on an existing installation.

Select a different runtime data folder or explicit Python installation with:

```powershell
.\scripts\setup_windows.ps1 -DataDirectory 'F:\ALFRED_DATA' -PythonExecutable 'C:\Path\To\Python312\python.exe'
```

Provider credentials belong only in the data folder's private
`config/local.env`. Native settings use SQLite, local diskcache and Huey;
do not carry over Compose database/broker settings as a native template.
Local configuration precedence is explicit process variables, then
`config/local.env`, then legacy `.env`. Native configuration then loads its
persisted signing key from `config/native.env`. Never replace that file
while recovering an existing database.

## Migrations and Django validation

For an empty new data directory, the bootstrap can migrate explicitly:

```powershell
.\scripts\setup_windows.ps1 -MigrateFresh
```

This refuses any existing `db.sqlite3`, including a restored database. It
runs the equivalent of `python manage.py check` and
`python manage.py migrate --noinput` after the same native configuration used
by the launcher. Do not use fresh-database migration as a private-data
recovery command.

For source-development checks using `alfred_ai.settings`, select the matching
data folder and SQLite explicitly. Explicit source configuration keeps priority;
when no source signing key is configured, settings reuse the persisted
`config/native.env` key instead of a public development default:

```powershell
$env:ALFRED_LOCAL_RUNTIME = 'true'
$env:ALFRED_AUTO_TRAIN_ON_STARTUP = 'false'
$env:ALFRED_DATA_DIR = 'F:\ALFRED\alfred_ai'
$env:DATABASE_URL = 'sqlite:///F:/ALFRED/alfred_ai/db.sqlite3'
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
# On an empty development database only:
.\.venv\Scripts\python.exe manage.py migrate
Remove-Item Env:DATABASE_URL, Env:ALFRED_LOCAL_RUNTIME, Env:ALFRED_AUTO_TRAIN_ON_STARTUP, Env:ALFRED_DATA_DIR
```

Change the example database path to your actual checkout. Retained native
databases should be reviewed and backed up before a launcher upgrade, which
automatically applies pending migrations. Optional browser validation is
`.\.venv\Scripts\python.exe scripts/run_browser_regressions.py --browser Chrome --require-browser`;
the runner uses disposable test data.

## Launch

From the repository root, for the default source runtime data folder:

```powershell
.\.venv\Scripts\python.exe alfred_native.py start
.\.venv\Scripts\python.exe alfred_native.py status
.\.venv\Scripts\python.exe alfred_native.py stop
```

Use `--data-dir 'F:\ALFRED_DATA'` on all three commands if setup used that
folder. The native launcher starts Waitress, the persistent Huey queue and the
tray icon, applies migrations, collects static assets, and opens the browser
at `http://127.0.0.1:8000/` (or the next free port). Source defaults to its
checkout; packaged releases default to `%LOCALAPPDATA%\ALFRED`. Closing the
browser leaves the worker running; use `stop` for graceful shutdown.

`Start ALFRED.cmd` also works, but it prefers an existing `dist` build. Use the
explicit Python command after rebuilding a source checkout to select its
current code. Package creation and Inno Setup are optional release tasks,
documented in [Windows packaging](WINDOWS_PACKAGE.md); they are not required
to launch the source application.
