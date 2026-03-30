# Project Status

## Completed So Far

### Dashboards and UI

- finance dashboards wired across major sections
- centralized `/documents/` upload hub for statements, loan PDFs, vehicle files, service bills, and resumes
- dedicated vehicle-service dashboard
- mobility dashboard for travel plans, logs, gallery, and heat map
- rebuilt/fixed behavioral page empty-state and duplicate-insight handling
- roadmap and completion tracking moved into a separate superuser-only project-details dashboard instead of the main dashboard
- project-details is now a live superuser operations console with internal-clock timestamps, evidence watchlists, ticket-routing counts, report-library rollups, and adaptive learning progress

### Vehicle and Mobility

- upload-first vehicle documents
- service-log import from service bills and work notes
- manual service logging fallback
- imported and manual service logs are now summarized together so long-term vehicle history stays usable
- issue/fault reporting with probable cause, suggestion, and projected cost
- condition snapshots with score and AI assessment
- parts-and-performance impact guidance based on service history, condition state, and open issues
- multiple saved vehicle profiles with primary-vehicle behavior
- travel advisor with weather, offbeat suggestions, stay-budget guidance, and vehicle-readiness context

### Data Verification

- document relevance checks against selected vehicle profiles
- source-aware evidence cache for external data
- freshness tracking and stale cleanup rules for external intelligence
- circuit-breaker-backed stale fallback when verified sources repeatedly fail
- scheduled background refresh for verified external evidence
- foreclosure documents are now checked against the selected loan before a close action is allowed
- chart paths were audited to keep live API-backed data or empty states instead of user-facing demo/report widgets

### Risk and Career

- career projection now uses macro context instead of a fixed placeholder growth rate
- career now shows dated risk-taking windows for job switches, promotion asks, skill upgrades, and side-income moves
- risk outlook now blends user-entered risk snapshots with macro context, market signals, financial pressure, behavioral pressure, and vehicle readiness
- related risk news is now consolidated under Risk Radar instead of being split across multiple module views
- resume uploads are parsed into role/skills/experience signals across broader formats including html, rtf, odt, and image-based CV uploads
- resume parser learning memory is now stored per user so parser adaptation does not leak across users
- pasted job links are analyzed for fit score, missing skills, and market risk
- study recommendations are now generated from experience stage, latest skill gaps, and live opening signals
- layoff news and suggested openings are pulled from live configured internet sources with evidence
- scanned/image CV uploads now fall into review state instead of breaking the upload flow when OCR is unavailable on the server
- credit score surfaces now distinguish internal estimates from official bureau pulls instead of saving fake bureau pulls as real scores

### Expense Import Integrity

- statement intake now supports bank, credit-card, loan, investment, and other statement kinds
- parser status, confidence, and extracted payload are retained even when transaction extraction is incomplete
- account-scoped transaction fingerprints now reduce duplicate statement imports
- same-account repeated uploads are skipped more reliably
- similar transactions on different bank accounts are preserved instead of being deduped incorrectly
- imported loan-like statement entries are now matched against the active loan book with confidence and review flags
- assets and liabilities are now surfaced in the expense intelligence view, including vehicle classification based on usage and utility

### Loans And Support Workflow

- active loans can now be consolidated into a new loan record while source loans are marked prepaid
- loan foreclosure now requires an uploaded closure or no-due document
- loan PDF imports now expose detected document type and parse confidence for sanction letters, statements, and repayment schedules
- manual user ticket creation is no longer part of the normal user flow
- Alfred can auto-create summarized tickets when loan matching is low-confidence or a closure document is rejected
- low and medium severity tickets are now auto-handled by ALFRED, while high severity is escalated to superuser developers
- reports and ticket-routing visibility are now superuser-only

## Pending / Incomplete

- broad official catalog coverage for more bikes, scooters, and cars
- parser feedback workflow for unknown or messy document formats
- deeper verification for more user-entered data outside mobility
- stronger test coverage
- visual OCR/document review overlays
- official bureau integrations with consent flow if real CIBIL/Experian/Equifax/CRIF pulls are required
- salary benchmarks, recruiter-email parsing, and broader job-source coverage
- richer market/career/risk modeling than the current lightweight signal blending

## Risks Remaining

- browser-only issues can still exist where no live frontend interaction pass was run
- some external sources are authoritative APIs, but market data still relies on Yahoo Finance
- multiple-vehicle support is structurally improved, but some naming remains bike-centric in code paths for backward compatibility
- job-link parsing is robust for many public pages, but some portals can still block direct fetches or hide content behind script/runtime layers
- project-details is now dynamic from live operational data, but it is still not generated from a formal release registry
- balance-sheet vehicle classification is heuristic and should still be reviewed against real ownership/use patterns where the financial treatment matters
