# Travel continuation verification — 30 September 2026

This records validation of development changes before committing on codex/native-runtime-hardening-20260918,
based on e68e8fd1c49085ed714b315d7982b77a7554b334. Published v1.1.0-preview.1
is unchanged and predates this work.

Later source changes and validation: [T07 monetary fixes, 1 October](TRAVEL_T07_VERIFICATION_20261001.md).
The frozen candidate and full-suite result in this report predate T07.

## Recovery and changes

Repository recovery found migration 0012, secure web research, dynamic discovery
and frontend panels already implemented. The prior browser run had finished with
1 failure and 1 error. It compared a pre-research allowance with the completed
hotel result and used shared in-memory SQLite across live-server threads. The
browser now waits for Ready and uses the existing isolated browser runner. A new
backend regression verifies scoped day edits and their survival across rechecks.

The staff provider panel now lists all weather/flight/web/discovery categories
without exposing keys. Maps preserve the user's view on unchanged polling data,
label disabled tiles and fit route geometry without an animated marker flash.
Browser fixtures verify route lines, external links, responsive views and staff
configuration. Upgrade preservation now runs through migration 0012.

Source/native startup reads config/local.env under the selected data directory.
Process variables win over local values, followed by legacy .env. Native signing
secrets remain authoritative in config/native.env. Native backend selection occurs
before importing the configuration helper. No operator secret file was edited.

## Isolated validation environment

Use the PyCharm-configured F:\ALFRED\.venv\Scripts\python.exe after checking
get_python_environment(filePath="manage.py"). The previously unused checkout
local.env selected PostgreSQL/Redis hosts that were unavailable. Tests select
isolated configuration without changing those operator settings:

```powershell
$env:ALFRED_LOCAL_RUNTIME='true'
$env:ALFRED_AUTO_TRAIN_ON_STARTUP='false'
$env:ALFRED_DATA_DIR='F:\ALFRED\artifacts\travel-validation-config-20260930'
$env:DATABASE_URL='sqlite:///:memory:'
$env:CACHE_BACKEND='django.core.cache.backends.locmem.LocMemCache'
$env:CACHE_LOCATION='alfred-validation'
```

Native verification creates its own disposable data folder and selects local
SQLite/disk cache/Huey. No real user database was migrated or replaced.

## Completed validation

All commands below use the configured interpreter. Test counts exclude skips.

| Command | Passed | Failed/errors | Skipped | Duration |
| --- | ---: | ---: | ---: | ---: |
| manage.py test tests.test_travel_planner.TravelPlannerTests.test_day_edit_after_hotel_research_survives_recheck tests.test_travel_planner.TravelPlannerTests.test_relax_one_day_retains_other_days tests.test_travel_continuation tests.test_travel_web tests.test_travel_http --noinput --verbosity 1 | 25 | 0 | 0 | 3.757 s |
| manage.py test tests.test_travel_continuation tests.test_travel_planner.TravelMigrationTests --noinput --verbosity 1 | 9 | 0 | 0 | 2.599 s |
| manage.py test tests.test_local_config tests.test_native_runtime tests.test_platform_hardening.SettingsHardeningTests --noinput --verbosity 1 | 11 | 0 | 0 | 0.599 s |
| manage.py test tests.test_production_readiness_contracts tests.test_local_config tests.test_native_runtime tests.test_platform_hardening.SettingsHardeningTests --noinput --verbosity 1 | 23 | 0 | 0 | 2.964 s |
| scripts/run_browser_regressions.py --browser Chrome --require-browser --artifact-dir artifacts/browser-all-isolated-20260930 --proof-label all-isolated-20260930 | 12 | 0 | 0 | 101.572 s |
| scripts/run_browser_regressions.py tests.test_travel_planner_browser --browser Chrome --require-browser --artifact-dir artifacts/browser-travel-label-20260930 --proof-label travel-label-20260930 | 3 | 0 | 0 | 35.365 s |

Browser runner wall time: 111.016 s. It covers document review, user data and three
travel workflows, including 390/768px layouts. Desktop route and mobile screenshots
were inspected. Proof: artifacts/browser-all-isolated-20260930/ and
artifacts/travel-resume-isolated-browser-20260930.log.

manage.py makemigrations --check --dry-run reports no changes. Read-only checkout
status: 0001–0009 applied, 0010–0012 pending. All three new migrations apply in test
and disposable native databases. Python syntax compilation, both planner JS syntax
checks and git diff --check passed.

scripts/verify_travel_runtime.py --report artifacts/ops/travel-runtime-isolated-20260930.json
passed using the source native runtime with providers disabled. It verified
startup/migrations, 0.078-second handoff, saving, scoped edits and queued work/context
through restart. Zero sources were checked; weather stayed UNKNOWN. This proves
offline recovery, not live inventory.

## Full backend validation

The first completed full run (manage.py test --noinput --verbosity 2) ran 529 tests:
516 passed, 1 failed, 12 browser cases skipped, in 631.591 s. The production-settings
subprocess inherited the runner's SQLite DATABASE_URL and correctly rejected it.
Both DB_ENGINE fixtures now explicitly clear DATABASE_URL. Production guards are
unchanged. The 23-test configuration/production rerun above passed. The final full
rerun was interrupted before summary: artifacts/travel-continuation-backend-final-20260930.log.
A durable rerun started 2026-10-01 03:04 local: artifacts/travel-backend-20261001.log;
Completion: 517 passed, 0 failed, 12 skipped, 562.575 s; exit 0, 588.422 s wall.
Command: F:\ALFRED\.venv\Scripts\python.exe manage.py test --noinput --verbosity 2.
Status/duration evidence: artifacts/travel-backend-20261001-result.json.
All skipped Selenium cases passed in the separate Chrome run. Current backend
and test changes are validated; earlier interrupted logs remain separate.
Initial full-run evidence: artifacts/travel-continuation-backend-20260930.log.

## Windows candidate

Command: python -m PyInstaller packaging/ALFRED.spec --noconfirm
--distpath artifacts/travel-candidate-20260930/dist
--workpath artifacts/travel-candidate-20260930/build.
Exit 0, 577.819 s build log clock; artifacts/travel-continuation-build-20260930.log.
The earlier interrupted build is retained separately and is not success evidence.

scripts.package_windows_release.inspect_bundle passed current asset hashes and
private-runtime-file exclusions for all 12,637 files. Evidence:
artifacts/ops/travel-candidate-inspection-20260930.json.
ALFRED.exe SHA256: 1d3174cf8c9a3ad80063aacd624a8f355537d780c4f07eca086c6ac9c20b9c0c.
ALFRED Launcher.exe SHA256: ec6d39e87c06e48c99cd5b98a33d7a245e0483b763c0ef6117e234b636e5deb8.

Command: scripts/verify_travel_runtime.py
--executable artifacts/travel-candidate-20260930/dist/ALFRED/ALFRED.exe
--report artifacts/ops/travel-runtime-frozen-20260930.json.
Passed: startup/migrations, 0.078 s handoff, saving, scoped edits, queued research
and saved context through restart. Uses disposable data and disabled providers.
Zero sources checked, weather UNKNOWN. No live inventory or installed-runtime claim.
Source and frozen runtime checks agree. No installer, archive or release promoted.

Native probes explicitly disabled providers in the parent environment before
running either command:

```powershell
$env:ALFRED_AUTO_TRAIN_ON_STARTUP='false'
$env:TRAVEL_WEB_ENABLED='false'
$env:TRAVEL_USE_MODE=''
$env:TRAVEL_OPEN_METEO_API_KEY=''
$env:TRAVEL_ORS_API_KEY=''
$env:TRAVEL_OVERPASS_URL=''
$env:TRAVEL_DUFFEL_API_KEY=''
$env:TRAVEL_DUFFEL_ALLOW_PAID_SEARCH='false'
$env:TRAVEL_BRAVE_API_KEY=''
$env:TRAVEL_BRAVE_ALLOW_PAID_SEARCH='false'
$env:TRAVEL_SEARXNG_URL=''
```


The latest requested search-link wording is implemented and verified by the
3-test travel browser rerun above. `manage.py check` reports no issues.
The expanded travel phase numbering places this completed automated checkpoint in PHASE 14; prior
TRAVEL 10 frontend/regression corresponds to expanded phases 12–14. Phase 13
optimization and Decimal price handling retain their outstanding backlog entries.

Earlier attempts are retained: recovered browser 1 failure/1 error; expanded staff
fixture 1 error (missing budget, now corrected); post-loader database/cache setup
failures; initial native failure due to early Celery import, fixed by startup
ordering. Interrupted backend attempts are not counted as passing suites.

## Remaining acceptance

Provider accounts/licensing and live inventory remain unavailable without operator
configuration. Source startup using existing local.env needs valid local DB/cache
settings. Release preparation, remaining Decimal itinerary-edit/filter work, targeted
enrichment and telemetry retention remain. money.py, core cost/bike formulas and
decimal-string provider prices were already implemented; preserve them. Clean second-PC,
LAN, manual screen-reader and real-data ML acceptance remain in
[completion audit](COMPLETION_AUDIT.md). No release was published or installed.
