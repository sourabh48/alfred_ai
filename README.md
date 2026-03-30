# ALFRED

ALFRED is a Django-based lifestyle intelligence system that combines personal finance, mobility, travel planning, and decision-support dashboards.

The project now includes:

- finance dashboards for expenses, budgets, loans, investments, reports, tax, credit, recommendations, family, career, behavioral, relationship, and risk
- a centralized document hub for statements, loan PDFs, vehicle documents, service bills, and resumes
- a loans workspace with document-backed foreclosure, consolidation tracking, and statement-linked repayment detection
- a dedicated vehicle-service dashboard with upload-first document parsing, service-bill import, part-impact analysis, compliance tracking, and condition scoring
- a mobility workspace with travel plans, trip logs, heat-map points, gallery history, and internet-backed travel advice
- a career workspace with resume upload, job-link matching, live market context, layoff news, and suggested openings
- source-aware external intelligence caching so travel, career, and risk modules can keep proof, freshness windows, stale-data cleanup rules, and circuit-breaker-backed fallbacks
- a separate superuser-only project-details dashboard for in-progress work, live operational counts, learning progress, reports, risks, and guardrails outside the main user dashboard
- severity-based support routing where ALFRED auto-handles low and medium issues, while high-severity issues are escalated to superuser developers without a user-facing manual ticket form

## Current Status

- Backend: active and materially expanded beyond the original finance-only scope
- UI: dashboard coverage exists across the major modules, including mobility and bike/vehicle service
- Data verification: partially implemented
- uploaded vehicle documents are parsed and relevance-checked against the selected vehicle profile
- career now parses uploaded resumes, analyzes pasted job links, and attaches source-backed market/news evidence
- career now generates study recommendations from experience stage, resume skill coverage, latest job gaps, and live opening signals
- resume parser learning memory is stored per user so adaptation stays user-scoped instead of mixing patterns across accounts
- bank-statement imports now use stronger account-scoped transaction fingerprints to reduce duplicate imports
- statement uploads now retain parser status, confidence, and extracted metadata even when transaction extraction is partial
- travel, career, and risk now expose cached external evidence with source URLs and freshness metadata
- credit output now distinguishes internal estimates from official bureau pulls and no longer stores fake bureau pulls as if they were real
- support tickets and project-detail metrics now carry server-side internal-clock timestamps
- the balance-sheet view now separates assets and liabilities, including vehicle treatment based on usage and utility
- the vehicle-service dashboard now explains how serviced parts affect performance, reliability, mileage, and safety
- broader cross-module proof enforcement is still in progress

## Key Modules

- `apps/expenses`: transaction ingestion, account aggregation, forecasting hooks
- `apps/budgets`: budgeting dashboard and intelligence
- `apps/loans`: loan CRUD, PDF parsing, and payoff tracking
- `apps/investments`: portfolio analysis
- `apps/integrations`: credit score, tax/recommendation support, verified external intelligence cache
- `apps/mobility`: vehicle profiles, service intelligence, travel planning, trip media, and travel advisor
- `apps/career`, `apps/risk`, `apps/behavioral`, `apps/relationship`, `apps/family`: personal-life dashboards and APIs

## Mobility Highlights

- multiple vehicle profiles with primary-vehicle selection
- upload-first insurance / PUC / RC / invoice handling
- automatic service-log creation from service bills or work notes
- condition snapshots, fault reports, projected service cost, and workshop-ready wording
- travel advice with destination resolution, weather, offbeat suggestions, stay-budget guidance, and vehicle-readiness context

## Career Highlights

- resume upload and parsing for `pdf`, `docx`, and `txt`
- broader resume intake for `pdf`, `doc`, `docx`, `txt`, `md`, `rtf`, `html`, `odt`, and image-based CV files
- extracted skill, experience, and strength/weakness summaries
- pasted job-link parsing from structured/generic career pages
- job-fit scoring against the latest resume or profile
- study recommendations based on experience stage, latest job gaps, and current opening tags
- dated career-risk timing windows based on runway, fit, and market pressure
- live layoff-news panel and role-level market-risk view
- suggested openings with direct application links from a live job API source
- scanned or image-only CVs now degrade to `needs_review` instead of breaking the upload flow when OCR is not configured on the server

## Expense Import Highlights

- multiple bank accounts with account-specific import resolution
- statement imports can be tagged or auto-detected as bank, credit-card, loan, investment, or other statements
- stronger duplicate detection using account-scoped transaction fingerprints
- repeated statement uploads to the same account are skipped more reliably
- matching transactions on different accounts are preserved instead of being incorrectly collapsed
- partial parses are still stored as statement records so the document trail is not lost
- newly imported loan-classified statement entries are now rechecked against the loan book so Alfred can infer which loan is being paid

## Document Center Highlights

- `/documents/` gives users one place to upload statements, loan PDFs, vehicle documents, service bills, and resumes
- parser confidence is surfaced in the document hub instead of being hidden inside individual modules
- recent statements, recent vehicle documents, and the latest career file are visible from the same intake surface
- document intake is centralized, while the downstream dashboards still own their domain-specific analysis and actions

## AI And Adaptation Reality

- ALFRED is adaptive and AI-assisted today, but it is not fully model-trained end to end across every module
- ML-backed paths currently include behavioral anomaly detection, behavior signatures, personalization, expense confidence scoring, and parser-confidence tracking
- parser learning memory for resumes is now user-scoped so one user's document patterns do not calibrate another user's parser confidence
- several important dashboards still use evidence-backed heuristic blending rather than reviewed predictive models, especially in career timing, vehicle diagnosis, and consolidated risk
- project-details now shows an explicit learning-progress view so the current maturity of each adaptive path is visible to superusers instead of being implied

## Credit Integrity

- official bureau scores are not faked when no bureau-approved integration is configured
- ALFRED can still compute an internal credit-health estimate from the user's own balances, loans, missed-payment data, and utilization signals
- official TransUnion CIBIL, Experian, Equifax, or CRIF pulls require real partner integration and user consent flows; PAN alone is not treated as sufficient proof in the current codebase

## Assets vs Liabilities

- the expenses intelligence API now exposes a balance-sheet layer alongside cash-flow analytics
- bank balances, investments, loans, and vehicle positions are separated into asset and liability buckets
- vehicles can be treated as assets or liabilities based on usage pattern, running cost, market value, and declared utility or income support
- the balance-sheet view still appears even before expense history exists, as long as ALFRED already has accounts, loans, investments, or vehicle profiles

## Verified External Intelligence

ALFRED now stores external signals in `VerifiedExternalInsight` records with:

- source name and URL
- cached payload
- checksum
- fetched/verified timestamps
- stale-after window
- stale cleanup for failed or deactivated records
- circuit-breaker-backed fallback to the last verified payload when upstream sources keep failing
- scheduled refresh and cleanup tasks for the verified evidence cache
- server-side internal-clock snapshots for operational timestamps and support-ticket routing

Charts across the main dashboards are intended to render only live API-backed data or explicit empty states. This pass removed reliance on user-facing demo/report widgets and kept operational reporting inside superuser surfaces.

Current source-backed paths include:

- World Bank indicators for macro context
- Yahoo Finance market snapshots
- OpenStreetMap Nominatim for destination and nearby-place discovery
- Open-Meteo for travel weather windows
- Google News RSS for layoff and hiring-news panels
- Remotive Jobs API for suggested openings

## Installation

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Optional:

```bash
python manage.py createsuperuser
```

For scheduled verified-intelligence refresh and cleanup:

```bash
celery -A alfred_ai worker -l info
celery -A alfred_ai beat -l info
```

For production fault tolerance, point `CACHE_BACKEND` at a shared cache such as Redis. The default local-memory cache keeps circuit-breaker state per process only.

## Recommended Local Verification

```bash
python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py test
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Data Collection And Processing](docs/DATA_COLLECTION_AND_PROCESSING.md)
- [Project Status](docs/PROJECT_STATUS.md)
- [Future Scope](docs/FUTURE_SCOPE.md)

## What Still Needs Work

- broader official-source coverage across more vehicle models and life-intelligence domains
- OCR/parser correction feedback loops for unknown document layouts
- stronger cross-module proof enforcement for user-entered data
- broader job-source coverage beyond the currently configured opening feed and generic job-page parser
- larger automated test coverage
- richer risk/career modeling than the current lightweight signal blending

## Operational Hardening

- repeated failures from the same external source now trip a cache-backed circuit breaker before more fetch attempts are made
- stale verified records are reused as a fault-tolerant fallback instead of hard-failing dashboards when a source is temporarily down
- verified evidence refresh and stale cleanup are now scheduled through Celery beat
- roadmap and completion tracking moved out of the main dashboard into the superuser-only `/project-details/`
- the `/project-details/` screen now renders live operational counts for evidence watchlists, developer escalations, closure reviews, and ALFRED auto-resolutions
- support and system tickets are timestamped through the internal server clock before they are stored or triaged

## Loan Lifecycle Highlights

- loan payments from imported statements are matched to the most likely active loan with confidence and review flags
- multiple active loans can be consolidated into a new loan while the source loans are marked prepaid and linked to the consolidated record
- a loan can now be closed only after uploading a foreclosure / no-due document that matches the selected loan
- loan PDFs now expose detected document type and parse confidence, including sanction-letter, repayment-schedule, loan-statement, and loan-book paths
- rejected foreclosure documents can generate a superuser ticket with summarized context for follow-up

## Support Tickets

- manual user ticket creation is no longer part of the normal user flow
- low and medium severity issues are auto-handled by ALFRED with a recorded resolution summary
- high-severity issues are escalated to superuser developers
- Alfred can also auto-create tickets for lower-confidence loan-payment matches or rejected closure documents
- generated reports and ticket-routing state now live in superuser-only project-details and reports surfaces instead of the normal user dashboard flow

## Recent Direction

Recent work focused on:

- separating mobility from vehicle-service maintenance
- future-proofing toward multiple vehicles instead of a single-bike assumption
- centralizing uploads into a separate document hub instead of scattering them across every dashboard
- retaining parser metadata for non-perfect statement imports instead of discarding partial document understanding
- adding an assets-versus-liabilities layer that can treat vehicles differently based on usage and utility
- moving reporting and issue-routing visibility into superuser-only operational surfaces
- adding service-history intelligence and part-impact guidance to the vehicle dashboard
- removing duplicated mobility/bike-service data from the wrong screens
- adding verified external evidence to travel, career, and risk outputs
- adding circuit breakers, stale fallback, and scheduled refresh around verified external intelligence
- adding document-backed foreclosure, consolidation, and statement-linked loan matching
- adding a severity-aware support workflow, internal-clock timestamps, and restricting project-details visibility to superusers
- adding resume upload, job-link matching, live layoff news, and opening suggestions to career
- tightening duplicate-statement verification for repeated uploads on the same bank account
- tightening document relevance checks before data is accepted

## License

Proprietary.

## Completion Table

| Area | Status | What Is Done | Next Focus |
| --- | --- | --- | --- |
| Finance Core | Active | Expenses, budgets, loans, investments, reports, stronger statement dedupe, multi-statement intake, asset/liability view, loan consolidation, foreclosure workflow | Add broader automated tests and richer proof coverage |
| Career | Expanded | Resume parsing, job-link fit, market context, layoff news, suggested openings | Add more job sources and salary benchmarks |
| Risk Radar | Consolidated | Career, finance, health, relocation, and mobility risks with related news and evidence | Add broader category-specific news and stronger proof coverage |
| Document Center | Active | Centralized uploads for statements, loan docs, vehicle docs, service files, and resumes with parser confidence | Add visual review and correction workflow |
| Vehicle Service | Operational | Multi-vehicle support, document parsing, service-log import, part-impact intelligence, compliance tracking | Add parser correction feedback loop and broader official catalog coverage |
| Travel Planner | Adaptive | Weather, destination resolution, offbeat suggestions, vehicle-readiness context | Add richer route, stay, and cost evidence |
| External Intelligence | Hardened | Verified evidence cache, stale cleanup rules, proof metadata, circuit breakers, scheduled refresh | Broaden source coverage and replace weaker market dependencies |
| Project Details | Dynamic | Superuser-only in-progress dashboard, live operational metrics, learning progress, report rollups, risk, and guardrails outside the main UI | Move from manual progress proxies to a formal release registry |
| Support Workflow | Automated | System-created tickets with severity routing, ALFRED auto-handling, and developer escalation | Add richer ticket playbooks and correction-feedback loops |
