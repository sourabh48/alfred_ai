# Master M12A: inferred-loan verification

Date: 2026-10-01. Branch: `codex/native-runtime-hardening-20260918`.
HEAD remains `b4e89742717d0f4ce1d8b6e49ccb7b6b6abde525`. Changes are local and uncommitted.

## Behavior

Recurring-payment inference still creates a reviewable loan estimate. It now carries an explicit `estimated` verification state and `emi_pattern` provenance. It does not enter canonical liabilities, recurring EMI commitments, home acquisition-cost/equity proxies, loan-summary totals, or net-worth breakdowns until confirmed. Observed expense transactions remain visible as recorded cash flows. Direct loan consumers in credit estimates, voice summaries, recommendations and tax home-loan selection also exclude unconfirmed loans.

The loan page labels estimates and their exclusion. Editing one exposes an unchecked confirmation control. Confirmation requires submission of lender, principal, rate, EMI, tenure, start date and a non-null current balance. Merely editing notes or submitting a verification-status field does not confirm a loan. The serializer keeps verification metadata read-only, uses an atomic update with a row lock, validates finite nonnegative inputs, and updates the cache revision through `updated_at`. Zero remaining balance is retained in the form.

Loan confirmation and payment matching remain distinct. Unconfirmed loans produce review payment rows with unknown allocations and no balance effects. Accepting their payments first requires confirming the loan terms. A payment recorded before confirmation, or dated on/before the reviewed balance date, can be accepted as a relationship without applying an old inferred allocation to the new balance. Automatic late imports use the same guard. A newly user-created loan with an explicit non-null current balance receives the same verification timestamp; omitted/null balances retain their prior unstamped semantics. Existing history is retained. Confirmed foreclosure-pending debt remains a liability and is excluded from recurring EMI; ordinary foreclosure reconciliation tests still pass.

Bureau creation/matching records confirmation provenance explicitly and verifies report ownership. A weak report or missing current balance cannot confirm a guessed balance. The parser now preserves balance presence with `balance_reported`: an explicit zero is accepted, while the old parser's ambiguous default zero requires review. Positive legacy balances remain supported. When a bureau record confirms a previously inferred loan, absent EMI/rate values no longer inherit the old guesses. Such unknown zero-EMI loans permit notes edits without fabricating terms; explicitly submitted zero EMI remains invalid for manual creation, edits and estimate confirmation. Existing bureau rules and home-value proxies remain planning assumptions; this does not certify every bureau field, imported-document field, tax entitlement, or financial projection.

## Migration

`apps/loans/migrations/0013_loan_verification.py` adds verification status, source and timestamp. Existing manual records remain confirmed. Existing auto-detected records require review unless owned, successful, sufficiently confident bureau-sync results pair with exactly one retained raw account and the same saved loan identity. Reported balance, principal and EMI must support the retained amounts, and the retained rate must be zero because bureau parsing supplies no rate. Ambiguous old zero balances require review. Structured evidence is used instead of parsing free-text notes. This conservative check preserves monetary values while preventing a successful identity match from confirming retained guesses.

The migration preserves monetary values, lifecycle states, payment rows and source documents. It uses the migration connection alias. The test exercises an actual upgrade, ownership/confidence checks, repeat-safe backfill and rollback with record reconciliation. Only disposable test databases were migrated. The operator database, local secrets and frozen releases were not changed.

## Verification

Before each Python invocation, PyCharm reported `F:\ALFRED\.venv\Scripts\python.exe`, Python 3.12.2, pip.

Backend/check environment:

```powershell
$env:ALFRED_LOCAL_RUNTIME='true'
$env:ALFRED_AUTO_TRAIN_ON_STARTUP='false'
$env:ALFRED_DATA_DIR='F:\ALFRED\artifacts\loan-validation-20261001'
$env:DATABASE_URL='sqlite:///:memory:'
$env:CACHE_BACKEND='django.core.cache.backends.locmem.LocMemCache'
$env:CACHE_LOCATION='alfred-loan-validation'
$env:ALFRED_RUN_BROWSER_TESTS='false'
```

Check commands used a separate `artifacts/loan-checks-20261001` data directory. Browser runs used `artifacts/loan-browser-validation-20261001` and the existing temporary-file SQLite runner.

| Command (arguments after interpreter) | Result | Evidence |
|---|---|---|
| `manage.py test tests.test_loan_verification tests.test_loan_lifecycle_and_reports tests.test_financial_baseline_alignment tests.test_financial_relationships tests.test_document_center_and_statement_import tests.test_remaining_task_closures tests.test_tax_policy --noinput --verbosity 1` | 89 passed, 0 failed/skipped; 48.680 s; exit 0 | `artifacts/m12a-domain-final-20261001.log` and result JSON |
| `scripts/run_browser_regressions.py tests.test_user_data_browser.UserDataBrowserTests.test_inferred_loan_requires_explicit_confirmation_on_real_page --browser Chrome --require-browser --artifact-dir artifacts/browser-loan-verification-final-20261001 --proof-label loan-verification-20261001` | 1 passed, 0 failed/skipped; 11.179 s; exit 0 | `artifacts/m12a-browser-final-20261001.log`, browser summary |
| `manage.py check` | No issues; exit 0 | `artifacts/m12a-check-20261001.log` |
| `manage.py makemigrations --check --dry-run` | No model/migration drift; exit 0 | `artifacts/m12a-migrations-20261001.log` |
| `node --check static/js/loans.js`; `git diff --check` | Both exit 0 | Terminal output |

The browser verifies exclusion of a ₹2,40,000 estimate alongside an existing ₹1,00,000 confirmed balance, explicit review, and resulting totals of ₹2,50,000 debt / ₹19,000 EMI after confirmation of ₹1,50,000 current debt / ₹9,000 EMI. The final visible-capture run also passed: 1 test, 16.589 s, exit 0; `artifacts/m12a-browser-visible-20261001.log` and `artifacts/browser-loan-verification-visible-20261001/browser_regression_summary.json`. The confirmation control and confirmed totals screenshots were inspected.

The 89-test run above preceded the subsequent bureau-presence and serializer fixes. A targeted run passed 5 tests in 1.378 s, exit 0, covering parser-to-sync missing/explicit-zero evidence and the strengthened actual migration upgrade/backfill/rollback (`artifacts/m12a-bureau-evidence-targeted-20261001.log`). A second targeted run passed 4 API tests in 0.199 s, exit 0, covering user creation followed by historical import/review, absent/null current balances, unknown bureau EMI notes edits and submitted zero-EMI rejection (`artifacts/m12a-loan-api-boundary-targeted-20261001.log`).

The final combined finance gate passed all 156 tests in 120.950 s, with 0 failures/skips, exit 0 at 2026-10-01 23:46:30 +05:30. It covers the final M12A/B/C source including these follow-ups and the strengthened actual migration test. Evidence: `artifacts/m12-finance-final-20261001.log` and result JSON; the exact command/environment are in `docs/MASTER_M12C_VERIFICATION_20261001.md`. System and migration drift checks are also clear on the final source.

Earlier attempts are retained: the first 39-test run had 38 passes and one migration-fixture error from an incomplete historical user migration state. Fixing that fixture yielded 88 passes; an added bureau missing-EMI regression and final reconciliation adjustment yielded the final 89 above. The first browser attempt failed on a stale Edit button during live refresh; a bounded click retry fixed the test, and the browser run above passed. Intentional database-lock injection in domain tests logs an exception but the final suite exits successfully.

## Scope and next work

M12A is implemented and has focused domain, migration and browser validation. The preceding Phase 1 full backend gate passed 543 tests with 13 skips before M12A runtime changes; the entire backend suite has not been rerun after M12A. No commit/push, real-data migration, installer promotion, clean-PC acceptance or remote CI was performed.

M12B vehicle accounting follows in `docs/MASTER_M12B_VERIFICATION_20261001.md`. Preserve the other master backlog entries and completed Travel work; this note does not close the entire finance or release backlog.
