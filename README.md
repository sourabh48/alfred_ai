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
| Career source coverage | 88% - current resume, recruiter/JD, multi-feed jobs, job-page adapter, and geography-aware compensation scope is implemented, but real salary/outcome breadth still needs growth |
| Shared document review / retry flow | 86% - parser confidence, schema-aware OCR candidates, ChatGPT context import, accepted corrections, retry learning, and tougher service-invoice recovery are implemented; long-tail layouts and browser interaction proof still need more real samples |
| External proof and freshness | 90% - proof contracts and freshness metadata are active; due/stale evidence still needs refresh monitoring |
| UI polish and responsive shell | 45% - live-server smoke coverage and the guarded vehicle catalog picker are active, but Playwright/Selenium browser interaction coverage is not installed locally |
| Mobility vehicle catalog and service intelligence | 88% - supported India consumer-vehicle seed scope has 80 source-linked models across 32 manufacturers, route-aware wear guidance, and service-cost learning; not exhaustive |
| ML-assisted features | 76% - supervised trainable models are fresh and ready; broader ML maturity is capped by confidence, data volume, heuristic fallbacks, and a planned future RL learner |
| Production hardening | 84% - heavy dashboard materialization exists for the current app scope; production cache sizing, TTL tuning, and observability remain open |

## Verification Snapshot

Last verified locally on 31 July 2026.

| Scope | Verified state |
| --- | --- |
| Project tracker | Broad product areas now stay in In Progress until implementation, data maturity, and browser verification are all strong enough |
| Scope completion | 80% in the current local snapshot; this is the average maturity across active broad product scopes |
| Verified complete checks | Backend/API regression baseline, vehicle make/model picker fix, and supervised model refresh are the only 100% entries |
| Vehicle maintenance learning | 88% - current catalog, route-aware maintenance, service-cost learning, and brand-filtered selection are implemented, but long-tail models, source upkeep automation, condition snapshots, and real issue outcomes still matter |
| Vehicle catalog UI | One Make / Brand combobox submits the actual `make` value; Official Catalog Model is populated only after a make is selected and is guarded from live-refresh re-render while the user is choosing |
| Catalog API | `/api/mobility/bike-models/catalog/` supports `vehicle_type` plus `make`, `brand`, or `manufacturer` filters |
| ChatGPT context import | `/api/reports/chatgpt-imports/` and the document center accept pasted transcripts or ChatGPT JSON exports, then store detected module evidence for review |
| Document OCR correction | Generic OCR amount/date candidates are mapped into scope-specific correction fields, and vehicle service invoices now recover label-collapsed compact rows such as embedded `Qty`, `Hrs`, `Amount`, and currency tokens |
| Model training | 7/7 supervised trainable model states are fresh and ready; 1 planned future RL learner is excluded from supervised coverage |
| Evidence watchlist | 1 stale, failed, rejected, or due verified evidence record in the current local data snapshot |

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

## Large Data Hardening

- budget, loan, net-worth, behavioral, risk, recommendation, tax, career, family, relationship, investment, and mobility dashboard payloads use cache-aware materialized summaries
- materialized payloads include `_materialized` metadata with cache hit status, revision, generation time, and TTL
- remaining production work is environment-specific cache sizing, TTL tuning, and observability

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
- full browser automation is not installed in this local environment; UI regression coverage currently uses Django live-server rendering, static-asset checks, form-contract checks, and backend/API functional tests

## Test Commands

```bash
python manage.py check
python manage.py test
```

For focused UI and vehicle-service coverage:

```bash
python manage.py test tests.test_live_ui_contracts tests.test_mobility_vehicle_dashboard tests.test_mobility_endpoint_contracts tests.test_project_details_live
```

For focused finance coverage:

```bash
python manage.py test tests.test_loan_lifecycle_and_reports tests.test_credit_report_upload tests.test_investment_and_relationship_advisory
```
