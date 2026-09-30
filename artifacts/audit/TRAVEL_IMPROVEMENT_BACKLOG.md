# Travel improvement backlog

Updated 2026-10-01 after final backend validation. No confirmed P0; this is not a completed security certification.

| ID | Priority | Area | Problem / impact | Solution | Complexity | Dependencies | Tests required | Status |
|---|---|---|---|---|---|---|---|---|
| T01 | P1 | HTTP | Direct requests can reach unsafe configured endpoints; unbounded download | Shared pinned HTTPS client, no redirects, size/type/time limits | M | urllib3, url_safety | SSRF, mixed DNS, rebinding, redirects, gzip/size, timeout | Implemented; focused and prior broad tests pass |
| T02 | P1 | Freshness | Interrupted changes not validated; weather alternatives can age | Read-time and action-time expiry guards | S | Existing evidence | Nested expired offers, weather action | Implemented; read/action expiry tests pass |
| T03 | P1 | Discovery | Suggestions limited to seed catalog | No-key travel wiki discovery, normalized coordinates, local ranking and fallbacks | M | T01 | New destination, dedup, visits, unavailable | Implemented; fixture/browser discovery verified; prior wiki live proof retained |
| T04 | P1 | Web research | No contextual web search or source hierarchy | Configured legitimate search, sanitized slots, official-source ranking | M | T01, current provider terms | Privacy, malformed, source trust, cache | Implemented; provider keys/terms remain optional |
| T05 | P1 | Link output | Missing stay/transport/permit link-out fallback | Safe HTTPS link builder; label searches as unchecked | S | URL normalization | Dates/occupancy encoding, unsafe URLs, frontend rel | Implemented; safe links/browser checks pass |
| T06 | P1 | UI | New providers/evidence/maps invisible | Extend existing chat/cards and source panels, opt-in map, refresh | M | T02–T05 | Selenium desktop/mobile/reload/failure | Implemented; all 12 Chrome workflows passed, zero skips; desktop/mobile visually checked |
| T07 | P2 | Costs | Itinerary edit float multipliers; quote filter rejects decimal strings | Reuse existing Decimal helpers and exact provider strings for remaining edits/filtering; preserve schema | M | Existing money.py/provider contracts | Half-rupee rounding, totals, decimal-string scope/currency/expiry guards | Complete: Decimal edits/targets/ranges, exact string quote filtering and bounded serialization; 95 backend + 3 Chrome passed, source-native passed |
| T08 | P2 | Conversation | Stored pillion and wrong-type preference risks; limited edits | Validate preferences, confirm current pillion, preserve unrelated day choices | M | Existing session state | Followups, profile override, scoped edit | Typed preferences/pillion/scoped edits implemented; broader language remains P2 |
| T09 | P2 | Efficiency | Unnecessary enrichment, telemetry incomplete, unbounded request logs | Changed-category reuse, status/latency metrics, retention | M | T03–T06 | Call counts, quota, stale jobs | Pending |
| T10 | P1 | Acceptance | New changes not packaged/live validated | Mocked broad suite, browser/native isolated runtime; record remaining live-key checks | M | T01–T09 | Regression, migration, source/native | Prior full backend/frozen candidate passed before T07. Current T07: backend 95/0/0, Chrome 3/0/0, source-native passed. Rebuild before promotion; live keys/clean-machine/manual acceptance remain |
| T11 | P2 | Permits/transport | No authorized inventory/automated authoritative rule feed | Honest research leads and official links; add documented contracted APIs only | L | Authority/operator access | Uncertainty and no fabricated availability | Ongoing limitation |
| T12 | P2 | Legacy HTTP | Non-planner verified-intelligence fetchers still use direct requests | Separate shared-client migration after travel hardening | M | T01, existing integrations tests | Integrations regression | Pending |


Recovery 2026-09-30: prior browser failure was a stale pre-research allowance
baseline; the runner must use alfred_ai.browser_test_settings for separate SQLite
connections. Added day-edit/recheck regression, route fixture and staff panel coverage.
Provider configuration now includes all web/weather/flight categories and hides keys.
Migrations 0010–0012 are pending only in the real checkout DB, not test databases.
New source/native local.env loader is covered by precedence/isolation tests; source
validation explicitly selects isolated config, SQLite and memory cache. Existing
local.env database/cache hosts were unavailable and were not edited. Source startup
with that file requires a deliberate valid local DB/cache selection. Native startup
forces its own SQLite/disk cache/Huey settings and preserves native signing secrets.
