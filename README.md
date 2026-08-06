# ALFRED AI

ALFRED is a Django application that turns personal financial records into one working system. Instead of separate tools for expenses, loans, credit reports, investments, and documents, Alfred keeps them linked so the user can see what is happening across cash flow, debt, and assets in one place.

## What Alfred Does

- imports bank statements and classifies transactions into expense, loan, other outflow, and credits
- tracks loans, repayments, foreclosure documents, and closure confirmation through statement matching
- uploads bureau reports such as CIBIL PDFs and extracts score, tradelines, and active/closed loan details
- tracks investments manually and through portfolio PDF imports, and can surface a proof-backed short-horizon mutual-fund watchlist from official AMFI NAV data
- imports pasted ChatGPT dashboard/chat context into the document center as reviewable source material with module hints
- shows balance-sheet style outputs: assets, liabilities, net worth, debt pressure, cash flow, and behavioral signals
- includes additional modules for career, mobility, risk, family, behavioral patterns, and relationship planning

## Current Progress

| Area | Status |
| --- | --- |
| Expenses and statements | Working |
| Loans and foreclosure reconciliation | Working |
| Credit report upload and tradeline sync | Working |
| Investments manual + PDF intake | Working |
| Career source coverage | 88% - current resume, recruiter/JD, multi-feed jobs, job-page adapter, geography-aware compensation, specialty-source gap policy, and salary-bearing outcome tracking are implemented, but accepted/rejected salary outcome breadth still needs growth |
| Shared document review / retry flow | 91% - parser confidence, schema-aware OCR candidates, ChatGPT context import, cross-family unknown-layout fixtures, accepted correction outcomes, retry learning, tougher service-invoice recovery, and Selenium-proven vehicle OCR correction are implemented; real unknown layouts and validated correction outcomes must keep growing before field-level learning is mature |
| External proof and freshness | 88% - required-source proof contracts now cover current recommendation and relationship-adjacent surfaces, freshness metadata, circuit breakers, stale fallback, scheduled-refresh contracts, and refresh-health observability; source upkeep still needs healthy scheduled runs over time |
| UI polish and responsive shell | 74% - live-server smoke coverage, static/form contracts, login, statement upload, vehicle setup, dashboard live refresh, core form wiring, the guarded vehicle catalog picker, a dedicated Selenium runner, CI browser workflow, run-summary proof, and browser failure artifacts are active; full UI maturity still depends on repeated healthy driver-backed execution plus broader real interaction depth |
| Mobility vehicle catalog and service intelligence | 88% - supported India consumer-vehicle seed scope has 80 source-linked models across 32 manufacturers, route-aware wear guidance, source-refresh policy tracking, and service-cost learning; long-tail models, condition snapshots, and resolved/costed issue outcomes still need real usage growth |
| ML-assisted features | 87% - production-ready supervised model counts exclude the planned future RL learner; broader ML maturity is capped by confidence, data volume, artifact freshness, and heuristic fallbacks |
| Production hardening | 90% - heavy dashboard materialization and cache health observability cover all 21 registered materialized namespaces under deterministic staging traffic; production cache sizing, TTL tuning, and sustained real-traffic telemetry still need deployment proof |

## Verification Snapshot

Last verified locally on 6 August 2026.

| Scope | Verified state |
| --- | --- |
| Project tracker | Broad product areas now stay in In Progress until implementation, data maturity, and browser verification are all strong enough |
| Scope completion | 87% in the current local snapshot; this is the average maturity across active broad product scopes |
| Verified complete checks | Backend/API regression baseline, vehicle make/model picker fix, and supervised model refresh are the only 100% entries |
| Vehicle maintenance learning | 88% - current catalog, route-aware maintenance, service-cost learning, source freshness metadata, and brand-filtered selection are implemented, but long-tail models, source upkeep automation, condition snapshots, and real issue outcomes still matter |
| Vehicle catalog UI | One Make / Brand combobox submits the actual `make` value; Official Catalog Model is populated only after a make is selected and is guarded from live-refresh re-render while the user is choosing |
| Catalog API | `/api/mobility/bike-models/catalog/` supports `vehicle_type` plus `make`, `brand`, or `manufacturer` filters |
| ChatGPT context import | `/api/reports/chatgpt-imports/` and the document center accept pasted transcripts or ChatGPT JSON exports, then store detected module evidence for review |
| Document OCR correction | Generic OCR candidates are mapped into scope-specific correction fields across statement, loan, loan-closure, investment, vehicle, resume, recruiter, and credit-report families; vehicle service invoices also recover label-collapsed compact rows such as embedded `Qty`, `Hrs`, `Amount`, and currency tokens |
| Model training | 7/7 production-ready supervised model states are fresh and ready; 1 planned future RL learner is excluded from production-ready ML and supervised coverage |
| Advisory proof contracts | Current recommendation and relationship-adjacent surfaces declare source URL, stale-after, scheduled refresh, stale fallback, and circuit-breaker requirements before any new signal can be treated as mature |
| Evidence watchlist | Project Details reports live stale, failed, rejected, and due verified evidence with per-scope refresh health, last attempt, and last success timestamps |
| Materialized cache health | Project Details reports registered cache namespaces, hit/miss counts, TTL metadata, stale regeneration, invalidation reason, revision key, generation latency, and deterministic staging traffic proof for all 21 registered namespaces |
| Browser coverage | Project Details reports Selenium-gated interaction workflows, the dedicated runner, CI workflow, local Chrome/Edge proof, CI Chrome proof, `browser_regression_summary.json`, screenshots/log artifacts, and always-on live-server contracts for login, uploads, dashboard refresh, vehicle setup, and core forms without calling the UI fully mature |

The live tracker now separates narrow verified checks from broad product maturity. A 100% entry means that exact check is closed; it does not imply the surrounding product area is fully mature.

## How A New User Uses Alfred

1. Create an account and sign in.
2. Upload a bank statement to populate transactions and monthly flow.
3. Add loans manually or upload loan / closure documents.
4. Upload a CIBIL or other bureau report to sync active and closed loans.
5. Add investments manually or import a portfolio PDF.
6. Import an existing ChatGPT dashboard or chat transcript from the document center if you already have prior planning context.
7. Open the dashboards to view cash flow, liabilities, net worth, recurring commitments, and risk signals.

## Key Finance Features

### Expenses

- filtered expense timeline with merchant, reference, and transaction-id search
- monthly flow chart and unwanted-spend detection
- balance-sheet summary with assets, liabilities, and net worth

### Loans

- manual loan book with repayment history
- foreclosure / pre-closure / closure document parsing
- deterministic lifecycle:
  verified document -> foreclosure pending -> foreclosed only after payment match
- settlement split into principal, interest, charges, penalties, and tax when the closure payment is reconciled

### Credit Reports

- upload PDF bureau reports directly
- extract score, borrower/report details, and tradelines
- sync active and closed bureau loans into Alfred's internal loan view conservatively

### Investments

- add mutual funds, stocks, debt, gold, REIT, cash, and crypto manually
- import broker / holdings PDFs to create or update positions
- allocation, growth projection, market-context guidance, and a transparent 1-2 month watchlist with proof links

### Recommendation Workspace

- focuses on investments and insurance for this workspace
- credit card and personal loan suggestions are intentionally suppressed
- all short-horizon fund watchlist items are ranked candidates, not guaranteed return claims
- new recommendation or relationship-adjacent signals must extend the proof contract before they are counted as mature

## Home Loan Note

Alfred now treats a home loan as an asset-backed position in the financial summary. It uses the financed amount as a conservative property-value proxy and keeps the remaining loan in liabilities. This helps show equity being built without pretending Alfred knows appreciation, down payment, or sale value unless the user tracks those separately.

## Quick Start

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Optional Local Setup

Copy the UI config example if you want local wording or branding overrides:

```bash
copy config\alfred_ui.example.json config\alfred_ui.json
```

If the local config file is missing, Alfred falls back to built-in defaults. The tracked example file should stay generic and safe for Git.

## Background Workers

Some retry, refresh, and training flows use Celery:

```bash
celery -A alfred_ai worker -l info
celery -A alfred_ai beat -l info
```

`refresh_verified_external_intelligence` calls `refresh_due_records`, which now records processed, refreshed, skipped, failed, per-scope watchlist, last-attempt, and last-success outcomes for Project Details.

Production deployments must run both Celery worker and Celery beat processes with Redis or another supported broker. The schedules are already implemented; production maturity depends on those processes staying healthy outside local Django requests.

## Large Data Hardening

- budget, loan, net-worth, behavioral, risk, recommendation, tax, career, family, relationship, investment, and mobility dashboard payloads use cache-aware materialized summaries
- materialized payloads include `_materialized` metadata with cache hit/miss status, revision key, generation time, expiration time, TTL, invalidation reason, stale-regeneration flag, and generation latency
- Project Details aggregates cache hit rate, stale regeneration, invalidation count, average generation latency, TTL coverage, and per-namespace status
- deterministic staging/test traffic can exercise every registered namespace and write `artifacts/cache/materialized_cache_traffic_summary.json`
- remaining production work is environment-specific cache sizing, TTL tuning, and sustained telemetry under real payload volume and concurrency

Run the deterministic materialized-cache traffic proof:

```bash
python scripts/exercise_materialized_cache_traffic.py
```

## Production Readiness

ALFRED is not production-ready until the deployment environment proves database, shared cache, worker, browser-regression, security, and production-like cache-traffic health. See [Production Readiness](docs/PRODUCTION_READINESS.md).

## ML Runtime

- Alfred prefers `scikit-learn` for supported tabular training tasks when the machine allows it.
- First-run startup asks a superuser for approval before auto-training.
- If Windows blocks sklearn native files, Alfred keeps the application running and explains the issue instead of crashing.
- Several outputs still use deterministic or evidence-backed heuristics where a trained model would not be safe or justified yet.

## Important Paths

- `apps/expenses/` - statements, transactions, financial intelligence
- `apps/loans/` - loans, repayment tracking, foreclosure parsing and reconciliation
- `apps/integrations/` - credit reports, verified evidence, recommendation support
- `apps/investments/` - positions, portfolio import, allocation and growth
- `templates/` and `static/js/` - user-facing pages and interactions
- `tests/` - regression coverage

## What Is Not Fully Automatic Yet

- live official bureau pulls still need real partner integrations
- market appreciation and property sale timing are not auto-guessed from the internet
- deployment choices such as production database, cache, workers, and host settings still need environment-specific setup
- browser interaction coverage is implemented, but full UI maturity is gated until the dedicated Selenium runner repeatedly records local Chrome or Edge and CI Chrome runs without skipped browser tests or runner failures

## Test Commands

```bash
python manage.py check
python manage.py test
```

For focused UI and vehicle-service coverage:

```bash
python manage.py test tests.test_live_ui_contracts tests.test_mobility_vehicle_dashboard tests.test_mobility_endpoint_contracts tests.test_project_details_live
```

For Selenium-backed browser coverage, normal Django test runs keep the browser suite explicitly skipped unless `ALFRED_RUN_BROWSER_TESTS=true`:

```bash
python manage.py test tests.test_document_review_browser
```

To run the real browser job locally with Chrome and require driver-backed execution:

```bash
python scripts/run_browser_regressions.py --browser Chrome --require-browser
```

Use Edge instead when that is the installed browser:

```bash
python scripts/run_browser_regressions.py --browser Edge --require-browser
```

On browser failures, Selenium writes screenshots, page HTML, browser logs where supported, and metadata under `artifacts/browser` by default. Override it with `--artifact-dir path/to/artifacts` or `ALFRED_BROWSER_ARTIFACT_DIR`.

Every browser runner invocation also writes `artifacts/browser/browser_regression_summary.json` plus a labeled proof file such as `browser_regression_summary.local-chrome.json`, `browser_regression_summary.local-edge.json`, or `browser_regression_summary.ci-chrome.json`. Project Details separates local Chrome/Edge proof from CI Chrome proof so local success does not overstate CI maturity.

For focused finance coverage:

```bash
python manage.py test tests.test_loan_lifecycle_and_reports tests.test_credit_report_upload tests.test_investment_and_relationship_advisory
```
