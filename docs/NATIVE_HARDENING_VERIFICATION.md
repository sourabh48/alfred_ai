# Native Windows hardening — 18 September 2026

The application remains a local/LAN project. The tested Windows runtime uses
Waitress, an acknowledged Huey SQLite queue and a shared disk cache.

## Verified locally

| Area | Result and scope |
| --- | --- |
| Backend regressions | Fresh Windows CI: 400 discovered, 394 passed, six browser tests intentionally separate; 415.964 seconds. Local full suite: 389 passed plus the five later layout fixtures |
| Browser workflows and CI | All six local Chrome workflows and all six fresh Linux CI Chrome workflows passed with zero skips; Windows native CI also passed all 21 integration checks |
| Focused recovery/document checks | All 21 passed, including five new generated-layout tests |
| Concurrent users | 12 simultaneous users, 60 saved transactions, correct per-user totals and ownership; 72 timed requests, zero errors, p95 1.375 seconds in the recorded source run |
| Responsive pages | Dashboard, Expenses, Settings, Documents and Loans at 360, 390, 768 and 1440 CSS pixels |
| Automated accessibility | axe-core 4.13.0 WCAG A/AA checks on those five pages at 390 and 1440 pixels; no serious/critical findings after fixes; keyboard skip link reaches main content |
| Interrupted worker | A diagnostic job was executing when its worker was terminated; the supervisor recovered it and the second attempt completed |
| Recovery boundaries | Atomic queue claims, retry/schedule transfers, completed-job acknowledgements, three-replay limit, retained unknown/import jobs and explicit reviewed retry tested against real SQLite |
| Host reboot retention | Windows booted at 03:33:53 IST. Pre/post-boot manifests match all 13 checked financial tables and 8,273 uploads; all 13 accounts remain. Native relaunch passed on port 8001 |
| Source HTTP and restore | Sign-up, financial arithmetic, private files, worker retry, process restart and restored signed-in account passed in isolated synthetic data |
| Packaged executable | All 22 checks passed, including bundled document/statement OCR and restoring a pending job from the queue backup; run `46d50ecb53` |
| Installer | Installed executable hash matched the verified bundle; synthetic signup and 42,000 income minus 1,200 expense = 40,800 verified through HTTP; uninstall removed the test program, preserved the data hash, and left the live app healthy |

The accessibility changes connect loan labels to controls, name consolidation
checkboxes, make scrollable transaction/review regions keyboard-accessible, and
add a skip-to-main link and visible focus indication. Automated scanning is not
a complete screen-reader or manual accessibility certification.

Port 8000 was occupied by a separately started Django development server.
The native launcher now binds exclusively and chooses a free port. Shutdown
uses OS locks so a reused PID after reboot does not imply ALFRED is still alive.

The new claim mechanism retains unfinished work across process death. Only
repeatable maintenance tasks replay automatically. Imports and training need
review because application updates can be partially committed before a crash.
This does not claim exactly-once execution or a physical power-cut test.

## Evidence

- `artifacts/native-hardening-regression.log`
- `artifacts/native-hardening-focused.log`
- `artifacts/ops/native_huey_extended_verification.json` (source run `e128ee1df3`)
- `artifacts/native-tests/e128ee1df3/mobile-accessibility.json` and screenshots
- `artifacts/ops/native_host_reboot_verification.json`
- `artifacts/ops/real_data_validation.json`
- `artifacts/ops/native_exe_extended_verification.json` (packaged run `46d50ecb53`)
- `artifacts/ops/native_hardening_installer_verification.json`
- `artifacts/ops/native_hardening_adoption.json`
- [Passing fresh CI run](https://github.com/sourabh48/alfred_ai/actions/runs/35332849042), commit `7c0d271`; both Windows native and Linux Chrome passed

The first Windows CI run exposed a test that assumed LF line endings in static
HTTP responses. The test now normalizes CRLF before comparing text; the fresh
run above passed the complete suite. CI artifacts are retained locally under
`artifacts/ci/35332849042`.

Latest private backup before the native restart:
`F:\ALFRED-backups\20260918T100600Z-before-native-launcher`.
It includes the application database, media, models, configuration and queue.
After adopting the hardened executable, all 55 application table contents and
all 8,361 media/model/config file hashes matched the pre-launch snapshot.
Queue-inclusive synthetic restore passed through the packaged application.

## Rebuilt release

`dist/ALFRED-Setup.exe`: 400,621,656 bytes. SHA-256:

```text
831D9A27E920C41FBC2F7D8F5B9ED706D03A22327F662AB32BD314247228D640
```

Portable executable SHA-256:

```text
03C4EB2123BA8DD923DA580E02175ADD463A5C7CE477BE9530DC8C8782F1213F
```

The privacy scan checked 11,676 bundled files and found no private database,
upload, model-registry or environment-file paths. The prior installer is retained
under `artifacts/releases/20260917`. The clean-PC PowerShell kit passed its Fresh
phase locally; its Reboot phase correctly refused an unchanged Windows boot time.
This validates the kit, not a separate-PC installation.

## Data and model validation

The audit reads SQLite without starting training or changing records. It found
13 accounts, nine with ML training consent, eight model states and eight document
families. Existing records include small/demo datasets and do not establish
independent ground truth. No model clears all recorded validation checks.
The expense model's recorded quality is poor; several other scores measure
proxy targets or very small holdouts. Their readiness gates remain in place.

Five new generated cases passed actual extraction: rotated PDF, two-column PDF
with repeated headers, landscape table with wrapped text, DOCX table/split runs,
and nested HTML tables/entities. Known invoice/reference/date fields were
checked. These are synthetic layout regressions, not real-document accuracy.

## Cleanup

- Retired `fix_structure.py`, whose outdated expected-file list could move valid
  project files, and the checked-in 29 MB Python installer. Recoverable local
  copies are under `artifacts/retired-20260918`.
- Removed generated model-registry JSON from Git tracking and added an ignore
  rule. The actual registry and trained models remain on disk.
- Kept current releases, historical test evidence, virtual environment, accounts,
  uploads, runtime queue/cache, configuration and private backups.

## Still pending

1. A clean, separate Windows PC. The [acceptance kit](WINDOWS_ACCEPTANCE.md)
   supports fresh-install and real-reboot phases without Python or Docker.
2. Sustained scheduled observation. The first attempt stopped after 20 minutes
   and Windows subsequently rebooted; it did not pass. A new 18-hour observation
   started at 16:50 IST on 18 September and runs until 10:50 IST on 19 September,
   spanning the next daily cleanup and training. Automatic sleep is suppressed
   only while the observer is running; shutdown/reboot interrupts it. The report is
   `artifacts/ops/native_overnight_verification.json`; `observing` is not a pass.
   Cleanup and eligible training are due at 07:45 and 08:30 IST. Training can
   legitimately skip ineligible models; its recorded outcome must be reviewed.
3. Independently checked real documents/model outcomes, broader screen-reader
   testing and higher-volume usage beyond the stated local test.

LAN access and live email/bureau integrations remain optional and unverified.
