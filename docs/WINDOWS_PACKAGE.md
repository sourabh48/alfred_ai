# Standalone Windows package

**Latest local review candidate — 2026-10-16:** Frozen source
`4aa7ac70fa27c1410e695470af5c3987235244b1`, branch
`release/post-audit-runtime-20261016`, is not deployed or published. A fresh
Python 3.12.10 / Django 6.0.9 bundle passed 35 native checks including seven
packaged Chrome flows. Exact-source gates passed 797 backend / 40 Chrome /
34 source-native/Ollama and actual M21 restore/promotion/restart/worker-crash/
source-rollback acceptance. The completed backend/Chrome/native suites have zero
failures/skips; M21's intentional worker failure is recorded separately.
[Current status](PROJECT_STATUS.md) records pending operational gates.

Local ignored evidence is under
`artifacts/releases/post-audit-4aa7ac7-28624710`: build/source manifest, complete
bundle inventory, copied native proof, hash-pinned dependency inputs and portable
verification. A second assembly in `post-audit-4aa7ac7-repeat-fa68edd5` matched
all 10,322 file paths and bytes, including these SHA-256 values:

| Accepted artifact | SHA-256 |
| --- | --- |
| `ALFRED.exe` | `39ef797c876cbbb434a467ef0697709524ff9a41c8f12c8adc05ac768673b5dc` |
| `ALFRED Launcher.exe` | `024ceab3c78756f2ad5e3e3f15abad4c130ab2c3debfbac068f28c19fc33dcae` |
| `portable/ALFRED-Windows-x64.zip` | `6db90bd1c03cb4689c7719030369efc3ba28c0cb1c393d2e92e4967e7465a90a` |

The 468,439,826-byte ZIP's 10,322 entries were independently decompressed and
matched to the accepted inventory by size and SHA-256. The acceptance kit is
prepared beside it. This is an application archive, not an encrypted user-data
backup. No private runtime was packaged, deployed or exported.

The SDK matched 151 application packages; those packages and bootstrap pip kept
their versions when five declared build tools were added. All 156 application/
build distributions have recorded public input hashes (154 wheels / two source
archives). Bootstrap pip is 25.0.1. Source-archive backend provenance and an
independent clean environment remain distinct from same-SDK repeatability.
Builds used fixed `PYTHONHASHSEED=1` and commit-time `SOURCE_DATE_EPOCH`, as in
[PyInstaller's reproducible-build guidance](https://www.pyinstaller.org/en/stable/advanced-topics.html#creating-a-reproducible-build).
These are build-process inputs; do not set them globally for application runtime.
Use a disposable data/configuration root and the house
`scripts.release_validation.environment` to strip operator credentials and disable
cloud, paid reasoning and startup training before analysis. Preserve its receipts
and use a fresh output directory. No installer compiler was available here;
installer lifecycle, separate-PC/reboot, normal-account and device-loss recovery
acceptance remain NOT_RUN. No live update or GitHub publication is authorized.

The Windows x64 release contains its own Python 3.12 runtime and application
dependencies. No Python, pip, virtual environment, Docker, PostgreSQL or Redis
installation is required on the destination PC.

The historical [1.1.0 travel preview verification](TRAVEL_RELEASE_VERIFICATION_20260929.md)
records that preview's package fingerprints, travel checks and local upgrade.

Previously published [Windows preview downloads](https://github.com/sourabh48/alfred_ai/releases/tag/v1.1.0-preview.1)
(these are not the local post-audit candidate):

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
