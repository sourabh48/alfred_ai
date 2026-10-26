# ALFRED 2.0 integration boundaries

This is the integration contract, not another roadmap. The canonical queue and
143-capability tracker select work; 13 extension stories remain separate.
Pinned sources, dispositions and inspection limits: [reference matrix](UPSTREAM_REFERENCE_MATRIX.md).
No upstream application/engine has been integrated merely by creating these docs.

## Shared canonical services

Django identity/session/CSRF and owner-scoped SQLite records remain authoritative.
Finance consumers use `resolve_canonical_financial_baseline` in
`apps/expenses/services/financial_intelligence.py`, existing domain Decimal money
helpers, transaction fingerprints/transfer legs, obligations and reconciliation.
Observed, reported, estimated, proposed, unknown and stale values stay distinct.
No implicit FX, locale-derived denomination, historical rewrite or synthetic cash.
Schema/valuation/currency approvals remain required where applicable.

Existing document/corpus/knowledge services retain encrypted originals, consent,
owner/account identity, citations/revisions, expiry, correction/deletion invalidation
and fail-closed corruption/key-loss behavior. Reuse `verified_intelligence` and
bounded public HTTP for source/date/cache provenance, quotas and safe failures.
Use current Django apps/templates/JavaScript; no replacement UI platform.

## Wealth reference boundary

Aurelio source/tests inform independently authored improvements to existing finance
services. Snapshot reconciliation must count only supported post-anchor events,
preserve transfer/dividend identity, explain unknown cost/price and retain opaque
look-through portions. Source cash flows are required for XIRR/CAGR; estimates and
missing historical prices cannot become actual performance. Reconcile Decimal
totals before recommendations. No Aurelio FastAPI/SQLAlchemy app or EUR/FX defaults.

## TradingAgents research-engine boundary

`Django Investment API → owner/consent/evidence adapter → compatible pinned
TradingAgents graph → approved data/local-model adapters → reviewed research packet
→ existing ALFRED persistence/UI`.

Prefer existing accepted ALFRED equivalents; otherwise reuse compatible upstream
analysts, debate/risk managers, memory, checkpoint and backtest engine through thin
adapters. Do not reimplement the engine for native appearance. Component/dependency
conflicts need a bounded isolated compatibility experiment when selected; the
current yfinance constraints conflict, so bulk install is prohibited. No engine
dependency enters the main SDK until validated and license obligations retained.

The adapter allows bounded structured tools, scoped dates/instrument identities,
point-in-time data, source fingerprints and cancellation/deadlines. A research
packet carries dated citations, missing/stale evidence, assumptions, bull/bear/risk
arguments and uncalibrated uncertainty explicitly. Watchlists are separate from
holdings. No brokerage orders, autonomous allocation writes, price fabrication,
paid provider activation or leaking confidential owner context to public analysts.
Upstream plain SQLite/checkpoints require ALFRED's private-storage review; the
engine cannot become an alternative canonical portfolio or private-history store.

## Career Ops native conversion boundary

The exact MIT upstream is resolved in the matrix. Port approved business behavior
incrementally into existing CareerProfile/resume/job/opportunity services and
owned documents, background jobs, Django APIs and templates. Preserve current
accepted intake/skill-gap/outcome flows. No permanent Node service, Go dashboard,
CLI installer/updater conversion or upstream files-as-canonical database switch.

Source-backed requirement matching, configurable Bengaluru/Java/Spring/AWS interests,
fresh job links, ATS PDF/version comparisons, company research, STAR practice,
draft messages and outcomes share ALFRED evidence/identity. Upstream holistic
scores are not calibrated probabilities; transparent requirement weighting must
be independently validated. Never invent CV credentials/achievements or submit an
application/send attachments without explicit user review/action. Advertised or
scenario salary feeds finance scenarios only, never actual income registers.

## TREK independent Travel boundary

Study AGPL product contracts; independently author approved desktop itinerary/day
editor, keyboard/pointer reordering, undo/locks/revisions, map/route interactions,
private organizers/checklists/reminders and exports in current Travel services/UI.
No upstream source, bundles, assets or separate backend is imported. Collaboration,
sharing, invitations, group settlements and mobile-specific expansion are excluded.

Explicit origin/destination wins over saved defaults. Show More advances candidates;
fresh external, cached and static fallback are labelled. Route geometry/identity,
measured road detours, independently supported motorcycle restrictions and source
expiry survive save/reopen. Car routes are not motorcycle-law evidence; geometric
distance is not routed distance. Booking/permit/closure/weather availability is
never inferred. Approved map fallback and financial affordability stay shared.

## Models, confirmation, failures and recovery

Ollama/local routing remains default with the existing 30-second AI deadline.
Cloud routes need explicit consent/cost/disclosure controls; no automatic fallback,
new credentials or assumed ChatGPT-plan API billing. Source material/model outputs
are untrusted; citations, structured validation and deterministic financial tools
bound advice. Reviewed proposals reject stale dependency fingerprints before an
authorized write. Private knowledge Git uploads stay disabled.

Bounded jobs/cache retries distinguish unavailable, stale and cached observations;
offline fallback never fabricates fresh evidence. Revisions, idempotency and owner
keys survive concurrent writers/crashes; source corrections invalidate derived
proposals. Existing migration/backup/rollback safeguards are reused, not replaced.

## Delivery and conditional integration

See [pipeline state](CI_PIPELINE_STATE.md) and AGENTS for sprint/section states.
One active coding scope, at most three outstanding candidates; isolated PR refs
protect concurrent CI from cancellation. Explicit stacks pin dependencies and must
be retargeted/revalidated against master before merge. Cumulative PR #16 needs its
full diff reviewed. Do not repeatedly push unrelated sections into it.

Owner now conditionally authorizes automatic section merges. Exact-head checks,
independent/project reviews, protections/rulesets, source/privacy/rollback and
dependencies must all pass. Pages source and consequences require verified,
explicit public-publishing authorization; application deployment is separate.
Verify merge SHA/source containment and post-merge CI, then synchronize safely.
403/unavailable governance or publishing gates block only integration, not safe
coding. No polling daemon or CI coverage reduction is introduced.
