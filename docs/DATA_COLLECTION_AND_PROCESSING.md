# Data Collection And Processing

## Purpose

This document explains how ALFRED collects, validates, stores, and uses data across the application, with emphasis on proof-backed processing, server-side timestamps, and career-risk timing.

## Data Sources

### User-Provided Data

- profile fields such as role, skills, salary, income, rent, and city
- uploaded files such as resumes, bank statements, vehicle documents, service bills, and foreclosure or no-due documents
- manual records such as expenses, loans, behavioral signals, family or dependent records, service logs, and risk snapshots
- pasted links such as job postings
- support-ticket summaries from the reports page

### Internet-Backed Data

- macro indicators via World Bank
- market snapshots via Yahoo Finance
- news via Google News RSS
- job openings via Remotive
- travel geocoding and place discovery via OpenStreetMap Nominatim
- travel weather via Open-Meteo

These are stored through `VerifiedExternalInsight` records so ALFRED can keep source URLs, freshness windows, timestamps, and summaries.

## Collection Flow

### Manual Forms

1. User submits a form from a dashboard.
2. Django API validates field shape and required values.
3. The record is stamped with the server-side internal clock before or during storage.
4. The record is stored under the authenticated user.
5. Downstream dashboards re-read the latest stored data and recalculate summaries.

### File Uploads

1. User uploads a file.
2. The file is parsed into extracted text and structured payload.
3. Parser status and confidence are stored with the original file.
4. Relevance checks run where applicable.
5. Accepted data is saved; weak or unrelated data is either marked for review or rejected.

Central upload note:

- `/documents/` acts as a unified intake surface for statements, loan PDFs, vehicle documents, service bills, and resumes
- the same file can still be consumed by its domain dashboard later, but intake metadata is retained centrally
- statement uploads now keep metadata even when no clean transaction table can be extracted, so partial understanding is not discarded
- career uploads now accept broader resume formats including html, rtf, odt, and image-style CV files; scanned/image CVs remain review-bound until OCR is available on the server
- resume parser learning memory is stored per user, so parser calibration does not borrow patterns from other users' uploads

Loan-specific note:

- foreclosure or no-due documents must match the selected loan before the loan can be closed
- rejected closure documents can raise a summarized support ticket for superuser review
- support tickets are severity-triaged at creation time so low and medium issues can be auto-handled while high severity is escalated to developers
- manual user ticket creation is no longer the default UX; issue routing is now primarily system-driven

### External Intelligence

1. ALFRED requests data from an allowlisted source.
2. The payload is normalized into a smaller internal structure.
3. A checksum, summary, freshness window, and timestamps are stored.
4. Fresh records are reused until stale.
5. Repeated upstream failures can trip a circuit breaker so the app stops hammering the same source temporarily.
6. Failed or deactivated stale records are cleaned up after retention windows.

## Processing Stages

### Normalize

- skill lists are normalized for comparison
- transaction references are normalized before fingerprinting
- vehicle identifiers are normalized before matching
- external payloads are reduced to the fields actually used in dashboards

### Verify

- resume uploads carry parser status and confidence
- job links must parse into enough structure for scoring
- vehicle documents are checked against the selected vehicle profile
- foreclosure documents are checked against lender text, closure keywords, and loan account references
- statement uploads keep document kind, parser status, confidence, and extracted hints so users and developers can see what ALFRED actually understood
- loan PDFs now expose detected document type such as sanction letter, repayment schedule, loan statement, or loan book
- repeated bank-statement uploads are filtered using account-scoped transaction fingerprints
- cached external signals keep source URL and verification metadata
- external-source cache records stay separate from user-owned records; user dashboards join them only at response-build time

### Score And Enrich

- finance dashboards compute cash flow, debt pressure, savings, recurring commitments, and lifestyle concentration
- finance dashboards now also compute an assets-versus-liabilities layer using active balances, investments, loans, and vehicle usage context
- behavioral dashboards compute stress and pattern signals
- career dashboards compute job fit, market risk, projections, and timing guidance
- career dashboards now also compute study recommendations from experience stage, latest job gaps, and live opening signals
- risk dashboards blend manual risk with finance, behavior, mobility, and external market context
- mobility dashboards compute compliance, service cost, trip cost, maintenance recommendations, and part-impact guidance from service history plus issue history
- support tickets are classified into severity, handler, and resolution route
- credit dashboards distinguish internal estimates from official bureau pulls instead of treating internal heuristics as real CIBIL or bureau records

### Store For Reuse

- raw user records remain in module tables
- parsed or extracted payloads remain attached to their source records
- verified external records are cached separately
- support tickets store summarized issue context, internal-clock metadata, and triage routing context
- dashboards read the stored data rather than trusting transient request state

## Career Timing Logic

Career timing is not a generic "take risk now" flag. It is a blended readiness estimate that currently uses:

- current role and experience
- listed or manual skills
- latest parsed resume, if available
- latest job-fit analysis, if available
- current macro and job-market risk
- liquid cash across active non-credit accounts
- active loan EMI and rent or fixed monthly load

The result is a timing payload with:

- readiness score
- readiness level
- exact window start and end dates
- next review date
- recommended move types such as job switch, promotion ask, upskilling, or side-income bet
- blockers that should be resolved before a larger career risk

## What The System Does Not Do Yet

- unrestricted autonomous crawling
- self-training without explicit review boundaries
- guaranteed correctness for every uploaded format
- visual OCR confidence overlays and end-user parser correction queues
- official-source verification for every user-entered field across every module

## Current Design Rule

ALFRED should prefer:

- source-backed data over unsupported claims
- parser confidence over silent acceptance
- explicit freshness windows over permanent cached assumptions
- circuit-breaker fallback over repeated failing upstream calls
- server-side internal-clock timestamps over browser-derived event timing
- scoped aggregation over loading entire histories when only a summary is needed
- live chart datasets or explicit empty states over demo or placeholder graph data
- user-scoped learning memory over cross-user parser contamination
