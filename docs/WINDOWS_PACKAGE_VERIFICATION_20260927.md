# Windows release verification - 27 September 2026

The current local/LAN release is in [release](../release), with the
[installer](../release/ALFRED-Setup.exe),
[portable ZIP](../release/ALFRED-Windows-x64.zip),
[checksums](../release/SHA256SUMS.txt) and
[manifest](../release/release-manifest.json). The installer and both launchers
use the ALFRED icon. The existing checkout remains available through `ALFRED.lnk`
and `Start ALFRED.cmd`.

## Installer and uninstaller

The installed Start menu includes **Uninstall ALFRED**, and the program folder
includes **Uninstall ALFRED.cmd**. Windows Settings > Apps also lists ALFRED.
Setup generates `unins000.exe` and its installation record during installation;
the uninstaller belongs with those installed files.

Upgrade and uninstall require a successful graceful shutdown before removing
application files. A failed stop cancels the operation. Uninstall preserves
saved accounts, documents, settings and models. It removes the Windows sign-in
entry only when its quoted executable path belongs to that installation.

The reproducible lifecycle verifier is `scripts/verify_windows_installer.py`.
It uses synthetic data in an isolated folder, without system Python in the
installed process's PATH, and refuses to overwrite an existing registered
installation. Lifecycle verification is in progress; see
`artifacts/final-20260927-installer-lifecycle.log` for the current run.

## Automated verification

- Django discovered 416 tests: **407 passed and nine browser cases were skipped**
  in the backend run, which completed in 523.798 seconds with exit zero.
- The separate Chrome run passed **all nine browser cases**, with zero skips,
  in 67.875 seconds; exit zero.
- Django system checks passed, and `makemigrations --check --dry-run` detected
  no changes. These checks used offline test mode.
- Inno Setup compiled the installer successfully. Packaging checked **12,608
  files**, found no prohibited private runtime paths, and verified the ZIP CRCs.
- The native executable hashes match the
  [26 September runtime verification](WINDOWS_PACKAGE_VERIFICATION_20260926.md),
  which passed 23 packaged checks, 24-user concurrency, bundled OCR, private-file
  access, worker recovery, backup/restore, mobile layouts and automated
  accessibility. Those runtime checks were not rerun for the installer-only
  changes on 27 September.

Local evidence:

- `artifacts/final-20260927-backend.log`
- `artifacts/final-20260927-browser.log`
- `artifacts/browser-final-20260927/browser_regression_summary.json`
- `artifacts/final-20260927-system-check.log`
- `artifacts/final-20260927-migration-check.log`
- `artifacts/final-20260927-packaging.log`

## Scheduled observation and remaining acceptance

A ten-hour observation began at **00:13 IST on 27 September**, using the existing
local app and its actual schedules. Its report is
`artifacts/ops/overnight-20260927.json`; completion is expected around
**10:13 IST** if uninterrupted. The observer temporarily prevents automatic
sleep. It does not restart Windows or restart the app.

The refresh, cleanup and nightly-training schedules fall at approximately
05:30, 07:45 and 08:30 IST. Training must still satisfy consent and eligibility
gates. Starting the observer is not a passing overnight result; inspect the
report's final `passed`, `status`, job outcomes and sampling gaps.

A read-only data audit is retained in
`artifacts/ops/real_data_validation-20260927.json`. It covers eight model states
and eight document families. Real-world accuracy is not established: models
still have sample-size, holdout-quality, confidence, missing-artifact or
proxy-target limitations. No synthetic data was added to the real database to
make those gates pass.

The following acceptance remains open: a separate clean Windows PC and its
reboot, actual Windows sign-in, a completed overnight observation, human
screen-reader checks, and independently reviewed real documents and outcomes.
The release includes the separate-PC acceptance kit. Follow
[Windows acceptance](WINDOWS_ACCEPTANCE.md) and
[human acceptance](MANUAL_ACCEPTANCE.md). Optional LAN and live-account
integrations require their own environment and credentials.
