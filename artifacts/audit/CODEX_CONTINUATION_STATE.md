# ALFRED CODEX CONTINUATION STATE

## Repository

Branch: codex/native-runtime-hardening-20260918
Base commit: b4e89742717d0f4ce1d8b6e49ccb7b6b6abde525 (clean starting point for master note).
Verified engineering source commit: db2f86d4f0101665abb0666a98644f91a3eda5ac, created during pre-Windows preparation on 2026-10-05. It preserves Phase 0/1, M12A/B/C and M13A/B source, migrations, tests and phase documentation. Read `git rev-parse HEAD` for the latest preparation commit.
Working tree at this checkpoint update: Windows setup, dependency constraints, encrypted-recovery scripts, project-local skills, hardware/tooling notes, the post-restore Ollama/Codex handoff and historical SQLite recovery checks are committed and pushed. This documentation update records the user's reported OneDrive upload of the Desktop recovery bundle; the pendrive remains an alternative. Generated logs, browser proof and private/runtime data remain local/ignored. Safe audit/reinstall documents are explicitly allowed in Git. No installer promotion.

## Active pre-Windows task

The user has superseded engineering continuation with complete PC cleanup preparation. Do not resume M13C or execute post-Windows restoration now. The user reports uploading the prepared Desktop recovery folder to OneDrive and supplied a sharing link privately. Do not place that link or its access identifiers in Git. A 6 GB pendrive remains an alternative. Read `docs/WINDOWS_ENCRYPTED_RECOVERY.md` and the generated `artifacts/reinstall/PRE_REINSTALL_FINAL_STATUS.md`. The source/recovery implementation was pushed and independently verified at `5bf9cbe3e4c0c609e5fff5adf135ebcdc6a213b4`, which is the application source checkpoint bound into the encrypted archive. Later safe documentation commits may advance HEAD; independently verify the live remote after pushing them.

On 2026-10-06 the user confirmed GitHub login, 2FA, recovery email, off-PC archive-password storage, required-secret recovery and Windows installation media: all YES. GitHub LFS capacity is no longer a gate for OneDrive or the pendrive. No temporary GitHub backup repository was created and no private backup uploaded to permanent source. Microsoft/OneDrive login, 2FA/recovery and recovery-email readiness after the wipe remain unconfirmed; ask YES/NO only, never credentials. ALFRED server and worker were gracefully stopped, with no active database writer. Docker was not running; WSL shutdown completed. Both main runtime locations were inventoried, together with a historical first-start profile, six earlier operator backups, cleanup/pre-update snapshots and unique private validation inputs. The offline historical Docker VHDX is required and included, rather than assumed unnecessary. All 17 required original and recovered SQLite databases passed integrity checks.

The actual private staging backup outside Git contains 51,617 files totaling 303,836,313 bytes, plus internal manifests. A required historical WAL of 4,120,032 bytes was discovered by the strict verifier and added unchanged beside its staged database; every raw historical database was checked for this gap. Original/staged/extracted hashes and all 17 SQLite checks pass. Historical DB/WAL/SHM bytes are preserved: the verifier uses disposable shadow copies, including committed WAL state, rather than checking only six backup-API snapshots. Four focused synthetic recovery tests and Graphify update passed; completed application suites were not repeated. Detailed paths, timestamps and hashes remain inside the encrypted archive. The compromised historical signing key is retained privately for recovery only; rotation/re-encryption remains deferred until verified restoration.

Real encryption and full local recovery validation are complete: one 7z AES-256/header-encrypted volume, `alfred-private-backup-20261006.7z.001`, 67,915,749 bytes. SHA256: `7a54b209a4bf5f8bca8d7346acfbe1c468629f88695df00a38736a68a7f6eed7`. The user entered the password only at native masked prompts; it is absent from commands, scripts, logs and Git. The prepared Desktop folder is `ALFRED_RECOVERY_20261006`, containing encrypted files, official portable 7-Zip, safe setup/restore/tooling notes and `VERIFY_SHA256.ps1`. Desktop copy hashes pass, and the checker rejects an incomplete synthetic copy. No plaintext private data or password is in the handoff folder.

The OneDrive upload is USER-REPORTED, NOT YET VERIFIED. The sharing page returned HTTP 200, but no backup file was downloaded; no browser or OneDrive connector is available to perform its normal Download action here. The new `C:\ALFRED_ONEDRIVE_REMOTE_VERIFY` directory is reserved for a fresh web download of the whole bundle, outside Desktop, staging and sync caches. Preserve the downloaded ZIP, safely extract into a new directory, compare against the trusted 16-file upload-time hash snapshot, then reuse the trusted `prepare_encrypted_recovery.ps1 -Mode VerifyDownloaded` helper with native masked password prompts. Require archive integrity, complete extraction, all 51,617 private hashes and all 17 SQLite checks. No sharing-page response or local copy is evidence of cloud recovery. The physical pendrive is also unverified and remains an alternative.

Desktop storage will be erased. After reinstall, download the retained OneDrive bundle or copy it from the verified pendrive back to Desktop, follow the saved restore guide, and retain that backup until finance/data/source/native recovery and historical-state preservation are proven. If using the pendrive, disconnect it during disk cleanup and do not reformat it into installation media. `SAFE TO REINSTALL WINDOWS = NO` until the selected retained-copy proof and its account-recovery readiness pass. Keep originals, staging and the upload-time Desktop bundle unchanged while comparing the cloud copy; do not install Ollama, rotate the old signing key or start feature work.

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

## M13C completion after Windows restoration — 2026-10-06

M13C Investment currency storage is implemented and verified in the isolated
`F:\ALFRED_DEV\m13c` worktree on `codex/investment-money-m13c-20261006`, based on
`5687a82ecb43702e90822f19e958b164dfe4cfdd`. Continue development there. The restored
source remains in `F:\ALFRED\alfred_ai` on the original development branch and its
native runtime remains active using `F:\ALFRED\restored-runtime`. No M13C migration
has been applied to private/operator databases. The code changes are uncommitted
and have not been merged or pushed.

The three Investment currency fields use bounded HALF_UP Decimal cents and owned
retained-original/apply-marker/guarded rollback evidence. Numeric API output,
summary/allocation/rate arithmetic, portfolio mix, canonical assets/tax callers,
document correction/retry, atomic PDF persistence, explicit-zero behavior and
owned orphan-snapshot reset are covered. Rates, confidence, NAV and raw evidence
remain separate. Projection timing and local-month cache semantics are preserved.

Final backend: 709 run, 692 passed, 17 browser skips, exit 0. Full serial Chrome:
18 passed, zero skips, exit 0. Investment-specific Chrome also passed independently.
The initial concurrent browser attempt crashed in Windows Python during test-user
password creation; its log is retained and the serial retry passed. System/drift,
whitespace and AST-only graph gates passed (7,398 nodes / 19,142 edges).
Evidence: development `docs/MASTER_M13C_VERIFICATION_20261006.md` and
`artifacts/audit/M13C_VERIFICATION_RESULT_20261006.json`; logs/proof summaries under
`F:\ALFRED_RECOVERY\m13c-*`.

Exact next development task: the dedicated Expense.amount, Expense.closing_balance
and BankAccount.current_balance stage. Start with a scoped Graphify query tracing
normalization, import fingerprints/deduplication, bank syncing and Loan detection.
Preserve source evidence, ownership and linkage, and continue isolated validation.
Do not repeat completed M13C gates without new source changes or failures.

Restoration and safe operator signing-key retirement were completed separately;
see `docs/WINDOWS_RESTORATION_VERIFIED_20261006.md`. Local real-account sign-in and
private finance/Travel/media UI acceptance remain unconfirmed, and historical data
plus the Docker VHDX require classification. Keep the Desktop backup, pristine
copies and recovery repositories. Do not promote M13C to the operator runtime as
part of development testing.

## Current development checkpoint: M13D — 2026-10-06

This supersedes the historical pre-Windows and uncommitted-M13C instructions above.
Continue in `F:\ALFRED_DEV\m13c`, branch
`codex/expense-bank-money-m13d-20261006`. The verified M13C implementation is
already preserved at `4ac6c100dad83193244d2933814bf1d48dbbcde9`; do not restart it
or completed audits. Hosted Codex completed the existing partial M13D changes.

Expense.amount/closing_balance and BankAccount.current_balance now use bounded
HALF_UP Decimal cents. Migration `expenses.0005_expense_bank_money_decimal`
retains original values, ownership, links, normalization and apply markers;
guards rollback and owned reset; and retains original transaction identity for
historical fingerprints/reference deduplication. Transfers and independently
recorded bank balances remain authoritative. Raw evidence, null/zero semantics,
numeric API totals, atomic invalid-input rejection, account posting and Loan
callers are covered. Remaining monetary domains and M14 remain outside this stage.

Final backend: 737 run / 718 passed / 19 disabled-browser skips / no failures or
errors, exit 0, 641.684 s. Full serial Chrome: 19 passed / no skips / exit 0,
125.521 s, driver-backed. Focused M13D gate: 34 passed; combined synthetic rehearsal:
1 passed; Loan/foreclosure compatibility gate: 38 passed; focused Expense Chrome:
1 passed. Drift and whitespace gates passed. Final AST-only index: 7,498 nodes /
19,529 edges, with the recorded 26 unclassified / 35 symbol-free limitations.
Detailed failed-attempt history and contracts are in
`docs/MASTER_M13D_VERIFICATION_20261006.md`. Logs/proof remain outside Git under
`F:\ALFRED_RECOVERY\m13d-*`. An unrelated untracked restoration verification
document is preserved and excluded from the M13D commit.

Validated M13D source commit: `a78ba533b39285745e696b52569a69dafd952d69`.
The subsequent combined private-copy rehearsal passed for exactly
`investments.0004_investment_money_decimal` and
`expenses.0005_expense_bank_money_decimal`: 2 Investment, 1,739 Expense and
2 BankAccount records/snapshots reconciled, zero currency or aggregate balance
mismatches, all unrelated fields/tables unchanged, 1,735 unchanged statement
fingerprints/reference signatures, and 834 preserved transfer legs. The private
values already had exact cents; no rounding adjustment was needed. Repeat apply
changed nothing; a second copy reversed to exact original application data.
SQLite integrity passed and foreign-key violations were zero before/after.

A separate verification process independently proved the fresh backup's schema,
all 66 SQLite table counts/values through bidirectional SQL EXCEPT, integrity,
foreign keys and SHA256. Source DB/WAL/SHM bytes still match the capture.
Private DB unchanged: YES. Readiness for controlled live migration: YES for this
verified source/database state. No M13C/D live migration, runtime promotion, push,
release or installer promotion was performed. Detailed private evidence/copies
are retained at `F:\ALFRED_RECOVERY\m13cd-private-rehearsal-20261006`; safe summary
is `artifacts/audit/M13D_VERIFICATION_RESULT_20261006.json`.

Exact next action: obtain explicit controlled-live-migration authorization; stop
all runtime writers, revalidate the independently verified backup against current
DB/WAL/SHM, promote validated development source to the runtime checkout, apply
only the two named migrations, reconcile and restart. If bytes changed after
capture, make and independently verify another fresh backup first. Keep all
historical backups. Do not restart completed audits or M13C/D implementation.

## Controlled M13C + M13D LIVE completion - 2026-10-07

This supersedes earlier private-DB-not-migrated and authorization-pending entries.
The user explicitly authorized this controlled live operation. Live source is
F:\ALFRED\alfred_ai, HEAD a9d096ea55839269fe6fce14d4f11ea2cbf05336. It was safely
fast-forwarded from 5687a82ecb43702e90822f19e958b164dfe4cfdd. Original local changes
and conflicting untracked documents were preserved outside Git before promotion.
No new product source changes, deployment commit, release or push were made.

Live DB F:\ALFRED\restored-runtime\db.sqlite3 has exactly the two authorized
migrations applied: investments.0004_investment_money_decimal and
expenses.0005_expense_bank_money_decimal. Dependencies were already applied;
full plan afterward is empty. Native runtime writers were gracefully stopped,
process/lock checks passed, and the fresh backup was independently reverified
before application. Runtime secrets/media/models were preserved unchanged.

Protected pre-migration backup:
F:\ALFRED_RECOVERY\m13cd-private-rehearsal-20261006\fresh-pre-migration-backup.sqlite3
SHA256 29b06e610ea008b1d5cb042a21b7e50bf9ee2ef95f11a1083ee957ce5c8ffcb0.
It matched the live DB/WAL/SHM capture before application and remains intact.
All 66 original SQLite tables passed independent schema/counts/bidirectional
SQL EXCEPT/integrity/foreign-key checks. Original backup and proof are unchanged.

Operation evidence: F:\ALFRED_RECOVERY\m13cd-live-migration-20261007.
Post-migration-before-restart.sqlite3 SHA256:
971228fd90387e4947d42d3e3a0f3aff12e97b7440ac7878c1a4e92cefeaf4ed.
Post-final-running.sqlite3 consistent snapshot SHA256:
02e42ebd7d0d0a55d097191d51489919f7b56c35d268e4b664f67a653630c267.
Detailed before/after source-file hashes, snapshots and private totals are in
live-migration-result.json and final-operation-result.json outside Git.

Pre-restart reconciliation passed all 66 original tables including sequence state,
with exactly 3 new snapshot tables (69 tables after migration). 1,739 Expenses,
2 BankAccounts, 2 Investments and their owned conversion snapshots retained;
1,735 fingerprints/reference signatures unchanged; 834 transfer legs preserved;
155 monthly groups reconciled. Zero currency/balance/aggregate/identity/ownership/
reference mismatches, duplicate fingerprint excess or foreign-key violations.
Private currency values already had exact cents: zero rounding adjustments.
Only the two intended migration-state entries were added. Exact resulting schema
matches the successful private-copy rehearsal. Database integrity passes.

The initial post-apply harness stopped on cached executor state after successful
application. Failure log/snapshot are retained. A fresh executor confirmed both
migrations recorded with no pending plan; resumed reconciliation passed without
reapplying either migration. No unexplained data mismatch or rollback occurred.
Checkout CRLF/LF differences were verified as line endings only; exact tested
migration file bytes and Git blobs were checked before application. Git index
stat refresh confirmed no product source changes afterward.

ALFRED restarted, gracefully stopped, and restarted again to verify persistence.
It is running at http://127.0.0.1:8000/. Both actual queued startup worker probes
completed. Final native readiness is 5/5: DB, cache, worker, scheduler and local
security ready. All four health endpoints HTTP 200; DB/cache/ML runtime/startup
checks ok. No pending/scheduled jobs or interrupted claims at final check; a
consistent native queue backup passes integrity. All 69 post-migration tables
were compared across restart with zero business-table changes. Startup added
expected snapshot-model content types (3) and permissions (12); one existing
account login timestamp and session records changed as authentication activity.
All other user fields and credentials are unchanged. Private config/media/model
file hashes remain identical; all 3 referenced uploaded media files are present.
Readonly live Decimal ORM/numeric serialization checks passed all 1,743 affected
register rows. Loan/Travel/document data are preserved by exact table comparisons.

Prior validated source tests remain 718 backend passed / 19 disabled-browser
skips / 737 run; serial Chrome 19 passed / no skips. Completed engineering suites
were not repeated. Live manual page acceptance remains PENDING: browser automation
has no Chrome or in-app browser surface. An operator sign-in question was sent;
UI review has not been confirmed. A login timestamp change does not establish
visual finance/Travel/document acceptance. Do not claim it passed.

Rollback required: NO. Protected verified backup, exact reverse rehearsal,
private runtime config/local source preservation, consistent post snapshots and
failure evidence remain available. Keep every recovery asset. Live DB changed
only through the authorized conversion and recorded normal runtime/auth metadata.

Exact next task: complete existing-account Finance/Expenses/BankAccounts/
Investments/Loans/Travel and uploaded document/media UI acceptance at the live URL.
Then classify preserved historical Docker data before unrelated engineering.
Read LIVE_MIGRATION_REPORT.md and final-operation-result.json in the private
operation evidence directory. Do not restart M13C/D work or completed audits;
do not delete backups. Preserve source HEAD a9d096ea55839269fe6fce14d4f11ea2cbf05336
for the deployed state; this continuation record is a local documentation update.

## Recovery closure and resumed development — 2026-10-07

This supersedes the recovery-only next action above. The user reports opening
ALFRED and finding the data apparently intact. Recovery is closed for development
as USER-REVIEWED PRELIMINARY UI ACCEPTANCE. No systematic Finance, Loans, Travel,
uploaded document/media or other untested UI coverage is claimed passed. Prior
live migration/reconciliation and 718 backend / 19 Chrome results remain recorded;
they were not rerun. Live source remains a9d096ea55839269fe6fce14d4f11ea2cbf05336.

Historical Docker data classification is DEFERRED, not complete. Preserve all
Docker/VHDX, historical databases, encrypted/pristine backups, WAL/SHM, source
preservation and recovery evidence. Later classify from disposable read-only
copies and document provenance/unique data before considering any cleanup. No
backup or recovery asset was deleted, modified or classified during this task.

Development resumed in F:\ALFRED_DEV\m13c on the existing M13D development branch.
Hosted Codex selected M14A Career job-page HTTP because current code still used
requests.get after separate DNS validation, allowing redirects, a second DNS
resolution and unbounded downloads. Reused existing public_http.request: public
HTTPS only, one DNS resolution with pinned peer/TLS hostname, no redirects,
HTML/XHTML MIME allowlist, 2,000,000-byte cap, compression rejection and bounded
transport timeouts. BeautifulSoup consumes bounded bytes for encoding detection.
Existing Workday/Ashby parser fixtures now mock the shared response boundary.

Focused isolated gate: 17 tests passed, zero failures/skips; 3.947 seconds;
Django system checks passed. Command: manage.py test tests.test_career_job_http
 tests.test_career_recruiter_and_evidence tests.test_travel_http --noinput
 --verbosity 1. Python: F:\ALFRED\alfred_ai\.venv\Scripts\python.exe.
Explicit synthetic ALFRED_DATA_DIR, secret, in-memory SQLite and locmem cache
prevented loading live private config/database. No network job fetch was made.
Five new tests exercise actual shared transport from Career: pinned DNS/TLS,
unsafe/private targets, blocked redirects, MIME/compression/declared and streamed
size bounds, sanitized timeout and cleanup. No migration/full audit/full backend
or browser suite was repeated. No runtime promotion, push or release.

M14A is complete for this Career job-page bypass only; other HTTP callers remain
unverified. M14B-I/privacy and remaining monetary domains remain open. T09/M15
retention remains deferred behind these P0s. Exact next atomic task: inspect
current password-validator enforcement at signup/password-change boundaries
(M14B); implement the smallest missing boundary with focused tests using hosted
Codex. If already enforced, advance to M14C/D auth/throttles. Do not repeat whole
repository audits. Local Ollama remains for low-risk work; this security task
used hosted Codex as directed by the hybrid policy.

M14A housekeeping: AST-only Graphify update passed (7,509 nodes / 19,549 edges;
26 unclassified / 35 symbol-free sources). Whitespace checks passed. Graphify's
stale uv launcher failed initially; direct tool interpreter succeeded without
installation or application dependency changes. Git commands use explicit
--work-tree because automatic worktree detection fails in this restored checkout.

## Current post-migration recovery status - 2026-10-07

This section supersedes earlier pre-M13C continuation text. Live source remains
HEAD a9d096ea55839269fe6fce14d4f11ea2cbf05336. Both investments.0004 and
expenses.0005 Decimal migrations remain APPLIED LIVE. No migration, engineering
implementation, financial-record write or cleanup occurred during acceptance.

Read-only consistent snapshot SHA256:
02e42ebd7d0d0a55d097191d51489919f7b56c35d268e4b664f67a653630c267,
identical to the prior verified post-migration snapshot. Integrity PASS,
foreign-key violations 0, 69 total tables (68 application tables plus
sqlite_sequence). All 24 scoped financial/Travel/document tables unchanged:
1739 Expenses, 2 BankAccounts, 2 Investments, 1735 statement identities,
834 transfer legs, 155 monthly groups, financial mismatches 0, fingerprint
duplicates 0. Saved Travel and all 3 referenced media files locally readable.
Private config/media/model hashes unchanged. Protected pre-migration backup
and Desktop encrypted recovery archive retain verified hashes. All preserved.

Native readiness 5/5 PASS, four health endpoints HTTP 200, worker/scheduler
healthy, no interrupted claims/queued/scheduled jobs. ALFRED remains running
at http://127.0.0.1:8000/ without an acceptance-phase restart. Actual local
configured Codex and hosted Codex neutral-response smoke PASS. Finance/migration
routing HOSTED and README routing LOCAL. Ollama uses its existing installation;
no private data included in coding prompts and persistent execution policy unchanged.

Historical Docker classification COMPLETE for the verified inventory. Sole
historical VHDX is Docker bootstrap Linux data; no reachable ALFRED/database/
PostgreSQL/volume payload identified. The initially UNKNOWN inode 12 is empty
ext4 orphan bookkeeping, confirmed by superblock and all 35 blocks. Restored
copy REGENERABLE; identical pristine backup RECOVERED and retained. Each is
100663296 bytes (96 MiB), combined standalone storage 192 MiB. Wider recovery
archive and rollback SQLite remain REQUIRED. Docker/WSL unnecessary for current
native ALFRED or its verified recovery. No install, writable original mount or
deletion. Detailed HISTORICAL_DOCKER_CLASSIFICATION.md is in private evidence.

Every real-account screen and console/network acceptance item remains PENDING:
no connected browser surface is available. Storage readability does not prove
UI acceptance. Checklist: docs/POST_MIGRATION_UI_ACCEPTANCE_20261007.md in live
checkout. Report only statuses and sanitized blockers, keeping credentials,
financial figures, screenshots and document contents local. Operator checklist
completion request sent; no verification yet received. Recovery closure PENDING.

Evidence: F:\ALFRED_RECOVERY\post-migration-acceptance-20261007,
RECOVERY_CLOSURE_REPORT.md, closure-readonly-checks.json, source-verification.json,
hybrid-smoke-result.json and offline ext4 evidence. Initial checker used application
table count against the historical total including sqlite_sequence; fixed count
convention, no data/schema mismatch. First script/log/snapshot preserved.

IMPORTANT CURRENT development HEAD: 6001a4ece2ab37ffba956625cba7b16c59fa5cac
already contains the completed focused M14A Career HTTP fix. It was not promoted;
live remains a9d096e. Do not repeat M14A, M13C/D or completed broad audits.
Prior live baseline: backend 718 passed / 19 disabled-browser skips; Chrome 19
passed. Completed suites not rerun. The existing development 17-test M14A gate
is prior evidence. No high-risk modification began during recovery acceptance.

Exact next action: operator completes the ten local read-only UI checks, compares
figures locally and reports only PASS/FAIL/PENDING plus sanitized blockers.
After acceptance, next provisional engineering task from CURRENT development
checkpoint is M14B signup/password-change password-validator enforcement,
using hosted Codex. If already enforced, advance to M14C/D as recorded.
Keep every backup and recovery asset. No cleanup is authorized.

## M14B password validation completed - 2026-10-07

Development source commit: 18457eff06a1b964c9208093f378f93ec2e86922.
Parent: 6001a4ece2ab37ffba956625cba7b16c59fa5cac (completed M14A Career HTTP fix).
Worktree F:\ALFRED_DEV\m13c; branch codex/expense-bank-money-m13d-20261006.
Current task: M14B standard Django password validation at user-facing writes.
Confirmed root cause: AUTH_PASSWORD_VALIDATORS absent, although signup already
uses UserCreationForm and admin uses Django's password-change form. Enabled
similarity, minimum length (8), common-password and numeric-password validators
in shared settings, inherited by native settings. No custom password API added.
Existing credentials/login are unaffected; no user-row migration or rotation.
Modified source: alfred_ai/settings.py, tests/test_password_security.py.

Five focused new tests cover seven independent weak-signup cases, rejected
password change without hash mutation, rejected and accepted actual admin
password-change requests, and continued login with an existing weak credential.
Before fix: five tests ran, nine failing assertions/subtests, zero errors.
After fix: 30 tests passed, zero failures/skips, 22.486 s; system checks PASS.
Integration gate included tests.test_auth_pages, tests.test_user_profile_api
and tests.test_native_runtime. Test configuration explicitly selects synthetic
ALFRED_DATA_DIR, synthetic signing key, in-memory SQLite, locmem cache and
training disabled. No live private configuration/database/media accessed.
Logs F:\ALFRED_DEV\isolated-tests\m14b-red.log and m14b-green.log.
AST-only Graphify update --no-cluster PASS (7523 nodes / 19565 edges), no model/API.
Whitespace/staged review PASS. Commit reused existing repository author identity
per command; no global Git identity or credential setting changed.

User now provisionally closes recovery and prioritizes development. Reported
visual inspection satisfactory; individually unverified UI checks remain
unclaimed and non-blocking. Docker classification previously completed; retained
Docker/backup/repository cleanup remains deferred housekeeping, never automatic.
Live checkout remains a9d096e and M13C/D stay applied; no source promotion or
live private data mutation. Earlier 718 backend/19 Chrome baseline not rerun.

Next atomic task: M14C remove unused API BasicAuthentication fallback and verify
session authentication/CSRF at the actual profile API using hosted Codex.
Current source still globally allows Basic auth and no application/script caller
uses it. M14D throttles, M14F error leaks and M14G/H privacy remain open; do not
repeat completed M14A/M14B, M13C/D, inferred-loan fixes or comprehensive audits.
Exact next command (in F:\ALFRED_DEV\m13c, with the same isolated environment):
F:\ALFRED\alfred_ai\.venv\Scripts\python.exe manage.py test tests.test_api_session_security --noinput --verbosity 1

## M14C session-only API authentication completed - 2026-10-07

Development source commit: 3497afedc41b090895422b0f1bda7119ec6d8d08.
Parent: 18457eff06a1b964c9208093f378f93ec2e86922 (M14B).
Removed unused global BasicAuthentication fallback. APIs now use existing Django
sessions and require CSRF for authenticated writes; Basic credentials alone are
rejected on HTTP and HTTPS. Application/scripts had no Basic-auth caller. This
is an intentional source API contract change; future API clients must use the
existing login/session/CSRF flow. No live deployment or credential changes.
Modified: alfred_ai/settings.py, tests/test_api_session_security.py,
tests/user_acceptance_scenario.py. Five new actual-profile-API tests verify
blocked Basic reads/writes, session reads, CSRF rejection and valid CSRF writes.
Before fix: 5 ran / 3 failing assertions/subtests. Final integration: 36 passed,
0 failures/skips, 37.727 s (auth policy/pages/profile/family). Synthetic acceptance
fixture suite: 8 passed / 0 failures/skips / 11.508 s. Relevant real Chrome
login/dashboard workflow: 1 passed / 0 skips / 11.996 s. No full suite rerun.
Initial Chrome fixture failed signup because its password resembled its username;
changed only the synthetic shared password to an unrelated valid password and
reran successfully. Production password validation remains unchanged. Logs in
F:\ALFRED_DEV\isolated-tests\m14c-*.log; initial failure evidence preserved.
All tests isolated synthetic configuration, SQLite/locmem or temporary browser
SQLite/media, training disabled. No private runtime/database/provider credentials
loaded. Graphify AST update requested; completion recorded in final checkpoint.

Next verified P0: M14F Career API raw exception disclosure. Current unexpected
exception handlers in recruiter intake, job-page parsing and career projection
return exception text directly. Inspect relevant callers, add focused regression
cases and replace the shared error boundary with safe messages/correlation IDs.
Keep intentionally controlled serializer/outcome validation separate.
Exact next command after configured-Python preflight and isolated environment:
F:\ALFRED\alfred_ai\.venv\Scripts\python.exe manage.py test tests.test_career_api_errors --noinput --verbosity 1

## Latest development checkpoint - M14B/M14C/M14F - 2026-10-07

DEVELOPMENT STATUS: ACTIVE. Recovery is provisionally closed for development by
explicit user instruction; visual inspection reportedly satisfactory. Untested
individual operator screens remain unclaimed, but do not block development.
Historical Docker classification was completed; retained-file cleanup is deferred
housekeeping. Preserve encrypted backups, SQLite copies, VHDX and recovery Git repo.

Actual development worktree: F:\ALFRED_DEV\m13c.
Branch: codex/expense-bank-money-m13d-20261006.
Last validated SOURCE HEAD: fb471b619b569b7647bcff1cab590539ae9f6d33.
Completed source commits:
- 6001a4ece2ab37ffba956625cba7b16c59fa5cac: prior M14A Career pinned HTTP fix.
- 18457eff06a1b964c9208093f378f93ec2e86922: M14B Django password validators.
- 3497afedc41b090895422b0f1bda7119ec6d8d08: M14C session-only API/CSRF.
- fb471b619b569b7647bcff1cab590539ae9f6d33: M14F Career exception disclosure.
Checkpoint/backlog metadata is committed separately after these source commits;
use git --work-tree=F:\ALFRED_DEV\m13c rev-parse HEAD for the actual current HEAD.

Last completed task: bounded M14F Career API unexpected-error handling. Confirmed
raw exception disclosure in recruiter intake, job-page parsing and projection.
All three now reuse _career_error_response: public message plus opaque error_id,
preserving detail/error fields and prior 400/500 status contracts. Logs contain
only error_id and exception class, with no raw message/traceback/document/URL.
Intentional outcome ValidationError messages remain; inspected controlled raises.
No projection arithmetic, ownership, parsed evidence or success payload changed.
Five new endpoint/log/anonymous regression tests reproduced four failures before
fix; final Career integration 31 passed / 0 failures/skips / 32.505 s. Included
recruiter/evidence, confidence, income signals, adaptive outcomes and pinned HTTP.
Source files: apps/career/views.py, tests/test_career_api_errors.py.
Logs: F:\ALFRED_DEV\isolated-tests\m14f-red.log and m14f-green.log.

Earlier gates in this session: M14B 30 passed / 0 final failures/skips; M14C
36 auth/profile/family + 8 synthetic acceptance = 44 passed / 0 final failures/
skips, plus 1 real Chrome login/dashboard workflow passed / 0 skips. These are
separate focused gates with overlapping coverage, not a new full-suite total.
Initial browser fixture failure was fixed by changing only its identity-similar
synthetic password; rerun PASS. No production validator weakened. All initial
red/error logs retained. Other modified code: alfred_ai/settings.py,
tests/test_password_security.py, tests/test_api_session_security.py,
tests/user_acceptance_scenario.py. Backlog updated for completed bounded phases.

All tests use synthetic config/signing key, in-memory SQLite/locmem, training off;
Chrome uses isolated temporary SQLite/media and synthetic account. No live
private configuration, credentials, records or runtime database entered models.
Existing application credentials remain unchanged. No DB migration, source
promotion, live deployment, live private-data write, backup deletion or paid
provider action. Live root checkout remains a9d096ea55839269fe6fce14d4f11ea2cbf05336;
both M13C/D remain applied as previously verified. Prior 718 backend / 19 Chrome
baseline not repeated; do not label focused gates as a comprehensive rerun.

Graphify AST-only/no-cluster updates PASS: M14B 7523 nodes/19565 edges,
M14C 7534/19580, M14F 7546/19605. No semantic/API extraction. Whitespace and
staged reviews PASS. No new application dependencies or runtime templates.
Security implementation and regression review used hosted Codex. Local Ollama
Codex generated a documentation draft from verified counts in an empty isolated
directory, without file tools or private records. Draft reviewed and reused for
M14B/C milestone wording; its then-in-progress M14F note is superseded here.
Local draft/log: F:\ALFRED_DEV\isolated-tests\local-checkpoint-summary.*.
Reference framework contracts: https://docs.djangoproject.com/en/6.0/topics/auth/passwords/
and https://www.django-rest-framework.org/api-guide/authentication/.

NEXT PRIORITY: M14G explicit opt-in and permissions for new family financial
sharing, using hosted Codex. Relevant code now checked: FamilyAccountLink all
three sharing flags default True; invite creation omits sharing choices and the
invite API ignores request sharing flags; accepted financial scope honors the
stored share_financial_summary. Existing tests assert automatic sharing and
exclusion when the flag is manually disabled. Next implement the smallest
complete opt-in flow with ownership/accepted-link/consent regressions. Preserve
existing grants and historical data; any migration is development/test only,
never apply to live DB without separate authorization. Inspect only relevant
family model/service/views/serializer/UI and tests. Do not redo whole audits.
Remaining M14D throttles, M14E caps, other API error paths, other HTTP callers,
M14H privacy, remaining money domains and tax work stay open. Completed inferred-
loan fixes stay preserved; T09 Travel telemetry remains behind these P0s.

Exact next command after Python-environment preflight:
powershell.exe -NoProfile -ExecutionPolicy Bypass -File F:\ALFRED_DEV\isolated-tests\run-development-tests.ps1 -Labels tests.test_family_account_links
This tested local runner selects F:\ALFRED_DEV\m13c, explicit synthetic config,
in-memory SQLite, locmem, isolated registry and disabled training/browser mode.
Read current family tests/flows, write the focused opt-in regression, then rerun
this command. Do not repeat this baseline without relevant changes or a concern.

Next-command runner verification: existing family-link baseline 7 passed / 0
failures/skips / 11.787 s, exit 0. No family source changed yet. Log:
F:\ALFRED_DEV\isolated-tests\next-family-baseline.log. Do not count this
overlapping gate as a new complete backend run.

## Latest development checkpoint - M14G COMPLETE - 2026-10-07

Actual worktree: F:\ALFRED_DEV\m13c.
Branch: codex/expense-bank-money-m13d-20261006.
Validated M14G SOURCE commit: b1ba243364b5a844f19afd55811a70c5b442f94e.
Parent: 909ab5a6d312ed7fe581333f8303ce82cf52ead0.
Checkpoint/backlog metadata is committed separately; read git rev-parse HEAD
with the explicit development worktree for the final current HEAD.
Current task: M14G per-owner explicit opt-in for family financial summaries.
Status COMPLETE in development; not deployed and not applied to private data.

New financial sharing defaults OFF for both participants. Creating or accepting
an invitation never grants financial access, including injected permission flags.
Accepted-link PATCH /api/family/account-links/<id>/financial-sharing/ requires
only share_financial_summary as a JSON boolean and authenticated session/CSRF.
Each account controls its own summary only; share_financial_summary stores the
creator's grant, linked_user_share_financial_summary stores the member's grant.
Snapshot share_financial_summary is the requesting user's own grant;
receives_financial_summary is the other participant's grant. Unrelated, pending,
expired, revoked and missing links cannot grant access. No transitive grants.
Settings UI offers an explicit confirmation naming disclosed financial fields,
plus immediate stop-sharing, separate from disconnecting. Admin UI cannot edit
owners, relationship status or either grant, or create links on others' behalf.

Financial queries/aggregate totals/members exclude accounts without that owner's
grant. Nested financial summaries also honor profile sharing: disabled identity
and location fields are redacted. Profile/dependent defaults remain unchanged.
Revocation invalidates both participants' caches; relationship disconnect clears
both grants. A financial-consent revision prevents reuse of pre-M14G cached
summaries. Financial writes invalidate authorized recipients' cached summaries,
including asymmetric sharing with dependent sharing disabled.

Migration: family.0004_financial_sharing_opt_in, depends only on family.0003.
Historical True has no consent provenance. Forward clears both financial grants
on every existing link; connected accounts stay connected and must choose again.
IDs, owners, statuses, invite hashes/hints, timestamps, dependent/profile flags
and all relationships are preserved. Synthetic migration reconciliation verified
4 links across accepted/pending/revoked/expired, 2 users and 1 dependent.
Forward, rollback and replay PASS; isolated plan applies only family.0004.
Rollback clears grants, including subsequent opt-ins, before dropping the new
field. It intentionally does not restore ambiguous historical True values.
Old code/schema can default new links to sharing True: keep family linking and
sharing unavailable during any reversal; do not restart unsafe old sharing flows.
No live migration is authorized. Future live promotion requires a fresh verified
consistent backup, disposable rehearsal, reviewed plan and explicit approval.

Regressions first: original 18-test family gate failed 16 assertions/subtests,
zero errors; initial full family fix passed 18. Review found profile metadata
leakage inside opted-in financial summaries; new regression failed and fix passed.
Final family/migration gate: 22 passed, 0 failures/skips, 36.803 s (20 family,
2 migration tests). Relevant integration gate: 61 passed, 0 failures/skips,
77.694 s across family/migration/session/password/auth/profile/data-reset/
synthetic acceptance. It preceded the final nested-profile guard, which the
final family gate covers. Settings live-HTTP/static contract: 1 passed / 6.273 s.
Final real Chrome settings + recipient Family workflow: 1 passed, no skips,
21.422 s; cancellation, directional opt-in, refresh persistence, revoke and
recipient financial display verified using synthetic accounts only. Earlier
Chrome passed too; do not count repeated workflow runs as distinct workflows.
Backend gates overlap; no new full-suite total. Prior 718/19 baseline not repeated.
Initial migration harness error used a historical User instance in a current
model service; corrected test lookup, then integration and migration gates passed.
All red/failure evidence retained in F:\ALFRED_DEV\isolated-tests\m14g-*.log.
Chrome artifacts/summaries in m14g-browser-final. No private records in prompts.

Source changed: alfred_ai/middleware.py; apps/family/models.py, services.py,
serializers.py, views.py, urls.py, admin.py; family/migrations/0004; settings.js;
templates/settings/account.html; tests/test_family_account_links.py,
test_family_consent_migration.py, test_user_data_browser.py.
makemigrations family --check --dry-run PASS (no drift, no generated files).
node --check settings.js and staged whitespace review PASS. Graphify final
AST/no-cluster update PASS: 7585 nodes, 19715 edges; no semantic/provider calls.
All backend and Chrome storage/config are synthetic isolated test environments,
with training disabled. Live checkout remains a9d096ea55839269fe6fce14d4f11ea2cbf05336;
no live DB access/write, source promotion, credential change or backup deletion.
Pre-existing restoration document remains untracked, untouched and unstaged.

Next action after this committed milestone and preserved checkpoint: inspect
existing inferred-loan verification/exclusion and its focused tests, without
repeating completed financial work. If already protected, select the next
verified unresolved security/financial item. Hosted Codex for sensitive changes.

Post-M14G next-task assessment (source committed and checkpoint preserved first):
M12A inferred-loan financial protection is ALREADY IMPLEMENTED in the actual
current development source. EMI guesses are verification_status=estimated;
canonical liability and recurring EMI predicates require is_confirmed. API
verification fields are read-only, confirmation defaults False and requires
reviewed terms; setting status alone cannot confirm an estimate. Existing
loan-verification tests cover repeated detection, API exclusion, explicit terms,
status bypass, ownership, payment acceptance and evidence provenance. Prior
real-Chrome estimate-confirmation test remains present. These files are unchanged
since the validated a9d096e baseline. No loan implementation or repeat test gate
was needed; do not report these inspected tests as newly executed.

NEXT PRIORITY: remaining M14F family-growth API exception disclosure, hosted
Codex. Actual apps/family/views.py still returns str(e) on unexpected exceptions;
Career's bounded error hardening is already complete and must not be repeated.
Trace existing safe error helpers/callers, add a focused response/log redaction
regression, then implement the smallest complete boundary. M14D throttles,
M14E upload caps, M14H retention and other verified backlog items remain open.
No additional high-risk implementation started after M14G.

EXACT NEXT COMMAND (absolute development source path):
rg -n 'family_growth|except Exception|str\(e\)' F:\ALFRED_DEV\m13c\apps\family\views.py
For subsequent Django regressions, first obtain the configured interpreter,
then use the existing isolated run-development-tests.ps1 runner with relevant
labels. Never load or migrate F:\ALFRED\restored-runtime\db.sqlite3 in development.
Development remains ACTIVE. M14G is source-validated, not a live rollout.

## 2026-10-07 - M14H Family Growth error hardening (development only)

User milestone M14H is COMPLETE. This names the Family Growth error slice of
backlog M14F; the older M14H raw-document-retention issue remains open.
Implementation commit: 391bad5def84dab31611923ffce0fe6e08aa4230.
Development checkout: F:\ALFRED_DEV\m13c.
Branch: codex/expense-bank-money-m13d-20261006. Source started at ea0747d.

Fixed endpoint: GET /api/family/growth/. Unexpected baseline, ORM, cache,
projection, and reference failures preserve HTTP 500 with a fixed safe message
and an opaque error_id. Shared safe_error_response extracts the already-tested
Career policy: ERROR-level logs contain only exception class/reference and
structured error_id/exception_type; no exception body, chain, stack, request
body or financial payload. Career's three existing callers retain their API
status/message/field contracts. No financial arithmetic or consent changes.
Family public reference evidence excludes notes and last_refresh_error,
including nested proof/freshness output. New cache revision bypasses pre-fix
materialized payloads containing diagnostic text. Stored evidence is unmodified.
Expected controlled validation, 400/403/404/405, session-only auth, CSRF,
participant scoping and M14G ownership/opt-in/revocation remain enforced.
No migration, dependency, runtime configuration or UI source change.

Files: alfred_ai/services/api_errors.py; apps/family/views.py;
apps/career/views.py; tests/test_family_api_errors.py;
tests/test_career_api_errors.py; tests/test_user_data_browser.py.

Regressions first: 9 new Family tests reproduced 10 failing assertions/subtests,
0 errors in 7.831 s. Initial focused Family/Career gate: 14 passed, 0 failures,
11.285 s. Final affected integration gate: 62 passed, 0 failures/skips,
76.357 s across Family errors/links, Career errors/recruiter/projection,
session/CSRF and auth pages; includes strengthened root/Django log assertions.
Gates overlap; do not add them as distinct backend tests. No full suite rerun.
Final real Chrome gate: 2 passed, 0 failures/skips, 37.744 s; driver-backed
summary true. Safe failure display/recovery plus owner sharing opt-in and
revocation verified using synthetic accounts only. Initial Chrome recovery
assertion timed out because CSS uppercases the label; assertion now casefolds
displayed text. Failed run evidence preserved, not claimed as a passing gate.
No production UI correction was required. Actual screenshots and text captures
are under m14h-browser-final\user-data (summary's artifact inventory is empty).
Backend/red/Chrome logs: F:\ALFRED_DEV\isolated-tests\m14h-*.log.
Final Chrome summary: m14h-browser-final\browser_regression_summary.json.

All backend/browser storage and credentials are synthetic isolated fixtures;
auto-training disabled, providers mocked. Source/staged whitespace review PASS.
Final graphify AST/no-cluster update PASS: 7608 nodes, 19787 edges; no semantic
provider/API calls. Prior 718 backend/19 Chrome baseline was not repeated.
Live checkout remains a9d096ea55839269fe6fce14d4f11ea2cbf05336. Live private DB
was not opened, written or migrated; source not promoted. Backup/recovery assets
preserved. Pre-existing untracked restoration document remains untouched.
No credential changes or external paid services. Development remains ACTIVE.

Current task: preserve this validated checkpoint and select the next verified
unresolved P0 security item. M14D throttles, M14E upload caps, other HTTP/error
paths, raw-document retention, token re-encryption and remaining monetary
fields stay open until targeted checks establish completion. Do not repeat
M13C/D, M14G, completed Career fixes or inferred-loan protection.

Post-M14H assessment (validated source committed and checkpoint preserved first):
NEXT PRIORITY: M14D scoped Family invitation creation/acceptance throttling,
hosted Codex. Current FamilyAccountLinkListCreateView/AcceptView have no throttle;
REST_FRAMEWORK has no DEFAULT_THROTTLE_CLASSES/RATES; configured middleware and
Family services contain no rate-limit guard. This is a verified unresolved P0,
not a rerun of completed auth/password/CSRF work. Preserve read-only snapshots,
sharing revocation and participant scoping; bound invite generation and invalid
code attempts, with isolated 429/retry/account-isolation/CSRF regressions first.
Do not claim a global authentication brute-force fix from this bounded slice.
No throttle implementation or tests added in the M14H commit.
T09 telemetry remains deferred behind open P0 issues. Historical Docker
classification remains deferred recovery housekeeping, not a development block.
M14G consent migration remains source-only, not applied to the live database.

EXACT NEXT COMMAND:
rg -n 'FamilyAccountLink(ListCreate|Accept)View|THROTTLE|throttle_classes' F:\ALFRED_DEV\m13c\apps\family\views.py F:\ALFRED_DEV\m13c\alfred_ai\settings.py
Then add scoped throttle regressions before the guard. Get the configured Python
environment before using the existing isolated run-development-tests.ps1 runner
with Family/session test labels. Never load the live private DB for development.
The implementation SHA above identifies validated source; the later checkpoint
commit contains only this file and ALFRED_DEEP_REVIEW_BACKLOG.md. Use git rev-parse
HEAD for the current checkpoint SHA; do not confuse it with the live source HEAD.

## 2026-10-07 - M14D Family invitation abuse protection (development only)

M14D Family invitation creation/acceptance is COMPLETE.
Implementation commit: 56b50cf944042cd728e53167e86657b363e2443a.
Development checkout/branch: F:\ALFRED_DEV\m13c,
codex/expense-bank-money-m13d-20261006; started at 65e4908.

Only POST /api/family/account-links/ and /api/family/account-links/accept/
are throttled, after authentication/permissions/CSRF and before services/parser
access. Separate scopes key authenticated account PK, never headers/IP/target.
Creation has no target parameter; repeated/changed payload targets cannot evade
the account quota. Defaults: 5 creation attempts/3600 seconds; 10 acceptance
attempts/600 seconds. Each positive limit/window is configurable via the four
ALFRED_FAMILY_INVITE_{CREATE,ACCEPT}_{LIMIT,WINDOW_SECONDS} environment names.
All admitted attempts count, including invalid/malformed/failed operations.

Existing default LocMemCache and native diskcache.DjangoCache/DRF read-modify-
write throttles are not treated as strict shared quotas. Reuse installed
pinned diskcache.Cache with one transact() reservation, non-evicting separate
persistent store and rolling timestamp histories. Location defaults to
ALFRED_DATA_DIR/artifacts/security/family-invites; can override with
ALFRED_FAMILY_INVITE_THROTTLE_DIR. One local host, same local-disk directory for
all processes; not network filesystems or cross-host deployment. Never reuse
or clear ordinary cache/protection state interchangeably. Active quotas survive
ordinary cache.clear() and process restart; expired history removed lazily.
Store contains account IDs, scope names and timestamps, no codes or finances.
Local privileged filesystem/clock changes and multi-account attacks are outside
these per-account guarantees; no global login or general network-DoS claim.

Quota exhaustion returns 429 plus Retry-After, without invitation creation,
acceptance, expiration/revocation updates, cache invalidation or permission
changes. Storage/invalid-config failures fail closed with safe 503/reference.
Unexpected invitation service failures use the existing class/reference-only
ERROR logging and safe 500 responses. No request bodies or raw exception strings
logged. Complete invalid/expired/revoked/consumed/self/duplicate invitation codes
share one controlled 400 response, avoiding invitation-state enumeration; blank
or malformed codes keep safe format guidance. Input aliases remain supported,
non-dictionary/non-string/overlong code input returns controlled 400.
Ownership, accepted links, one-time codes, CSRF, consent/revocation and financial
sharing defaults are preserved. Reads and unrelated endpoints are not limited.

Changed files: alfred_ai/settings.py; apps/family/throttles.py, views.py,
services.py; docs/FAMILY_INVITATION_THROTTLING.md;
tests/test_family_invitation_throttling.py, test_family_invitation_atomic.py,
test_family_account_links.py, test_family_api_errors.py,
test_user_data_browser.py. Existing test fixtures now isolate limiter stores;
two older API message assertions use the uniform response, preserving statuses.
No model/ownership-field changes, Django migration or new dependency.

Regressions first: 11 API tests exposed missing limits/state-enumeration and
malformed-input failures: 8 failures, 2 errors, 16.683 s. Evidence retained.
Focused final-new-tests gate: 16 passed, 0 failures/skips, 23.254 s.
Strengthened process concurrency with a four-process synchronization barrier;
final affected integration gate covers that change: 69 passed, 0 failures/skips,
86.217 s (new API/atomic, family links/error, session/CSRF/auth, Career errors).
Twelve simultaneous threads and forty reservations across four simultaneous
spawned processes each admit exactly the configured three attempts; reopened
instances retain the quota and other users/scopes retain independent capacity.
Backend gates overlap; do not add totals. No comprehensive backend rerun.
Chrome: 2 real-driver workflows passed, 0 failures/skips, 29.266 s; generated
codes, safe creation/acceptance 429 UI feedback, no throttled writes, valid
acceptance at retry expiry, plus existing opt-in/cancel/revoke/privacy workflow.
Driver-backed summary true. Artifacts under m14d-browser/user-data; all synthetic.
All logs/summaries retained under F:\ALFRED_DEV\isolated-tests\m14d-*.
Source and staged whitespace review PASS; graphify AST/no-cluster update PASS:
7654 nodes, 19919 edges. No semantic/API extraction. Test storage, passwords and
financial fixtures synthetic; providers offline/mocked and training disabled.

No live private DB read/write/migration, source promotion, credential changes,
paid external service or backup deletion. Live source remains at prior a9d096e
baseline. Recovery assets preserved. Pre-existing restoration document remains
untracked/untouched. Documented defaults apply only when this tested source is
separately promoted; no live rollout occurred. Development remains ACTIVE.

Current task: preserve M14D validated source/checkpoint, then inspect the next
unresolved P0 upload/privacy/error boundary. Do not repeat M14G/M14H, Decimal
migrations or inferred-loan protection. Broad global throttling, M14E caps,
other HTTP/error paths, raw-document retention and token re-encryption remain
open pending scoped checks; Travel T09 stays behind unresolved P0s.

## 2026-10-07 - Final M14D review and independent P0 follow-up

M14D implementation: 56b50cf944042cd728e53167e86657b363e2443a.
M14D configuration hardening: 7fc264fd0292f1e2486747b444645e7a6701d364.
Follow-up shared cleanup diagnostics: 63d0728dc5c48f38b4625dc1bf419a4fc7daedb8.
These are independent validated source commits. The f38791d checkpoint preserved
M14D before the next scoped P0 was implemented; this later metadata commit
records the final actual state. Current HEAD can be obtained with git rev-parse.

Final review reproduced invalid-directory fail-open: diskcache creates a new
temporary cache when given None. New regression received 201 instead of required
503 (one test, one failure, 1.477 s). Guard now rejects missing/relative directories
before opening the store, alongside nonpositive limits/windows. Defaults remain
absolute under the runtime data directory. Operator document updated. Final
M14D API + synchronized thread/process gate: 16 passed, 0 failures/skips,
24.703 s, including guarded None/relative paths. Original 69 integration and
2 Chrome gates preceded this validation-only path guard; nominal configuration,
public messages, valid invitation behavior and UI remain unchanged. No repeat
full audit or full suite. Logs: m14d-path-red.log, m14d-final-focused.log.

NEXT P0 ADDRESSED in independent commit 63d0728: shared source-upload cleanup
failure metadata stored raw exception strings and exposed them through upload
serializers. The shared producer used by nine call sites across statement,
loan/closure, investment, Career, vehicle and credit document flows now stores
only a fixed safe error and opaque reference; ERROR logs contain class/reference
without evaluating exception text. safe_error_details shares the existing API
policy; safe_error_response keeps all existing response/status/field contracts.
Failed deletion still leaves the file, model reference and extracted payload
intact, with deleted=False and an explicit error marker. Retention defaults and
successful deletion behavior are unchanged; no historical records rewritten.

Files changed in follow-up: alfred_ai/services/api_errors.py, upload_privacy.py;
tests/test_upload_privacy_retention.py. Regressions first: 5 upload privacy tests,
2 failures, 3.697 s; evidence retained. Final affected gate: 47 passed,
0 failures/skips, 40.257 s across cleanup/retry integrity, Family Growth, Career
errors and invitation API/atomic checks. Includes real API reading of new safe
metadata and an exception whose __str__ must never be evaluated. This gate
precedes the final directory guard; the final 16 cover that additional change.
Backend gates overlap, never add totals or claim a new complete-suite baseline.
No additional browser gate needed for the shared diagnostic producer; existing
M14D driver-backed workflows remain recorded. Logs m14f-cleanup-{red,integration}.
Final source/staged whitespace review PASS; final graphify AST/no-cluster PASS:
7661 nodes, 19933 edges. No semantic/provider call or new dependency.

Hybrid use: hosted Codex for security design/implementation/privacy regressions;
local Ollama Codex (alfred-routine:latest, read-only, empty isolated working dir)
completed an operator-summary draft from static non-sensitive configuration facts.
Draft reviewed against docs/FAMILY_INVITATION_THROTTLING.md. Initial Windows .cmd
multiline argument lost fact lines; corrected stdin-file invocation completed
successfully. Outputs/logs retained in m14d-local-doc-* outside the source tree.
No private data/credentials/runtime databases supplied to either documentation
run or hosted model. Model metadata fallback warnings did not prevent completion;
no global tooling/credential configuration changed.

NEXT PRIORITY: M14E shared upload-size/resource caps, hosted Codex. Confirmed
ExpenseStatementImportView checks missing file/PDF suffix, then calls the parser
without an application size check. No configured custom FILE_UPLOAD_HANDLERS or
file/body limits found in settings. Before implementing, verify native transport
and multipart behavior so memory-spool thresholds are not mistaken for hard
upload limits; bound parsing/temp-file work, reject oversize input before model
writes, and use isolated boundary/rejection/cleanup/auth tests. Retain existing
source files and ownership; never test against private documents. Historical
stored exception metadata still needs separate public filtering/review, without
rewriting live records. Other API errors, HTTP callers, raw-retention policy,
token re-encryption, remaining money domains and global abuse limits stay open.
T09 Travel remains behind unresolved P0s. Docker classification stays deferred
recovery housekeeping and is not a development blocker.

EXACT NEXT COMMAND:
rg -n 'class ExpenseStatementImportView|statement_file|FILE_UPLOAD|DATA_UPLOAD' F:\ALFRED_DEV\m13c\apps\expenses\views.py F:\ALFRED_DEV\m13c\alfred_ai\settings.py
Obtain the configured Python environment before each toolchain invocation, then
run new focused cases through the existing isolated development-test runner.

Live DB UNCHANGED: no private DB access/write/migration. No live source promotion,
backup deletion, credential changes or paid external calls. All database/media/
limiter fixtures were synthetic and isolated. Backups and restoration assets
preserved; pre-existing restoration document remains untracked and untouched.
Development ACTIVE; M14D COMPLETE, next scoped source task M14E above.

## 2026-10-08 - M14E shared upload/resource protection COMPLETE (development only)

Resume from this entry. Development branch codex/expense-bank-money-m13d-20261006
in F:\ALFRED_DEV\m13c. Validated implementation commit:
8cecd65748d333f7487bf008a835854a4ac10e50
Parent checkpoint 3bcab836381e5b39744da8a25db083e47399eaf1. A following metadata
commit records this entry/readiness/backlog; use actual Git HEAD, not the parent.
Live source independently rechecked with Git -C in the LIVE checkout:
a9d096ea55839269fe6fce14d4f11ea2cbf05336. Source not promoted; no live database
access/write/migration. Public app was already running at 127.0.0.1:8000 and
returned HTTP 200 when the user requested it. No restart was needed. Opening
the default browser with Start-Process was policy rejected; user received link.
No private browser session, credentials, documents or financial records read.

M14E implementation:
- Shared multipart middleware/handler counts actual framed body and decoded file
  bytes before disk writes; independent of Content-Length and memory thresholds.
- Defaults: file 25 MiB, request 32 MiB including multipart overhead, 4 files,
  1000 fields, 256 KiB form data. All files spool to disk in 64 KiB chunks.
  Positive-integer configuration, file <= request; invalid config fails closed.
- Windows native Waitress transport uses matching cap (inclusive via +1 for its
  >= comparison), including chunked bodies; 16 connections / 4 task threads.
  Its chunked cap counts framing; unframed WSGI without valid length isn't
  imported. Tests separately exercise unknown/understated framed streams.
- Upload/retry extraction streams to the existing local/frozen-worker dispatch;
  no whole-file parent RAM copy, cloud call or new framework/dependency.
  Shared 90s extraction deadline; actual Windows Job Object 1 GiB process/job
  commit-memory limit, OCR children inherit job and die with timed-out worker.
  Worker config is explicitly non-sensitive; no local.env/application/DB init.
- PDF 500 pages / 50000 objects (including sparse recovery IDs), 64 MiB decoded
  streams, 20M input/rendered pixels; DOCX/ODT 256 members / 64 MiB actual
  streamed expansion without path extraction; text/CSV 2 MiB / 50000 lines;
  recovered statement text bounded before transaction grouping; result JSON 4MiB.
  Existing PDF/OCR/damaged-file recovery and review behavior remain available.
  There is no existing Excel workbook statement importer; bank endpoint remains
  PDF-only. CSV text-document compatibility tested; CSV/XLSX bank rejection kept.
- Free temporary disk reserve 128 MiB + request budget, safe 503 on unavailability;
  size/processing/count limits 413, malformed forms/archive 400. New unexpected
  diagnostics use existing class/reference-only safe helper. No raw bodies logged.
  Completed/incomplete Django spools and bounded worker/OCR temp directories close
  after success/rejection. Existing source retention and cleanup redaction kept.
- Write transaction starts only after heavy extraction succeeds; no SQLite
  IMMEDIATE writer held during OCR. Failed post-extraction writes roll back.
  Recruiter profile creation moved after successful parsing. APIException
  resource failures bypass loan review fallback and Career generic error wrapper.
- Statement fingerprints, reference signatures, deduplication, transfer/balance
  logic unchanged; no monetary model/migration or ownership changes.

Protected paths: expenses import-statement; loans import-pdf and payoff evidence;
investments import-pdf; Career resume/recruiter attachments; credit report upload;
Mobility bike document/service uploads and multipart serializer paths. Manual
review retries and background statement retries use the same extraction budget.
POSIX memory code exists but Windows-native behavior is verified; POSIX tree
termination and a new frozen-package smoke test are NOT claimed as passed.
See docs/UPLOAD_RESOURCE_LIMITS.md and M14_SECURITY_RELEASE_READINESS.md.

Modified source: alfred_ai/upload_config.py; services/upload_limits.py,
bounded_parser.py, document_extraction.py, document_review.py, native_web.py,
ocr_process.py, pdf_recovery.py; settings.py; Career resume/job services + views;
Expense statement_import/lifecycle; Credit parser; Investment portfolio service;
Loan PDF/closure parsers + views; Mobility document AI. Tests: test_upload_limits.py
and 2 UserDataBrowserTests workflows. Operator docs: UPLOAD_RESOURCE_LIMITS.md.
Only explicit source/docs/tests staged; private assets/migrations staged = 0;
secret-marker and source/staged whitespace scans PASS. Existing untracked
WINDOWS_RESTORATION_VERIFIED_20261006.md preserved and unstaged.

Final validation on this implementation:
- 31 focused M14E methods passed (30-method focused gate 34.592s, extra rollback
  case 2.802s), included in final combined gate below. Actual stream chunks,
  exact boundaries, unknown/inaccurate lengths, multi-file aggregate/body/fields,
  formats, disk failures, temp cleanup, safe logs, auth/CSRF, parser error/timeout,
  PDF/archive/image/text/output bounds, actual Windows memory allocation refusal,
  real native HTTP chunked cap, no added writer during extraction, post-write
  rollback, and rejection without import mutations covered with synthetic data.
- FINAL combined affected/security gate: 198 passed, 0 failed/skipped, 243.503s.
  Includes upload/import/financial identity/statement columns/uploader persistence,
  document recovery/retry/integrity, Career/credit/Mobility/native boundaries,
  Family consent/invitation thread/process atomicity/growth errors, passwords,
  session/CSRF, Career HTTPS/SSRF and upload-cleanup redaction.
- FINAL Chrome gate: 3 passed, 0 skipped, 55.666s; driver_backed_success=true.
  Document rejection feedback -> valid resume; real synthetic PDF import/reimport
  verifies unchanged fingerprint/reference/amount rows + balances; existing
  login/statement/vehicle/dashboard workflow. Synthetic isolated SQLite/media.
- Django system checks PASS; isolated makemigrations --check --dry-run reports
  No changes detected (no file generated); graphify AST/no-cluster PASS:
  7760 nodes, 20264 edges. No semantic/provider call or complete-suite rerun.

Evidence: F:\ALFRED_DEV\isolated-tests\m14e-release-gate.log;
m14e-release-chrome.log + m14e-release-chrome/browser_regression_summary.json
and synthetic captures; m14e-migration-drift.log; m14e-final-graphify.log.
Earlier gates overlap; do not add totals or replace historical 718/19 baseline.
Initial red 8 methods: 12 failures/2 errors (oversize/400/raw exception); retained
m14e-red.log. First Chrome 3: 2 off-screen click errors before upload; fixed
scrolling, retained failed artifacts. Intermediate security gate 97 had 1 Windows
connection-abort in test that sent an already rejected Content-Length body;
changed header rejection proof to receive 413 before sending body, retained
chunked actual-byte proof. Subsequent 97, 196 and final 198 gates pass. Earlier
123 affected and 25/29/30 focused gates pass; repeated only after relevant code
changes. No unresolved test failures; previous failed-run evidence retained.

Hybrid: hosted Codex implemented all security/resource design and regression work.
Local Ollama Codex documentation-only attempt used static non-sensitive facts,
empty read-only directory, no repository/private input; service unavailable and
CLI retried network. Owned stalled Codex process stopped, draft exit -1; NOT a
successful local-model result. Hosted operator docs completed. Logs/prompt kept
outside source. Check local Ollama before the next routine-model task; no model,
credential or live runtime configuration changed to repair it in this milestone.

NEXT PRIORITY: hosted M14F loan upload diagnostic production + public historical
filtering. Verified current loan fallback embeds str(e) in summary/payload and
operational logs; LoanPDFParser prints it; LoanImportDocumentSerializer exposes
extracted_payload. Preserve usable review uploads, ownership, successful imports
and inferred-loan confirmation; never rewrite historical live data. Do not repeat
M14D/G/H, Career HTTP/password/session security, cleanup producer or Decimal work.
Other HTTP callers, raw retention, token re-encryption and global abuse limits
remain unresolved. Broad security release NOT READY; no deployment authorized.
Travel T09 stays behind these P0 issues. Docker classification is deferred
housekeeping; backups, recovery DBs/repos/VHDX and archives remain preserved.

EXACT NEXT COMMAND (source inspection only):
rg -n 'str\(e\)|Error parsing loan PDF|LoanImportDocumentSerializer' F:\ALFRED_DEV\m13c\apps\loans\views.py F:\ALFRED_DEV\m13c\apps\loans\services\loan_pdf_parser.py F:\ALFRED_DEV\m13c\apps\loans\serializers.py
Obtain the configured Python environment before each Python invocation; keep
future tests under isolated synthetic configuration. Development ACTIVE.

## 2026-10-11 — M14F loan diagnostic protection COMPLETE (development only)

Resume from this entry. Development checkout F:\ALFRED_DEV\m13c, branch
codex/expense-bank-money-m13d-20261006. Starting checkpoint:
a9d06a0b6450ce6b5914df5da85398edcb799869.
M14F implementation and validated application HEAD:
895ce13ee86bf5fddbd1332f5326389b7a3b7c5c.
The following evidence-only commit contains this checkpoint/readiness/hold plan;
read actual current HEAD with git rev-parse HEAD. Its exact final HEAD and full
promotion range are frozen outside Git in isolated-tests/m14-promotion-manifest.json.
Stable source rechecked through Git only remains
a9d096ea55839269fe6fce14d4f11ea2cbf05336. No live source promotion or private DB
read/write/migration; no private documents, credentials or backups were used.
The pre-existing untracked restoration document remains untouched and unstaged.

Scoped inspection confirmed the remaining Loan fallback str(e), parser print,
unfiltered import/closure payloads, nested settlement notes, review artifacts and
operational-log responses. Read AGENTS, the latest checkpoint/readiness/backlog,
used the existing scoped graph query, traced parser/serializer callers and reused
safe_error_details/safe_error_response. No broad audit or completed milestone redo.

M14F behavior:
- Loan import parser failures retain the reviewable-upload HTTP 201 contract,
  success=false, failed status, fixed safe error/code and opaque correlation ID.
  Persistence failures are logged 500s, not mistaken for parser review outcomes.
  Payoff operational errors are safe 500s; validation/resource/404/202/200 statuses
  remain. Other existing direct Loan error responses now use the same safe helper.
- Parser exceptions propagate to the appropriate API boundary; no exception text,
  nested cause, traceback, uploaded bytes, OCR text or private amount is formatted
  into diagnostics/logs. ERROR logs retain class/reference and parser/persistence
  stage. New failure records/operational events contain only safe error metadata.
- Import/closure serializers regenerate safe status messages and allowlist public
  diagnostics. Historical arbitrary errors/warnings/parser output, OCR snippets,
  raw notes, unknown nested keys and settlement diagnostics cannot be returned.
  Review/resolve/retry and operational-log responses use the same boundary.
  Loan/financial cache revisions invalidate older serialized watchlist content.
- New parsers keep extracted source evidence in the existing private extracted-text
  field and structured business fields, without text copies in diagnostic payloads.
  Loan cleanup metadata is filtered before persistence/response, excluding paths
  and filenames. Shared cleanup defaults and other domains are unchanged.
- Historical forensic records remain unchanged; no migration/rewrite/dependency.
  Normal owned Loan fields, monetary values, document links, statuses, business
  corrections and structured settlement components remain. Public raw loan OCR
  review artifacts are intentionally omitted; retained local files/manual review
  remain usable. Source retention policy, financial calculations, ownership,
  deduplication and inferred-loan confirmation rules are preserved.

Validation:
- 19 focused M14F tests passed, 0 failures/skips, 15.078s; final focused gate after
  cleanup-metadata producer filtering: 36 passed, 0 failures/skips, 19.551s,
  including all 19 M14F plus shared cleanup/retry integrity. Exceptions containing
  synthetic paths/loan IDs/amounts/OCR/tokens/stack fragments and uploaded bytes,
  unprintable/nested errors, actual parser-stage failures, image/payoff failures,
  historical serializer/API filtering, cleanup, successful import/dedup/payoff,
  HTTP statuses, owner scoping/authentication/CSRF covered.
- Affected backend: 192 passed, 0 failures/skips, 112.330s (before final producer
  filtering; final 36 and final combined gate cover that small change).
- M14F Chrome: 4 passed, 0 skipped, 51.461s, driver_backed_success=true: safe
  historical/current errors then real PDF import/reimport; loan/closure manual
  correction; existing inferred-loan confirmation. All fixtures synthetic.
- FINAL combined backend: 297 passed, 0 failures/skips, 243.888s. One actual gate includes the final M14F
  source, all 31 M14E regressions, Loan/serializer/import compatibility, password,
  session/CSRF/auth, Career disclosure/HTTPS transport/uploads, Family opt-in and
  Growth errors, invitation synchronized thread/process quotas, cleanup/retries,
  statement fingerprints/columns/uploader compatibility, and both family.0004
  forward/rollback/replay migration-rehearsal methods. Do not add earlier counts.
- FINAL combined Chrome: 10 passed, 0 failures/skips, 113.447s;
  driver_backed_success=true. All four Loan workflows above plus Family
  invitation throttling/expiry, opt-in/revocation, Growth safe-error recovery,
  upload limit/valid resume, real PDF statement reimport fingerprint/reference/
  amount/balance preservation, and login/statement/vehicle/dashboard workflow.
- System check PASS; isolated makemigrations --check --dry-run: No changes
  detected. No M14F migration created/applied. Source comparison adds only the
  already-tested family.0004 migration relative to stable; live migration table
  was not read. Graphify AST/no-cluster PASS: 7804 nodes / 20474 edges, no API cost.
- First focused run: 17 run, one erroneous pagination assertion, corrected.
  First Chrome run: off-screen click and wrong in-memory harness caused failure;
  switched to existing run_browser_regressions.py/browser_test_settings. Next
  Chrome run relied on an operational-log filename now deliberately hidden;
  expectation now verifies the actual saved closure on the Loans page. Corrected
  gates pass; failed logs/screenshots/proof summaries remain preserved.

Evidence under F:\ALFRED_DEV\isolated-tests: m14f-focused-final.log,
m14f-final-focused.log, m14f-affected.log, m14f-chrome-verified.log and
m14f-chrome-final/browser_regression_summary.json, m14-final-backend.log,
m14-final-chrome.log and m14-final-chrome/browser_regression_summary.json,
m14f-system-check.log, m14f-drift-check.log, m14f-graphify-complete.log.
No full repository suite, frozen-package gate or real-account acceptance claimed.

Release scope: the user's latest note identifies M14F as the remaining verified
blocker. The existing readiness report separately retains unverified HTTP callers,
raw-retention policy, token fallback re-encryption and global abuse protection.
A clarification was requested while the combined gate continued. Until explicitly
resolved/deferred, retain those reported entries; a passing regression gate does
not establish their safety. Broad M14 RELEASE READY remains NO, and M14 DEVELOPMENT
is not marked COMPLETE. M15 has not begun. Do not reopen completed M14D/E/G/H or
M13C/D and do not run a broad audit to resolve this scope question.

Promotion is prepared only in M14_CONTROLLED_PROMOTION_PLAN.md: exact source
range, final HEAD manifest, family.0004 OFF-consent impact, fresh verified encrypted
backup, disposable rehearsal, rollback, smoke tests and real-account acceptance.
No live action is authorized by this plan. Originals/backups/recovery assets and
financial balances remain preserved. All automated data/media/limiter stores are
synthetic and isolated. Git identity was absent; the implementation commit used
the established previous-commit identity via command-scoped -c only, without
editing global/local configuration.

NEXT ACTION: combined M14 regression integration PASS; resolve the retained release
scope before M14 readiness/PASS, promotion authorization or M15 work.
EXACT NEXT COMMAND:
Get-Content -LiteralPath F:\ALFRED_DEV\m13c\artifacts\audit\M14_SECURITY_RELEASE_READINESS.md

## M14 retained blocker resolution: HTTP - 2026-10-11

Continued from 97c06fa. Authoritative four reported issue groups classified in
M14_RETAINED_BLOCKER_DISPOSITIONS.md; no broad audit or completed milestone redo.
Remaining Investment/Verified Intelligence direct GET adapters now reuse the
existing pinned, bounded public HTTPS transport, with typed text/RSS/HTML caps.
Safe provider failure observations replace raw exception persistence/logging.
Six synthetic regressions first reproduced the gap; related gate: 41 passed,
0 failures/skips, 11.585 seconds (m14-http-after.log). No live modification,
dependency, migration or monetary calculation change. Source commit is the commit
containing this checkpoint; exact SHA is recorded in the next checkpoint.
Next: transactional verified EmailConnection token rotation, then abuse limits.

## M14 retained blocker resolution: token rotation - 2026-10-11

HTTP commit: 7bb5086ac1046382f4abb84fc0e6c1ad647304b7.
Implemented the count-only dry-run / explicitly applied atomic email-token
rotation command and operator recovery/key-retirement procedure. Existing
fallback reads remain. Primary-only re-read verification, invalid-token rollback,
conflict detection, mixed-key/legacy/idempotence/timestamp tests passed:
7 focused (0.041 s), 18 integration (11.529 s), zero failures/skips.
No live token/key mutation, schema migration or dependency. Source commit is the
commit containing this checkpoint. Next: reuse atomic invitation reservation
pattern for login and authenticated expensive-endpoint abuse protection.

## M14 retained blocker resolution: abuse protection - 2026-10-11

Token source commit: 64d21f37607b1a765c0ea7ca746216c3cb014c69.
Login/signup/account/global API and expensive-operation protection now reuses the
invitation atomic rolling-window pattern through a shared helper, with the
existing invitation wrapper and independent persistent scopes preserved.
Safe 429/Retry-After precedes view writes; invalid/unavailable store fails 503;
HMAC identities, no forwarding-header trust, safe reference/class logging.
No auth/CSRF bypass, dependency, migration, live mutation or money changes.
Focused 12 passed (12.335 s); related 55 passed (79.462 s); Chrome 2 passed
(16.940 s), zero failures/skips and driver-backed success true. Fixture-only
failures were corrected (scoped mock, complete URLconf, navigation wait/helper).
Source commit is the commit containing this checkpoint. Final combined gate and
retention deferral evidence/config verification still precede M14 completion.

## M14 retention disposition verified - 2026-10-11

Abuse implementation: cf799d46c17d7241acc4cfb33c8b5ef2fc9d8f60.
Raw local-vault/Travel telemetry retention is explicitly deferred with all seven
required fields in M14_RETAINED_BLOCKER_DISPOSITIONS.md. Native private-media
ownership/traversal checks and retaining active review evidence pass (3 new
methods, in the 55-test related gate; corrected fixture recheck 5 passed).
Native release config/check/migration-drift proof PASS in synthetic directories,
including DEBUG=false, private media, deletion option, session/CSRF and limits.
No historical evidence deleted, no cleanup migration/job created/applied, no
live source/database/config/token/key/backups touched. M14 completion now waits
for one new combined backend/Chrome gate on the complete source candidate.

## M14 DEVELOPMENT COMPLETE / release candidate frozen - 2026-10-11

Source candidate: 495a184c7a44bfe169978f8e0c018f8a286fb208.
Resolved separately: HTTP 7bb5086ac1046382f4abb84fc0e6c1ad647304b7;
token rotation 64d21f37607b1a765c0ea7ca746216c3cb014c69;
abuse limits cf799d46c17d7241acc4cfb33c8b5ef2fc9d8f60.
Raw local-vault/Travel T09 retention explicitly deferred with rationale, owner,
mitigations and required evidence in M14_RETAINED_BLOCKER_DISPOSITIONS.md.
Consent-reset source already resolved; private promotion remains unauthorized.

Actual updated gate on candidate 495a184: 356 backend passed, 0 failures/skips,
354.594 s; 12 Chrome passed, 0 failures/skips, 138.356 s (runner 148.546 s),
driver_backed_success=true. All old 19 M14F/31 M14E methods and both family.0004
forward/rollback/replay methods included. No overlapping totals added.
Native config/check/drift PASS; no changes detected. Graph AST-only update PASS
7892 nodes / 20678 edges. No new migration/dependency. Only family.0004 differs
from stable source; no live migration table or private DB access.
Evidence: m14-blockers-combined-backend.log, m14-blockers-combined-browser.log,
m14-blockers-chrome/browser_regression_summary.json,
m14-native-config-proof-final.log, m14-blockers-final-graph.log, scoped logs.
Initial synthetic fixture failures corrected/preserved; zero unresolved failure.

M14 DEVELOPMENT = COMPLETE. M14 RELEASE READY = YES. Freeze the evidence-only
commit containing this checkpoint on release/m14-20261011, and write exact HEAD /
full source range to isolated-tests/m14-promotion-manifest.json. Application/test
source is identical to the validated candidate. Promotion plan includes source,
DB/config/media backups, disposable consent/token rehearsals, OFF-consent impact,
primary-only token verification, config checks, rollback/smoke/real acceptance.
No live source/database/config/key/token/backups modified; stable Git-only HEAD
remains a9d096ea55839269fe6fce14d4f11ea2cbf05336. No promotion authorized/performed.
Existing untracked docs/WINDOWS_RESTORATION_VERIFIED_20261006.md remains untouched.

M15 DEVELOPMENT READY = YES. Next create F:/ALFRED_DEV/m15 on separate branch
codex/m15-persistent-memory-20261011 from frozen release HEAD and implement only
verified local structured memory/provenance/sensitivity, Ollama embedding,
semantic new-session retrieval/owner isolation, append-only encrypted event,
restart/restore/retrieve. Cloud reasoning optional/privacy-gated; no cloud sync
or broad autonomous learning. Never mix M15 commits into frozen M14.
No full repository/installer/live-provider/real-account acceptance claimed.

NEXT ACTION: start the isolated M15 vertical slice; live M14 awaits authorization.
EXACT NEXT COMMAND:
git -C F:/ALFRED_DEV/m13c worktree add -b codex/m15-persistent-memory-20261011 F:/ALFRED_DEV/m15 release/m14-20261011
