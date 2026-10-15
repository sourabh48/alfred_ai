# Project Status

## Active post-audit implementation — 2026-10-15

Production remains 3932f391; audit baseline bced104 is preserved. Isolated work:
F:/ALFRED_DEV/post-audit, fix/post-audit-critical-20261015. Audit is complete;
the 143-feature inventory is not regenerated. AWS is decommissioned by the user;
older activation advice is superseded. No live configuration, ACL, database,
service, paid provider or GitHub operation is authorized here.

**Current verified critical-fix source: b162c8fb2c43b357e840c3a298d06ffa4bed3251.**
753 backend tests, 37 Chrome tests and 34 source-native/Ollama checks PASS,
zero failures/skips. Actual M21 exact promotion, nine browser checks, restart/
encrypted memory persistence, independent local restore, typed financial/family
reconciliation, injected worker crash and source rollback PASS. Evidence:
artifacts/release-gates/post-audit-critical-b162c8f/release.json and
F:/ALFRED_DEV/post-audit-rehearsal-b162c8f/rehearsal.json. The failure-injection
child report deliberately records FAIL with rollback PASS; the parent rehearsal
is PASS. No database was overwritten by source rollback. All recovery assets
and failed earlier evidence remain. Screenshots reviewed at the preceding
3a46e1c equivalent UI gate; current Chrome gate also PASS.

M20 technical decision is PASS; production promotion is BLOCKED and unauthorized.
Off-device copy/key/device-loss restore, fresh package, normal account, separate
PC, installer, remote Git/CI and branch protection are NOT_RUN. Source-native
checks are not a frozen executable proof. The M15 HDD waiver is not inherited.
P0 fixes and Django 6.0.9 are development-only; live ACL repair/deployment need
separate authorization. Newer M16 source progress is recorded below.

M16/T09 request retention is now implemented in development: configurable 7-day
non-network/90-day network history, current UTC quota windows preserved, active
attempts deferred, bounded oldest-first batches, dry-run CLI and shared 15-minute
source/native scheduling. Saved plans/evidence, owners, expenses, balances, cache
results and provider state are not cleanup targets. Full backups retain telemetry;
post-start canonical reconciliation excludes only the expiring request table.
**156 focused Travel/worker/recovery/promotion tests PASS, zero skips; system and
migration drift PASS** (artifacts/post-audit/m16-integration-a065eaeb/receipt.json).
These overlap prior tests and are not added to 753. This extension is after the
frozen critical candidate; its full combined/package gate has not run.
M16 remains IN PROGRESS: dependency-aware selective refresh/invalidation is next.
Implementation commit d66ce9904e560ade110ccf41be210eedc6f7b7e8 also passed exact
source/privacy/dependency/migration preflight and nine targeted retention tests
(artifacts/release-gates/post-audit-m16-d66ce99/release.json). Its full backend,
browser and native gates correctly remain NOT_RUN; the targeted success is not
transferred into a release PASS.

### Earlier development evidence (preserved; current result above supersedes pending actions)

Latest pinned integration: **3a46e1cb24234c586a40be446501a83c48cce2ea — 751 backend,
37 Chrome and 34 source-native/Ollama checks PASS; zero failures/skips**. Isolated
pip check PASS (shared baseline libraries, not clean-install/package proof).
Evidence: artifacts/release-gates/post-audit-final-3a46e1c/release.json. Synthetic
dashboard/mobile Travel screenshots reviewed. Overall promotion remains BLOCKED.
Actual M21 in F:/ALFRED_DEV/post-audit-rehearsal-3a46e1c passed exact promotion,
nine browser checks, financial preservation and memory restart persistence, then
failed before worker-crash injection because its nested evidence directory did
not exist. Reproduced FileNotFoundError; sandbox approval now creates/verifies
that private directory before writing. 33 focused acceptance/promotion/recovery
tests PASS (artifacts/post-audit/m21-output-directory-2f27f838/receipt.json).
All failed evidence/backups remain; complete actual rollback acceptance is pending.

P0 temporary-file follow-up: uploads and both isolated OCR paths now create
private parent directories before opening document files. Tightening a file ACL
after creation alone cannot revoke an already-open read handle. The creation-time
regression reproduced all three gaps (temp-parent-repro-ee45ea20). Streamed files
retain Django's Windows-safe temporary wrapper; the first attempt using Python's
different sharing mode failed and is preserved (private-temp-parent-efce6af0).
Corrected **115 focused storage/upload/document/loan/finance tests PASS**, zero
skips (artifacts/post-audit/private-temp-fixed-900cdd22/receipt.json). Temporary
directories close with their files; OCR uses private scoped input and safe
classified errors, without raw cleanup paths. No production ACL/file change.

| Unit | Development status | Evidence / remaining acceptance |
| --- | --- | --- |
| P0-B profile money | Implemented: finite, bounded cent validation at API/form/model/ORM and Career scenario inputs; existing Float SQL schema/API numeric contract preserved | 47 combined focused tests PASS, zero skips; migration drift PASS; production not remediated |
| P0-C private media | Implemented: source/debug and native use the same owner-filtered handler; safe missing/permission response, public static assets separate | Same 47-test gate includes anonymous/invalid session/foreign owner/traversal/deletion/source/native tests; packaged/live acceptance pending |
| P0-A Windows storage | Implemented: native and source/debug SQLite/config/cache checks, private retained/streamed uploads, memory/parser/recovery protection; pinned quiesced repair/rollback | Native unit: 117 focused PASS, 11 overlapping CLI PASS, 18 native PASS. Source extension: 89 focused PASS, system/drift PASS. Production ACL repair remains approval-gated |
| P0-D M20 gates | Reused/merged existing 0052410 engine: ignored target file collisions fail before mutation; quoted JSON credentials fail with redacted findings | Both original failures reproduced; 70 focused gate/recovery/promotion/acceptance tests PASS; 13 overlapping incomplete-run/privacy tests PASS |
| AWS / replacement | AWS runtime provider removed; provisioning rejects before prompts/writes; historical flags report disabled. Old protocol is network-free test quarantine only | 86 focused memory/sync/UI tests PASS; 2 final decommission tests and SyntaxWarning-as-error compile PASS; neutral encryption/sync unchanged; R2 is an unimplemented candidate |
| M18 Django security patch | Development requirements and Windows constraints pinned to 6.0.9 | Separate development venv: 227 focused security/finance/upload/document tests PASS, zero skips; system/drift PASS; fresh browser/native/package gates pending |

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

M20 integration commit: 6045904824a86413396eac16d5b16d9464dcd2fa. Its actual
pinned preflight source/privacy/dependency/migration scope PASS is saved at
artifacts/release-gates/post-audit-m20-6045904/release.json. Overall readiness is
correctly BLOCKED on unexecuted technical/operational gates and approval.

Django 6.0.9 is the compatible 6.0 security patch dated 2026-10-06; it addresses
language/header parsing denial of service and additional scoped security fixes.
No framework major upgrade or schema change is included.
[Official release notes](https://docs.djangoproject.com/en/6.0/releases/6.0.9/).
Receipt: artifacts/post-audit/django609-focused-4084887b/receipt.json. The isolated
.venv supplies its own Django while sharing other baseline libraries read-only;
this is not a clean full dependency installation or reproducible package proof.
Production's interpreter and requirements remain unchanged. Broader dependency
maintenance and M19/clean-PC acceptance remain open.

AWS decommission changes: memory_cloud.py, memory API/status and sync command,
configure_memory_cloud.py, synthetic-only proof script and test fixture. No stored
profile/key is removed or rotated. Active provider documentation and the existing
master prompt/roadmap carry the explicit override; the 143 audit rows/history are
preserved. Receipts: artifacts/post-audit/aws-off-9cadde31/receipt.json (86 tests)
and aws-final-582984f8/receipt.json (two overlapping tests plus strict syntax check).
The documented regex warning was fixed in the quarantined fixture using raw
patterns; no AWS transport is imported by application runtime.

Non-AWS choice: R2 implementation candidate after official atomic CAS, token,
security/pricing/limits review. No adapter/account is activated. Private bucket
configuration proof and least-privilege verification must be resolved before an
implementation can claim readiness; no checkbox replaces that proof. Alternatives
and exact constraints are in the [provider register](ALFRED_EXTERNAL_INTEGRATIONS.md#non-aws-intelligence-storage-decision).
Real cloud, real OpenAI and device-loss recovery remain unaccepted/OFF.

Pinned 3b73d78916b4c5f545e8148ec0abcaee143855cd combined attempt:
**736 backend PASS / zero skips; 34 native/Ollama checks PASS; 36 of 37 Chrome
tests PASS, one Travel quick-ideas timeout.** Overall gate correctly FAIL, not
release-ready. The isolated failing browser test reran PASS without source changes
(travel-browser-debug-7812ac83); a whole browser retry is required, not a claimed
fix. Evidence: artifacts/release-gates/post-audit-integrated-3b73d78/release.json.
Loan/investment monetary screenshots reviewed; their captures were intentional
successful evidence, not additional browser failures.

Source storage extension closes a reproduced part of P0-A: ordinary source/debug
SQLite, retained media and streamed temporary uploads inherited broad fixture
permissions. Synthetic receipt: source-storage-repro-final-84402574. New checks
run before source SQLite/cache use or configuration reads; PrivateFileSystemStorage
and PrivateTemporaryUploadHandler protect data before payload writes. Static
assets stay separate. Existing unsafe directories/files fail for approved repair;
none are automatically changed. Receipt: artifacts/post-audit/source-storage-final-62f32718/receipt.json
(89 PASS / zero skips); system/drift PASS in source-storage-fixed-12c75b59.
The first upload fixture run failed because its intentionally shared media/temp
directory was broad; the disposable fixture is now protected before seeding.
No money, schema, provider, key or production change is included.

8978fe1 combined attempt retained: 744 backend executed, 26 failures/28 errors
from pre-existing broad shared media fixtures; 37 Chrome executed with one different
intermittent navigation error; 34 native/Ollama checks PASS. Overall FAIL remains.
The guard was not weakened. Corrected release environments now select a fresh
ALFRED_MEDIA_ROOT; source startup protects it before preview/document generation.
The shared M14F temp/media fixture is private before seeding. Standalone browser
runs use the same stripped, disposable environment instead of inheriting operator
DB/media/cloud settings. 150 focused document/loan/upload/financial tests PASS
(artifacts/post-audit/media-isolation-fixed-20c05611/receipt.json); 22 overlapping
runner/isolation/fail-fast tests PASS (runner-final-67f8460e). Backend/browser
failure stops subsequent expensive gates and leaves unexecuted gates NOT_RUN.

Pinned e4c66471e34a4eae14eb90a1bae3ce13577a5925 passed **747 backend / 37 Chrome /
34 native-Ollama checks**, zero failures/skips. Source/privacy/configuration/drift
PASS. Receipt: artifacts/release-gates/post-audit-isolated-e4c6647/release.json.
Actual M21 sandbox F:/ALFRED_DEV/post-audit-rehearsal-e4c6647 independently backed
up/restored synthetic data, booted the baseline and exercised fast-forward. It
then failed operator_file_changed_after_promotion because clean tracked checkpoint
source changes were incorrectly hashed as operator overlays. Authorized synthetic
source rollback PASS; data/configuration and all evidence/backups preserved.
This is a real M21 failure, not COMPLETE or real-account acceptance.

Correction: hash protected operator files only when the candidate does not change
them; clean tracked source advances normally, while dirty overlapping operator
edits and ignored-file collisions still block. CLI main/imports share GateError
identity so fixed errors stay actionable. 58 focused M20/promotion tests PASS
(artifacts/post-audit/m21-operator-fix-d24c0908/receipt.json); three overlapping
actual CLI boundary tests PASS (m21-cli-final-18f0f3fd). New candidate requires
fresh combined validation and a new disposable M21 rehearsal.

Pinned f79690a8c42eab6b2ae3182445af5002a87da6a8 retry executed 750 backend tests,
zero skips, with one error; browser/native correctly remained NOT_RUN. Evidence:
artifacts/release-gates/post-audit-m21-resume-f79690a/release.json. The earlier
post-audit-m21-f79690a attempt was interrupted before a final receipt, not PASS.
The redactor omitted setup/subtest failure headers; its reproduced regression
now retains test/class identifiers without parameter values or exception content.
15 runner tests PASS (failure-log-fix-49532b0a); 27 overlapping source/acceptance
tests PASS (m21-three-debug-296f6a15). These targeted results do not clear the
combined failure. Preserve all receipts; repeat the pinned combined gate, identify
any repeated error, then perform the new disposable M21 rehearsal.

The safe failure-header correction is committed at 3a46e1c. Its full rerun passed
as recorded above; the earlier one-error run did not reproduce, and is retained.
Next action: finish the private temporary-parent P0 follow-up under focused tests,
pin the corrected candidate and repeat actual M21 acceptance. No production action.
Specialized audit/runbooks and
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
