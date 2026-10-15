# Project Status

## Active post-audit implementation — 2026-10-15

Production remains 3932f391; audit baseline bced104 is preserved. Isolated work:
F:/ALFRED_DEV/post-audit, fix/post-audit-critical-20261015. Audit is complete;
the 143-feature inventory is not regenerated. AWS is decommissioned by the user;
older activation advice is superseded. No live configuration, ACL, database,
service, paid provider or GitHub operation is authorized here.

| Unit | Development status | Evidence / remaining acceptance |
| --- | --- | --- |
| P0-B profile money | Implemented: finite, bounded cent validation at API/form/model/ORM and Career scenario inputs; existing Float SQL schema/API numeric contract preserved | 47 combined focused tests PASS, zero skips; migration drift PASS; production not remediated |
| P0-C private media | Implemented: source/debug and native use the same owner-filtered handler; safe missing/permission response, public static assets separate | Same 47-test gate includes anonymous/invalid session/foreign owner/traversal/deletion/source/native tests; packaged/live acceptance pending |
| P0-A Windows storage | Implemented: owner/SYSTEM creation and verification in native runtime/config, memory, parser/OCR scratch and recovery copies; explicit pinned, quiesced repair/rollback | 117 focused backend PASS; 11 repair CLI tests PASS (overlapping); 18 fresh native checks PASS; production ACL repair requires separate approval |
| P0-D M20 gates | Reused/merged existing 0052410 engine: ignored target file collisions fail before mutation; quoted JSON credentials fail with redacted findings | Both original failures reproduced; 70 focused gate/recovery/promotion/acceptance tests PASS; 13 overlapping incomplete-run/privacy tests PASS |
| AWS / replacement | User decision: no AWS runtime/provider activation | Decommission active path, evaluate non-AWS official contracts; real cloud remains OFF |

Changed money/media files: apps/users/money.py, models.py, serializers.py, forms.py;
apps/career/serializers.py; alfred_ai/urls.py, native_views.py; new boundary/profile
tests. Test receipt: artifacts/post-audit/money-media-3570b592/receipt.json (local,
synthetic). First money test attempt exposed a test transaction/savepoint issue;
the fixture was corrected without weakening validation. Historical failed receipt
is preserved. No migration, financial record conversion or balance change.

Storage files: alfred_private_storage.py; alfred_native.py; local_config.py;
memory_key.py; bounded_parser.py; document_extraction.py; statement_import.py;
backup/verification/recovery scripts and synthetic permission fixtures.
Evidence: artifacts/post-audit/storage-final-f320dc9c/receipt.json (117 tests and
WAL/config/media backup fixture); storage-cli-0dc1fcd2/receipt.json (11 tests);
storage-native-final-7e6dbb9c/receipt.json (18 actual native checks). Earlier native
attempt reached 16 checks then refused inherited restored-directory permissions;
the guard now accepts exact owner/SYSTEM inheritance only from a verified private
ancestor. Its failed receipt is preserved. No source/debug database encryption,
portable-key verification or production ACL remediation is claimed.

M20 integration preserves its prior history and both recovery-verifier changes:
private scratch protection plus caller-selected scratch roots. Recovery fixtures
now create private directories before seeding synthetic data; the initial mixed
branch failure is retained under m20-focused-7e820d51. Fixed receipts:
artifacts/post-audit/m20-corrected-67461836/receipt.json and
m20-incomplete-d8fd4607/receipt.json. Zero/skipped successful runner output now
reports NOT_RUN and blocks readiness; an actual failing runner remains FAIL.
The source scanner retains exact path/value-hash exemptions for six reviewed
public synthetic identifiers, never a blanket test-file exception. New P0
regressions are included in the standard release backend gate. M20 full pinned
integration and actual M21 native rehearsal are still pending; production approval,
off-device/key recovery, real-account and external CI gates are not filled by tests.

Next action: decommission AWS dispatch and apply the supported dependency patch;
then run a pinned integrated release gate. Specialized audit/runbooks and
historical results below remain reference material, not fresh acceptance.

**Current status — 2026-10-15:** M14/M15 consolidated source is deployed and GitHub master matches 3932f391aa4eed7b3200ad3b034f7991435e01e4. Dated release results are 619 backend/15 Chrome/35 native (overlapping packaged scope); this audit independently ran 86 focused tests, zero skips, plus isolated system/drift checks. Normal-account, real-provider, clean-PC and device-loss acceptance remain incomplete. Port 8000 did not respond during the audit; no service action was taken. M20 is unfinished separate development; M16–M19/M21 are not declared complete.

Use the [authoritative feature matrix](ALFRED_MASTER_FEATURE_MATRIX.md), [completion roadmap](ALFRED_COMPLETION_ROADMAP.md) and [acceptance plan](ALFRED_END_TO_END_ACCEPTANCE.md). The earlier progress narrative below is historical module detail, not proof of current production availability or comprehensive AI accuracy.

Final read-only observation: /health/live/ returned 200 on a runserver listener;
/health/native/ returned 404. No audit restart occurred. Actual DB/worker/native
readiness remains unconfirmed; the initial unavailable observation is historical.

The [completion audit](COMPLETION_AUDIT.md) records the current verification
results and remaining local/LAN runtime work. The sections below describe
implemented capabilities, not a guarantee of complete real-data coverage.

The [29 September travel release continuation](TRAVEL_RELEASE_VERIFICATION_20260929.md)
records the 1.1.0 preview packaging, current travel tests and local upgrade evidence.

The [28 September continuation](WINDOWS_TRAY_VERIFICATION_20260928.md) records
the current tray, branding, website, attribution and cleanup work.

The [27 September release verification](WINDOWS_PACKAGE_VERIFICATION_20260927.md)
records the previous installer/uninstaller, 407 passing backend tests and nine
passing Chrome workflows. All six installer lifecycle checks passed. The same
native executables passed the
[26 September runtime checks](WINDOWS_PACKAGE_VERIFICATION_20260926.md), including
23 packaged checks and a 24-user load test. Overnight attempts interrupted by
host restarts are retained separately. The supervisor restarts verification
after Windows sign-in; use its Status action for the current attempt and expected
finish. Completed overnight acceptance remains pending; 16 focused tests
passed for the observation and supervisor logic.

The active Windows runtime is [Waitress + Huey + SQLite](NATIVE_WINDOWS.md),
with a double-click launcher, persistent task queue, shared local cache and
standalone installer build. The [earlier recovery proof](NATIVE_RECOVERY_PROOF.md)
records the original SQLite snapshot/restore. Current native verification also
exercises real HTTP, worker execution, retries, restart and an isolated restore.
Docker/PostgreSQL/Redis/Celery remain an optional, separately unverified runtime.
The BIOS virtualization issue does not block native Windows operation.
The [native verification report](NATIVE_WINDOWS_VERIFICATION.md) records the
passing full suite, Chrome workflows, packaged OCR, worker/recovery tests and
preservation of the existing account data.

The [18 September hardening report](NATIVE_HARDENING_VERIFICATION.md) adds
durable job claims/recovery, post-reboot retention proof, 12 concurrent-user
checks, mobile and automated accessibility coverage, and project cleanup.
The separate-PC test, real overnight outcomes and independently checked model
accuracy remain open; the report links the fresh verification branch/CI run.

The [sample-user acceptance audit](USER_DATA_ACCEPTANCE.md) records an isolated
signup/API scenario, independently reconciled money totals, correction tests,
and browser checks of the finance pages. It also documents the calculation,
cache, validation and wording defects found and fixed in that pass.

## Completed So Far

### Dashboards and UI

- finance dashboards wired across major sections
- dedicated sign-up and sign-in entry points are now available for users
- expense financial-flow charts now switch between monthly, quarterly, and yearly aggregation
- centralized `/documents/` upload hub for statements, loan PDFs, vehicle files, service bills, resumes, and credit reports
- centralized `/documents/` upload hub now also includes diagnostics, low-confidence review queues, all-scope retry controls, and linked delete behavior for document-derived data
- multi-file upload handling across the document hub, expenses, loans, career, credit-report, and vehicle-service pages
- dedicated vehicle-service dashboard
- mobility dashboard for travel plans, logs, gallery, and heat map
- rebuilt/fixed behavioral page empty-state and duplicate-insight handling
- roadmap and completion tracking moved into a separate superuser-only project-details dashboard instead of the main dashboard
- project-details is now a live superuser operations console with internal-clock timestamps, evidence watchlists, ticket-routing counts, report-library rollups, and adaptive learning progress
- project-details learning progress now refreshes live through a dedicated JSON endpoint instead of only on full page loads
- project-details in-progress progress bars now bind to named learning tracks instead of sorted positions, preventing progress drift as module maturity changes
- live-refresh pages now use interaction guards and selective DOM updates so active forms and dropdowns are not torn down every second
- browser interaction coverage now has a dedicated Selenium runner, a CI browser workflow, separate local Chrome/Edge and CI Chrome `browser_regression_summary.json` proof records, and failure artifacts for screenshots, page HTML, metadata, and browser logs where supported
- heavy finance, mobility, bike-service, and career dashboard reads now use cache-aware materialized payloads keyed to data revisions
- investment summary, allocation, and growth reads now also use cache-aware materialized payloads keyed to portfolio revision
- deterministic staging traffic now exercises all 21 registered materialized cache namespaces and records hit/miss, TTL, generation latency, stale regeneration, revision, and invalidation proof without marking production cache maturity complete
- Project Details selects readiness checks for the active runtime; native Windows checks use Huey, while Celery worker/beat requirements apply to the optional Compose runtime
- the shared `tests/` package is now discoverable by default so the normal `manage.py test` command runs the suite instead of silently skipping it
- supported ML models now persist training state, run history, quality estimates, and freshness windows in the database
- supported ML models can train on the scheduled nightly cycle when consent, data and runtime gates pass; the native Windows runtime disables startup training
- project status now treats local/LAN hosting as the only active operating path; provider-specific deployment leftovers have been removed from tracked source, IDE metadata, artifacts, and local cached evidence

### Vehicle and Mobility

- upload-first vehicle documents
- service-log import from service bills and work notes
- manual service logging fallback
- imported and manual service logs are now summarized together so long-term vehicle history stays usable
- issue/fault reporting with probable cause, suggestion, and projected cost
- condition snapshots with score and condition assessment
- parts-and-performance impact guidance based on service history, condition state, and open issues
- structured service-log and vehicle-document payloads now use centralized merge helpers so partial updates do not drop nested parsed data
- multiple saved vehicle profiles with primary-vehicle behavior
- travel advisor with weather, offbeat suggestions, stay-budget guidance, and vehicle-readiness context
- the vehicle catalog now includes broader official manufacturer coverage and model guidance across Royal Enfield, Suzuki, Honda, TVS, Bajaj, Yamaha, Ather, Tata, Mahindra, Kia, and NEXA-backed entries
- the service dashboard now attaches model-specific maintenance highlights with proof links where the catalog has official references
- the official vehicle catalog now filters model choices by selected vehicle type before the user picks a catalog entry

### Data Verification

- document relevance checks against selected vehicle profiles
- source-aware evidence cache for external data
- freshness tracking and stale cleanup rules for external intelligence
- circuit-breaker-backed stale fallback when verified sources repeatedly fail
- scheduled background refresh for verified external evidence
- foreclosure documents are now checked against the selected loan before a close action is allowed
- chart paths were audited to keep live API-backed data or empty states instead of user-facing demo/report widgets
- document parsers now share a layered extraction engine for PDF text, layout, table flattening, repaired-PDF fallback, and OCR retries
- parser-learning memory now adapts statement, loan-document, loan-closure-document, investment-document, recruiter/JD-document, credit-report, vehicle-document, and resume confidence from repeated uploads, accepted corrections, and retry outcomes
- operational diagnostics now persist document-processing failures, metadata-only saves, retry outcomes, and client-side visualization issues with timestamps and payload context
- recommendation and tax advisory outputs now expose freshness-backed evidence blocks and explicit grounding notes instead of opaque summaries
- investment guidance now exposes verified market and macro proof, freshness metadata, and materialized portfolio payloads
- relationship alignment now exposes factors, grounding notes, and freshness-backed proof instead of a fixed placeholder score
- verified external job feeds now filter blocked cloud-provider skill tokens before storing career evidence, and prior matching local cached job-evidence rows were purged

### Risk and Career

- career projection now uses macro context instead of a fixed placeholder growth rate
- career now shows dated risk-taking windows for job switches, promotion asks, skill upgrades, and side-income moves
- risk outlook now blends user-entered risk snapshots with macro context, market signals, financial pressure, behavioral pressure, and vehicle readiness
- related risk news is now consolidated under Risk Radar instead of being split across multiple module views
- resume uploads are parsed into role/skills/experience signals across broader formats including html, rtf, odt, and image-based CV uploads
- resume parser learning memory is now stored per user so parser adaptation does not leak across users
- pasted job links are analyzed for fit score, missing skills, and market risk
- recruiter mail and JD intake can now be parsed into the same career-fit pipeline, including optional attachment extraction
- study recommendations are now generated from experience stage, latest skill gaps, and live opening signals
- compensation benchmark summaries are now derived when salary-bearing evidence exists in job pages or recruiter/JD intake
- public job parsing now has deeper adapters for JSON-LD pages plus Greenhouse and Lever style openings
- layoff news and suggested openings are pulled from live configured internet sources with evidence
- scanned/image CV uploads now fall into review state instead of breaking the upload flow when OCR is unavailable on the server
- credit score surfaces now distinguish internal estimates from official bureau pulls instead of saving fake bureau pulls as real scores
- relationship alignment is now grounded in partner inputs, user cash-flow pressure, verified planning context, and a bounded optional relationship-model blend

### Expense Import Integrity

- statement intake now supports bank, credit-card, loan, investment, and other statement kinds
- parser status, confidence, and extracted payload are retained even when transaction extraction is incomplete
- account-scoped transaction fingerprints now reduce duplicate statement imports
- same-account repeated uploads are skipped more reliably
- similar transactions on different bank accounts are preserved instead of being deduped incorrectly
- mixed-overlap statement imports now keep new rows even when duplicate rows share the same reference and amount
- malformed or truncated statement PDFs now degrade to a stored review item instead of crashing the import flow
- structurally broken statement PDFs that still contain page objects can now be rebuilt to salvage metadata before they fall back to review
- structurally broken statement PDFs can now also fall through an isolated OCR worker to recover holder/account/period metadata even when the in-process OCR runtime is unhealthy
- metadata-only statement uploads now remain visible in the expenses workspace and central document hub with parser notes and recovered header details
- low-confidence statement uploads now queue deeper background retries instead of staying permanently dead-ended after the first pass
- repaired broken bank PDFs can now import partial OCR-preview transactions immediately, keep page-progress metadata on the upload, and continue deeper retries in the background for the remaining pages
- accepted corrections on partial or metadata-only statements now force a deeper retry window so OCR-recoverable uploads can populate expenses after review instead of only saving header fixes
- imported loan-like statement entries are now matched against the active loan book with confidence and review flags
- assets and liabilities are now surfaced in the expense intelligence view, including vehicle classification based on usage and utility

### Loans And Support Workflow

- active loans can now be consolidated into a new loan record while source loans are marked prepaid
- loan foreclosure now requires an uploaded closure or no-due document
- loan PDF imports now expose detected document type and parse confidence for sanction letters, statements, and repayment schedules
- uploaded loan PDFs are now saved as first-class import records, even when the parse is weak and only a review item can be created
- manual user ticket creation is no longer part of the normal user flow
- Alfred can auto-create summarized tickets when loan matching is low-confidence or a closure document is rejected
- low and medium severity tickets are now auto-handled by ALFRED, while high severity is escalated to superuser developers
- reports and ticket-routing visibility are now superuser-only
- the central document hub now exposes retry controls for statement, loan, vehicle, resume, and credit-report items instead of statement-only retry
- the central document hub now also supports review, correction, retry, and parser-learning feedback for loan-closure, investment-import, and recruiter/JD intake documents
- accepted corrections for invoice-style vehicle documents now update linked service-record fields such as service date, workshop, odometer, cost, and work summary instead of stopping at the document shell
- the document hub and expense intake now keep recent upload stacks scrollable and capped to the latest 10 visible cards per panel so the page height stays stable as history grows
- unresolved retries now create internal retry tickets keyed to the retry count, so ALFRED can auto-handle lower-severity parsing failures and escalate exhausted cases to developers
- parser-confidence calibration is now a trainable ML path that learns from parser outcome history instead of relying only on static confidence heuristics
- relationship-model training is now a safe, bounded path that only activates when enough scored partner profiles exist

## Pending acceptance

- Clean second-PC installation and reboot acceptance. Installer, host-reboot retention and backup/restore checks have passed on the development PC.
- Full overnight scheduled refresh, cleanup and eligible-training outcomes. The September 18 report was interrupted after 4.1344 hours; it is not an active or passing observation.
- More independently checked documents and model outcomes, with enough consenting data to pass quality and freshness gates. The September 25 comparison passed 68 checked fields across three private documents.
- Manual screen-reader testing and heavier real usage. Nine Chrome workflows and a 24-user/480-write synthetic load check passed; the three newly found dropdown-label issues are fixed and included in packaged verification.
- A real Windows sign-in check. Current-user startup registration succeeded on September 25 and remains registered.

See the [September 25 continuation](ACCEPTANCE_20260925.md),
[standalone package guide](WINDOWS_PACKAGE.md) and
[completion audit](COMPLETION_AUDIT.md) for acceptance conditions and dated
evidence. The earlier Windows/Chrome CI proof is dated September 18; current
continuation checks are local.

## Optional extensions

- LAN access and live email/bureau integrations, with the required account access and consent.
- More vehicle catalog models, job sources and geography coverage, informed by real usage.
- Additional model families and richer career/market/risk guidance after current models have sufficient validation evidence.

The [future scope](FUTURE_SCOPE.md) records broader product ideas. Public/cloud
deployment requires a separate explicit decision and is outside current scope.

## Risks Remaining

- browser-only issues can still exist where no driver-backed Selenium pass was recorded; normal test runs still skip browser tests unless `ALFRED_RUN_BROWSER_TESTS=true`, and full UI maturity still needs repeated no-skip browser summaries from both local and CI jobs
- selective fragment refresh now prevents most interaction resets, but any remaining page that still swaps whole DOM blocks in-browser could regress until it gets the same treatment
- some external sources are authoritative APIs, but market data still relies on Yahoo Finance
- multiple-vehicle support is structurally improved, but some naming remains bike-centric in code paths for backward compatibility
- job-link parsing is robust for many public pages, but some portals can still block direct fetches or hide content behind script/runtime layers
- project-details is now dynamic from live operational data, but it is still not generated from a formal release registry
- large-data hardening has deterministic staging proof for all registered cache namespaces, but production maturity still requires shared-cache telemetry under realistic concurrency and payload volume
- public-production readiness remains inactive and decision-gated; native Waitress/Huey/SQLite with a shared disk cache is the active Windows path, and Docker/PostgreSQL/Redis/Celery is an optional alternative
- balance-sheet vehicle classification is heuristic and should still be reviewed against real ownership/use patterns where the financial treatment matters
- auto-training is now safe and stateful, but several modules still remain heuristic, placeholder, or data-poor and should not be treated as fully learned systems yet
- parser adaptation is materially stronger now, but "all document types without fail" is still not a truthful guarantee for arbitrary or severely degraded files
