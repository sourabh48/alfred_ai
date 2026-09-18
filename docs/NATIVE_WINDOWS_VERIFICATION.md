# Native Windows verification — 17 September 2026

## Result

ALFRED runs on Windows with **Waitress, Huey and SQLite**, without Docker,
WSL, Redis or a Celery service. A Windows x64 executable and installer were
built, and the executable passed an isolated end-to-end drill.

| Check | Result |
| --- | --- |
| Complete Django suite | 384 discovered: 378 passed, six browser tests intentionally deferred to the browser runner |
| Separate Chrome regression runner | All six workflows passed; no skips |
| Native source runtime | Signup, arithmetic, labels, pages, browser charts, private files, background execution, concurrent cache, retry, worker recovery, scheduled heartbeat, restart and restore passed |
| Packaged executable | All source-runtime checks plus native admin readiness and both bundled OCR subprocesses passed |
| Bundle privacy audit | 11,676 collected entries checked; no live database, uploads, trained models, local config or secrets included |
| Installer smoke test | Installed successfully, matched the verified executable, passed login/API checks, then uninstalled while preserving the test account database |
| Existing-account adoption | Pre-adoption snapshot verified; all 55 table contents and 8,284 existing file hashes unchanged after startup |

The native browser drill blocked the CDN and Google Fonts and still rendered
the correct totals and charts. It confirmed that Settings contains Remove My
Data, family connections use link codes, and the connected-members list is
separate from profile information. Screenshots were inspected for readability.

The sample account independently reconciled income **80,000**, living expenses
**30,000**, loan payments **10,000**, investments **5,000**, card payments
**2,000**, confirmed outflow **47,000**, and recorded cash left **33,000**.
Another **60,000** remained visibly excluded pending review.

Two thread workers completed 20 atomic shared-cache increments without losing
an update. An intentional transient task failure succeeded on the second
attempt. The supervisor replaced an exited worker. A task queued while stopped
completed after restart. Backup/restore preserved authenticated HTTP access,
the same financial totals and an owner-only document download.

## Artifacts on this computer

- Installer: `F:\ALFRED\dist\ALFRED-Setup.exe` (400,609,548 bytes).
- Portable folder: `F:\ALFRED\dist\ALFRED`; keep its `_internal` folder with
  `ALFRED.exe`.
- Source runtime report: `artifacts/ops/native_huey_verification.json`.
- Executable report: `artifacts/ops/native_exe_verification.json`.
- Package privacy report: `artifacts/ops/native_bundle_privacy.json`.
- Account preservation: `artifacts/ops/native_adoption_verification.json`.
- Installer install/uninstall: `artifacts/ops/native_installer_verification.json`.
- Full-suite log: `artifacts/native-full-regression.log`.
- Chrome proof: `artifacts/browser/browser_regression_summary.native-windows-chrome.json`.
- Executable screenshots: `artifacts/native-tests/1636ef8226/dashboard.png` and
  `settings.png` in the same folder.

The pre-adoption backup is:

```text
F:\ALFRED-backups\20260917T172206Z-before-native-launcher
```

It contains the database, retained uploads, models and configuration. The
generated native secret and previous-key fallback were also saved with it.
Verification accounts remain inside ignored, isolated test folders; no demo
account was added to the live account database.

SHA-256 of the installer:

```text
A5F0065CCBFCE09DD618314149F5A2E25AAB9A80F496E13253769DAB7E46917A
```

## Limits at the 17 September baseline

The [18 September continuation](NATIVE_HARDENING_VERIFICATION.md) supersedes
the reboot, interrupted-job and broader local-test limitations below. This
section preserves the scope of the original executable/installer evidence.

This proves operation on the current Windows x64 computer. A clean second-PC
installation, host reboot, LAN access and sustained overnight job outcomes
have not been tested. Queued work survives restart; abrupt termination of an
in-flight task is not guaranteed to replay. External integrations need their
own configured accounts and internet access. Real-data model accuracy and
unseen document-layout coverage remain separate requirements.

See [Native Windows](NATIVE_WINDOWS.md) for startup, shutdown, data locations,
backup and build commands. The installer is a local unsigned build.
