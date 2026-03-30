# Architecture

## Core Shape

ALFRED is a Django monolith with module-oriented apps and template-driven dashboards.

- UI pages are served from `alfred_ai/views.py` and `templates/`
- module APIs live inside each app under `views.py` and `urls.py`
- intelligence logic is mostly kept in `services/`
- user-facing scripts live in `static/js/`
- cross-module operational timestamps are generated through `alfred_ai/internal_clock.py`
- superuser-only operational state is centralized through `alfred_ai/project_details.py`

## Main Domains

### Finance

- expenses
- budgets
- loans
- investments
- reports
- integrations for credit/tax/recommendations

### Life Intelligence

- career
- behavioral
- relationship
- family
- risk

Career now includes:

- resume ingestion and parsing
- job-link parsing and fit scoring
- market/news/openings enrichment through verified external intelligence

### Mobility

- `BikeProfile` currently acts as the generic saved vehicle profile model
- vehicle maintenance records are stored in service, document, issue, and condition tables
- travel plans, trip logs, and trip photos are kept separately from maintenance data

## Verified External Intelligence

`apps/integrations/models.py`

- `VerifiedExternalInsight` stores source-backed cached records
- records carry source URL, summary, checksum, freshness window, and status
- stale records are downgraded and old failed/inactive records are cleaned up
- circuit-breaker state is kept in the cache layer so repeated source failures do not keep hammering the same upstream dependency

Current consumers:

- `apps/mobility/services/travel_advisor.py`
- `apps/career/views.py`
- `apps/risk/views.py`

Operational hardening now also includes:

- scheduled refresh and cleanup tasks in `apps/integrations/tasks.py`
- batch-limited refresh of due/stale evidence records
- circuit-breaker-backed stale fallback inside `apps/integrations/services/verified_intelligence.py`
- severity-based support routing inside `apps/reports/services.py`

By default the circuit breaker uses Django's configured cache backend. In local development this is a local-memory cache; in production it should be moved to a shared backend so breaker state is consistent across processes.

## Data Collection And Processing

ALFRED currently handles data through four broad paths:

1. Manual user input through module forms.
2. File uploads that are parsed into extracted payloads plus confidence/status metadata.
3. External allowlisted fetches that become `VerifiedExternalInsight` cache records.
4. Derived summaries that blend stored records across modules for dashboard use.

The detailed lifecycle is documented in [DATA_COLLECTION_AND_PROCESSING.md](DATA_COLLECTION_AND_PROCESSING.md).

## Operations Console

- `alfred_ai/project_details.py` builds the superuser-only project-details payload
- the page is rendered from `templates/project_details.html`
- it combines live ticket-routing counts, report-library rollups, evidence-watchlist counts, loan-review queues, and adaptive learning-progress summaries
- the main user dashboard intentionally does not render this operational data

Project-details now also documents the difference between:

- ML-backed paths
- adaptive but heuristic/evidence-blended paths
- not-yet-fully-learned paths

## Career Risk Timing

Career timing is now a first-class derived output in the career dashboard. It blends:

- market risk from verified external signals
- resume and job-fit signals where available
- liquid runway from active bank balances
- fixed monthly load from rent and active loan EMI

This produces a dated window for when a larger career move is more reasonable, plus blockers and safer move types.

## Vehicle Data Flow

1. User creates or selects a vehicle profile.
2. ALFRED matches it against the internal catalog and applies defaults.
3. User uploads a document or service bill.
4. `bike_document_ai` extracts structured fields.
5. Relevance is checked against the selected vehicle profile.
6. Accepted records are saved and fed into service intelligence.
7. The vehicle-service dashboard renders compliance, pending work, cost trends, part-impact guidance, and service-history summaries.

## Query and Growth Strategy

Recent schema changes added indexes on high-growth paths such as:

- user + vehicle profile + service date
- user + vehicle profile + document type + expiry date
- user + risk/status/timestamp combinations
- user + travel plan + log/photo dates
- user + bank account + transaction fingerprint
- user + bank account + external reference + transaction date

The current approach is now a hybrid: request/response dashboard reads plus scheduled refresh/cleanup for verified external intelligence. Broader async orchestration across more modules remains future work.
