# Standalone Windows package

The Windows x64 release contains its own Python 3.12 runtime and application
dependencies. No Python, pip, virtual environment, Docker, PostgreSQL or Redis
installation is required on the destination PC.

The completed 26 September release is available locally:

- [Windows installer](../artifacts/releases/20260926/distributables-retry/ALFRED-Setup.exe)
- [Portable ZIP](../artifacts/releases/20260926/distributables-retry/ALFRED-Windows-x64.zip)
- [SHA-256 checksums](../artifacts/releases/20260926/distributables-retry/SHA256SUMS.txt)
- [Release manifest](../artifacts/releases/20260926/distributables-retry/release-manifest.json)

These generated files are untracked. The earlier `distributables` folder holds
an interrupted attempt; use `distributables-retry` for this release.

## Start using ALFRED

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
.\.venv\Scripts\python.exe -m PyInstaller packaging/ALFRED.spec --noconfirm --distpath artifacts/releases/20260926 --workpath build
.\.venv\Scripts\python.exe scripts/verify_native_runtime.py --executable artifacts/releases/20260926/ALFRED/ALFRED.exe --launcher "artifacts/releases/20260926/ALFRED/ALFRED Launcher.exe" --browser --extended --load-users 24 --load-writes 20 --load-seconds 120
.\.venv\Scripts\python.exe scripts/package_windows_release.py --bundle artifacts/releases/20260926/ALFRED --output artifacts/releases/20260926/distributables --iscc F:/ALFRED-tools/InnoSetup/ISCC.exe
```

Use a new output directory for a new release. Packaging checks the bundled
Python, Tcl/Tk, OCR models, templates and web assets; scans for private runtime
paths; verifies the ZIP CRCs; and writes `SHA256SUMS.txt` and a release manifest.
The integration runner clears system Python environment variables and removes
the development tools from the packaged process's PATH.

The separate-PC and real reboot checks remain distinct from local packaged
verification. Follow [Windows acceptance](WINDOWS_ACCEPTANCE.md) and retain its
Fresh/Reboot proofs and the [human observations](MANUAL_ACCEPTANCE.md).
