# Travel planner continuation audit — 2026-09-30

Repository: sourabh48/alfred_ai, branch codex/native-runtime-hardening-20260918,
Validation base e68e8fd1c49085ed714b315d7982b77a7554b334; implementation committed
as 46113c968b1e6d85d4c0d05cbcfa0270174a5a56 after runtime commit a610ab3.
User authorized Git delivery on 2026-10-01. Published v1.1.0-preview.1 predates
this development. No new release/installer promoted.

## Recovered stopping point

The prior checkpoint was stale. Shared secure HTTP, dynamic Wikivoyage discovery,
web-search adapters, external link builders, intent/research integration, Leaflet
and frontend research panels had landed. Migration 0012 bus mode also existed.
The previous browser run finished with 1 failure and 1 error; it was not pending.

The day-edit failure compared a pre-research UI snapshot with completed hotel
research. Waiting for Ready fixed it; backend regression confirms other days and
edited budgets survive later rechecks. Shared in-memory SQLite caused cross-thread
browser errors. The existing scripts/run_browser_regressions.py selects isolated
file SQLite via alfred_ai.browser_test_settings and passes all 12 workflows.

The latest user sequence places resumed work in TRAVEL PHASE 14, corresponding to
the old TRAVEL 10 frontend/regression boundary. Phases 12–14 validation was resumed,
not restarted. Earlier engineering audit/backlog names supplied by the user are
absent; docs/COMPLETION_AUDIT.md retains main-project acceptance limitations.

## Preserved architecture and privacy

Existing planning sessions/messages, revisioned research outbox, leases and
supersession remain. Owner-scoped plans, vehicles, destination history, logs and
photos remain isolated. New providers reuse VerifiedExternalInsight cache and
retain original evidence timestamps after a failed refresh.

Shared HTTPS pins validated public IPs with TLS hostname verification, rejects
redirects/unsafe endpoints and bounds response size/type/time. Public research
uses validated place/date/mode/category slots. Search leads never become verified
rules or availability. No booking, reservation, payment or cloud runtime added.
Generated search links say: 'Search link — open to check latest availability.'

## Changes and completed verification

- Staff usage/configuration exposes every implemented provider category and hides
  credentials. Maps preserve the current view for unchanged polling geometry,
  label disabled tiles and fit without an animated marker flash. Browser fixtures
  check route LineStrings, marker size, safe external links and responsive views.
- Focused backend: 25 passed, 0 failed, 0 skipped, 3.757 s. Provider configuration
  and upgrade preservation through 0012: 9 passed, 0 failed, 0 skipped, 2.599 s.
- Local configuration/native boundary: 11 passed, 0 failed, 0 skipped, 0.599 s.
  Latest production/configuration group: 23 passed, 0 failed, 0 skipped, 2.964 s.
- Full Chrome workflows: 12 passed, 0 failed, 0 skipped, 101.572 s. Latest label-only
  travel rerun: 3 passed, 0 failed, 0 skipped, 35.365 s. Desktop route and 390px
  mobile screenshots inspected. Other document/user-data workflows also covered.
- Django check: no issues. Migration drift check: no changes. Python/JS syntax
  checks and git diff --check passed.
- Source-native and frozen-native offline runtime probes both passed using separate
  disposable storage. Each verified migrations, 0.078 s request handoff, saving,
  scoped day edits, queued research and saved context through restart. Providers
  disabled: zero checked sources, weather UNKNOWN. This is offline recovery proof.
- Separate PyInstaller candidate build passed in 577.819 s (build log clock).
  inspect_bundle passed all current asset hashes and private-runtime exclusions
  for 12,637 files. Output: artifacts/travel-candidate-20260930/dist/ALFRED.
  Reports: artifacts/ops/travel-candidate-inspection-20260930.json and
  artifacts/ops/travel-runtime-frozen-20260930.json. No installer/release promotion.

Exact commands and evidence are in docs/TRAVEL_CONTINUATION_VERIFICATION_20260930.md
and CODEX_CONTINUATION_STATE.md. Earlier interrupted runs are not passing evidence.
The first completed backend run had 516 passed, 1 failed, 12 skipped in 631.591 s.
Its only failure inherited DATABASE_URL=sqlite:///:memory: in a subprocess testing
PostgreSQL configuration. Both fixtures now clear DATABASE_URL; production guards
unchanged. Focused rerun passed 23/0/0. Final full backend rerun was interrupted before summary:
artifacts/travel-continuation-backend-final-20260930.log. Durable 2026-10-01 rerun:
artifacts/travel-backend-20261001.log; passed 517/0/12 in 562.575 s, exit 0.
Final exit/duration evidence: artifacts/travel-backend-20261001-result.json.
All skipped Selenium cases passed in the separate Chrome suite. The automated
PHASE 14 checkpoint is complete for current source; external acceptance remains.

## Configuration and migration state

Source/native now read config/local.env from the selected data directory, with
process environment > local.env > legacy .env precedence. Native signing secrets
remain in config/native.env. Native backend/environment are selected before the
configuration helper import, preventing early Celery initialization.

Existing checkout local.env held previously unused PostgreSQL/Redis targets that
could not resolve. The file was not edited. Validation explicitly selects an
isolated config directory, SQLite and memory cache. Source startup using that file
requires valid local DB/cache configuration. Native startup selects its own local
SQLite, disk cache and Huey. No real user runtime database/configuration changed.

Read-only checkout status: 0001–0009 applied; 0010–0012 pending. All three apply in
isolated tests and disposable source/frozen native data. No new migration created.

## Remaining priorities

No confirmed P0 or unresolved P1 code defect. P1 acceptance: live checks where
accounts/licensing are required, plus clean-machine/manual acceptance. Operator source configuration must be resolved
before starting source with its existing local.env. No keys or licenses assumed.

T07 completed on 2026-10-01: Decimal itinerary discounts/ranges/targets, exact
quote filtering and bounded quote serialization. Regression: 95 backend, 3 Chrome,
zero failed/skipped; source-native offline and Django checks passed. See
docs/TRAVEL_T07_VERIFICATION_20261001.md for exact commands. Earlier full-suite
and frozen-candidate evidence predates T07; rebuild before release promotion.

P2 next: T09 bounded request-telemetry retention, then targeted enrichment, telemetry
retention and legacy non-travel HTTP migration. Broader language, clean second-PC,
LAN, manual screen-reader and real ML outcome acceptance remain under
COMPLETION_AUDIT.md. Published preview remains separate from this candidate.
