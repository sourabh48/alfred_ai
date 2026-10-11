# Master remediation: Windows baseline and tax/dependency P0

Date: 2026-10-01. Branch: `codex/native-runtime-hardening-20260918`.
Base/inspected HEAD: `b4e89742717d0f4ce1d8b6e49ccb7b6b6abde525`.
The working tree was clean before this work. These changes are local and uncommitted.
This is a bounded continuation of the user's master note, not a new repository audit or a release approval.

## Changes

- Fixed the native guide test to expect `guide.resolve().as_uri()`. Production URI resolution is unchanged.
- Updated the requirement and configured virtual environment from Django 6.0 to 6.0.8. The official [download table](https://www.djangoproject.com/download/) lists 6.0.8 for the 6.0 series as of the verification date; the [release notes](https://docs.djangoproject.com/en/6.0/releases/6.0.8/) document its security fixes. The 6.0.9 notes found during research are dated October 6, after this checkpoint, so were not treated as an available release.
- Replaced inline tax slabs with an immutable, versioned Decimal policy for **FY 2025-26 / AY 2026-27**. The policy carries source URLs, verification/effective dates, regime, slabs, standard deduction, deduction eligibility ceilings, rebates, surcharge, marginal relief and cess.
- Applied rebate and marginal relief before cess; added surcharge relief at income thresholds. Ordinary non-salary income gets no salary standard deduction; nonresidents get no resident rebate; resident senior age groups use the appropriate old-regime exemptions.
- Explicitly reject unsupported years, mismatched FY/AY, invalid/nonfinite/negative income, unsupported regimes/sections and special-rate income. No current-year fallback or request-time rule scrape.
- The tax overview validates inputs before cache lookup, includes policy/year in its cache signature, and uses the same income and selected FY for comparison, recorded home-loan payment deductions and savings scenarios. FY/AY and the salary/residency/age assumptions appear in the UI.
- Fixed the separate stale tax reference payload and gave it a versioned cache key. Successful creation of the replacement deactivates the legacy unversioned record, preserving its payload/history and avoiding endless scheduled refreshes. Refreshing a static reference does not change its policy verification date.
- Created the master remediation backlog and updated the continuation state. Prior Travel T07 work remains intact.

## Authoritative tax references and scope

Rules were checked against the Income Tax Department's [AY 2026-27 salaried-individual tables](https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1) and [Budget 2026 FAQs, pages 64–67](https://www.incometaxindia.gov.in/documents/20117/15766092/FAQs-Budget-2026.pdf/ff3d0e10-88a0-b11f-3c27-b58375974227?download=true&t=1770036575267&version=1.0). These cover slabs, age exemptions, resident rebate, surcharge, marginal relief, standard deduction and cess. The new-regime salary example at ₹15,00,000 gives ₹97,500; salary through ₹12,75,000 has zero tax in the supported resident scenario.

This policy is a **planning estimate before statutory return-filing rounding**, with amounts rounded half up to paise. Callers must supply already-eligible deduction amounts; section ceilings do not establish entitlement. Capital gains, lottery/special-rate income, agricultural integration, loss set-offs and credits require separate calculations. FY/TY 2026-27 and other years are deliberately unsupported until their complete policies are independently verified and added; the UI defaults explicitly to FY 2025-26, not the current year.

The existing automatic portfolio deduction leads and HRA/home-loan/action suggestions remain estimates requiring eligibility review. Their 30% marginal-rate assumptions and conditional insurance scenario are labelled. They are not a filed-return engine. Further deduction-evidence/80EEA eligibility cleanup is recorded in the master backlog; this checkpoint does not certify all finance or security work complete.

## Validation environment

PyCharm `get_python_environment(filePath="manage.py")` was called before every Python invocation and returned `F:\ALFRED\.venv\Scripts\python.exe`, Python 3.12.2, pip. Dependencies were changed only for Django.

PowerShell environment for backend/check/migration runs:

```powershell
$env:ALFRED_LOCAL_RUNTIME='true'
$env:ALFRED_AUTO_TRAIN_ON_STARTUP='false'
$env:ALFRED_DATA_DIR='F:\ALFRED\artifacts\master-validation-20261001'
$env:DATABASE_URL='sqlite:///:memory:'
$env:CACHE_BACKEND='django.core.cache.backends.locmem.LocMemCache'
$env:CACHE_LOCATION='alfred-master-validation'
$env:ALFRED_RUN_BROWSER_TESTS='false'
```

No real user database or local secret file was modified. Browser validation used the existing isolated file-SQLite browser runner and `artifacts/master-browser-validation-20261001` as its data directory.

## Executed checks

All Python commands below use the executable above, after the environment preflight.

| Command (arguments after executable) | Result | Local evidence |
|---|---|---|
| `-m unittest tests.test_native_tray -v` | 7 passed, 0 failed/skipped; 0.033 s | `artifacts/phase0-tray-20261001.log` |
| `manage.py test tests.test_native_tray tests.test_native_runtime tests.test_native_launcher tests.test_native_observation tests.test_durable_queue --noinput --verbosity 1` | 32 passed, 0 failed/skipped; 2.209 s | `artifacts/phase0-native-20261001.log` |
| `-m pip install Django==6.0.8 --disable-pip-version-check` | Installed successfully | `artifacts/phase1-django-install-20261001.log` |
| `manage.py check` | No issues, exit 0 | `artifacts/phase1-check-20261001.log` |
| `manage.py makemigrations --check --dry-run` | No changes, exit 0 | `artifacts/phase1-migrations-20261001.log` |
| `manage.py test tests.test_auth_pages tests.test_platform_hardening tests.test_production_readiness_contracts tests.test_local_config tests.test_financial_baseline_alignment tests.test_financial_relationships --noinput --verbosity 1` | 53 passed, 0 failed/skipped; 48.544 s | `artifacts/phase1-django-regression-20261001.log` |
| `manage.py test tests.test_tax_policy tests.test_remaining_task_closures.TaxDeductionTests tests.test_financial_baseline_alignment tests.test_advisory_evidence_freshness tests.test_operational_hardening tests.test_application_smoke --noinput --verbosity 1` | 54 passed, 0 failed/skipped; 32.608 s | `artifacts/phase1-tax-domain-final-20261001.log` |
| `scripts/run_browser_regressions.py tests.test_user_data_browser.UserDataBrowserTests.test_tax_planning_uses_selected_year_and_income --browser Chrome --require-browser --artifact-dir artifacts/browser-tax-policy-20261001 --proof-label tax-policy-20261001` | 1 passed, 0 failed/skipped; 10.724 s | `artifacts/phase1-tax-browser-20261001.log`, browser summary and screenshot |
| `manage.py test --noinput --verbosity 2` (original run) | Interrupted without a summary or exit record; no surviving process when resumed | `artifacts/phase1-backend-gate-20261001.log`; expected result JSON was absent |
| `manage.py test --noinput --verbosity 2` (resumed run) | 556 run: 543 passed, 13 skipped, 0 failed; 576.488 s; exit 0 | `artifacts/phase1-backend-gate-resumed-20261001.log`, `phase1-backend-gate-resumed-20261001-result.json` |

`node --check static/js/tax_optimizer.js` and `git diff --check` passed. The Chrome screenshot was inspected: selected year, scenario scope, ₹97,500 new-regime tax and recalculated comparison are visible.

Test coverage includes all slab boundaries at -1/exact/+1, both rebate thresholds, the official marginal-relief examples, every surcharge boundary, surcharge caps, nonresidency, age exemptions, salary vs ordinary income, Decimal inputs, invalid values/years, eligible/ignored deductions, API cache reuse, selected-year payments, reference refresh/history and user isolation.

Earlier attempts are retained honestly: initial tax test run had one cache-fixture failure; initial domain run had one legacy-reference refresh failure (fixed); a follow-up fixture omitted required `stale_after` (fixed). The final 54-test run supersedes those failures. They are not counted as additional passing suites.

## Remaining acceptance

No GitHub CI run, commit/push, installer build, release promotion, keyed provider check or clean-machine acceptance was performed. Older frozen artifacts do not contain this patch. Continue with the highest unresolved master P0, retaining the exact work queue in `artifacts/audit/ALFRED_DEEP_REVIEW_BACKLOG.md`.

The resumed full gate completed on 2026-10-01 at 18:36:16 +05:30 before applying M12A runtime changes. Its 13 skips are opt-in browser tests; it is not a full-suite result for the subsequent loan-verification patch. See `docs/MASTER_M12A_VERIFICATION_20261001.md` for that patch's focused migration/domain/browser evidence.
