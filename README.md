# ALFRED

ALFRED keeps personal finances and documents together: spending, budgets,
loans, credit reports, investments and related planning.
ALFRED is local or LAN-hosted; the current Windows build runs on this PC using
**Waitress + Huey + SQLite**. It includes the web server and background jobs.

## What you can do

- Import statements and review transactions, spending and cash flow.
- Track budgets, loans, repayments, investments and net worth.
- Upload credit reports, loan documents and other supported files; review and
  correct uncertain extraction results in the document center.
- Use career, vehicle and family planning workspaces.
- Link consenting family accounts with a link code. Manage linked members and
  **Remove my data** in Settings.

## Run on Windows

**Existing checkout:** double-click the **ALFRED** shortcut (`ALFRED.lnk`) or
**Start ALFRED.cmd**. It uses the packaged
launcher when available and keeps this checkout's existing data. Stop it with
**Stop ALFRED.cmd**.
For a fresh development checkout, follow the [development guide](docs/DEVELOPMENT.md).

**Packaged application:** run [ALFRED-Setup.exe](release/ALFRED-Setup.exe), then
open the ALFRED desktop shortcut. The installer includes Python and dependencies.
For portable use, extract the [Windows ZIP](release/ALFRED-Windows-x64.zip) and double-click
**ALFRED Launcher.exe**. Keep its complete folder together. Neither package
requires a separate Python, pip or Docker installation. See the
[standalone package guide](docs/WINDOWS_PACKAGE.md).

**Uninstall:** use **Uninstall ALFRED** in the Start menu or Windows Settings >
Apps. The installed folder also contains **Uninstall ALFRED.cmd**. Your saved
accounts, documents and settings are retained.

The launcher opens your browser, normally at <http://127.0.0.1:8000/>. It chooses
another port if needed. Create an account or sign in. Closing the browser leaves
background jobs running; installed users can use the **Stop ALFRED** Start menu shortcut.

**Automatic startup:** for this checkout, run **Enable ALFRED startup.cmd** once.
It registers quiet startup after Windows sign-in, using the checkout's existing
data. See [startup controls](docs/NATIVE_WINDOWS.md#automatic-startup-after-windows-sign-in)
for status, disabling it, or selecting another installation.

## Your data and recovery

- The checkout launcher uses data in the repository folder.
- Installer and portable launches default to `%LOCALAPPDATA%\ALFRED`. They do
  not automatically import an existing checkout's accounts or uploads.
- Keep the database, uploads, models and private configuration together when
  backing up. Follow the [backup/restore instructions](docs/NATIVE_WINDOWS.md#backup-and-restore).
- Queued jobs survive restart. Interrupted maintenance jobs can retry;
  interrupted imports and training are retained for review.

Schedules run while ALFRED and the PC are on. Windows startup does not resume
an interrupted overnight verification automatically.

## Verification and remaining work

The **27 September 2026** release includes the installer, named uninstaller and
ALFRED icon. The fresh backend run passed 407 tests, and all nine Chrome browser
cases passed separately. The unchanged native executables passed 23 packaged
runtime checks and a 24-user load check on 26 September. See the
[current release verification](docs/WINDOWS_PACKAGE_VERIFICATION_20260927.md).

As of **18 September 2026**, the packaged runtime, installer, backup/restore,
interrupted-worker recovery, host reboot retention and Windows/Chrome CI checks
passed. Concurrent-user, mobile-layout and automated accessibility checks also
passed within their recorded scope. See the [verification report](docs/NATIVE_HARDENING_VERIFICATION.md).

Remaining acceptance work:

- Install and test on a clean second Windows PC, including a reboot.
- Finish the overnight observation of refresh, cleanup and eligible training
  (started 27 September at 00:13 IST; expected completion around 10:13 IST).
- Validate accuracy with independently checked real data and more document layouts.
- Extend manual screen-reader testing and testing under heavier real usage.

Model fitting alone does not establish accuracy. Current validation limits and
per-requirement evidence are in the [completion audit](docs/COMPLETION_AUDIT.md).
LAN access and live email/bureau integrations remain optional and unverified.

## Further documentation

- [Windows operation, startup, schedules and recovery](docs/NATIVE_WINDOWS.md)
- [Development, tests and builds](docs/DEVELOPMENT.md)
- [Clean-PC acceptance checklist](docs/WINDOWS_ACCEPTANCE.md)
- [Data privacy and storage](docs/DATA_PRIVACY_AND_STORAGE.md)
- [Architecture](docs/ARCHITECTURE.md) and [future scope](docs/FUTURE_SCOPE.md)
- [Optional Docker Compose hosting](docs/LOCAL_HOSTING.md)

Docker/PostgreSQL/Redis/Celery remains an optional runtime documented separately.
It is not required for the native Windows application. Public/cloud deployment
is outside the current scope.
