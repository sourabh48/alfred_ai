# Future Scope

## Highest-Value Next Steps

1. Add parser correction and review queues.
2. Expand verified evidence beyond travel/career/risk into recommendation, tax, and relationship signals where appropriate.
3. Introduce a generalized `VehicleProfile` naming refactor once backward compatibility is planned.
4. Add stronger automated tests for upload, parsing, statement dedupe, dashboard aggregation, and external-evidence caching.
5. Expand career intelligence to more job sources, recruiter-email parsing, and role-specific compensation benchmarks.
6. Replace the current lightweight career-timing heuristic with a calibrated evidence model once enough reviewed history exists.
7. Add breaker telemetry, refresh observability, and admin review surfaces for the verified-intelligence pipeline.
8. Replace progress-proxy learning metrics with a formal release or model-maturity registry.
9. Add bureau-approved official credit integrations with explicit consent and authentication flow instead of internal-only credit estimates.

## Improvements Worth Considering

- add model-specific maintenance schedules from more official manufacturers
- add OCR confidence overlays and visual document review
- support route-aware trip costing with fuel-price estimates and service-prep buffers
- add user feedback loops so corrections can improve parser heuristics over time
- add more model-specific part-life assumptions so vehicle performance guidance is less generic
- add portfolio and job-market alerting with freshness thresholds and proof links
- add recruiter mail / JD attachment parsing into the same career-fit pipeline
- add salary benchmark sources with evidence and geography-aware compensation views
- move large dashboard aggregations to materialized/cache layers if data volume grows substantially

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
