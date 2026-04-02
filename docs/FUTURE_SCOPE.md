# Future Scope

## Highest-Value Next Steps

1. Expand the current document-review flow into visual OCR overlays and richer field-level correction tooling.
2. Expand verified evidence beyond travel/career/risk/recommendation/tax into relationship, investment, and other advisory signals where appropriate.
3. Introduce a generalized `VehicleProfile` naming refactor once backward compatibility is planned.
4. Add stronger automated tests for upload, parsing, statement dedupe, dashboard aggregation, and external-evidence caching.
5. Expand career intelligence to more live job sources, richer recruiter attachment persistence, and more geography-aware compensation benchmarks.
6. Replace the current lightweight career-timing heuristic with a calibrated evidence model once enough reviewed history exists.
7. Add breaker telemetry, refresh observability, and admin review surfaces for the verified-intelligence pipeline.
8. Replace progress-proxy learning metrics with a formal release or model-maturity registry.
9. Add bureau-approved official credit integrations with explicit consent and authentication flow instead of internal-only credit estimates.

## Improvements Worth Considering

- broaden model-specific maintenance schedules and service intervals across more official manufacturers
- add OCR confidence overlays and visual document review
- support route-aware trip costing with fuel-price estimates and service-prep buffers
- add user feedback loops so corrections can improve parser heuristics over time
- add more model-specific part-life assumptions so vehicle performance guidance is less generic
- add portfolio and job-market alerting with freshness thresholds and proof links
- add richer recruiter-mail attachment review and persistence beyond the current intake path
- add broader salary benchmark sources with evidence and geography-aware compensation views
- expand materialized/cache layers and observability as more high-history dashboards mature

## What Should Be Avoided

- uncontrolled background crawling without source allowlists
- silent acceptance of weak or unrelated uploaded documents
- claiming ML accuracy where only heuristics exist
- deleting stale verified data before a replacement record is available

## Suggested Product Direction

The strongest direction for ALFRED is not "more dashboards," but a tighter evidence and feedback loop:

- every important external signal should show proof
- every parser should expose confidence and allow correction
- every long-lived cache should have a freshness contract
- every recommendation should be grounded in either user history, verified external data, or both
