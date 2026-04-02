# ALFRED

ALFRED is a Django application for personal finance, documents, loans, credit, career, mobility, and cross-module decision support. It is built as one shared workspace instead of separate disconnected dashboards.

## At A Glance

| Area | What exists now |
| --- | --- |
| Finance core | Expenses, budgets, loans, investments, reports, tax, credit, recommendations, family, career, behavioral, relationship, and risk modules |
| Documents | Central document hub for statements, loan PDFs, service bills, resumes, and uploaded bureau reports |
| Loan intelligence | Statement-linked repayment detection, consolidation tracking, foreclosure parsing, reconciliation, and settlement allocation |
| Shared shell | Responsive navbar/sidebar shell, upgraded auth pages, branded 404/500 pages, loading bars, and richer motion across cards/panels |
| External proof | Source-aware verified intelligence cache with freshness, stale cleanup, and circuit-breaker-backed fallbacks |
| Ops | Superuser-only project-details view, ML runtime approval flow, scheduled retries, and internal support routing |

## Product Experience

- upgraded sign-in and sign-up pages with a finance-themed animated background
- one shared navbar across the application, including auth and error pages
- isolated workspace scrolling so the dashboard content scrolls without dragging the shell with it
- page-level and global loading progress bars for data-heavy screens
- filtered expense timeline with direct lookup by Alfred transaction ID, merchant, reference, or fingerprint
- balance-sheet and expense summary cards now refresh by updating text in place instead of rebuilding the whole card grid on every poll
- config-backed UI copy so branding and shared wording can be changed without editing templates

## Quick Start

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Optional local setup:

```bash
copy config\alfred_ui.example.json config\alfred_ui.json
python manage.py createsuperuser
```

For scheduled retries, verified-intelligence refresh, and cleanup:

```bash
celery -A alfred_ai worker -l info
celery -A alfred_ai beat -l info
```

## Configuration Notes

- `config/alfred_ui.json` is the local override file and is intentionally gitignored
- `config/alfred_ui.example.json` is the tracked team-safe reference
- if both config files are missing or invalid, ALFRED falls back to built-in defaults from `alfred_ai/services/ui_config.py`
- the tracked example file should stay generic so new developers can copy it and start quickly

## scikit-learn Runtime

- ALFRED prefers `scikit-learn` for classic tabular training when the local machine allows it
- startup now asks a superuser for first-run training approval once, then continues automatically on later healthy startups
- if Windows Application Control or endpoint security blocks sklearn native files, ALFRED explains the issue in-app instead of crashing at startup
- lighter in-repo fallback models remain available so the application still runs when sklearn is blocked

## Current Status

- Backend: active and materially expanded beyond the original finance-only scope
- UI: dashboard coverage exists across the major modules, including mobility and bike/vehicle service
- shared shell: navbar-backed auth and error pages now use the same responsive layout as the main app
- Data verification: partially implemented
- uploaded vehicle documents are parsed and relevance-checked against the selected vehicle profile
- career now parses uploaded resumes, analyzes pasted job links, and attaches source-backed market/news evidence
- career now generates study recommendations from experience stage, resume skill coverage, latest job gaps, and live opening signals
- resume parser learning memory is stored per user so adaptation stays user-scoped instead of mixing patterns across accounts
- bank-statement imports now use stronger account-scoped transaction fingerprints to reduce duplicate imports
- statement uploads now retain parser status, confidence, and extracted metadata even when transaction extraction is partial
- travel, career, and risk now expose cached external evidence with source URLs and freshness metadata
- credit output now distinguishes internal estimates from official bureau pulls and no longer stores fake bureau pulls as if they were real
- uploaded bureau reports can now create official credit-score snapshots without requiring a live bureau API
- document upload surfaces now support multi-file selection for statements, loan PDFs, vehicle documents, service bills, resumes, and uploaded credit reports
- uploaded loan PDFs are now persisted as reviewable import records instead of disappearing after parse/update, and the saved history is visible in both the loan workspace and the document hub
- document parsers now share a layered extraction engine that retries PDF text, layout, table flattening, repaired-PDF fallback, and OCR before giving up
- parser-learning memory now records repeated document shapes per user so confidence and review behavior can adapt over time instead of restarting from zero on every upload
- low-confidence documents now surface through a central review queue where accepted corrections are fed back into parser learning memory
- all document types in the review queue can now be retried from the same document-center workflow instead of only statements
- parser learning now also incorporates accepted correction fields and retry outcomes across statements, loan documents, loan-closure documents, investment documents, resumes, recruiter/JD intake, vehicle documents, and credit reports
- repeated unresolved retries now create internal retry tickets keyed to the retry count, so low and medium parsing failures can be auto-handled while exhausted cases escalate to developers
- the document center now keeps a diagnostics log for metadata-only imports, parser review states, retry outcomes, and client-side visualization issues
- statement uploads now queue deeper background retries and can recover header metadata from structurally broken PDFs through an isolated OCR worker
- structurally broken image-style bank PDFs can now import partial OCR preview transactions immediately, mark the upload as an in-progress partial parse, and keep page-progress metadata visible while deeper retries continue
- accepted corrections on low-confidence statements now force a deeper retry window so previously metadata-only uploads can repopulate expenses automatically when OCR text is already recoverable
- recent document and statement panels now keep the latest 10 items in scrollable stacks instead of stretching the whole page vertically
- expense timeline now defaults to filtered, capped results with search by merchant/reference/fingerprint and direct lookup by Alfred transaction ID
- expense timeline now exposes a compact filtered-total summary card so users can see matching spend without scanning the full table
- source-document deletion now removes directly linked derived data where ALFRED can prove the linkage, including statement-derived expenses and imported vehicle service logs
- dashboard charts and visual panels now auto-refresh every second on the active page without a full window reload, while refresh guards pause updates during active form and dropdown interaction
- the expense `Financial Flow` chart can now switch between monthly, quarterly, and yearly aggregation without leaving the page
- the expense timeline now surfaces a monthly expense window with current-vs-previous outflow, a recent six-month window, and a flagged unwanted-spend lane for emotional or discretionary outflows
- support tickets and project-detail metrics now carry server-side internal-clock timestamps
- the balance-sheet view now separates assets and liabilities, including vehicle treatment based on usage and utility
- the balance-sheet cards now update in-place during live refresh so core totals do not blink on every poll
- the vehicle-service dashboard now explains how serviced parts affect performance, reliability, mileage, and safety
- the vehicle-service dashboard now tracks refill history and compares actual mileage against the saved model benchmark with proof links
- uploaded vehicle service invoices now extract job-card metadata, customer/service-center details, itemized parts and labour lines, section totals, and final customer-payable amount
- invoice parsing now also derives advisor/contact clues, tax rollups, affected systems, item counts, operation lists, and replaced-part summaries when the document exposes them
- mobility document and service-log payloads now use centralized merge helpers so nested parsed data is not dropped during partial updates
- the superuser project-details learning progress now refreshes through a dedicated JSON endpoint and client polling instead of requiring a full page reload
- project-details in-progress progress bars now derive from named learning tracks instead of sorted list positions, so progress does not drift when the learning-track order changes
- regression tests now cover mobility endpoint contracts, service-log payload preservation, and live project-details learning progress updates
- the top-level `tests/` package is now discoverable by default, so `python manage.py test` no longer reports a false empty suite
- supported ML models now persist training state, quality/confidence estimates, artifact freshness windows, and run history in the database
- supported ML models now self-train safely on startup and scheduled refresh, but only when data thresholds and runtime dependencies are healthy
- startup ML approval now asks a superuser once, then continues automatically on later startups when runtime health is good
- ALFRED now prefers scikit-learn for classic tabular training when the local machine allows it, while keeping lighter in-repo fallbacks when Windows blocks sklearn DLLs
- heavier finance, mobility, bike-service, and career aggregations now return cache-aware materialized payloads keyed by data revision instead of recomputing the full graph on every request
- parser-confidence calibration is now a trainable ML path that learns from parser outcomes instead of hard-coding confidence as static heuristics
- recommendation and tax advisory outputs now expose proof, freshness metadata, and explicit grounding notes instead of only returning opaque summaries
- career now supports recruiter-mail and JD intake, deeper public job-page adapters, and compensation benchmark summaries when salary-bearing evidence exists
- investment advisory output now exposes verified market/macro proof, freshness metadata, and cache-aware materialized portfolio reads
- relationship alignment is no longer a fixed placeholder; it now blends partner inputs, household cash-flow signals, verified planning context, and an optional bounded model blend
- broader cross-module proof enforcement is still in progress

## Key Modules

- `apps/expenses`: transaction ingestion, account aggregation, forecasting hooks
- `apps/budgets`: budgeting dashboard and intelligence
- `apps/loans`: loan CRUD, PDF parsing, and payoff tracking
- `apps/investments`: portfolio analysis with verified market grounding and materialized heavy reads
- `apps/relationship`: relationship alignment, partner profiles, and grounded household-planning guidance
- `apps/integrations`: credit score, tax/recommendation support, verified external intelligence cache
- `apps/mobility`: vehicle profiles, service intelligence, travel planning, trip media, and travel advisor
- `apps/career`, `apps/risk`, `apps/behavioral`, `apps/family`: personal-life dashboards and APIs

## Mobility Highlights

- multiple vehicle profiles with primary-vehicle selection
- upload-first insurance / PUC / RC / invoice handling
- automatic service-log creation from service bills or work notes
- service-invoice parsing now stores structured job-card, parts, labour, and payable-total data instead of only a flat summary string
- fuel-refill logging with trip-value entry after each refill for actual-vs-optimal mileage comparison
- condition snapshots, fault reports, projected service cost, and workshop-ready wording
- travel advice with destination resolution, weather, offbeat suggestions, stay-budget guidance, and vehicle-readiness context
- vehicle-document and service-bill parsing now use the shared extraction engine and adaptive parser memory
- the vehicle catalog now covers more official bikes, scooters, and cars, and the primary vehicle panel now attaches maintenance guidance with official proof links where available
- the official vehicle catalog now filters by selected vehicle type before the user chooses a model
- official coverage now includes additional manufacturer-backed references and model guidance across Bajaj, Yamaha, Ather, Mahindra, Kia, KTM, Toyota, and MG entries, alongside the earlier Royal Enfield, Suzuki, Honda, TVS, Tata, and NEXA-backed catalog data
- high-volume models such as Hunter 350, SP125, and Activa 6G now carry more model-specific maintenance checks instead of only class-level defaults

## Career Highlights

- resume upload and parsing for `pdf`, `docx`, and `txt`
- broader resume intake for `pdf`, `doc`, `docx`, `txt`, `md`, `rtf`, `html`, `odt`, and image-based CV files
- extracted skill, experience, and strength/weakness summaries
- pasted job-link parsing from structured/generic career pages
- recruiter-mail and JD intake with optional attachment extraction through the shared document extraction layer
- broader public job adapters for JSON-LD job pages plus Greenhouse, Lever, Workday, and Ashby style openings
- job-fit scoring against the latest resume or profile
- study recommendations based on experience stage, latest job gaps, and current opening tags
- compensation benchmark summaries when salary-bearing evidence is present in parsed openings or recruiter/JD intake
- dated career-risk timing windows based on runway, fit, and market pressure
- live layoff-news panel and role-level market-risk view
- suggested openings with direct application links from a live job API source
- scanned or image-only CVs now degrade to `needs_review` instead of breaking the upload flow when OCR is not configured on the server

## Credit Highlights

- users can upload bureau reports directly in the credit dashboard instead of depending on a live bureau API
- parsed official report snapshots can populate score, bureau, account summary, factor chart inputs, and trend history
- weak or printed/scanned bureau exports are stored as `needs_review` instead of being silently treated as valid official data
- credit-report parsing now uses the shared extraction engine plus adaptive parser memory instead of a single PDF text path

## Investments And Relationship Highlights

- investment summary, allocation, and growth endpoints now use cache-aware materialized payloads keyed to portfolio revision
- investment guidance now combines user-held positions with verified market and macro context, including proof and freshness metadata
- relationship alignment now uses partner profile data, current household load, savings capacity, and verified planning-pressure context instead of a hardcoded score
- relationship alignment can blend in a trained relationship regressor when enough scored profiles exist, but falls back cleanly to bounded heuristics when no model is ready

## Expense Import Highlights

- multiple bank accounts with account-specific import resolution
- statement imports can be tagged or auto-detected as bank, credit-card, loan, investment, or other statements
- stronger duplicate detection using account-scoped transaction fingerprints
- repeated statement uploads to the same account are skipped more reliably
- matching transactions on different accounts are preserved instead of being incorrectly collapsed
- mixed-overlap statement imports now keep new rows even when duplicate rows share the same statement reference, date, and amount
- partial parses are still stored as statement records so the document trail is not lost
- malformed or truncated statement PDFs are now stored for review with parser notes instead of crashing the import request
- structurally broken statement PDFs that lost their page tree or xref can now be rebuilt to salvage bank/account/period metadata instead of staying completely blank
- metadata-only statement uploads now stay visible in both the expenses workspace and the central document hub with parser notes, institution/account clues, and recovered period details
- failed or low-confidence statements now enter a background retry ladder instead of staying dead-ended after the first pass
- structurally broken HDFC-style PDFs can now recover bank, account, holder, and period metadata through isolated OCR even when the in-process OCR runtime is unavailable
- newly imported loan-classified statement entries are now rechecked against the loan book so Alfred can infer which loan is being paid
- statement imports now participate in the shared parser-learning memory, so repeated uploads from the same bank/document shape can calibrate confidence more realistically

## Document Center Highlights

- `/documents/` gives users one place to upload statements, loan PDFs, vehicle documents, service bills, resumes, and uploaded credit reports
- the main document-oriented upload surfaces now accept multiple files in one action and process them sequentially with per-file success/failure feedback
- parser confidence is surfaced in the document hub instead of being hidden inside individual modules
- recent statements, recent loan documents, recent vehicle documents, recent credit reports, and the latest career files are visible from the same intake surface
- low-confidence uploads now appear in a document review queue with retry state, accepted-correction input, and parser-learning feedback
- every document scope in that review queue can now be retried directly from the hub
- accepted corrections and retry outcomes now push deeper into parser learning for loan-closure and investment documents in addition to the earlier statement, loan, vehicle, resume, and credit-report flows
- accepted corrections now also reach OCR-heavy partial statement imports and invoice-style vehicle documents deeply enough to update linked service records, not just the top-level document metadata
- accepted corrections on invoice-style vehicle documents now also carry line-item structure, impacted systems, and other deeper service-bill payload fields into linked service records
- recruiter-mail and JD intake now also keep parser status/confidence and can enter the same correction/retry learning loop when confidence stays low
- unresolved retries now surface as internal retry tickets with retry-count context instead of silently looping in the background
- the hub now exposes a diagnostics log so metadata-only imports, parse failures, and visualization/API issues are visible with timestamps and context
- deleting a source document from the document hub now removes directly linked downstream data where ALFRED tracks that derivation safely
- document intake is centralized, while the downstream dashboards still own their domain-specific analysis and actions

## Adaptive And Model-backed Reality

- ALFRED is adaptive and evidence-backed today, but it is not fully model-trained end to end across every module
- ML-backed paths currently include behavioral anomaly detection, behavior signatures, personalization, expense confidence scoring, and parser-confidence tracking
- parser learning memory for resumes is now user-scoped so one user's document patterns do not calibrate another user's parser confidence
- parser adaptation is now cross-module for statements, credit reports, vehicle documents, and loan documents, and accepted review corrections now reinforce future confidence for similar document shapes
- parser adaptation is still confidence calibration plus retry orchestration, not a guarantee that every arbitrary format will parse perfectly
- supported structured models now auto-train through a guarded orchestration layer that tracks refresh windows, sample counts, quality estimates, and skip reasons
- bounded mobility service-cost training is now part of that guarded orchestration layer, using stored service records as the target instead of unsupported synthetic labels
- several important dashboards still use evidence-backed heuristic blending rather than reviewed predictive models, especially in career timing, vehicle diagnosis, and consolidated risk
- project-details now shows an explicit learning-progress view so the current maturity of each adaptive path is visible to superusers instead of being implied
- startup auto-training is bounded by cooldowns, data sufficiency checks, and placeholder exclusion, so Alfred does not pretend every module is safely trainable yet

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
- official tax-regime, PPF, and NPS references for tax-planning evidence blocks
- risk and travel advisory payloads now expose the same freshness-summary contract as other grounded modules instead of only raw evidence arrays

## Cache-Aware Materialization

Heavy read paths now use cache-aware materialized payloads so growing history does not force full recomputation on every page refresh.

Current materialized paths include:

- financial intelligence aggregates in `apps/expenses/services/financial_intelligence.py`
- investment summary, allocation, and growth payloads in `apps/investments/views.py`
- mobility dashboard payloads in `apps/mobility/views.py`
- bike-service dashboard intelligence in `apps/mobility/services/bike_service_intelligence.py`
- career dashboard aggregation in `apps/career/views.py`
- relationship alignment payloads in `apps/relationship/views.py`

These payloads expose `_materialized` metadata so superusers and tests can verify whether a response was served fresh or from cache.

## Developer Setup Details

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Optional local UI copy override:

```bash
copy config\alfred_ui.example.json config\alfred_ui.json
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

Setup guidance for config-backed UI text and the ML runtime approval flow is documented above in `Configuration Notes` and `scikit-learn Runtime`.

## Recommended Local Verification

```bash
python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py test
```

## Git And GitHub Push Prep

- `.gitignore` excludes local runtime artifacts, SQLite sidecars, caches, secrets, local UI config, virtual environments, and generated model artifacts
- keep `config/alfred_ui.example.json` tracked, and keep `config/alfred_ui.json` local-only
- before pushing, make sure your local database, media uploads, and environment files are not staged
- if you are setting up a new machine, copy `config/alfred_ui.example.json` to `config/alfred_ui.json` and then adjust the local values as needed

Typical push flow:

```bash
git status
git add .
git commit -m "Prepare Alfred AI for GitHub push"
git push origin master
```

If the local config file is missing:

- ALFRED still starts with built-in defaults from `alfred_ai/services/ui_config.py`
- create `config/alfred_ui.json` from the tracked example file when you want local branding or wording overrides

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Backup And Restore](docs/BACKUP_AND_RESTORE.md)
- [Configuration](docs/CONFIGURATION.md)
- [Data Collection And Processing](docs/DATA_COLLECTION_AND_PROCESSING.md)
- [Project Status](docs/PROJECT_STATUS.md)
- [Future Scope](docs/FUTURE_SCOPE.md)

## Backup And Restore

ALFRED does not yet ship with automated backup orchestration. The minimum recoverable set today is:

- `db.sqlite3`
- `media/`
- `ml_models/`

The documented stop-copy-restore workflow lives in [docs/BACKUP_AND_RESTORE.md](docs/BACKUP_AND_RESTORE.md).

## What Still Needs Work

- broader official-source coverage across more vehicle models and life-intelligence domains
- visual OCR overlays and richer field-level review for more document layouts
- stronger cross-module proof enforcement for user-entered data
- broader job-source coverage beyond the current Remotive-backed feed and the current public-page adapters
- larger automated test coverage
- richer risk/career modeling than the current lightweight signal blending
- richer recruiter attachment persistence and review tooling for parsed mail/JD intake
- broader materialization telemetry and cache invalidation observability as high-history modules grow

## Operational Hardening

- repeated failures from the same external source now trip a cache-backed circuit breaker before more fetch attempts are made
- stale verified records are reused as a fault-tolerant fallback instead of hard-failing dashboards when a source is temporarily down
- verified evidence refresh and stale cleanup are now scheduled through Celery beat
- low-confidence statement retries are now scheduled through Celery beat so broken uploads can keep escalating page coverage in the background
- ML auto-training now debounces startup triggers and skips unsupported or data-poor models instead of blindly running every trainer
- document-processing diagnostics are now persisted as operational logs instead of being visible only as transient UI errors
- client-side visualization/runtime failures can now be logged back to the server for superuser review and debugging
- roadmap and completion tracking moved out of the main dashboard into the superuser-only `/project-details/`
- the `/project-details/` screen now renders live operational counts for evidence watchlists, developer escalations, closure reviews, and ALFRED auto-resolutions
- support and system tickets are timestamped through the internal server clock before they are stored or triaged

## Loan Lifecycle Highlights

- loan payments from imported statements are matched to the most likely active loan with confidence and review flags
- multiple active loans can be consolidated into a new loan while the source loans are marked prepaid and linked to the consolidated record
- a loan can now be closed only after uploading a foreclosure / no-due document that matches the selected loan
- loan PDFs now expose detected document type and parse confidence, including sanction-letter, repayment-schedule, loan-statement, and loan-book paths
- loan PDF uploads are now stored as `LoanImportDocument` records even when Alfred can only save them for review, so the raw document trail is not lost
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
- surfacing a tighter expense-control view with monthly windows and flagged unwanted spend instead of making users infer it from raw timeline rows
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
- shifting credit-score ingestion toward document-backed uploads instead of unimplemented live bureau pulls

## Dormant / Not Evidenced In Routed Flows

The table below is intentionally strict. These models exist in the repo, but active routed product usage is not evidenced clearly enough to call them live features.

| Model | Path | Current repo evidence | Action |
| --- | --- | --- | --- |
| `EmailConnection` | `apps/integrations/models.py` | Storage, admin registration, encryption-at-rest tests, and service code exist, but an active routed end-user email-connection flow is not evidenced in the UI or URLs | Keep feature-flagged or complete the connection/sync flow before treating it as live |

## License

Proprietary.

## Completion Table

| Area | Status | What Is Done | Next Focus |
| --- | --- | --- | --- |
| Finance Core | Active | Expenses, budgets, loans, investments, reports, stronger statement dedupe, multi-statement intake, asset/liability view, monthly expense window, unwanted-spend surfacing, loan consolidation, foreclosure workflow | Add broader automated tests and richer proof coverage |
| UI Surfaces | Refined | Expense timeline now includes a monthly window and unwanted-spend lane, and project-details queues/signals are laid out in scroll-safe operational cards | Extend the same higher-density layout treatment to more dashboards with browser QA |
| Career | Expanded | Resume parsing, recruiter/JD intake, job-link fit, compensation benchmark, market context, layoff news, suggested openings | Add more live job sources and deeper recruiter attachment review |
| Risk Radar | Consolidated | Career, finance, health, relocation, and mobility risks with related news and evidence | Add broader category-specific news and stronger proof coverage |
| Investments / Relationship | Expanded | Verified portfolio grounding, materialized investment reads, grounded relationship alignment, and bounded relationship-model training | Broaden proof sources and deepen reviewed labels |
| Document Center | Active | Centralized uploads, multi-file intake, credit-report upload, review queue, all-scope retry, diagnostics logging, accepted corrections, retry-fed parser learning, and linked delete behavior for document-derived data | Add visual OCR overlays and broader document-source coverage |
| Vehicle Service | Operational | Multi-vehicle support, document parsing, service-log import, part-impact intelligence, compliance tracking, and maintenance guidance with proof links | Add broader official model coverage and richer model-specific schedules |
| Travel Planner | Adaptive | Weather, destination resolution, offbeat suggestions, vehicle-readiness context | Add richer route, stay, and cost evidence |
| External Intelligence | Hardened | Verified evidence cache, stale cleanup rules, proof metadata, circuit breakers, scheduled refresh, and freshness-backed tax/recommendation grounding | Broaden source coverage and replace weaker market dependencies |
| Dashboard Materialization | Active | Cache-aware materialized payloads for finance, mobility, bike-service, and career heavy reads | Expand cache telemetry and revision contracts to more modules |
| ML Training Ops | Active | Persisted training state, safe startup/scheduled auto-training, run history, model freshness, guarded sklearn-backed trainers, and parser-confidence calibration | Extend safe training coverage and improve model quality with richer datasets |
| Project Details | Dynamic | Superuser-only in-progress dashboard, live operational metrics, live-refresh learning progress, report rollups, risk, and guardrails outside the main UI | Move from manual progress proxies to a formal release registry |
| Support Workflow | Automated | System-created tickets with severity routing, ALFRED auto-handling, and developer escalation | Add richer ticket playbooks and correction-feedback loops |
