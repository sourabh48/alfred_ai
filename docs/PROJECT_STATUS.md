# Project Status

## Completed So Far

### Dashboards and UI

- finance dashboards wired across major sections
- dedicated sign-up and sign-in entry points are now available for users
- expense financial-flow charts now switch between monthly, quarterly, and yearly aggregation
- centralized `/documents/` upload hub for statements, loan PDFs, vehicle files, service bills, resumes, and credit reports
- centralized `/documents/` upload hub now also includes diagnostics, low-confidence review queues, all-scope retry controls, and linked delete behavior for document-derived data
- multi-file upload handling across the document hub, expenses, loans, career, credit-report, and vehicle-service pages
- dedicated vehicle-service dashboard
- mobility dashboard for travel plans, logs, gallery, and heat map
- rebuilt/fixed behavioral page empty-state and duplicate-insight handling
- roadmap and completion tracking moved into a separate superuser-only project-details dashboard instead of the main dashboard
- project-details is now a live superuser operations console with internal-clock timestamps, evidence watchlists, ticket-routing counts, report-library rollups, and adaptive learning progress
- project-details learning progress now refreshes live through a dedicated JSON endpoint instead of only on full page loads
- project-details in-progress progress bars now bind to named learning tracks instead of sorted positions, preventing progress drift as module maturity changes
- live-refresh pages now use interaction guards and selective DOM updates so active forms and dropdowns are not torn down every second
- browser interaction coverage now has a dedicated Selenium runner, a CI browser workflow, `browser_regression_summary.json` proof records, and failure artifacts for screenshots, page HTML, metadata, and browser logs where supported
- heavy finance, mobility, bike-service, and career dashboard reads now use cache-aware materialized payloads keyed to data revisions
- investment summary, allocation, and growth reads now also use cache-aware materialized payloads keyed to portfolio revision
- the shared `tests/` package is now discoverable by default so the normal `manage.py test` command runs the suite instead of silently skipping it
- supported ML models now persist training state, run history, quality estimates, and freshness windows in the database
- supported ML models can now auto-train on startup and on the scheduled nightly cycle when data thresholds and dependencies are healthy

### Vehicle and Mobility

- upload-first vehicle documents
- service-log import from service bills and work notes
- manual service logging fallback
- imported and manual service logs are now summarized together so long-term vehicle history stays usable
- issue/fault reporting with probable cause, suggestion, and projected cost
- condition snapshots with score and condition assessment
- parts-and-performance impact guidance based on service history, condition state, and open issues
- structured service-log and vehicle-document payloads now use centralized merge helpers so partial updates do not drop nested parsed data
- multiple saved vehicle profiles with primary-vehicle behavior
- travel advisor with weather, offbeat suggestions, stay-budget guidance, and vehicle-readiness context
- the vehicle catalog now includes broader official manufacturer coverage and model guidance across Royal Enfield, Suzuki, Honda, TVS, Bajaj, Yamaha, Ather, Tata, Mahindra, Kia, and NEXA-backed entries
- the service dashboard now attaches model-specific maintenance highlights with proof links where the catalog has official references
- the official vehicle catalog now filters model choices by selected vehicle type before the user picks a catalog entry

### Data Verification

- document relevance checks against selected vehicle profiles
- source-aware evidence cache for external data
- freshness tracking and stale cleanup rules for external intelligence
- circuit-breaker-backed stale fallback when verified sources repeatedly fail
- scheduled background refresh for verified external evidence
- foreclosure documents are now checked against the selected loan before a close action is allowed
- chart paths were audited to keep live API-backed data or empty states instead of user-facing demo/report widgets
- document parsers now share a layered extraction engine for PDF text, layout, table flattening, repaired-PDF fallback, and OCR retries
- parser-learning memory now adapts statement, loan-document, loan-closure-document, investment-document, recruiter/JD-document, credit-report, vehicle-document, and resume confidence from repeated uploads, accepted corrections, and retry outcomes
- operational diagnostics now persist document-processing failures, metadata-only saves, retry outcomes, and client-side visualization issues with timestamps and payload context
- recommendation and tax advisory outputs now expose freshness-backed evidence blocks and explicit grounding notes instead of opaque summaries
- investment guidance now exposes verified market and macro proof, freshness metadata, and materialized portfolio payloads
- relationship alignment now exposes factors, grounding notes, and freshness-backed proof instead of a fixed placeholder score

### Risk and Career

- career projection now uses macro context instead of a fixed placeholder growth rate
- career now shows dated risk-taking windows for job switches, promotion asks, skill upgrades, and side-income moves
- risk outlook now blends user-entered risk snapshots with macro context, market signals, financial pressure, behavioral pressure, and vehicle readiness
- related risk news is now consolidated under Risk Radar instead of being split across multiple module views
- resume uploads are parsed into role/skills/experience signals across broader formats including html, rtf, odt, and image-based CV uploads
- resume parser learning memory is now stored per user so parser adaptation does not leak across users
- pasted job links are analyzed for fit score, missing skills, and market risk
- recruiter mail and JD intake can now be parsed into the same career-fit pipeline, including optional attachment extraction
- study recommendations are now generated from experience stage, latest skill gaps, and live opening signals
- compensation benchmark summaries are now derived when salary-bearing evidence exists in job pages or recruiter/JD intake
- public job parsing now has deeper adapters for JSON-LD pages plus Greenhouse and Lever style openings
- layoff news and suggested openings are pulled from live configured internet sources with evidence
- scanned/image CV uploads now fall into review state instead of breaking the upload flow when OCR is unavailable on the server
- credit score surfaces now distinguish internal estimates from official bureau pulls instead of saving fake bureau pulls as real scores
- relationship alignment is now grounded in partner inputs, user cash-flow pressure, verified planning context, and a bounded optional relationship-model blend

### Expense Import Integrity

- statement intake now supports bank, credit-card, loan, investment, and other statement kinds
- parser status, confidence, and extracted payload are retained even when transaction extraction is incomplete
- account-scoped transaction fingerprints now reduce duplicate statement imports
- same-account repeated uploads are skipped more reliably
- similar transactions on different bank accounts are preserved instead of being deduped incorrectly
- mixed-overlap statement imports now keep new rows even when duplicate rows share the same reference and amount
- malformed or truncated statement PDFs now degrade to a stored review item instead of crashing the import flow
- structurally broken statement PDFs that still contain page objects can now be rebuilt to salvage metadata before they fall back to review
- structurally broken statement PDFs can now also fall through an isolated OCR worker to recover holder/account/period metadata even when the in-process OCR runtime is unhealthy
- metadata-only statement uploads now remain visible in the expenses workspace and central document hub with parser notes and recovered header details
- low-confidence statement uploads now queue deeper background retries instead of staying permanently dead-ended after the first pass
- repaired broken bank PDFs can now import partial OCR-preview transactions immediately, keep page-progress metadata on the upload, and continue deeper retries in the background for the remaining pages
- accepted corrections on partial or metadata-only statements now force a deeper retry window so OCR-recoverable uploads can populate expenses after review instead of only saving header fixes
- imported loan-like statement entries are now matched against the active loan book with confidence and review flags
- assets and liabilities are now surfaced in the expense intelligence view, including vehicle classification based on usage and utility

### Loans And Support Workflow

- active loans can now be consolidated into a new loan record while source loans are marked prepaid
- loan foreclosure now requires an uploaded closure or no-due document
- loan PDF imports now expose detected document type and parse confidence for sanction letters, statements, and repayment schedules
- uploaded loan PDFs are now saved as first-class import records, even when the parse is weak and only a review item can be created
- manual user ticket creation is no longer part of the normal user flow
- Alfred can auto-create summarized tickets when loan matching is low-confidence or a closure document is rejected
- low and medium severity tickets are now auto-handled by ALFRED, while high severity is escalated to superuser developers
- reports and ticket-routing visibility are now superuser-only
- the central document hub now exposes retry controls for statement, loan, vehicle, resume, and credit-report items instead of statement-only retry
- the central document hub now also supports review, correction, retry, and parser-learning feedback for loan-closure, investment-import, and recruiter/JD intake documents
- accepted corrections for invoice-style vehicle documents now update linked service-record fields such as service date, workshop, odometer, cost, and work summary instead of stopping at the document shell
- the document hub and expense intake now keep recent upload stacks scrollable and capped to the latest 10 visible cards per panel so the page height stays stable as history grows
- unresolved retries now create internal retry tickets keyed to the retry count, so ALFRED can auto-handle lower-severity parsing failures and escalate exhausted cases to developers
- parser-confidence calibration is now a trainable ML path that learns from parser outcome history instead of relying only on static confidence heuristics
- relationship-model training is now a safe, bounded path that only activates when enough scored partner profiles exist

## Pending / Incomplete

- broad official catalog coverage for more bikes, scooters, and cars
- visual OCR overlays and richer field-level review inputs for unknown or messy document formats
- deeper verification for more user-entered data outside mobility
- stronger test coverage
- broader live-browser verification across more pages after the Selenium runner keeps recording required-browser Chrome or Edge runs with zero skipped browser tests in local and CI jobs
- official bureau integrations with consent flow if real CIBIL/Experian/Equifax/CRIF pulls are required
- broader live job-source coverage beyond the current Remotive feed and current public-page adapters
- richer market/career/risk modeling than the current lightweight signal blending
- broader endpoint and browser-interaction coverage beyond the new mobility and project-details regression tests
- broader document-center browser interaction coverage beyond the new retry and diagnostics regression tests
- broader upload-history coverage in the central document hub beyond the newly added saved loan-import trail
- broader trainable-model coverage beyond the currently supported structured salary, expense, burnout, behavioral-risk, and parser-confidence paths
- visual OCR review is still pending, but the parser learning loop now adapts from both repeated upload outcomes and accepted document-center corrections

## Risks Remaining

- browser-only issues can still exist where no driver-backed Selenium pass was recorded; normal test runs still skip browser tests unless `ALFRED_RUN_BROWSER_TESTS=true`, and full UI maturity still needs repeated no-skip browser summaries from local or CI jobs
- selective fragment refresh now prevents most interaction resets, but any remaining page that still swaps whole DOM blocks in-browser could regress until it gets the same treatment
- some external sources are authoritative APIs, but market data still relies on Yahoo Finance
- multiple-vehicle support is structurally improved, but some naming remains bike-centric in code paths for backward compatibility
- job-link parsing is robust for many public pages, but some portals can still block direct fetches or hide content behind script/runtime layers
- project-details is now dynamic from live operational data, but it is still not generated from a formal release registry
- balance-sheet vehicle classification is heuristic and should still be reviewed against real ownership/use patterns where the financial treatment matters
- auto-training is now safe and stateful, but several modules still remain heuristic, placeholder, or data-poor and should not be treated as fully learned systems yet
- parser adaptation is materially stronger now, but "all document types without fail" is still not a truthful guarantee for arbitrary or severely degraded files
