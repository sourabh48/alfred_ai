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
installation. All **six lifecycle checks passed**: fresh install, installed
startup without system Python, upgrade retention, failed-shutdown protection,
normal uninstall retention, and removal of only the installation's own startup
entry. The final evidence is
`artifacts/ops/installer-lifecycle-final-20260927.json`, completed at 13:42 IST.
It combines the initial checks and focused continuation runs against the same
installer hash, rather than claiming a single uninterrupted run.

The first retention attempt took a database byte hash before the stopped
process finished SQLite's final WAL checkpoint. That assertion failed while
the uninstall guard correctly preserved the program. The verifier now waits
for the recorded processes to exit before taking that hash. The repeated
guard and retention checks passed. The original failed attempt is retained,
and the final report identifies which earlier checks it continues.

The final uninstall was interrupted during the previous session. After the
host restarted, its temporary startup entry and partially removed test copy
were recovered; the normal checkout startup and desktop shortcut were restored.
The test copy was stopped, and its uninstall completed. The ownership check was
then repeated with a fresh installation. An additional verifier fix waits for
the uninstaller's final log closure before examining the startup value: Inno's
original process can exit before its clone finishes the final callbacks. See
[Inno Setup's exit-code documentation](https://jrsoftware.org/ishelp/topic_uninstexitcodes.htm).

The helper also preserves an existing desktop shortcut during future runs:
Inno Setup's `/NOICONS` does not suppress this installer's desktop shortcut.
Five shortcut-restoration scenarios, two process-exit scenarios and three
uninstaller-completion scenarios passed separately. The helper now saves
`original-windows-state.json` and any original desktop shortcut in its test
folder before modifying Windows. Its temporary startup command explicitly
selects disposable data. External edits to a shortcut or startup entry are
preserved instead of overwritten.

The normal app is running from `dist/ALFRED`, using the existing `F:\ALFRED`
data folder, at `http://127.0.0.1:8000/` after the latest host restart. The root and desktop ALFRED shortcuts
use its embedded icon and discover the active port. The temporary test copy
is stopped and uninstalled; the original startup entry and shortcut were
verified restored in the final lifecycle report.

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
- All **16 observation/supervisor tests passed**. They simulate interruption,
  cancellation, schedule timing and business failures; they do not constitute
  an elapsed overnight pass. PowerShell parsing and live launch succeeded.
  A controlled verifier interruption preserved the previous report, started
  a distinct attempt and left the app's instance running unchanged. Duplicate
  supervisors exit with code four while preserving both startup entries.
- Read-only post-crash checks found both SQLite databases healthy, with zero
  foreign-key errors. The runtime health endpoint is also healthy.

Local evidence:

- `artifacts/final-20260927-backend.log`
- `artifacts/final-20260927-browser.log`
- `artifacts/browser-final-20260927/browser_regression_summary.json`
- `artifacts/final-20260927-system-check.log`
- `artifacts/final-20260927-migration-check.log`
- `artifacts/final-20260927-packaging.log`
- `artifacts/ops/release-hash-verification-20260927.json`
- `artifacts/ops/installer-shortcut-helper-20260927.json`
- `artifacts/ops/installer-process-exit-helper-20260927.json`
- `artifacts/ops/installer-clone-wait-helper-20260927.json`
- `artifacts/ops/installer-lifecycle-final-20260927.json`
- `artifacts/final-20260927-installer-lifecycle-confirmed.log`
- `artifacts/ops/observation-supervisor-tests-final-20260927.log`
- `artifacts/ops/observation-startup-20260927.json`
- `artifacts/ops/observation-restart-20260927.json`
- `artifacts/ops/post-crash-integrity-latest-20260927.json`

## Cleanup

The previous pass removed 5,482,411,212 bytes of superseded bundles, installers,
an interrupted installation and build caches; its exact record is
`artifacts/ops/cleanup-20260926.json`. Current release outputs are isolated in
the ignored `release` folder. Source, local data, private configuration, models,
backups and verification evidence are retained.

Automatic approval review rejected permanent deletion of old release binaries
and Python caches with "blocked by policy". A recoverable archive subsequently
completed the project cleanup: the old installer and ZIP (1,026,735,877 bytes)
were moved to `F:\ALFRED-retired\20260927\release`, and 385 generated source cache
files (3,931,514 bytes) were moved to its `source-caches` folder. These moves
removed 1,030,667,391 bytes from the project but did not free disk space.
Current caches can regenerate normally when Python runs. Historical manifests
and verification evidence remain in the project.

The exact archive records are `artifacts/ops/release-archive-20260927.json` and
`artifacts/ops/source-cache-archive-20260927.json`. The earlier denial record is
retained in `artifacts/ops/cleanup-blocked-20260927.json`.

## Scheduled observation and remaining acceptance

A ten-hour observation began at **00:13 IST on 27 September** but stopped after
1.07 hours. Its last healthy sample was at 01:17 IST, and Windows subsequently
restarted. Its retained report is `artifacts/ops/overnight-20260927.json`; the
stale-report detector records **interrupted**, not passed, in
`artifacts/ops/overnight-20260927-interrupted-status.json`.

A second observation started at **13:40 IST on 27 September** and stopped after
about 32 minutes. Its report, `artifacts/ops/overnight-20260927-restarted.json`,
is also interrupted. Windows recorded further host restarts; no cause is
established by these application checks.

A fresh supervised attempt began at **18:44 IST on 27 September**, with expected
completion around **09:00 IST on 28 September**. Its manifest is
`artifacts/ops/continuous-observation/current.json`. A separate current-user
startup entry, `ALFRED Verification`, is enabled; it launches after sign-in and
is removed after a completed pass. The normal app startup entry was verified
unchanged. The supervisor preserves interrupted attempts and starts a new full
window after a reboot or long sampling gap. It does not combine those windows
or automatically retry a completed failed business cycle. Its actual launch
after a future Windows sign-in remains to be observed.

The first live wrapper check exposed a missing PowerShell process exit code.
The wrapper now retains its child process handle before waiting and refuses to
report success if the exit code is missing. The repeated check passed. Its
first short attempt was deliberately interrupted to load the corrected wrapper
and verify recovery; that report is retained separately from the current run.

The helper leaves Windows power settings unchanged. The PC must remain awake
and the app running for a continuous result. See
[verification controls](NATIVE_WINDOWS.md#verification-across-windows-sign-ins).

Refresh runs at 05:30, 11:30, 17:30 and 23:30 IST; cleanup and nightly training
run at 07:45 and 08:30 IST. Training must still satisfy consent and eligibility
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
