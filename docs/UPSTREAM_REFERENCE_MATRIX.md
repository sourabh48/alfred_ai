# Pinned upstream reference and adoption matrix

Researched 2026-10-26. This is a source/feature comparison, **not integration or
upstream test execution evidence**. The existing execution queue alone selects
work; original 143 capabilities and 13 extensions are unchanged. Grouped rows
cover related workflows without inventing additional roadmap IDs.

## Immutable repositories and inspection level

| Key | Authoritative repository / default branch | Immutable source | Declared license / runtime | Decision boundary |
| --- | --- | --- | --- | --- |
| A | [LosaLosSantos/aurelio-finance](https://github.com/losalossantos/aurelio-finance), main | [821049126efc6c0993f2ee1dcd8879eb7d7ed917](https://github.com/losalossantos/aurelio-finance/tree/821049126efc6c0993f2ee1dcd8879eb7d7ed917) | MIT; Python >=3.12, FastAPI/SQLAlchemy | Algorithm reference only; no application/runtime transplant |
| T | [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents), main | [e8f5503e9b86d5c2710b0c76b1f686703968c9df](https://github.com/TauricResearch/TradingAgents/tree/e8f5503e9b86d5c2710b0c76b1f686703968c9df) | Apache-2.0; Python >=3.11, LangGraph/LangChain | Compatible Python engine reuse first through thin adapters |
| R | [liketrek/TREK](https://github.com/liketrek/TREK), main | [d4da05bbc93bcfa9668e7a8f4e5384b788452418](https://github.com/liketrek/TREK/tree/d4da05bbc93bcfa9668e7a8f4e5384b788452418) | AGPL-3.0; Node/React/Nest ecosystem | Product inspiration; independent Django implementation only |
| C | [career-ops-hq/career-ops](https://github.com/career-ops-hq/career-ops), main | [4df3d0525a0a466f6b08928a7c3bd23946cb410f](https://github.com/career-ops-hq/career-ops/tree/4df3d0525a0a466f6b08928a7c3bd23946cb410f) | MIT; Node ^22.13 or >=23.4, optional Go dashboard | Incremental native Python/Django business-workflow port |

Repository API/default refs, LICENSE text, README and recursive path inventories
were inspected at these pins. Component/dependency licenses must be rechecked
when code is selected for reuse. No upstream code/assets were copied or installed.
MIT adaptations retain copyright/license; Apache adaptations retain license,
applicable NOTICE/attribution and modification notices. TREK copying remains gated.

Inspection levels: **S** = relevant source/test bodies inspected; **C** = catalog
or path inventory only, implementation details UNVERIFIED. No upstream suites were
executed. A test path demonstrates a contract to inspect, not a test we passed.
All dispositions below are selected strategy, not newly accepted functionality.
Unselected rows remain deferred behind their existing queue/dependencies.

## Wealth / Finance — A

ALFRED targets existing `apps/expenses/services/financial_intelligence.py`,
`apps/investments/services/portfolio_intelligence.py`, budget/loan services,
owned documents and current Django APIs/UI; canonical records stay authoritative.

| Feature / upstream source and tests at A pin | ALFRED equivalent / target IDs | Gap / intended refinement | Disposition | Status, dependencies and validation |
| --- | --- | --- | --- | --- |
| Net worth and allocation; README, `backend/app/positions.py`; `backend/tests/test_wealth.py` (S) | Accepted finance/portfolio totals FIN-01, INV-01, INV-08 | Preserve accepted totals; do not substitute another register | ALREADY_VERIFIED | Existing ALFRED receipts only; no new real-account claim |
| Dated institution snapshots + strictly later ledger events; `positions.py`, `routers/snapshots.py`; `test_wealth.py` (S source; deeper event tests C) | Financial baseline/import reconciliation FIN-09/10/14, WEALTH2-001 | Explain cutoffs and incomplete anchors; prevent transfers/dividends counted twice | ADAPT_ALFRED | Deferred; compare event identity/cutoffs with Decimal tests before any approved schema/mutation |
| Return/performance analytics; `backend/app/analytics.py` and prices paths (C) | INV-03/05/06 | XIRR/CAGR only with dated actual cash flows; no synthetic historical prices | ADAPT_ALFRED | Algorithm details UNVERIFIED; inspect source/tests on selection; currency/outcome gates remain |
| Look-through/overlap, issuer identity; `composition.py`; `test_composition.py` (S) | INV-04, WEALTH2-002 | Retain opaque/unpriced portions, dated source coverage and overlap depth | ADAPT_ALFRED | Deferred; tests must reconcile weights, unknown portions and duplicate fund holdings; no EUR/FX assumptions |
| Goals/reserves/savings capacity; `planning.py`, `sizing.py` (C) | FIN-05/07, INV-06, WEALTH2-003 | Reuse canonical obligations and reserves; uncertainty and goal dependencies explicit | ADAPT_ALFRED | Deferred; inspect algorithm/tests first; goals/currency/valuation approval as applicable |
| Analyst/private-context separation and reviewable proposals; `advisor.py`, `analyst_tools.py`; `test_advisor.py` (C) | DOC-07, AI-12, WEALTH2-004 | Evidence/date/fingerprint checks and explicit user confirmation; no AI financial writes | ADAPT_ALFRED | Deferred; inspect source/tests and owner/stale/malicious proposal acceptance before adoption |

## Investment engine — T

Inspected `tradingagents/graph/setup.py`, `graph/checkpointer.py`,
`llm_clients/factory.py`, `dataflows/vendors/yahoo/ohlcv.py`,
`tests/test_checkpoint_resume.py`, `test_backtest.py`, `test_instrument_identity.py`,
`test_ohlcv_latest_bar.py`, README and pyproject. Other component paths below are
inventory, not a claim of detailed review.

| Feature / upstream source and tests at T pin | ALFRED equivalent / target IDs | Gap / intended refinement | Disposition | Status, dependencies and validation |
| --- | --- | --- | --- | --- |
| Owned portfolio, account-safe import and deterministic projections | INV-01/02/03/08; existing Investment/models/money/import services | Preserve accepted core and bounded INV-02 scopes; research never becomes holdings | ALREADY_VERIFIED | Only accepted scopes; full INV-02 remains unaccepted |
| Yahoo daily bars, stale cache/point-in-time handling; `dataflows/vendors/yahoo/ohlcv.py`; `tests/test_ohlcv_latest_bar.py` (S), `test_ohlcv_cache_freshness.py` (C) | Existing public-HTTP `VerifiedIntelligenceService`; INV-05/SCOPE-02 | Fix existing adapter's symbol/date/close alignment and cache provenance; no new engine for this fetcher | ADAPT_ALFRED | Next eligible scope; existing bounded transport avoids incompatible yfinance bulk import. Preserve observations, reject bad evidence, synthetic backend/Chrome/money/privacy tests |
| Fundamental/market/news/sentiment analysts; `agents/analysts/`; `test_analyst_execution.py`, `test_news_lookahead.py`, `test_fundamentals_lookahead.py` (C) | INV-04, INVEST2-001/002; ALFRED evidence/router/portfolio/UI | Retain compatible upstream analysts via thin adapter, Indian identities and missing-source packet | REUSE_UPSTREAM | Deferred; component licenses, dependency isolation, point-in-time tests and approved data/model providers required |
| Bull/bear debate, research/portfolio/risk managers and graph; `graph/setup.py`, `agents/researchers/`, `agents/risk_mgmt/`; `test_graph_end_to_end.py` (S graph; agents/tests C) | INV-04, COUNCIL-02/05, INVEST2-001 | Bounded research graph; no brokerage execution, arbitrary tools or private-context leakage | REUSE_UPSTREAM | Deferred; canonical portfolio/consent adapter, cancellation/quality gates; do not rebuild equivalent engine |
| Checkpoints, memory/decision logs, settlement/backtests; `graph/checkpointer.py`, `memory/`, `backtest.py`; `test_checkpoint_resume.py`, `test_backtest.py` (S tests/checkpointer) | AI-16, COUNCIL-04, INVEST2-001/002 | Owner-scoped encrypted persistence, run fingerprints, isolated paper history and no look-ahead | REUSE_UPSTREAM | Deferred; plain upstream SQLite/memory is not automatic private-vault acceptance; crash/race/retention/backtest evidence needed |
| Model/provider tier routing; `llm_clients/factory.py`; `test_ollama_base_url.py`, `test_llm_max_retries.py` (S factory; tests C) | Existing ALFRED local provider/registry, AI-15, COUNCIL-01 | Preserve Ollama default and authorized cloud controls; bound retries/deadlines | REUSE_UPSTREAM | Deferred; explicit runtime/model/provider compatibility; no cloud fallback or ChatGPT-plan credential assumption |
| Automatic orders, paid feeds/remote credentials | No approved automatic trading scope | Outside this adoption; watchlists/research remain distinct from owned positions | EXCLUDE | No broker activation, orders, paid or private-data disclosure |

**Exact compatibility boundary:** T pyproject requires `pandas>=3.0.6`,
`yfinance>=1.7.0`, `langchain-core>=1.6.5`, `langgraph>=1.2.12` and
`langgraph-checkpoint-sqlite>=3.1.1`. ALFRED requirements pin `yfinance==0.2.36`
and declare pandas without that upstream minimum. This metadata comparison proves
a yfinance constraint conflict, not an executable compatibility result. Do not
bulk-install. When engine adoption is selected, test a compatible pinned component
or isolated environment with a bounded data contract; document remaining conflict
instead of replacing the whole framework. Engine compatibility remains UNVERIFIED.

## Native Travel — R

Inspected README/product workflows, LICENSE, `client/src/components/Planner/DayReorderPopup.tsx`
and `client/e2e/reorder-arrows.spec.ts` (S). Other paths/features below are C unless
noted. No AGPL source/assets are copied; future algorithms/UI are independently authored.
Targets existing `apps/mobility/services/travel/`, owned trip models, APIs and desktop UI.

| Feature / upstream evidence at R pin | ALFRED equivalent / target IDs | Gap / intended refinement | Disposition | Status, dependencies and validation |
| --- | --- | --- | --- | --- |
| Destination discovery and comparisons (README) | Accepted TRAVEL-03 candidate pool; other discovery TRAVEL-02 | Preserve accepted pool/show-more behavior and explicit origins/default override | ALREADY_VERIFIED | Accepted TRAVEL-03 only; provider freshness/novelty beyond it unaccepted |
| Day/stop editor, reorder arrows, route sorting and locked stops; DayReorderPopup + e2e (S) | TRAVEL-04/07, TRAVEL2-001 | Desktop pointer/keyboard edits, undo/revision/save/reopen, user locks | IMPLEMENT_INDEPENDENTLY | Deferred; current itinerary/restriction scopes preserved; actual Chrome/keyboard/owner/concurrency acceptance required |
| Routed stops/maps/scenic detours; README (C implementation) | TRAVEL-07/08/09/15/17 | Route identity, measured detours, independent motorcycle/permit evidence, stale/offline states | IMPLEMENT_INDEPENDENTLY | Deferred TRAVEL-09 patch preserved; authorized providers only; no car-legality or geometric-road-distance claims |
| Booking/document organizer and reviewed confirmation extraction; README, `server/src/nest/booking-import/kitinerary-extractor.service.ts` (C) | DOC-06, TRAVEL2-002 | Owned originals/review, source expiry, no inferred availability or booking writes | IMPLEMENT_INDEPENDENTLY | Deferred; no booking/provider/attachment disclosure without confirmation |
| Packing/reminders, budgets/affordability, trip cost/photo history, PDF/GPX/ICS; README (C implementation/tests) | TRAVEL-19, TRAVEL2-003/004/005 | Durable owner opt-in, canonical reserve-aware budget, private evidence-preserving exports | IMPLEMENT_INDEPENDENTLY | Deferred; finance/currency/export approval and source/UI/offline validation as applicable |
| Saved-plan offline access/location-aware search and selective refresh; README (C) | TRAVEL-02/16/17/23, existing caching | Distinguish cached/static from fresh results, quotas and expiry; preserve approved map fallback | IMPLEMENT_INDEPENDENTLY | Deferred; inspect relevant source/tests at selection; no new credentials implicitly activated |
| Collaboration/invites/polling/public share/group settlements/mobile PWA/nav/sync, separate backend | Explicit exclusions | Do not port infrastructure or social/mobile-specific product scope | EXCLUDE | No silent removal of required desktop behavior; exclusions are owner's scope decisions |

## Native Career — C

Identity blocker **resolved**. Inspected README, ARCHITECTURE, DATA_CONTRACT,
`modes/README.md`, scoring in `modes/_shared.md`, `lib/story-bank.mjs`,
`tests/story-bank-contract.test.mjs`, `providers/greenhouse.mjs`,
`tests/providers/greenhouse.test.mjs` and package runtime requirements (S).
The mode catalog covers all root business modes; C rows retain uninspected details
for later source/test review. Upstream canonical files/derived SQLite are NOT a
reason to replace ALFRED's Django-owned canonical database.

| Feature / C source or mode family | ALFRED equivalent / target IDs | Gap / intended refinement | Disposition | Status, dependencies and validation |
| --- | --- | --- | --- | --- |
| Core owned resume intake/review and source-grounded JD skill gaps; DATA_CONTRACT, `_shared.md` (S) | Accepted CAREER-01/02, resume/job services | Preserve accepted evidence/ownership; do not duplicate ingestion | ALREADY_VERIFIED | Existing ALFRED acceptance, not upstream accuracy proof |
| Scan/discover/portal registry, liveness, pagination/dedup/fresh links; Greenhouse source/tests (S), other providers C | CAREER-03, verified_intelligence/job services | Accept existing approved feeds first; source-specific gaps visible | ACCEPT_EXISTING | Existing provider scope only; new board integrations require scoped source/terms/security review |
| Oferta/ofertas/triage/pipeline/batch, titles/upskill/training/project; `_shared.md`, catalog (S/C) | CAREER-02/03/07 | Real role evidence, configurable interests, requirement weights and confidence explanations | PORT_PYTHON | Deferred; upstream Global score is holistic 1–5, NOT an arithmetic probability. No invented weighted formula/experience; golden JD/CV and uncertainty tests required |
| ATS/pdf/text/latex/latex-tex, tailoring/writing guardrails; catalog (C) | CAREER-01/02, owned resumes/templates | ATS-compatible PDF, exact resume revisions, no invented achievements | PORT_PYTHON | Deferred; inspect actual generation/scoring/tests first; no permanent Node runtime |
| Resume versions/master-profile/intake/interview/add/expand; DATA_CONTRACT/catalog (S/C) | CAREER2-001, CAREER-01 | Review deltas, source evidence and stale-decision invalidation | PORT_PYTHON | Deferred; private originals/owner review/contradiction tests; AI output cannot invent credentials |
| Cover/email/contacto/apply and reviewed attachment/form proposals; catalog and reply contract (S/C) | CAREER-04, CAREER2-002 | Grounded drafts and user-visible form preparation; explicit send/submit/disclosure | PORT_PYTHON | Deferred; no automatic application or recruiter messaging; malicious JD/attachment/correction tests |
| Tracker/outcome/archive, status/follow-up/reply receipts; DATA_CONTRACT (S), mode internals C | CAREER-05, CAREER-04, existing outcomes | Preserve accepted outcome tracking; port missing reminders/reply review only | PORT_PYTHON | Deferred; idempotent correction/replay/owner/timezone tests; accepted CAREER-05 not rebuilt |
| Deep/company research/interview-prep/redflags/practice/debrief/STAR; story-bank source/test (S), other modes C | CAREER-07 | Real candidate examples, role-specific rehearsal and sourced company evidence | PORT_PYTHON | Deferred; provenance/no invented stories, bounded local model and UI validation |
| Offer-prep/negotiation/salary observations and progression; DATA_CONTRACT (S), salary-gap internals C | CAREER-06/08, FIN-07 scenarios | Source/date/currency, desired/advertised/actual distinction; never projected salary as cash | PORT_PYTHON | Deferred; inspect salary/outcome tests, no predictive claims absent held-out outcomes; currency policy gated |
| Patterns/calibrate/retro and advisory learning; catalog (C) | CAREER-08, AI-14/16, existing reviewed learning | Outcome-supported calibration and reviewed proposals only | PORT_PYTHON | Deferred; no automatic scoring/model/code changes; genuine outcomes/consent prerequisites |
| Agent-inbox/session continuation | Existing EXECUTION_STATE/queue and bounded job recovery | Preserve ALFRED continuation contract rather than duplicate a CLI inbox | EXCLUDE | Infrastructure-only upstream workflow; no user feature discarded |
| CLI installers/updater/system-layer tooling, separate Node/Go dashboards, wholesale translations/layout ecosystem | Existing Django desktop architecture | No unrelated platform conversion | EXCLUDE | Infrastructure-only; user data and useful business modes stay mapped above |

## Validation and adoption rule

For the selected row, pin/recheck component source and tests, trace ALFRED callers,
record one disposition and smallest gap, then run focused backend, relevant actual
Chrome/Axe, privacy/ownership, financial reconciliation and failure/offline tests.
Separate synthetic/local/provider/packaged/real-account results. All unselected
implementations remain deferred; this matrix adds no acceptance counts or queue jumps.
Source inspection receipts/pins are cached under ignored `artifacts/sprint-8f505a3/`.
