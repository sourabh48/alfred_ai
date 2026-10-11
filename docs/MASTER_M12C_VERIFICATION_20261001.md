# Master M12C: investment projection boundary

Date: 2026-10-01. Branch: `codex/native-runtime-hardening-20260918`.
HEAD remains `b4e89742717d0f4ce1d8b6e49ccb7b6b6abde525`. Changes are local and uncommitted.

## Behavior

Month zero now equals the portfolio's recorded current value, without a new SIP or growth. The former helper ran `months + 1` periods: ₹1,00,000 with ₹1,000 SIP and 12% entered annual return became ₹1,02,010 at month zero. That amount now correctly belongs to month one.

The existing contribution timing is preserved: each elapsed future month adds one SIP at the beginning of the month, then applies the assumed monthly return. The monthly decimal rate is the entered annual percentage divided by 1200. The engine performs exactly `months` iterations. This remains a scenario using entered rates, rather than a guaranteed return or effective-annual-rate model.

The growth API retains `labels` and `values` and now returns thirteen points for elapsed months 0 through 12. `months_elapsed` and `assumptions` make the recorded-value boundary, contribution timing, rate source and conversion explicit. The existing chart consumes the longer arrays without a JavaScript change. The page caption explains the same timing.

Only owned investments are included. A growth-specific cache version prevents old shifted curves from surviving the code change. A captured local month anchor is shared by the revision and builder, so month/year rollover updates labels without waiting for a position edit. Other investment summary/allocation cache schemas are unchanged.

## Verification

PyCharm environment preflight reported `F:\ALFRED\.venv\Scripts\python.exe`, Python 3.12.2, before each Python invocation. Tests use disposable `artifacts` data directories, test SQLite databases and locmem caches; the operator database and local secrets are untouched.

The focused command `manage.py test tests.test_investment_projection tests.test_investment_and_relationship_advisory --noinput --verbosity 2` passed 20 tests in 10.541 s, exit 0, with no failures/skips. It covers 0/1/12 months, zero SIP/return, negative return, the independent annuity formula, thirteen-point API aggregation/ownership, edits, empty holdings, old-cache rejection and local month/year rollover. Evidence filenames mistakenly use the next day's suffix: `artifacts/m12c-domain-20261002.log` and `artifacts/m12c-domain-20261002-result.json`; the actual finish was 2026-10-01 23:42:42 +05:30. The final combined gate below uses the standard project local-runtime/training flags and the correct date suffix.

The Chrome workflow `tests.test_user_data_browser.UserDataBrowserTests.test_investment_projection_starts_with_recorded_value_on_real_page` passed: 1 test, 0 failures/skips, 13.817 s, exit 0. Evidence: `artifacts/m12c-browser-20261001.log` and `artifacts/browser-investment-projection-20261001/browser_regression_summary.json`.

The browser checks actual Chart.js data, not just page text: ₹1,10,000 at month zero, ₹1,15,766.67 at month one and ₹1,81,794.57 at month twelve for ₹5,000 SIP and 8% entered annual return. It checks the timing caption. The inspected screenshot `artifacts/browser-investment-projection-20261001/user-data/investment-month-zero-projection.png` shows October 2026 through October 2027 and the full caption. Captured chart data is saved alongside it in `investment-growth-values.json`.

`manage.py check` and `manage.py makemigrations --check --dry-run` both exit 0 with no issues/drift (`artifacts/m12-finance-check-20261001.log` and `artifacts/m12-finance-migrations-20261001.log`). No schema change is needed for M12C. `node --check` passed for expenses, loans and investments JavaScript; `git diff --check` passed.

## Final combined finance gate

All 156 tests passed, with 0 failures/skips, in 120.950 s; exit 0 at 2026-10-01 23:46:30 +05:30. This run includes final M12A bureau-presence/serializer/migration changes, M12B vehicle/catalog-preservation changes and M12C projection changes. Evidence: `artifacts/m12-finance-final-20261001.log` and `artifacts/m12-finance-final-20261001-result.json`. The database-lock traceback in the log is an intentional mocked fault in a passing statement-import resilience test.

Command after the interpreter:

```text
manage.py test tests.test_loan_verification tests.test_loan_verification_api tests.test_bureau_balance_evidence tests.test_vehicle_accounting tests.test_mobility_vehicle_dashboard tests.test_loan_lifecycle_and_reports tests.test_financial_baseline_alignment tests.test_financial_relationships tests.test_document_center_and_statement_import tests.test_remaining_task_closures tests.test_tax_policy tests.test_calculation_risk_snapshot tests.test_user_data_acceptance tests.test_investment_projection tests.test_investment_and_relationship_advisory --noinput --verbosity 1
```

Environment:

```powershell
$env:ALFRED_LOCAL_RUNTIME='true'
$env:ALFRED_AUTO_TRAIN_ON_STARTUP='false'
$env:ALFRED_DATA_DIR='F:\ALFRED\artifacts\finance-m12-validation-20261001'
$env:DATABASE_URL='sqlite:///:memory:'
$env:CACHE_BACKEND='django.core.cache.backends.locmem.LocMemCache'
$env:CACHE_LOCATION='alfred-finance-m12-validation'
$env:ALFRED_RUN_BROWSER_TESTS='false'
```

System and drift checks use separate disposable directories (`finance-m12-checks-20261001` and `finance-m12-migration-checks-20261001`). Browser runs use the existing temporary-file SQLite test runner and `investment-browser-validation-20261001`.

## Scope

This closes the elapsed-month boundary and makes existing scenario timing explicit. Monetary FloatFields and broader financial assumptions remain separate backlog items (M13/M12D). No user database migration, commit, push, release or installer promotion was performed. The full backend Phase 1 gate predates M12A/B/C; the final focused finance gate is separate evidence.
