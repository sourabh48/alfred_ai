# Travel preview release continuation — 29 September 2026

The interrupted **1.1.0-preview.1** release was resumed from commit
`3bd5bbb9a04c7096b7697af3917f43fd6d5f4c73`. ALFRED remains a local/LAN application.
No cloud runtime, new provider credentials or hosted language model was added.

## Completed build and test evidence

The 28 September build and verification processes had already finished
successfully. Their reports were inspected before continuing; these checks were
not rerun or represented as new 29 September test executions.

| Check | Recorded result | Local evidence |
| --- | --- | --- |
| Backend regression suite | 477 discovered: 466 passed, 11 browser cases skipped | `artifacts/travel-regression-final-error.log` |
| Chrome workflows | 11 passed, zero skipped | `artifacts/browser-travel-all/browser_regression_summary.travel-release.json` |
| Focused travel checks | 42 passed | `artifacts/travel-final-tests-error.log` |
| Packaged travel runtime | Live weather research, targeted edits, saved context and queued research after restart passed | `artifacts/ops/travel-packaged-verification.json` |
| Packaged launcher | GUI launch, tray registration/removal and bundled guide passed without system Python | `artifacts/ops/travel-launcher-verification.json` |
| Extended packaged runtime | 23 checks passed; 24 users, 480 writes and zero load errors | `artifacts/ops/travel-native-extended-verification.json` |
| Responsive and automated accessibility | Seven pages at four widths; seven pages at two widths with zero serious/critical violations | Same extended-runtime report |

The extended report is run `b22de4c341`, using the travel candidate under
`artifacts/releases/20260928-travel/ALFRED`. Its responsive/accessibility page
set does not include the travel planner. Travel viewport workflows are covered
by the separate Chrome suite. Automated audits do not establish human
screen-reader acceptance.

## Packaging

The candidate's offline installation guide was refreshed from the committed
guide before packaging. Its application executables were unchanged.

`scripts/package_windows_release.py` completed on 29 September using the
configured Python 3.12.2 environment and Inno Setup. It checked **12,630 files**,
found **zero private runtime paths**, compiled the installer, verified every ZIP
entry's CRC, and generated a release manifest and SHA-256 checksums. The log is
`artifacts/travel-packaging-20260929.log`.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `ALFRED-Setup.exe` | 484845667 | `66a2f8ba5e2afdde144ba7a8eb6e57062fc5a1cafab5d440a8bb150949f31363` |
| `ALFRED-Windows-x64.zip` | 542472307 | `cc6a72150a143864d930e8d803bfc1246ef74c655ba00278542208db85e79a29` |
| `ALFRED.exe` | 82423013 | `2c2efe348e4c811beb3602a75b994cfab568059eb228d61e02841d4e04f737d9` |
| `ALFRED Launcher.exe` | 82417893 | `83e512535bfe7db6e7e2205714696c9be338b753245fd558560772cf04c4cdf7` |

The installer remains unsigned. Hashes identify these exact files; they are not
digital signatures. The machine-bound acceptance kit is separate from public
release assets.

## Local upgrade and recovery

The prepared upgrade script completed successfully on 29 September. Windows
registration now reports **1.1.0**, and the uninstaller remains present. The
verified bundle was copied to `dist/ALFRED` and its distributables to `release`.

Before installation and migration, both stopped data folders were backed up
together with uploads, models, configuration and durable queue files. The backup
database hashes matched their originals. The installer left both databases
unchanged before migration startup. Old program folders, distributables and data
backups remain under `F:\ALFRED-retired\20260928-before-travel-1.1.0`.

Read-only post-upgrade verification passed for both data folders:

- SQLite integrity was `ok`, and mobility migration `0009` was applied.
- Existing fields and row counts in the user, expense, travel-plan, trip-log and
  trip-photo tables matched the stopped backups.
- HTTP health returned 200, and served travel-planner JavaScript matched source.
- Each runtime reported its own visible, running tray icon.

The checkout uses `http://127.0.0.1:8000/` with data in `F:\ALFRED`. The separately
installed copy uses port 8001 with data in `%LOCALAPPDATA%\ALFRED`. Their accounts
were not merged. These ports describe this startup, not permanently reserved ports.

Evidence: `artifacts/ops/travel-upgrade-backups.json`,
`artifacts/ops/travel-installed-upgrade.json`,
`artifacts/ops/travel-upgrade-verification-20260929.json` and
`artifacts/travel-upgrade-20260929.log`.

All six promoted artifact checks matched the candidate manifest: the installer,
ZIP, and both executables in each program folder. The results are in
`artifacts/ops/travel-release-hashes-20260929.json`.

The normal ALFRED startup entry was unchanged. The pre-existing verification
startup entry was restored after the upgrade. Its earlier attempt was interrupted;
a fresh observation started against the upgraded checkout. This does **not**
close overnight acceptance. See `artifacts/ops/continuous-observation/current.json`
for the current attempt, and `artifacts/ops/travel-startup-restored-20260929.json`
for startup preservation evidence.

## Remaining acceptance

Full installer/uninstaller lifecycle testing for this release requires an
isolated Windows user or machine: the current account has a real registered
installation. Do not uninstall it to satisfy an isolated-test precondition.
Clean second-PC installation/reboot, a completed continuous observation of
scheduled outcomes, human screen-reader checks and independently reviewed
real-data/model accuracy remain open.

The initial local upgrade finished before GitHub publication. Public release
publication and remote link/download verification are tracked separately from
the local package and installation checks above.
