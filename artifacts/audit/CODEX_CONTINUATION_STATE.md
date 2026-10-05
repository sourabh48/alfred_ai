# ALFRED CODEX CONTINUATION STATE

## Repository

Branch: codex/native-runtime-hardening-20260918
Base commit: b4e89742717d0f4ce1d8b6e49ccb7b6b6abde525 (clean starting point for master note).
Verified engineering source commit: db2f86d4f0101665abb0666a98644f91a3eda5ac, created during pre-Windows preparation on 2026-10-05. It preserves Phase 0/1, M12A/B/C and M13A/B source, migrations, tests and phase documentation. Read `git rev-parse HEAD` for the latest preparation commit.
Working tree at this checkpoint update: Windows setup, dependency constraints, encrypted-recovery scripts, project-local skills, hardware/tooling notes, the post-restore Ollama/Codex handoff and historical SQLite recovery checks are committed and pushed. This documentation update records the user's replacement recovery destination: a Desktop bundle for manual transfer to a pendrive. Generated logs, browser proof and private/runtime data remain local/ignored. Safe audit/reinstall documents are explicitly allowed in Git. No installer promotion.

## Active pre-Windows task

The user has superseded engineering continuation with complete PC cleanup preparation. Do not resume M13C or execute post-Windows restoration now. The latest instruction replaces the temporary GitHub/LFS backup destination with a Desktop recovery folder that the user will manually copy to a 6 GB pendrive, then copy back to Desktop after Windows reinstall. Read `docs/WINDOWS_ENCRYPTED_RECOVERY.md` and the generated `artifacts/reinstall/PRE_REINSTALL_FINAL_STATUS.md`. The source/recovery implementation was pushed and independently verified at `5bf9cbe3e4c0c609e5fff5adf135ebcdc6a213b4`, which is the application source checkpoint bound into the encrypted archive. Later safe documentation commits may advance HEAD; independently verify the live remote after pushing them.

On 2026-10-06 the user confirmed GitHub login, 2FA, recovery email, off-PC archive-password storage, required-secret recovery and Windows installation media: all YES. GitHub LFS capacity is no longer a gate for the chosen pendrive method. No temporary GitHub backup repository was created and no private backup uploaded. ALFRED server and worker were gracefully stopped, with no active database writer. Docker was not running; WSL shutdown completed. Both main runtime locations were inventoried, together with a historical first-start profile, six earlier operator backups, cleanup/pre-update snapshots and unique private validation inputs. The offline historical Docker VHDX is required and included, rather than assumed unnecessary. All 17 required original and recovered SQLite databases passed integrity checks.

The actual private staging backup outside Git contains 51,617 files totaling 303,836,313 bytes, plus internal manifests. A required historical WAL of 4,120,032 bytes was discovered by the strict verifier and added unchanged beside its staged database; every raw historical database was checked for this gap. Original/staged/extracted hashes and all 17 SQLite checks pass. Historical DB/WAL/SHM bytes are preserved: the verifier uses disposable shadow copies, including committed WAL state, rather than checking only six backup-API snapshots. Four focused synthetic recovery tests and Graphify update passed; completed application suites were not repeated. Detailed paths, timestamps and hashes remain inside the encrypted archive. The compromised historical signing key is retained privately for recovery only; rotation/re-encryption remains deferred until verified restoration.

Real encryption and full local recovery validation are complete: one 7z AES-256/header-encrypted volume, `alfred-private-backup-20261006.7z.001`, 67,915,749 bytes. SHA256: `7a54b209a4bf5f8bca8d7346acfbe1c468629f88695df00a38736a68a7f6eed7`. The user entered the password only at native masked prompts; it is absent from commands, scripts, logs and Git. The prepared Desktop folder is `ALFRED_RECOVERY_20261006`, containing encrypted files, official portable 7-Zip, safe setup/restore/tooling notes and `VERIFY_SHA256.ps1`. Desktop copy hashes pass, and the checker rejects an incomplete synthetic copy. No plaintext private data or password is in the handoff folder.

The physical pendrive is NOT YET VERIFIED. Desktop storage is on this PC and will be erased. The user must copy the whole bundle to the pendrive; verify hashes, decryption, extraction and all private hashes/SQLite from that device before declaring wipe readiness. Keep the pendrive disconnected during disk cleanup and do not reformat it into installation media. After reinstall, copy the retained bundle back to Desktop, restore from the saved guide, and retain the USB backup until finance/data/source/native recovery and historical-state preservation are proven. `SAFE TO REINSTALL WINDOWS = NO` until the retained USB copy is verified. Keep originals and staging; do not install Ollama, rotate the old signing key or start feature work.

Final pre-wipe hardware/tooling handoff: read `artifacts/reinstall/HARDWARE_BASELINE.md`, `AGENT_TOOLS_REINSTALL.md` and `OLLAMA_CODEX_HYBRID_PLAN.md`. The current machine has a Ryzen 5 3500X, 15.91 GiB RAM and an AMD RX 6700 XT with approximately 12 GiB driver-reported dedicated memory. Ollama installation, GPU/backend verification and model selection are strictly AFTER successful Windows/ALFRED restoration. No Ollama model or new application feature was installed or implemented during this phase. Repeated local-provider failure must checkpoint the existing task/diff/failing tests and hand it to hosted Codex, rather than restarting the work.

The engineering verification entries below retain their historical pre-commit state; they do not override the newer source-preservation commit or active reinstall task.

Additional local changes observed during this continuation: AGENTS.md Graphify guidance, .codex/ skill/hooks and graphify-out/ cache. These were preserved. The required code-graph refresh passed using an isolated temporary helper installation; see Repository housekeeping below. Do not remove or overwrite those local instructions/tool files.

## Active master phase

Master remediation note dated 2026-10-01; resumed 2026-10-05: Phase 0 complete; Phase 1 dependency/tax full gate passed; M12A/B/C implemented and 156 combined finance tests passed. M13A/B Loan currency stages complete: latest full backend 671 passed / 17 browser skips / exit 0, plus 2 separate Chrome workflows passed. Next is scoped M13C Investment register money, followed by remaining M13 domains and M14. This replaces the earlier Travel-only T09 priority. Do not restart completed Travel work or conduct another whole-repository audit.

## Active subtask

M13B is complete. Seventeen ancillary Loan fields now use bounded Decimal cents, with retained related snapshots/reset/migration 0015, exact foreclosure allocation, numeric JSON and history/canonical/tax/document compatibility. Finalized-settlement review cannot overwrite the register; explicit zero cannot infer closure; corrections roll back atomically. Final full backend: 688 run / 671 passed / 17 browser skips / zero failures/errors, 641.053 s, exit 0 at 2026-10-05 15:40:05 +05:30; artifacts/m13b-backend-verified-20261005.log/result JSON. Root sessions 75653 and 75735 are closed. Focused and Chrome evidence is below and in docs/MASTER_M13B_VERIFICATION_20261005.md. Final Graphify refresh passed, 7,220 nodes/18,817 edges; artifacts/m13b-graphify-update-complete-20261005.log/result JSON. No active test/refresh process remains. No operator DB migration, commit or release. Next subtask: M13C Investment register's three currency fields; see Exact next task. All application checks use isolated local-runtime SQLite/locmem and no helper PYTHONPATH.

## Travel phase

Prior T07 Decimal travel cost work remains complete. The new master note identifies origin/discovery/pagination/mode/alternatives/corridor/detour gaps for targeted remediation after higher-priority financial/security P0s. Prior recorded Travel phases are not proof of the newly expanded requirements. T09 telemetry retention remains open (master Phase 15), followed by scoped invalidation/telemetry (Phase 16).

## Completed work

- Master M00: tray test now expects guide.resolve().as_uri(); production unchanged. 7 tray and 32 native/recovery tests passed.
- Master M01A: official current 6.0-series release verified on 2026-10-01; requirements and PyCharm venv updated from Django 6.0 to 6.0.8. System/migration checks and 53 settings/auth/finance tests passed. Resumed full gate passed 543 with 13 skips.
- Master M01B: immutable versioned Decimal tax policy for FY 2025-26 / AY 2026-27; corrected new-regime slabs/rebate, cess ordering, rebate/surcharge marginal relief, residency/age/income-type handling, bounds/invalid-input checks, explicit unsupported-year errors and official metadata. API/cache/UI use explicit year; comparison and savings use the same income; payment deductions use selected FY. Legacy wrong static reference preserved but deactivated after replacement. 54 domain tests and one targeted Chrome test passed; screenshot inspected.
- Added master backlog (all requested phases, reported gaps not presumed fixed). Exact commands, sources, limitations and failed-attempt history: docs/MASTER_PHASE01_VERIFICATION_20261001.md.
- Master M12A: loan-level estimated/review/confirmed state, provenance and confirmation timestamp; explicit owner confirmation with complete terms; unconfirmed loans excluded from canonical debt, EMI, home proxies and direct loan advisories. Payment matching cannot confirm guessed terms or restore a pre-confirmation balance. Owned bureau evidence remains supported; missing EMI does not inherit a guess. Migration 0013 backfills safely without changing monetary values/history. 89 domain/migration tests and one Chrome workflow passed. Exact evidence and limitations: docs/MASTER_M12A_VERIFICATION_20261001.md.
- M12A follow-up: parser retains explicit balance presence; legacy default zero requires review. Migration confirmation now requires matching raw/sync/loan identity and supported retained terms. User-created explicit current balances get a timestamp; unknown bureau EMI permits metadata edits while submitted zero remains invalid. 5 evidence/migration + 4 API tests passed, followed by the final combined 156-test gate.
- Master M12B: every usage type counts positive recorded market value as an estimated asset; confirmed Loan ledger debt counted once; costs/income do not manufacture asset values or liabilities. Net-worth vehicle cache revision and API aliases updated, all-history costs labelled separately. Catalog updates preserve omitted owner financial values and explicit zeros. Initial 77-test run exposed this reset; fix passed 21 targeted tests and final combined gate. Chrome passed (9.374 s), screenshot inspected. Exact evidence: docs/MASTER_M12B_VERIFICATION_20261001.md.
- Master M12C: month 0 recorded value; exact elapsed-month SIP/growth; 13 points 0..12; beginning-of-month contribution and rate assumptions explicit; growth cache version/local month anchor. 20 targeted tests passed, followed by final combined gate. Chrome passed (13.817 s), actual Chart.js values checked and screenshot inspected. Exact evidence: docs/MASTER_M12C_VERIFICATION_20261001.md.
- Master M13A: seven Loan register fields use bounded Decimal cents with HALF_UP; numeric API output, exact register posting/home arithmetic, cache revisions and nullable zero semantics preserved. Migration 0014 retains source money/owner identity, applies once and reverses unchanged values without losing later edits. Data reset removes owned snapshots including orphans. Targeted migration/field/runtime/reset checks, 2 Chrome workflows and final whole-backend gate passed (628 passed, 16 browser skips, exit 0). The gate also corrected an old Decimal/float assertion and Travel usage's UTC/local-day mismatch, with deterministic midnight coverage. No operator DB migration. Exact evidence: docs/MASTER_M13A_VERIFICATION_20261005.md.
- Master M13B: remaining 17 Loan-domain currency fields use the same bounded cents boundary. Migration 0015 retains raw values/linkage, applies once, guards rollback and owner reset, and reports child/register rounding differences without rewriting the register. Computed foreclosure allocation conserves each component and transaction; preserved history may retain different component amounts. Finalized evidence makes reconciliation repeat-safe and prevents review from erasing settlement state. Explicit accepted/requested zero cannot infer an unfinalized closure; later corrections do not reverse an already posted settlement. Numeric API/cache/canonical/tax/document boundaries and atomic correction passed focused gates, 2 distinct Chrome workflows and the final whole backend (671 passed / 17 browser skips / exit 0). Career DNS-only fixture repair also passed without changing runtime URL validation. Exact evidence/limits: docs/MASTER_M13B_VERIFICATION_20261005.md.
- Prior T07: exact itinerary discount/range/target and quote-string fixes; 95 travel tests, 3 Chrome tests, Django check and source-native offline/restart verification passed. See docs/TRAVEL_T07_VERIFICATION_20261001.md. No redo.
- Prior source/native config precedence, durable recovery, travel source/freshness/map/provider work remains. See docs/TRAVEL_CONTINUATION_VERIFICATION_20260930.md. Prior frozen candidate predates T07 and this master remediation.

## Files changed

M13A additionally: apps/loans/money.py and migrations/0014_loan_money_decimal.py (new); Loan model/snapshot, serializers, loan_intelligence/payment_review/views updates; loan_foreclosure_service.py; financial_intelligence.py/financial_relationships.py; bureau/credit/integrations tax/voice updates; apps/users/services.py reset. New tests/test_loan_money_field.py, test_loan_money_migration.py, test_loan_money_runtime.py, test_loan_money_retention.py; docs/MASTER_M13A_VERIFICATION_20261005.md. Gate follow-up: travel/cache.py usage local date and tests/test_travel_providers.py midnight coverage; test_loan_lifecycle_and_reports.py exact Decimal assertions.

M13B additionally: migrations/0015_related_loan_money_decimal.py, LoanRelatedMoneySnapshot and 17 fields; shared Loan serializers/runtime/foreclosure/parser, financial_intelligence, tax_optimizer, user reset, document_review and public correction API; tests/test_related_loan_money_migration.py, test_loan_foreclosure_money.py, test_loan_related_money_runtime.py, expanded field/runtime/browser checks and fixed historical migration-test target states. docs/MASTER_M13B_PLAN_20261005.md records scope; docs/MASTER_M13B_VERIFICATION_20261005.md records actual evidence. See git status for exact dirty inventory.

M13B full-gate follow-up: tests/test_career_recruiter_and_evidence.py mocks public DNS alongside the existing mocked page responses, avoiding live lookup failures. Production URL validation is unchanged. apps/loans/money.py docstring now reflects its related-field use; behavior unchanged.

requirements.txt; apps/ml_engine/services/tax_policy.py (new), tax_optimizer.py; apps/integrations/views.py and services/verified_intelligence.py; templates/integrations/tax_optimizer.html; static/js/tax_optimizer.js; tests/test_native_tray.py, test_tax_policy.py (new), test_user_data_browser.py; docs/MASTER_PHASE01_VERIFICATION_20261001.md (new); this checkpoint and ALFRED_DEEP_REVIEW_BACKLOG.md (new).

M12A additionally: apps/loans/models.py, serializers.py, views.py, services/loan_intelligence.py, payment_review.py, migrations/0013_loan_verification.py (new); apps/expenses/services/financial_intelligence.py; apps/integrations/services/credit_loan_sync.py, credit_score_tracker.py; apps/ml_engine/services/recommendation_engine.py, voice_assistant.py; templates/loans/list.html; static/js/loans.js; tests/test_loan_lifecycle_and_reports.py, test_loan_verification.py (new); docs/MASTER_M12A_VERIFICATION_20261001.md (new). Also updates the shared integrations/tax/browser files above. Use git status for the exact current inventory.

M12A/B follow-up: credit_report_parser.py; tests/test_bureau_balance_evidence.py and test_loan_verification_api.py (new); apps/mobility/views.py; alfred_ai/services/calculation_risk.py; static/js/expenses.js; templates/expenses/list.html; tests/test_vehicle_accounting.py (new), test_document_center_and_statement_import.py; docs/MASTER_M12B_VERIFICATION_20261001.md (new). M12C: apps/investments/views.py, templates/investments/list.html, tests/test_investment_projection.py and docs/MASTER_M12C_VERIFICATION_20261001.md (new), plus shared browser test.

## Migrations

Created loans/0013 verification, 0014 Loan-register Decimal currency/snapshot and 0015 related Loan currency/snapshot migrations. Upgrade, reconciliation, repeat-safe application and edit-preserving rollback validated on disposable SQLite databases only, including a nondefault alias for 0015. No migration applied to a user database. Model/migration drift check passed. Existing mobility 0010-0012 were previously validated in isolated runtimes; older user database status unchanged. Other monetary-domain stages remain pending.

## Focused tests

Interpreter: F:\ALFRED\.venv\Scripts\python.exe, PyCharm Python 3.12.2, pip. MUST get_python_environment(filePath="manage.py") before every Python invocation.

Isolated backend variables: ALFRED_LOCAL_RUNTIME=true; ALFRED_AUTO_TRAIN_ON_STARTUP=false; ALFRED_DATA_DIR=F:\ALFRED\artifacts\master-validation-20261001; DATABASE_URL=sqlite:///:memory:; CACHE_BACKEND=django.core.cache.backends.locmem.LocMemCache; CACHE_LOCATION=alfred-master-validation; ALFRED_RUN_BROWSER_TESTS=false. Browser runner selects isolated file SQLite; browser data dir master-browser-validation-20261001. Do not load the operator's real config/local.env for validation.

Command: -m unittest tests.test_native_tray -v
Passed: 7; Failed: 0; Skipped: 0; 0.033 s. artifacts/phase0-tray-20261001.log.
Command: manage.py test tests.test_native_tray tests.test_native_runtime tests.test_native_launcher tests.test_native_observation tests.test_durable_queue --noinput --verbosity 1
Passed: 32; Failed: 0; Skipped: 0; 2.209 s. artifacts/phase0-native-20261001.log.
Command: manage.py test tests.test_auth_pages tests.test_platform_hardening tests.test_production_readiness_contracts tests.test_local_config tests.test_financial_baseline_alignment tests.test_financial_relationships --noinput --verbosity 1
Passed: 53; Failed: 0; Skipped: 0; 48.544 s. artifacts/phase1-django-regression-20261001.log.
Command: manage.py test tests.test_tax_policy tests.test_remaining_task_closures.TaxDeductionTests tests.test_financial_baseline_alignment tests.test_advisory_evidence_freshness tests.test_operational_hardening tests.test_application_smoke --noinput --verbosity 1
Passed: 54; Failed: 0; Skipped: 0; 32.608 s. artifacts/phase1-tax-domain-final-20261001.log.
Command: scripts/run_browser_regressions.py tests.test_user_data_browser.UserDataBrowserTests.test_tax_planning_uses_selected_year_and_income --browser Chrome --require-browser --artifact-dir artifacts/browser-tax-policy-20261001 --proof-label tax-policy-20261001
Passed: 1; Failed: 0; Skipped: 0; 10.724 s (19.672 s runner). Screenshot inspected. artifacts/phase1-tax-browser-20261001.log.
Command: manage.py check; manage.py makemigrations --check --dry-run (separate invocations with environment preflight)
Passed: both exit 0, no issues/drift. artifacts/phase1-check-20261001.log and phase1-migrations-20261001.log.
Command: node --check static/js/tax_optimizer.js; git diff --check
Passed: both exit 0.

Earlier failed attempts: initial tax test had a cold reference-cache fixture failure; first domain run found stale legacy-reference refresh behavior (fixed); a follow-up fixture omitted stale_after (fixed). Final domain run above passed all 54 including these regressions. Do not count failed attempts as passing evidence.

M12A command: manage.py test tests.test_loan_verification tests.test_loan_lifecycle_and_reports tests.test_financial_baseline_alignment tests.test_financial_relationships tests.test_document_center_and_statement_import tests.test_remaining_task_closures tests.test_tax_policy --noinput --verbosity 1
Passed: 89; Failed/Skipped: 0; 48.680 s; exit 0. artifacts/m12a-domain-final-20261001.log and result JSON. Data dir loan-validation-20261001; otherwise same isolated variables. System check, migration drift, node --check static/js/loans.js, and git diff --check also passed. Initial migration-test historical user-state error was fixed; earlier 88-domain run also passed. Chrome workflow passed (11.179 s) after a stale live-refresh button click was handled by bounded retry; final screenshot proof is recorded in the M12A verification note.

Final M12A/B/C command: manage.py test tests.test_loan_verification tests.test_loan_verification_api tests.test_bureau_balance_evidence tests.test_vehicle_accounting tests.test_mobility_vehicle_dashboard tests.test_loan_lifecycle_and_reports tests.test_financial_baseline_alignment tests.test_financial_relationships tests.test_document_center_and_statement_import tests.test_remaining_task_closures tests.test_tax_policy tests.test_calculation_risk_snapshot tests.test_user_data_acceptance tests.test_investment_projection tests.test_investment_and_relationship_advisory --noinput --verbosity 1
Passed: 156; Failed/Skipped: 0; 120.950 s; exit 0, finish 23:46:30 +05:30. artifacts/m12-finance-final-20261001.log and result JSON. Data dir finance-m12-validation-20261001; local runtime true, startup training false, in-memory DB, locmem cache. Final system/drift checks clear in m12-finance-check/migrations-20261001.log. Node syntax checks for expenses/loans/investments and whitespace check clear. Intentional mocked database-lock traceback is passing resilience coverage.
Vehicle Chrome: 1 passed / 0 skips, 9.374 s, exit 0; artifacts/m12b-browser-20261001.log and browser-vehicle-accounting-20261001 summary. Projection Chrome: 1 passed / 0 skips, 13.817 s, exit 0; artifacts/m12c-browser-20261001.log and browser-investment-projection-20261001 summary. Both screenshots inspected. Projection narrow 20-test log has mistaken 20261002 filename suffix; actual run was Oct 1, and the final combined gate uses the correct suffix/standard flags.

## Full-suite evidence

Current M13B final gate: manage.py test --noinput --verbosity 1; 688 run, 671 passed, 17 disabled-browser skips, zero failures/errors, 641.053 s; exit 0 at 2026-10-05 15:40:05 +05:30. artifacts/m13b-backend-verified-20261005.log and result JSON. All M13A/B application paths and the deterministic Career fixtures are covered. Data dir related-loan-backend-verified-validation-20261005, memory SQLite, locmem; no operator configuration/helper PYTHONPATH. Initial M13B attempt: 688 run / 669 passed / 17 skipped / 2 Career fixture DNS errors, 746.737 s, exit 1; artifacts/m13b-backend-final-20261005.log/result JSON. The five-test Career module passed after fixture repair and the final full rerun cleared both errors. Do not count the initial attempt as passing evidence.

M13A gate: manage.py test --noinput --verbosity 1; 644 run, 628 passed, 16 disabled-browser skips, zero failures/errors, 617.345 s; exit 0 at 2026-10-05 06:14:12 +05:30. artifacts/m13-loan-backend-final-20261005.log and result JSON. This includes M12A/B/C and M13A runtime changes, final migration-marker/field/reset tests, exact-value assertion and Travel midnight fix, and predates the new M13B changes. Earlier initial M13A run: 643 run, 625 passed, 16 skipped, one failure/error each, 639.053 s, exit 1; artifacts/m13-loan-backend-20261005.log and result JSON. Fixes passed targeted tests and the final whole gate; do not count the first attempt as passing.
Master Phase 1: original run interrupted with no summary/result and no surviving process. Resumed manage.py test --noinput --verbosity 2 completed: 556 run, 543 passed, 13 skipped, 0 failed; 576.488 s; exit 0 at 2026-10-01 18:36:16 +05:30. Evidence artifacts/phase1-backend-gate-resumed-20261001.log and phase1-backend-gate-resumed-20261001-result.json. This predates M12A/B/C runtime changes; the current gate above supplies whole-backend evidence for them and M13A.
Historical pre-T07 full backend: 529 run, 517 passed/0 failed/12 skipped, 562.575 s, exit 0; artifacts/travel-backend-20261001.log and result JSON. Historical 12 Chrome workflows passed separately. These predate current changes.
Historical frozen build/offline runtime: 12,637 inspected files, private-file scan passed; frozen offline handoff 0.078 s, save/edit/restart/queue recovery passed, zero live sources. SHA256 1d3174cf8c9a3ad80063aacd624a8f355537d780c4f07eca086c6ac9c20b9c0c. September candidate does not contain T07 or master remediation; do not promote it as current.

## Travel status

Dynamic origin: M02 explicit/default/bare-city and around semantics pending focused remediation.
Dynamic discovery: existing Wikivoyage provider; master dynamic-first/fallback behavior pending.
Candidate pool: M03 >3 pool not yet verified/remediated.
Pagination: M03 durable batches/show-more pending.
Primary route: existing ORS implementation; M04 mode resolution pending.
Alternative routes: structural support exists; M05 actual provider alternatives pending.
Selected route: M05 persistence/scoped recalculation pending.
Route POIs: M07 route-corridor implementation pending.
50-km detour: M07 actual road-detour verification pending.
Map: existing Leaflet geometry/markers/pan work preserved; master route selection/layer matrix pending.
Weather: existing Open-Meteo/freshness/horizon guards; M09 focused reconciliation pending.
Hotels: opt-in authorized Duffel stays; unverified external search links labelled; no new live proof.
Flights: opt-in Duffel; estimates separate; no new live proof.
Trains: live inventory unverified; official links only.
Buses: live inventory unverified; external links only.
Permits: authority/reference trust guards preserved; no new live checks.
Caching: shared cache/lease/quota work exists; retention/scoped invalidation/circuit telemetry pending.

## Finance status

Tax: FY 2025-26 / AY 2026-27 ordinary-income Decimal engine and tests implemented. All other FY/AY rejected; no claim to implement TY 2026-27 or complete filed-return rules. Dashboard explicitly assumes resident/under-60/salary. Automatic deduction leads and HRA/home-loan/action eligibility still need focused work (M01C); planning assumptions labelled.
Money Decimal migration: Travel T07 calculations complete. M13A/B cover 24 Loan-domain currency fields in source and disposable SQLite; originals/linkage retained, numeric JSON preserved, exact runtime allocation and finalized settlement guards implemented. M13B focused gates, 2 distinct Chrome workflows and final full backend (671 passed / 17 browser skips / exit 0) passed. Next M13C Investment register has three currency fields; Expense/BankAccount normalization requires a later dedicated deduplication/source-evidence stage. No operator database migration.
Loan detection: M12A implemented; estimated/review loans remain visible but do not count toward debt/EMI/home proxies. Explicit owner confirmation or supported owned raw bureau evidence is required. Parser missing/explicit-zero evidence is preserved. Migration 0013 preserves values/history and is test-validated only. Payment-level acceptance is distinct from loan verification. Full M12A evidence is in its verification note.
Vehicle net-worth semantics: M12B implemented; recorded positive market-value estimate is an asset for all usage types; actual confirmed loans count once; operating costs remain separate. Owner values survive catalog edits. Focused vehicle/mobility/browser and combined finance gates passed; no schema change or user DB migration.
Investment projections: M12C implemented; exactly months iterations; month0 recorded value, 0..12 elapsed months, beginning-of-month SIP and entered annual rate/1200 assumptions, month-aware/versioned cache. Domain/browser and combined finance gates passed.

## Security status

HTTP: shared Travel public-HTTPS transport preserved; remaining Career/direct fetch paths reported unsafe (M14A), pending.
Uploads: existing document/OCR/privacy protections preserved; master central resource-cap requirements pending.
Passwords: M14B standard validators pending focused remediation.
Authentication: M14C-D BasicAuthentication/TLS and scoped throttles pending.
Privacy: family opt-in defaults and explicit source-retention modes pending reconciliation (M14G-H).
Token encryption: current encryption exists; verified re-encryption/key retirement workflow pending (M14I).
Django: patched to 6.0.8; Phase 1 full regression passed (543 passed / 13 skipped).

## Remaining P0

M13 staged monetary storage; M14 HTTP/auth/upload/error/privacy/key-rotation gaps. User note reports these; only targeted reads were made, and no blanket security/finance completion is claimed. Core M01B and M12A/B/C implemented; complete tax deduction evidence/eligibility tracked separately as M01C.

## Remaining P1

M02-M10 expanded Travel behavior/test matrix; M01C tax deduction provenance/eligibility; M12D planning assumptions; dependency/package reproducibility; master CI/protection; new frozen/clean-second-PC/installer/LAN/manual release acceptance. Phase 1 full gate passed; final master release gate and remote CI remain pending.

## Remaining P2

M15 bounded Travel telemetry retention preserving current-month quota/active rows and all evidence/plans/history. M16 scoped enrichment/invalidation and telemetry. M17 unsupported experimental ML exclusion. No obsolete “no remaining P0” claim from the old Travel checkpoint applies to the master note.

## API keys required

No keys needed for current tax/financial work. Existing Travel configuration: TRAVEL_USE_MODE=personal_noncommercial or licensed TRAVEL_OPEN_METEO_API_KEY; TRAVEL_ORS_API_KEY; authorized public HTTPS TRAVEL_OVERPASS_URL; optional Duffel Stays/flight access plus TRAVEL_DUFFEL_ALLOW_PAID_SEARCH=true; optional Brave storage/paid-search authorization or authorized SearXNG. Rail/bus require real authorized inventory agreements. Keys only in untracked config/local.env. Wiki no key; disable with TRAVEL_WEB_ENABLED=false. No paid calls this session.

## Current blockers

None for independent code remediation. Keyed/licensed live checks and clean-PC/manual release checks remain external acceptance limits. Existing operator config/local.env had previously unresolved PostgreSQL/Redis targets; not touched. Always use isolated variables for tests. No cloud wiring or credentials added.

## Decisions made

Local/LAN Windows-first; preserve existing models/ownership/history/native durability. Current master P0s outrank old T09 continuation. Same-series Django security patch only. Tax policies are source-reviewed version tables, not live scraped rules. Correctly reject unsupported years/special-rate income. Retain old reference history while deactivating obsolete tax table. No bookings/payments/card collection, secret changes or release promotion.

## Do not redo

Do not repeat the whole repository audit, T07 monetary travel work, historical preview audit, Phase 1 gate or completed focused tests without new failures/changes. M13B's final full gate passed and its session is closed; do not rerun it before new source changes justify another gate. Existing failed attempts are documented, not blockers after passing reruns. Do not use real runtime DB/config or old frozen binaries for current acceptance. Read UTF8. Preserve remaining backlog and this resumable checkpoint.

## Exact next task

Implement M13C: Investment.invested_amount, monthly_sip and current_value only. Reuse the strict HALF_UP currency/retained-original/apply-marker/owned rollback pattern; preserve annual_return_rate, parse_confidence, provider NAV/rates/scores and raw portfolio evidence. Cover numeric serializer/output, Decimal/rate arithmetic in investment summary/allocation/portfolio mix, canonical asset/tax totals, document correction/retry persistence, nullable/zero compatibility and owned reset. Preserve projection semantics already verified in M12C. Scoped orientation is retained in artifacts/m13c-storage-scope-graph-query-20261005.log. Expense.amount, Expense.closing_balance and BankAccount.current_balance are a later stage because normalized money also affects import fingerprints/deduplication, bank syncing and Loan detection. No real-data migration or blanket FloatField replacement. Do not restart the whole-repository audit or resume T09 first.

## Repository housekeeping

Normal git diff --check passed (artifacts/m13-final-diff-check-20261005.log/result JSON). Do not use core.autocrlf=false as a workaround for warnings; it makes CRLF content look like wholesale whitespace changes. No files were rewritten by that failed check.

Graphify code refresh passed: 6,524 nodes / 17,885 edges, AST-only, no clustering/semantic extraction/model calls/HTML. Graphify was missing from PATH and the application environment. Temporary graphifyy 0.9.76 helper dependencies were installed with pip --target outside the repository; the application venv/requirements were not changed. Temporary target is recorded in artifacts/m13-graphify-tool-path-20261005.txt. Read the local .codex/skills/graphify/SKILL.md before using its workflow; follow new AGENTS.md guidance to query the graph before codebase questions and refresh it after source changes. The code index omits 24 unsupported files and 33 symbol-free sources; do not treat it as full semantic evidence.

M13B first source refresh passed, 7,220 nodes / 18,816 edges; final refresh after the Career fixture and money helper docstring updates passed, 7,220 nodes / 18,817 edges. Both use the same AST-only/no-cluster mode and 24 unsupported / 33 symbol-free limitations. Latest evidence: artifacts/m13b-graphify-update-complete-20261005.log/result JSON. Application behavior was unchanged by the docstring update. Full backend, Chrome, system/drift and whitespace gates passed; no active process remains.

The helper path may disappear when temporary files are cleaned; if missing, set up an isolated helper again. Set its PYTHONPATH only inside the separate Graphify command process, never for application tests/runtime (helper NumPy dependencies differ). Use the configured Python executable and perform the mandatory preflight for every Python command. Refresh evidence: artifacts/m13-graphify-update-final-20261005.log/result JSON. Initial missing-module attempt is retained as failed housekeeping history, not an application blocker. No active process remains.

## Exact next command

M13B verification passed; all root test/refresh sessions are closed. Next-stage orientation starts with:
Get-Content -Encoding UTF8 docs/MASTER_M13B_VERIFICATION_20261005.md
Before code exploration, in a separate Graphify command process after Python preflight:
$loanGraphToolTarget=(Get-Content -Encoding UTF8 artifacts/m13-graphify-tool-path-20261005.txt -Raw).Trim()
$env:PYTHONPATH=$loanGraphToolTarget
& 'F:\ALFRED\.venv\Scripts\python.exe' -m graphify query 'Investment monetary storage summary allocation portfolio correction retry'
Then use focused source reads after graph orientation:
rg -n 'FloatField|invested_amount|monthly_sip|current_value|annual_return_rate' apps/investments/models.py apps/investments/serializers.py apps/investments/views.py
rg -n '_create_or_update_investment|_portfolio_mix|_apply_investment_correction|_retry_investment_document' apps/investments/services/portfolio_intelligence.py alfred_ai/services/document_review.py
Before any Python command: get_python_environment(filePath="manage.py"), then the isolated variables above.
