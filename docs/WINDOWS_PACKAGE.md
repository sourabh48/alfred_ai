# Standalone Windows package

The Windows x64 release contains its own Python 3.12 runtime and application
dependencies. No Python, pip, virtual environment, Docker, PostgreSQL or Redis
installation is required on the destination PC.

The [1.1.0 travel preview verification](TRAVEL_RELEASE_VERIFICATION_20260929.md)
records the current package fingerprints, travel checks and local upgrade.

Download the [Windows preview from GitHub Releases](https://github.com/sourabh48/alfred_ai/releases/tag/v1.1.0-preview.1):

- [Windows installer](https://github.com/sourabh48/alfred_ai/releases/download/v1.1.0-preview.1/ALFRED-Setup.exe)
- [Portable ZIP](https://github.com/sourabh48/alfred_ai/releases/download/v1.1.0-preview.1/ALFRED-Windows-x64.zip)
- [SHA-256 checksums](https://github.com/sourabh48/alfred_ai/releases/download/v1.1.0-preview.1/SHA256SUMS.txt)
- [Release manifest](https://github.com/sourabh48/alfred_ai/releases/download/v1.1.0-preview.1/release-manifest.json)

Local builds remain in the ignored `release` folder; binaries are distributed
as release assets rather than committed to Git. The developer's complete local
release folder also contains separate-PC acceptance launchers and a machine-bound
manifest; see `ACCEPTANCE.txt` there. That acceptance kit is separate from the
public downloads.
The [28 September tray verification](WINDOWS_TRAY_VERIFICATION_20260928.md)
records the preceding release's launcher, tray, installer and guide checks. The
[27 September verification](WINDOWS_PACKAGE_VERIFICATION_20260927.md)
records the previous release's checks, uninstall behavior and cleanup. The
[26 September runtime verification](WINDOWS_PACKAGE_VERIFICATION_20260926.md)
records the previous release's runtime, load, mobile and accessibility checks.

## Start using ALFRED

Follow the [illustrated installation guide](INSTALLATION.md) for pictures of
the download, setup, first launch and tray controls. The same guide is bundled
for offline use under **Installation guide** in the tray menu.

Choose either distribution:

- **Installer:** run `ALFRED-Setup.exe`, then open ALFRED from the desktop or
  Start menu. Installation is per Windows user and does not need administrator
  access.
- **Portable ZIP:** extract all of `ALFRED-Windows-x64.zip`, then double-click
  `ALFRED Launcher.exe` inside the `ALFRED` folder. Keep `_internal` and both
  executable files together. `Start ALFRED.cmd` opens the same launcher.

The launcher shows progress while the local server and worker start, then opens
the default browser. On a new PC, create an account. Double-click `Stop ALFRED.cmd`
or use the installed Stop ALFRED shortcut to finish background work and stop.
Closing the browser leaves scheduled work running.

The **ALFRED A icon** remains in the Windows notification area while the native
server runs, including quiet startup after sign-in. Click it to open the app;
right-click for the installation guide, data folder and graceful shutdown.
If Windows places it in the overflow area, use the arrow next to the clock.

To uninstall an installed copy, choose **Uninstall ALFRED** in the Start menu,
use Windows Settings > Apps, or run **Uninstall ALFRED.cmd** in its program
folder. Setup creates the actual `unins000.exe` uninstaller and its installation
record. Keep those files together. Uninstall cancels before deleting files if
ALFRED cannot stop; retry after background work finishes. It removes an ALFRED
sign-in entry only when that entry points to this installation. Saved data is
retained. For a portable copy, stop ALFRED and delete the extracted program folder.

Data is stored in `%LOCALAPPDATA%\ALFRED`, separately from the program files.
Replacing the portable folder, updating or uninstalling retains that data.
On the development checkout, the root `Start ALFRED.cmd` explicitly selects
`F:\ALFRED` so the existing workspace accounts and uploads remain available.
Neither distributable includes those accounts, private uploads or credentials.

The interface assets and OCR engines are bundled. Live external sources need
internet access. Background schedules run only while Windows and ALFRED are on.

## Build the same release

From the configured development environment:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller packaging/ALFRED.spec --noconfirm --distpath artifacts/releases/next-build --workpath build
.\.venv\Scripts\python.exe scripts/verify_packaged_launcher.py --bundle artifacts/releases/next-build/ALFRED
.\.venv\Scripts\python.exe scripts/verify_native_runtime.py --executable artifacts/releases/next-build/ALFRED/ALFRED.exe --launcher "artifacts/releases/next-build/ALFRED/ALFRED Launcher.exe" --browser --extended --load-users 24 --load-writes 20 --load-seconds 120
.\.venv\Scripts\python.exe scripts/package_windows_release.py --bundle artifacts/releases/next-build/ALFRED --output artifacts/releases/next-build/distributables --iscc F:/ALFRED-tools/InnoSetup/ISCC.exe
.\.venv\Scripts\python.exe scripts/verify_windows_installer.py --installer artifacts/releases/next-build/distributables/ALFRED-Setup.exe --report artifacts/ops/next-installer-lifecycle.json
```

Use a new output directory for a new release. Packaging checks the bundled
Python, Tcl/Tk, OCR models, templates and web assets; scans for private runtime
paths; verifies the ZIP CRCs; and writes `SHA256SUMS.txt` and a release manifest.
The integration runner clears system Python environment variables and removes
the development tools from the packaged process's PATH.

The installer verifier requires no existing registered ALFRED installation. It
uses disposable data and a program path with spaces and an apostrophe, verifies
upgrade retention and failed-shutdown protection, and restores the original
Windows startup entry and desktop shortcut after checking ownership-aware
uninstall cleanup. Before making changes it saves the original Windows state
and any desktop shortcut in its generated test folder, allowing recovery if
Windows or the test process is interrupted.

The separate-PC and real reboot checks remain distinct from local packaged
verification. Follow [Windows acceptance](WINDOWS_ACCEPTANCE.md) and retain its
Fresh/Reboot proofs and the [human observations](MANUAL_ACCEPTANCE.md).
