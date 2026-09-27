# Windows package verification - 26 September 2026

The Windows release with the ALFRED icon passed local verification and is now
running from `dist/ALFRED` with the existing `F:\ALFRED` data folder. Open the
local `ALFRED.lnk` shortcut or `Start ALFRED.cmd`.

## Release and icon

The installer and portable ZIP tested on this date were subsequently archived
to `F:\ALFRED-retired\20260927\release`. Use the current
[installer](../release/ALFRED-Setup.exe) and
[portable ZIP](../release/ALFRED-Windows-x64.zip). The historical
[manifest](../artifacts/releases/20260926-icon/distributables/release-manifest.json)
and [checksums](../artifacts/releases/20260926-icon/distributables/SHA256SUMS.txt)
identify the tested binaries. The bundle scan checked 12,608 files and found
no prohibited private runtime paths. ZIP CRC verification passed.

The Windows icon is derived from `static/alfred-icon.svg`; `static/alfred.ico`
contains nine sizes from 16 to 256 pixels. Both executables, the installer,
the progress window and the local shortcut use it. Icons extracted from the
compiled launcher and installer were visually checked.

The release folder includes both separate-PC phase launchers, instructions
and an acceptance manifest. Its development-PC rejection was verified before
any test data was created. The old incomplete acceptance folder was removed.

## Verification

All **23 packaged runtime checks passed**, run `b409c2cf4f`, exit zero.
The run used relative executable paths, exercising the earlier verifier fix
that resolves the launcher path before changing the working directory.

- Signup and financial totals, private-upload ownership and access controls passed.
- Chrome rendered the finance UI with CDN access disabled. Seven pages passed
  layout checks at 360, 390, 768 and 1440 pixels. Automated accessibility checks
  at 390 and 1440 pixels found no serious or critical violations.
- Twenty-four concurrent users completed 480 writes and 2,625 timed requests
  with zero errors and correct isolated totals. Each user continued reading
  for 120 seconds. Recorded p95 was 3.36 seconds; packaging and installation
  also ran on this PC. This is synthetic local traffic.
- Worker execution, retry, recovery after a killed worker, scheduled heartbeat,
  bundled document and statement OCR, queued-job/account persistence after
  restart, and backup/restore of data, uploads and a pending job passed.
- The installer completed into a disposable path containing spaces. Its GUI
  launcher started and stopped successfully with Python removed from PATH.
  Uninstall removed the program and registration, retaining the test database
  with an unchanged hash.
- All three existing launcher unit tests passed.

Local evidence:

- `artifacts/plug-and-play-20260926-icon-verification.log`
- `artifacts/ops/native_exe_extended_verification.json`
- `artifacts/native-tests/b409c2cf4f/mobile-accessibility.json`
- `artifacts/ops/packaged_installer_verification-icon-20260926.json`
- `artifacts/ops/packaged_launcher_verification.json`
- `artifacts/ops/acceptance-kit-guard-20260926.json`

The bundle was verified in `artifacts/releases/20260926-icon/ALFRED`, then
moved to `dist/ALFRED`. Its executable hashes match the release manifest.
The existing app was stopped gracefully before that replacement. A SQLite
backup passed its integrity check, and the original database hash stayed
unchanged during the binary swap. The updated runtime passed its health check
on port 8000. Adoption evidence and the private database backup are under
`artifacts/ops/icon-release-adoption-20260926.json` and
`artifacts/ops/pre-icon-update-20260926` respectively.

## Cleanup

Removed **24,520 files totaling 5,482,411,212 bytes (5.48 GB)**: superseded
installers and bundles, the interrupted installation, the incomplete old
acceptance kit, the retired Python installer, a diagnostic browser profile,
and build caches. Exact paths and sizes are recorded in
`artifacts/ops/cleanup-20260926.json`.

Application data, uploads, models, configuration, backups, source work and
historical test reports were preserved. Old release manifests and checksums
were retained under `artifacts/ops/retired-release-manifests-20260926`.

## Remaining acceptance

A clean second PC, a real sign-in/reboot on that PC, a completed overnight
observation, human screen-reader checks and broader real-data/model validation
remain separate. This local run does not establish those outcomes. See
[Windows acceptance](WINDOWS_ACCEPTANCE.md) and
[human acceptance](MANUAL_ACCEPTANCE.md).
