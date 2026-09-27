# Claude audit and completion prompt

Copy the prompt below into Claude Code with this repository open. It asks Claude
to inspect the current state first, because release and runtime evidence can
change after this document was written.

---

You are working on **Alfred - Finance Assistant**, a product of **Life on our
Trails**, in `F:\ALFRED` on Windows. Act as the engineer responsible for testing,
fixing confirmed defects, verifying configuration and completing the release.
Do the work, preserve existing user data, and report exactly what remains.

## Project context

- Repository: https://github.com/sourabh48/alfred_ai
- Default branch: `master`; recent work branch:
  `codex/native-runtime-hardening-20260918`. Inspect before switching branches.
- Website: https://sourabh48.github.io/alfred_ai/
- Illustrated guide: https://sourabh48.github.io/alfred_ai/guide/
- Product name: `Alfred - Finance Assistant`.
- Copyright: `Copyright (c) 2026 Life on our Trails. All rights reserved.`
- Project ID: `4bd97575-d520-4add-b0db-0afe0661156f`.
- Runtime: Django, Waitress, Huey, SQLite and diskcache. Native Windows is the
  supported local runtime. Docker/PostgreSQL/Redis/Celery is an optional route.
- A Windows tray icon belongs to the native supervisor. Closing the browser or
  launcher leaves it running; Stop ALFRED uses graceful shutdown.

Read `AGENTS.md`, `README.md`, `docs/DEVELOPMENT.md`, `docs/NATIVE_WINDOWS.md`,
`docs/WINDOWS_PACKAGE.md`, `docs/WINDOWS_TRAY_VERIFICATION_20260928.md`,
`docs/COMPLETION_AUDIT.md`, `docs/CONFIGURATION.md`, `docs/WEBSITE.md`,
`docs/OWNERSHIP.md`, and `docs/REPOSITORY.md` before changing behavior.

## First inspect and preserve the current state

1. Run `git status`, inspect recent commits/remotes and preserve uncommitted work.
   Do not reset, force-push or overwrite other changes.
2. Inspect active build/test processes and their logs before starting another
   build. A recent build uses `artifacts/run-tray-release-build.ps1`, logs to
   `artifacts/build-tray-release-error.log`, and writes
   `artifacts/tray-build-result.json` when finished. A folder or executable's
   existence alone does not establish a completed build.
3. Inspect `artifacts/native/runtime.json`, `artifacts/native/tray.json`,
   `artifacts/native/tray-preview.json` if present, and the health endpoint.
   A temporary tray preview helper was used while rebuilding. Verify that the
   final running package owns its own icon, then let the helper exit cleanly.
4. Inspect `artifacts/ops/continuous-observation/current.json` and the report it
   references. Do not interrupt a valid observation casually or count separate
   interrupted windows as a completed overnight observation.
5. Preserve `db.sqlite3`, `media/`, `ml_models/`, `config/native.env`,
   `config/local.env`, and the queue/cache under `artifacts/native/`. Back up the
   database, uploads, models and private configuration together before an upgrade.
   Never test destructive workflows against the owner's data.

## Configuration to verify

| Setting | Expected behavior |
| --- | --- |
| Existing Python | `F:\ALFRED\.venv\Scripts\python.exe`, Python 3.12; verify it before use and use PyCharm's environment tool if available |
| Source default data | `F:\ALFRED` |
| Installed/portable default data | `%LOCALAPPDATA%\ALFRED` |
| Explicit data selection | `--data-dir` overrides `ALFRED_DATA_DIR` |
| Native secret | Generated in the selected data folder's `config/native.env`; do not print, replace or commit it |
| Other local secrets | Untracked `config/local.env`; inspect key names without exposing values |
| Default URL | `http://127.0.0.1:8000/`; launcher can choose another available port |
| Native queue/backend | Huey and SQLite, selected by `alfred_native.py`; no Redis service required |
| Desktop icon | Normal startup must not set `ALFRED_NO_TRAY=1`; this variable is for deliberate headless checks |
| UI overrides | `config/alfred_ui.json`, then tracked example, then built-in defaults |
| Startup | Current-user `ALFRED` Run entry; verify executable and selected data path |
| Observation startup | Separate `ALFRED Verification` Run entry; do not confuse it with normal app startup |
| Public site | GitHub Pages: `master`, `/docs`, HTTPS, `.nojekyll`; documentation only |

`config/local.env.example` describes the optional container profile. Do not
blindly copy its PostgreSQL/Redis settings over the native configuration.
Keep loopback as the default. LAN access requires deliberate bind, allowed-host,
CSRF/origin and firewall configuration plus a real second-device test. Do not
expose private application routes to the public internet.

## Run tests and fix confirmed defects

Use the configured interpreter, fresh synthetic data and the repository's
verification runners. Capture exit codes, counts, reports and relevant errors.
Do not call skipped tests passes. Do not invent results or rely on old reports
as proof for a changed binary.

Backend and focused checks, in PowerShell:

```powershell
Set-Location F:\ALFRED
$env:ALFRED_LOCAL_RUNTIME = 'true'
$env:ALFRED_AUTO_TRAIN_ON_STARTUP = 'false'
$env:ALFRED_RUN_BROWSER_TESTS = 'false'
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test --noinput
```

Browser workflows:

```powershell
.\.venv\Scripts\python.exe scripts/run_browser_regressions.py --browser Chrome --require-browser --proof-label claude-audit
```

Native source integration (creates its own disposable data folder):

```powershell
.\.venv\Scripts\python.exe scripts/verify_native_runtime.py --port 8053 --browser --extended
```

Inspect `scripts/verify_native_extended.py` and the native guide for the required
pinned axe-core asset. Do not silently skip browser/accessibility checks if a
dependency is missing.

For each confirmed failure: reproduce it, identify the cause, make a focused
fix, add a meaningful regression test when warranted, and rerun the affected
checks. Rebuild and repeat packaged verification if packaged runtime code changes.

Review these behaviors in particular:

- Sign-up/login/logout, session timeout and access control.
- Income, expenses, budgets, loans and investment totals, using independently
  calculated fixture totals; cross-user and family-consent isolation.
- Document upload, extraction, uncertain-result review, correction, retry and
  retention. Use synthetic fixtures rather than publishing private documents.
- Worker execution, acknowledged job recovery, retries, scheduler heartbeat,
  cache invalidation, queued work after restart, backup and restore.
- Launcher progress, brand name and icon; one tray icon per running instance;
  actual selected browser port; offline guide; open-data action; graceful stop;
  removal of the tray icon after shutdown and recovery after Explorer restart.
- Desktop and mobile layout, keyboard navigation, labels, focus and contrast.
  Distinguish automated accessibility checks from human screen-reader testing.

## Complete and verify the Windows release

First inspect whether `v1.0.1-preview.1` has already been published and whether
the local bundle matches its manifest. Keep existing published releases intact.
Use a new output directory for any new release; never overwrite signed/verified
artifacts while reporting their old hashes.

Current build locations to inspect:

- `artifacts/releases/20260928-tray/ALFRED`
- `artifacts/releases/20260928-tray/distributables`
- `dist/ALFRED` — the checkout launcher target
- `release/ALFRED-Setup.exe` — the convenient local installer location
- Inno Setup compiler: `F:\ALFRED-tools\InnoSetup\ISCC.exe`

If a fresh build is needed, substitute a fresh folder for `next-build` below:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller packaging/ALFRED.spec --noconfirm --distpath artifacts/releases/next-build --workpath build/next-build
.\.venv\Scripts\python.exe scripts/verify_packaged_launcher.py --bundle artifacts/releases/next-build/ALFRED
.\.venv\Scripts\python.exe scripts/verify_native_runtime.py --executable artifacts/releases/next-build/ALFRED/ALFRED.exe --launcher "artifacts/releases/next-build/ALFRED/ALFRED Launcher.exe" --port 8054 --browser --extended --load-users 24 --load-writes 20 --load-seconds 120
.\.venv\Scripts\python.exe scripts/package_windows_release.py --bundle artifacts/releases/next-build/ALFRED --output artifacts/releases/next-build/distributables --iscc F:/ALFRED-tools/InnoSetup/ISCC.exe
.\.venv\Scripts\python.exe scripts/verify_windows_installer.py --installer artifacts/releases/next-build/distributables/ALFRED-Setup.exe --report artifacts/ops/next-installer-lifecycle.json
```

The installer verifier requires no existing registered ALFRED installation.
Use an isolated Windows user/VM if a real installation is registered. Its
disposable install verifies upgrade retention, shutdown protection, uninstall
and restoration of the original desktop shortcut/startup entry. Check any
recovery file after an interrupted run before making further changes.

Validate installer/ZIP contents, CRCs, hashes, offline guide, project identity
and copyright notice. Ensure no database, private uploads, trained personal
models, secrets or development-machine acceptance manifest enter public assets.
The public identity and hashes are attribution/change detection, not copy
protection or digital signatures. Do not add hidden telemetry or destructive
anti-tamper behavior. Windows code signing remains separately configurable.

If updating the active checkout, gracefully stop its exact selected instance,
wait for processes to exit, preserve the old program folder for rollback, copy
the verified bundle and start with `--data-dir F:\ALFRED`. Confirm health and
Windows tray registration. Preserve data and normal startup settings. If the
observation must restart for the upgrade, retain the cancelled report and start
a fresh full window; do not claim that it has already passed.

## Website, SEO, copyright and cleanup

- Confirm the public homepage and `/guide/` return HTTP 200 with current content,
  images, working release downloads, canonical URLs and a valid sitemap.
- Preserve the exact company/product spelling supplied above.
- Validate title/description, SoftwareApplication JSON-LD and mobile layouts.
  Do not invent ratings, testimonials or guaranteed Google placement.
- Search Console ownership verification and sitemap submission need the owner's
  Google account/token. Report that dependency; never fabricate verification.
- `docs/REPOSITORY.md` records 11 removed obsolete files. Keep required package
  initializers, migrations, active training code and historical evidence. Remove
  other code only after reference analysis and appropriate regression checks.
- Move old generated packages outside the active workspace only after verifying
  exact absolute paths and rollback needs. Never broadly delete user data,
  private configuration or useful evidence. Do not add cloud application hosting.

## Evidence and final delivery

Earlier evidence includes 407 backend checks and 9 Chrome workflows on the
previous release; 23 packaged checks and 24-user load on an earlier binary;
and 16 focused tray/native/launcher tests plus 18 source native checks during
the tray update. Reconcile current reports and timestamps before quoting counts.
The 28 September report is the starting point for current release evidence.

Finish with:

1. **Working now:** functions actually exercised and the exact build/commit.
2. **Bugs fixed:** trigger, cause, changed files and verification result.
3. **Configuration:** what is configured, what you changed, and missing owner
   credentials/choices, without printing secrets.
4. **Test results:** commands, passed/failed/skipped counts and report paths.
5. **Still left:** each item with its priority, reason and acceptance condition.
6. **Installer/website/Git:** real links, release version, checksums and pushed
   commit. Verify links after publication and keep the README consistent.

Keep the clean-second-PC/reboot check, continuous scheduled outcomes, human
accessibility and independently reviewed real-data/model accuracy open until
their evidence exists. Model fitting or a process restart does not close those
checks. Fix what you can independently; clearly identify genuine external
blockers. Do not declare the product fully complete while required acceptance
work is still pending.
