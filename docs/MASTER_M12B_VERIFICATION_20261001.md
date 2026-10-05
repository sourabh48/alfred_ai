# Master M12B: vehicle net-worth accounting

Date: 2026-10-01. Branch: `codex/native-runtime-hardening-20260918`.
HEAD remains `b4e89742717d0f4ce1d8b6e49ccb7b6b6abde525`. Changes are local and uncommitted.

## Behavior

Every owned vehicle contributes its recorded positive current market-value estimate to assets, regardless of personal, essential, mixed or commercial usage. Missing, zero, negative or non-finite legacy values contribute zero. Running costs and income support never supply a resale value or create a liability. Catalog/specification verification does not verify resale value; calculation-risk reporting labels all vehicle values as user estimates.

Confirmed open vehicle loans remain in the canonical Loan ledger and are counted once as debt. Unconfirmed loans remain excluded under M12A. Foreclosure-pending debt remains a liability without recurring EMI; closing a loan does not remove vehicle ownership. BikeProfile has no loan foreign key, so this change introduces no inferred loan association or new schema.

Service and trip costs remain separate context labelled as all recorded history. The former all-history-total divided by twelve is no longer presented as a monthly running cost. Expense transactions continue through the existing cash-flow calculation. Mobility records do not create a duplicate cash-flow expense or debt.

The net-worth API exposes `assets.vehicles`. Its existing `utility_and_income_supporting_vehicles` field remains a same-value compatibility alias; totals sum canonical rows once. The legacy `lifestyle_vehicle_burden` field is zero. Vehicle value edits and deletions participate in the loan/net-worth cache revision. The expenses page displays estimated asset value and recorded running costs separately.

The focused edit regression found that a catalog refresh reset an omitted owner value to zero. Vehicle updates now preserve saved usage, market value and income-support overrides, including explicit zero, when the request omits them.

## Verification

Python commands use the PyCharm-reported `F:\ALFRED\.venv\Scripts\python.exe` (3.12.2), with a fresh environment preflight before each invocation. Validation uses `ALFRED_LOCAL_RUNTIME=true`, startup training disabled, disposable `artifacts` data directories, in-memory/test-file SQLite and locmem cache. The operator database and `config/local.env` are untouched.

The Chrome workflow `tests.test_user_data_browser.UserDataBrowserTests.test_vehicle_value_and_running_costs_are_separate_on_real_page` passed: 1 test, 0 skips, 9.374 s, exit 0 (runner 19.86 s). Evidence: `artifacts/m12b-browser-20261001.log` and `artifacts/browser-vehicle-accounting-20261001/browser_regression_summary.json`.

The inspected screenshot `artifacts/browser-vehicle-accounting-20261001/user-data/vehicle-value-and-running-costs.png` shows ₹3,10,000 total assets, ₹1,00,000 unchanged debt and ₹2,10,000 net worth. Its vehicle row shows an estimated ₹50,000 asset and ₹6,000 recorded running costs (all history).

The initial domain run executed 77 tests in 85.630 s with one failure: an unrelated usage edit erased the recorded vehicle value during catalog refresh. It is retained in `artifacts/m12b-domain-20261001.log` and is not passing evidence. After the fix, `tests.test_vehicle_accounting tests.test_mobility_vehicle_dashboard` passed all 21 tests in 14.043 s, exit 0 (`artifacts/m12b-profile-fix-targeted-20261001.log`).

The final combined finance gate passed all 156 tests in 120.950 s, with no failures/skips, exit 0 at 23:46:30 +05:30. It includes the final vehicle, mobility, loan-verification, migration, tax and investment changes. Evidence: `artifacts/m12-finance-final-20261001.log` and result JSON. The exact command/environment are in `docs/MASTER_M12C_VERIFICATION_20261001.md`. System check and migration drift check both exit 0 with no issues/drift; expenses/loans/investments JavaScript syntax and whitespace checks also passed. Checks migrated no user database.

## Scope

This corrects vehicle accounting and preserves the existing local/LAN runtime. No user database migration, commit, push, release or installer promotion was performed. Market values remain estimates. The preceding whole-backend Phase 1 gate predates M12A/M12B changes; focused results do not constitute a fresh entire-backend run.
