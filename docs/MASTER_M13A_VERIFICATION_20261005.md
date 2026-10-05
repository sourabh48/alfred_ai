# Master M13A: Loan register monetary storage

Task date: 2026-10-05. Branch: `codex/native-runtime-hardening-20260918`.
HEAD remains `b4e89742717d0f4ce1d8b6e49ccb7b6b6abde525`. Work is local and uncommitted.

## First domain

The model schema and disposable test databases now use Decimal storage for seven Loan register currency fields: principal, EMI, remaining balance, home purchase price, down payment, other upfront payments and total paid. No operator database was migrated. Rate, confidence, ratio and measurement fields keep their existing types. Payment-history, foreclosure-document and foreclosure-snapshot money remains a later stage; other domain monetary models are also still open under M13.

The currency boundary is two decimal places with ROUND_HALF_UP. It accepts finite values within ±₹999,999,999,999.99 (14 digits including two decimal places). Signed legacy values are preserved through normalization; manual API validation still rejects negative amounts. Null remaining balance stays distinct from explicit zero. API input requires at most two decimal places. The custom LoanMoneyField normalizes ordinary ORM create, bulk create, update and partial-save values before persistence.

This bound is deliberate for the local SQLite runtime: Django's SQLite Decimal conversion uses fifteen significant digits. SQLite retains numeric storage limitations, so this does not claim arbitrary-precision SQLite arithmetic or exact aggregates performed inside SQLite. The supported per-field bounds are tested by actual ORM round trips. Portfolio/property totals may exceed a single field's bound; aggregate output does not apply the per-field limit again.

Loan register arithmetic crosses a defined currency boundary. Payment detection/review and foreclosure register posting use Decimal cents, including HALF_UP conversion of legacy half-cent payment amounts. Reviewed total-paid recomputation adds individually normalized payment amounts rather than rounding a binary-float aggregate. Source expenses and payment-history evidence are retained in their current storage types. Canonical amortization/payoff arithmetic accepts Decimal amounts without mixed float operations. Match scores and tax/credit advice retain explicit numeric analysis boundaries.

Loan APIs retain JSON numbers. Serializer fields explicitly disable Decimal-to-string coercion; canonical loan rows, net-worth breakdowns, bureau/credit totals and voice summaries also preserve numeric output. Cache schema markers expire prior loan/financial payloads. Home purchase/down-payment computations use Decimal money, and explicit zero balance yields 100% completion rather than falling back to principal.

## Migration and retained evidence

Migration `0014_loan_money_decimal.py` captures source float values as round-trippable strings before altering columns. A LoanMoneySnapshot retains the original owner/loan identity, source values, normalized two-place values, policy and application timestamp. Snapshots are not exposed through the loan API. The data-reset path removes an owner's snapshots, including orphan evidence after a deleted loan, while preserving other owners' records.

The migration validates all pending legacy rows before writing snapshots. Non-finite or out-of-range currency raises an error identifying the loan and field; the SQLite atomic upgrade tests verify unchanged source records and unapplied migration state after rejection. It does not silently replace invalid money with zero.

The frozen migration conversion applies HALF_UP normalized values after schema conversion, preserving half-cent source evidence across backend conversion defaults. Application runs once per snapshot in an alias-specific transaction. Repeating capture/normalization preserves both originals and later edits. Original currency strings remain unchanged when the application marker is written.

Rollback first restores FloatFields, then restores original precision for currency fields whose rounded value still matches the migration snapshot. Later corrections, null/zero transitions and new rows retain their current values. Deleted loans are not recreated. Loan ownership, verification, lifecycle state, timestamps, payment rows and source documents are reconciled in tests. No operator database was migrated; migration behavior is validated on disposable SQLite databases only.

## Targeted verification

Before each Python invocation, PyCharm reported `F:\ALFRED\.venv\Scripts\python.exe`, Python 3.12.2. Runs use local-runtime mode, disabled startup training, disposable artifact data directories, test SQLite and locmem cache.

| Target | Result | Evidence |
|---|---|---|
| `tests.test_loan_money_migration` final | 10 passed, 0 failures/skips, 15.359 s, exit 0 | `artifacts/m13-loan-migration-final-20261005.log` |
| `tests.test_loan_money_runtime` | 9 passed, 0 failures/skips, 0.277 s, exit 0 | `artifacts/m13-loan-runtime-targeted-20261005.log` |
| `tests.test_loan_money_field` initial | 16 passed, 0 failures/skips, 0.032 s, exit 0 | `artifacts/m13-loan-money-field-20261005.log` and result JSON |
| `manage.py makemigrations --check --dry-run` initial | No drift, exit 0 | `artifacts/m13-loan-migrations-20261005.log` |

The field module subsequently gained a seventeenth test for virtual home totals exceeding the individual field bound. The final migration gained application-marker repeat safety after its first 9-test run; the final 10-test result above includes it.

Final `manage.py check` and `manage.py makemigrations --check --dry-run` both exit 0 with no issues/drift, including the application marker. Evidence: `artifacts/m13-loan-check-final-20261005.log` and `artifacts/m13-loan-migrations-final-20261005.log`.

The Chrome runner passed two workflows in 30.288 s, 0 failures/skips, exit 0: inferred-loan explicit confirmation and sample financial totals across dashboard, budgets, loans and investments. Evidence: `artifacts/m13-loan-browser-20261005.log` and `artifacts/browser-loan-money-20261005/browser_regression_summary.json`. Command after the interpreter:

```text
scripts/run_browser_regressions.py tests.test_user_data_browser.UserDataBrowserTests.test_inferred_loan_requires_explicit_confirmation_on_real_page tests.test_user_data_browser.UserDataBrowserTests.test_sample_totals_and_explanations_on_real_pages --browser Chrome --require-browser --artifact-dir artifacts/browser-loan-money-20261005 --proof-label loan-money-20261005
```

The inspected confirmed-loan screenshot shows ₹2,50,000 debt and ₹19,000 EMI. The inspected dashboard screenshot shows ₹30,000 living expenses, ₹80,000 recorded income, ₹47,000 confirmed outflow and ₹1,00,000 recorded loan balance, with review transactions excluded. Both use the migrated disposable schema.

## Full backend gate

The initial full run completed 643 tests: 625 passed, 16 skipped, one failure and one error, 639.053 s, exit 1. Evidence: `artifacts/m13-loan-backend-20261005.log` and result JSON. This is failed-attempt history, not passing evidence.

The payment-review failure was an old assertion comparing Decimal('52642.67') with a binary float. Exact Decimal assertions now match both accepted/rejected balances. The corrected lifecycle test and 9 runtime regressions passed together: 10 tests, 1.085 s, exit 0, in `artifacts/m13-historical-review-targeted-20261005.log`.

The travel error exposed an existing daily-usage calendar mismatch. ORM date grouping uses the active local timezone, while the summary compared the UTC date. `usage_summary()` now uses `timezone.localdate(now)` on the comparison side. A deterministic regression covers Chicago and Kolkata on opposite sides of UTC midnight, excluding adjacent local days and checking network/cache counts. All 8 provider tests passed in 0.109 s, exit 0: `artifacts/m13-travel-cache-targeted-20261005.log`. Quota, retention, TTL and network behavior are unchanged; this does not close Travel telemetry retention.

The final whole-backend run completed with these fixes and a fresh isolated environment: **644 run, 628 passed, 16 skipped, zero failures/errors, 617.345 s, exit 0**. It finished at 2026-10-05 06:14:12 +05:30. The seventeenth field test and snapshot-retention reset test are included in this passing gate. Command after the interpreter:

```text
manage.py test --noinput --verbosity 1
```

Environment: `ALFRED_LOCAL_RUNTIME=true`, `ALFRED_AUTO_TRAIN_ON_STARTUP=false`, `ALFRED_DATA_DIR=F:\ALFRED\artifacts\loan-money-final-backend-validation-20261005`, `DATABASE_URL=sqlite:///:memory:`, `CACHE_BACKEND=django.core.cache.backends.locmem.LocMemCache`, `CACHE_LOCATION=alfred-loan-money-final-backend-validation`, `ALFRED_RUN_BROWSER_TESTS=false`. Evidence: `artifacts/m13-loan-backend-final-20261005.log` and `artifacts/m13-loan-backend-final-20261005-result.json`. The 16 skips are explicitly disabled browser acceptance tests; the two M13A Chrome workflows above ran separately. Intentional mocked lock, malformed-document, access-denial and durable-queue exception logs are passing resilience coverage, not additional test failures. Exec session 41885 completed and is closed.

## Repository housekeeping

Normal `git diff --check` passed, exit 0: `artifacts/m13-final-diff-check-20261005.log` and result JSON. An attempted check with `core.autocrlf=false` incorrectly treated Windows line endings as whitespace changes; the normal repository settings are the valid check above.

New Graphify guidance in `AGENTS.md`, `.codex/` files and the graph cache appeared during this continuation and were preserved. The instruction to refresh the graph after code changes was handled with a local AST-only update. Graphify was absent from PATH and the configured environment, so `graphifyy==0.9.76` and its helper dependencies were installed with pip `--target` into a temporary directory outside the repository. This did not install those packages into the application environment or change its requirements. The helper `PYTHONPATH` was set only for its separate command process.

`F:\ALFRED\.venv\Scripts\python.exe -m graphify update . --no-cluster` passed, exit 0: **6,524 nodes, 17,885 edges**, written to `graphify-out/graph.json`. Evidence: `artifacts/m13-graphify-update-final-20261005.log` and result JSON; temporary helper path is recorded in `artifacts/m13-graphify-tool-path-20261005.txt`. No model calls, semantic document extraction, clustering or HTML rendering ran. The extractor reported 24 unsupported files and 33 symbol-free code files; this code index is not a complete semantic corpus audit. The initial missing-module attempt is retained separately in `artifacts/m13-graphify-update-20261005.log`. No application runtime edits followed the passing backend gate.

## Remaining scope

M13 is a staged domain migration. This stage covers the Loan register and its runtime boundaries. Payment-history/closure storage and other monetary domains remain open. The next 17-field stage and its allocation, API, snapshot and rollback requirements are recorded in [MASTER_M13B_PLAN_20261005.md](MASTER_M13B_PLAN_20261005.md); that document is a plan, not implemented work. No real-data migration, commit, push, remote CI, frozen build or installer promotion occurred. Local/LAN hosting and untracked local secrets remain as configured.
