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
| S | [D4Vinci/Scrapling](https://github.com/D4Vinci/Scrapling), main | [v0.5.1 = 3a4bb5b0a008233c85269a0a38a6d08edd4ce329](https://github.com/D4Vinci/Scrapling/tree/3a4bb5b0a008233c85269a0a38a6d08edd4ce329) | BSD-3-Clause; Python >=3.10; PyPI "4 - Beta" | Core HTML parser only, on bytes ALFRED already fetched; fetcher/stealth/AI extras rejected |
| J | [open-jarvis/OpenJarvis](https://github.com/open-jarvis/OpenJarvis), main | [86f75ef7faeeb2b022a6621716d88c57ba105db0](https://github.com/open-jarvis/OpenJarvis/tree/86f75ef7faeeb2b022a6621716d88c57ba105db0) | Apache-2.0 (no NOTICE file); Python + Rust, FastAPI, Tauri desktop | Ideas and small pattern sets only; its runtime, mining, analytics, Docker sandboxes and marketplace are excluded |

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
| Yahoo daily bars, stale cache/point-in-time handling; `dataflows/vendors/yahoo/ohlcv.py`; `tests/test_ohlcv_latest_bar.py` (S), `test_ohlcv_cache_freshness.py` (C) | Existing public-HTTP `VerifiedIntelligenceService`; INV-05/SCOPE-02 | Symbol/date/close alignment, dated baseline, persisted source expiry and safe owner-cache fallback; no new engine for this fetcher | ADAPT_ALFRED | Local synthetic implementation: 80 backend PASS; final Chrome/contrast/Axe and exact-head CI in EXECUTION_STATE. `tests/test_yahoo_market_acceptance.py`; receipts `artifacts/ci-repair-ac05515/inv05-yahoo-*.json`. No upstream code/engine adopted or conflicting yfinance installed; live/real-account/exchange-close acceptance remains absent |
| Fundamental/market/news/sentiment analysts; `agents/analysts/`; `test_analyst_execution.py`, `test_news_lookahead.py`, `test_fundamentals_lookahead.py` (C) | INV-04, INVEST2-001/002; ALFRED evidence/router/portfolio/UI | Retain compatible upstream analysts via thin adapter, Indian identities and missing-source packet | REUSE_UPSTREAM | Deferred; component licenses, dependency isolation, point-in-time tests and approved data/model providers required |
| Bull/bear debate, research/portfolio/risk managers and graph; `graph/setup.py`, `agents/researchers/`, `agents/risk_mgmt/`; `test_graph_end_to_end.py` (S graph; agents/tests C) | INV-04, COUNCIL-02/05, INVEST2-001 | Bounded research graph; no brokerage execution, arbitrary tools or private-context leakage | REUSE_UPSTREAM | Deferred; canonical portfolio/consent adapter, cancellation/quality gates; do not rebuild equivalent engine |
| Role sequence (analysts → bull/bear → research manager → trader → risk debators → portfolio manager), five-tier rating Buy/Overweight/Hold/Underweight/Sell, market-analyst indicators (SMA50/200, MACD, RSI), daily run and settlement with reflection; `graph/setup.py`, `agents/`, `graph/reflection.py` read at main [9fa1196fffbcfd9de5146d2dd2869df84ab99838](https://github.com/TauricResearch/TradingAgents/tree/9fa1196fffbcfd9de5146d2dd2869df84ab99838) (S graph/roles; tests C) | INV-04, INVEST2-001; `apps/investments/services/research_desk.py`, existing research packet, journal and scheduler | Deterministic roles over the dated Yahoo packet; stale/thin data not rated; owner only accepts or rejects; accepted call becomes a journal view settled after 91 days against NIFTY; holdings and orders never touched; local Ollama challenge stays on demand | IMPLEMENT_INDEPENDENTLY | Owner approval 2026-11-12 (independent role-based copy). No upstream code or dependency. Local synthetic: `tests.test_research_desk` 12 PASS, browser `test_research_desk_suggests_with_charts_and_the_owner_only_accepts` PASS with axe light/dark; 2026-11-18 adds `research_backtest.py` (monthly replay, 90-day statement lag, 91-day score vs NIFTY; after `backtest.py`), ATR stop and support/resistance levels, World Bank macro context, quarterly revenue, opt-in weekly NIFTY 50 ideas from NSE's public CSV, resumable daily runs and a printable report; `tests.test_research_desk` 22 PASS and the browser test PASS locally; 2026-11-18 (later): the local model debates each call and decides the rating (`research_debate.py`, numbers not in the evidence dropped), Reddit mood with the owner's keys, a pretend-money paper trader on accept, Yahoo/Alpha Vantage price switch with fallback, FRED/Alpha Vantage/SEC EDGAR context (owner-approved; keys in Settings); `tests.test_research_desk` 33 PASS; Trading-R1 has no public weights, so lessons from settled calls are used instead; NSE/BSE filings not built; `cc26e14` CI passed, the later work has no hosted CI yet; real-world accuracy unverified |
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
| Scan/discover/portal registry, liveness, pagination/dedup/fresh links; Greenhouse source/tests (S), other providers C | CAREER-03/SCOPE-01, native job_intelligence and Career API/UI | Fix fabricated fresh metadata, stale verified labels, unsafe URLs, duplicate source ordering and owner-cache expiry; retain explicit cached leads | ADAPT_ALFRED | Pin4df3d052 Greenhouse provider/test re-inspected for identity/HTTPS/date boundaries; no copied code or new board integration. Synthetic normalized-feed backend66 PASS; Chrome/Axe/checkpoint/CI evidence in EXECUTION_STATE. Live provider/terms/geography/listing availability and full capability remain unaccepted |

| Remote work versus geographic eligibility; Greenhouse work-model-only enrichment/source and provider tests (S) | CAREER-03/SCOPE-02, existing job_intelligence location parser/filter and owner dashboard/UI | Preserve explicit region restrictions, missing/ambiguous locations and state filters; do not infer worldwide eligibility from remote | ADAPT_ALFRED | MIT pin4df3d052 re-inspected; independent native correction, no upstream code or new provider. Backend56 PASS; browser/checkpoint evidence in EXECUTION_STATE. Both Career scopes reconciled on a local preparation candidate; review/new exact-head CI still gate canonical integration; arbitrary/live geography and full parent unaccepted |
| Oferta/ofertas/triage/pipeline/batch, titles/upskill/training/project; `_shared.md`, catalog (S/C) | CAREER-02/03/07 | Real role evidence, configurable interests, requirement weights and confidence explanations | PORT_PYTHON | Partly ported: triage ported 2026-11-12 (pin 775861b): triage.md formula on an owner brief, `application_kit.triage`; A-G evaluation (`evaluation.evaluation_report`, posting-only importance tiers, 12-row budget) and batch triage ported 2026-11-12; titles and upskill ported 2026-11-12 (pin 775861b): `application_kit.skill_gaps` (upskill.mjs weighting 5 minus triage score, low-fit under 4.0, Critical/High/Medium/Low tiers, 5 scored jobs minimum, CV skills never gaps; no web-searched learning plan) and `title_suggestions` (posted titles from saved jobs not covered by target roles, verbatim CV lines required, nothing written to the brief; no Lateral/Stretch/Pivot axis). Each gap now links to Coursera, edX and Microsoft Learn search pages for the skill name only (ALFRED fetches nothing). training/project ported 2026-11-12 as `application_kit.plan_check`: training.md's six dimensions scored 1-5 from saved postings, skill gaps and owner inputs (DO 4-12 week plan, DO WITH TIMEBOX capped at 6 weeks, DON'T DO naming a more pressing gap); project.md's weighted matrix (signal and time computed, uniqueness/demo/metrics/story rated by the owner; BUILD 3.5+, PIVOT 2.5+, else SKIP; interview pack and 80/20 plan). Thresholds are ALFRED's; upstream gives none. Nothing stored. Remaining: upstream Global score is holistic 1–5, NOT an arithmetic probability. No invented weighted formula/experience; golden JD/CV and uncertainty tests required  |
| ATS/pdf/text/latex/latex-tex, tailoring/writing guardrails; catalog (C) | CAREER-01/02, owned resumes/templates | ATS-compatible PDF, exact resume revisions, no invented achievements | PORT_PYTHON | Partly ported: text/ats/cover ported 2026-11-12: ATS plain-text CV from verbatim CV lines with a printable page (browser PDF); styled HTML and escaped LaTeX layouts plus local-Ollama bullet rewording with deterministic invention checks ported 2026-11-12. Remaining: inspect actual generation/scoring/tests first; no permanent Node runtime  |
| Resume versions/master-profile/intake/interview/add/expand; DATA_CONTRACT/catalog (S/C) | CAREER2-001, CAREER-01 | Review deltas, source evidence and stale-decision invalidation | PORT_PYTHON | Deferred; private originals/owner review/contradiction tests; AI output cannot invent credentials |
| Cover/email/contacto/apply and reviewed attachment/form proposals; catalog and reply contract (S/C) | CAREER-04, CAREER2-002 | Grounded drafts and user-visible form preparation; explicit send/submit/disclosure | PORT_PYTHON | Partly ported: cover letter and six email drafts ported 2026-11-12, read-only, never sent; CAREER2-002 slice 2026-11-12: attachment manifest and signed send confirmation for owner-reviewed email (owner approval 2026-11-12); job-board form submission not done (employer API key, CAPTCHA); CAREER2-002 UNACCEPTED. Remaining: no automatic application or recruiter messaging; malicious JD/attachment/correction tests  |
| Tracker/outcome/archive, status/follow-up/reply receipts; DATA_CONTRACT (S), mode internals C | CAREER-05, CAREER-04, existing outcomes | Preserve accepted outcome tracking; port missing reminders/reply review only | PORT_PYTHON | Deferred; idempotent correction/replay/owner/timezone tests; accepted CAREER-05 not rebuilt |
| Deep/company research/interview-prep/redflags/practice/debrief/STAR; story-bank source/test (S), other modes C | CAREER-07 | Real candidate examples, role-specific rehearsal and sourced company evidence | PORT_PYTHON | Partly ported 2026-11-12 (pin 775861b): owner-written STAR+reflection stories and post-interview debriefs per saved job, story bank across jobs; story figures missing from the current CV listed as not in your CV (story-provenance rule); nothing generated. Ported 2026-11-12 (same pin): deep.md research checklist naming only company and role, owner research notes with a source link per axis; interview/practice question order (real questions first, then round defaults) with saved answers checked for length, reflection and figures not in the CV, plus optional comments from the owner's local Ollama model only (withheld when they bring in figures not in the answer or CV; nothing stored); sessions README transcript import (front matter, speaker turns, competency tags, stated priorities; practice/mock carry no signals); interview-redflag four-signal score and levels from signals the owner marks on real rounds. Step 2c ported: protected-grounds.yml's three verified rows (Ontario, Japan, Germany) with ALFRED's own topic hints; jurisdiction chosen by the owner (no profile location field; no row for India, so not checked); one question is an observation, two counted questions in a round add the signal to the score; grounds with legitimate contexts are named and never counted; never a legal verdict. Step 2b ported: entry-level label plus a stated pay figure in the saved posting plus a catalogue skill the posting never names, reported apart from the score. Not ported: owner below-market notes for 2b, blacklist suggestion, retracted-claims file |
| Offer-prep/negotiation/salary observations and progression; DATA_CONTRACT (S), salary-gap internals C | CAREER-06/08, FIN-07 scenarios | Source/date/currency, desired/advertised/actual distinction; never projected salary as cash | PORT_PYTHON | Partly ported: offer-prep clause walk and same-currency pay gaps ported 2026-11-12; no verdicts, no stored offer text; statutory notes stay lawyer questions. Remaining: inspect salary/outcome tests, no predictive claims absent held-out outcomes; currency policy gated  |
| Patterns/calibrate/retro and advisory learning; catalog (C) | CAREER-08, AI-14/16, existing reviewed learning | Outcome-supported calibration and reviewed proposals only | PORT_PYTHON | Partly ported: patterns report ported 2026-11-12 (5-sent floor, no recommended threshold); calibrate ported 2026-11-12 (calibrate.mjs bands, per-band floor 5, separating/flat/inverted/insufficient, advisory only); retro EXCLUDED: it turns agent-session corrections into rule files, which has no ALFRED equivalent. Remaining: no automatic scoring/model/code changes; genuine outcomes/consent prerequisites  |
| Agent-inbox/session continuation | Existing EXECUTION_STATE/queue and bounded job recovery | Preserve ALFRED continuation contract rather than duplicate a CLI inbox | EXCLUDE | Infrastructure-only upstream workflow; no user feature discarded |
| CLI installers/updater/system-layer tooling, separate Node/Go dashboards, wholesale translations/layout ecosystem | Existing Django desktop architecture | No unrelated platform conversion | EXCLUDE | Infrastructure-only; user data and useful business modes stay mapped above |

## Web Intelligence (AWIE) — S

Reviewed 2026-11-11 for the owner's ALFRED 2.0 brief (section 11). Inspection level **S** for
`scrapling/__init__.py` and `scrapling/parser.py` imports/storage at the pin; other modules **C**.
PyPI and GitHub list no security advisories for 0.5.1 (released 2026-11-04). Nothing installed or copied.

| Feature / upstream source at S pin | ALFRED equivalent / target | Gap / intended refinement | Disposition | Status, dependencies and validation |
| --- | --- | --- | --- | --- |
| `Selector` CSS/XPath/text parsing on lxml; `scrapling/parser.py` (S) | BeautifulSoup + JSON-LD extraction in `apps/career/services/job_intelligence.py` | Faster lxml parsing; same selectors. Core deps lxml (already pinned 6.1.3), cssselect, orjson, tld, w3lib, typing_extensions | ADAPT_ALFRED | Deferred pilot. Feed only bytes returned by `alfred_ai/services/public_http.py` (HTTPS, no redirects, cookies, proxy or credentials). Owner approved the core `scrapling==0.5.1` dependency (no extras) for this Career pilot on 2026-11-11; add it no earlier than 2026-11-18 (14 days after release), with the CI reviewed-source pin move |
| Adaptive element relocation after layout change; `parser.py` `adaptive`, `core/storage.py` `SQLiteStorageSystem` (S/C) | Layout-change detection required by brief 11.7 | Default store is `elements_storage.db` inside the installed package: outside private storage, read-only when packaged. Use only with an ALFRED-owned store under the private data dir, or keep disabled. A relocated match is a candidate, never a silent replacement of verified data | ADAPT_ALFRED | Deferred; acceptance needs saved synthetic before/after layout fixtures showing correct relocation and fail-closed mismatch, compared with the BeautifulSoup baseline |
| `Fetcher`, `AsyncFetcher`, `StealthyFetcher`, `[fetchers]` extra: curl_cffi impersonation, playwright/patchright, browserforge, apify-fingerprint-datapoints (C) | `public_http.py` secure boundary | Browser/TLS fingerprint spoofing and stealth automation conflict with brief 11.4 (no stealth, identity rotation or bot-detection evasion) and bypass the SSRF/redirect/size boundary | REJECT | Never installed. Any later JavaScript rendering needs its own reviewed, policy-enforced isolated adapter (brief 11.14) |
| `[ai]` MCP server, `[shell]`, spiders/crawl engine (C) | Read-only tools USE-04; queue/Huey | Arbitrary model-driven fetching and unbounded crawling are outside the permission model | REJECT | Use ALFRED's own allowlisted tools, quotas and Huey jobs instead |

Pilot order once approved: one permitted public source, Career job-page parsing behind a side-by-side
comparison with the current parser on synthetic fixtures; adopt only on measured improvement with no regression.

## Validation and adoption rule

For the selected row, pin/recheck component source and tests, trace ALFRED callers,
record one disposition and smallest gap, then run focused backend, relevant actual
Chrome/Axe, privacy/ownership, financial reconciliation and failure/offline tests.
Separate synthetic/local/provider/packaged/real-account results. All unselected
implementations remain deferred; this matrix adds no acceptance counts or queue jumps.
Source inspection receipts/pins are cached under ignored `artifacts/sprint-8f505a3/`.

## Upstream gap build — 2026-11-18

Pins inspected at code level: TradingAgents main `9fa1196f`, career-ops main `fe9cb888`, TREK main `2bcfc1bf`.
Local synthetic tests only; no hosted CI on these commits yet; live accuracy unverified.

| Feature / upstream source at pin | ALFRED equivalent / target IDs | Gap / intended refinement | Disposition | Status, dependencies and validation |
| --- | --- | --- | --- | --- |
| Aggressive/conservative/neutral risk debators, debate rounds, reflection; `agents/risk_mgmt/`, `graph/reflection.py` (T) | INV-04, INVEST2-001; `research_debate.py` | Grounded sentences only; reflection appended to settled accepted calls | IMPLEMENT_INDEPENDENTLY | `tests.test_research_desk` PASS; desk browser test PASS |
| Prediction-market context (T dataflows) | INV-04; `research_sources.prediction_markets` | Polymarket public search, context only, "not a forecast" | IMPLEMENT_INDEPENDENTLY | Owner approval 2026-11-18; live check returned markets |
| master-profile, expand, discover, gambit, retro modes (C) | CAREER2-001, CAREER-08; `career_tools.py` | Owner ticks each fact; public board JSON only; local model; rules re-validated | PORT_PYTHON | MIT attribution in source; `tests.test_career_tools` PASS; browser test PASS |
| reply-watch mode (C) | CAREER-05; `reply_watch.py` | Read-only inbox through the person's own Gmail (gmail.readonly) or Outlook (Mail.Read) since 2026-11-19 (IMAP removed); plain rules, no model, Apply only by owner | PORT_PYTHON | Owner approval 2026-11-18 (mailbox read); synthetic Gmail/Graph tests PASS; live NOT_RUN |
| Posting signals 13, 15, 16, 19, 20 (C) | CAREER-02; `evaluation.posting_notes` | Jurisdiction signals 08-12, 14, 17, 22 not ported (no verified law tables) | PORT_PYTHON | `tests.test_career_evaluation` PASS |
| H-1B sponsor signal (C) | CAREER-02; `h1b_sponsor.py` | Owner-downloaded DOL LCA file read locally; no PERM evidence | PORT_PYTHON | DOL blocks automated access; synthetic xlsx tests PASS |
| Reservations, GPX tracks, places import (R) | TRAVEL; `trip_tools.py` | Records only, never books; AI fields must appear in the confirmation | IMPLEMENT_INDEPENDENTLY | No AGPL code copied; `tests.test_trip_tools` PASS; browser test PASS |
| Transit and holiday/vacation planner (R) | TRAVEL; `GoogleTransit`, `NagerHolidays` | Google only for transit; Nager.Date for holidays (no India coverage) | IMPLEMENT_INDEPENDENTLY | Owner approval 2026-11-18; Nager live check PASS; Google transit faked in tests |
| Collaboration, cost splitting, public share, photo book (R) | none | Out of scope | EXCLUDE | Not approved |

## Local assistant — J (OpenJarvis) — 2026-11-25

Owner request (session of 2026-11-25): scan OpenJarvis in depth and add what helps, keeping security in mind; no crypto mining;
Docker not required. Shallow clone at the pin read in a scratch folder, never run. Inspection **S** for
`learning/routing/complexity.py`, `security/injection_scanner.py`, `mining/`, `analytics/client.py`, `learning/`,
`traces/` and `memory/` imports; other modules **C**.

Ledger check: the learning, trace and memory code does not import or call the mining code. Mining (Pearl) is off unless
a `[mining]` config section exists and submits only proofs to its gateway. The only other outbound path is opt-in
PostHog analytics (ALFRED now has its own, allow-listed sender). Learning data is therefore not shared as a ledger at this pin; ALFRED adopts neither part.

| Feature / upstream source at J pin | ALFRED equivalent / target IDs | Gap / intended refinement | Disposition | Status, dependencies and validation |
| --- | --- | --- | --- | --- |
| Query complexity score and tiers; `learning/routing/complexity.py` (S) | AI-15; `question_complexity.py`, `hybrid_intelligence.easy_question` | Same signals and weights, money words added to the arithmetic signal; simple Finance, Travel and Career lookups use the fast local model, anything with arithmetic, comparison or advice keeps the main one | ADAPT_ALFRED | Apache attribution and change note in source; `tests.test_local_thinking` PASS (commit `0c3bfff`); answer quality on the owner's PC not measured |
| Per-request timing and model in traces; `traces/` (C) | AI-15; `local_model` and `answer_seconds` on a local answer | Shown beside the answer only; nothing stored or sent, no analytics | IMPLEMENT_INDEPENDENTLY | `tests.test_local_thinking` PASS (commit `0e8b701`) |
| Prompt-injection patterns; `security/injection_scanner.py` (S) | AI-12, INV-04; `prompt_injection.py` in `web_lookup.search` and `research_social` | Web results and Reddit titles that match are left out before any model reads them; prompts still treat all text as data | ADAPT_ALFRED | `tests.test_assistant_web_lookup`, `tests.test_research_desk` PASS (commit `54cadcd`); patterns are not a complete defence |
| Morning digest agent and spoken output (C) | AI-18; Home "Read my briefing" with the existing Piper voice | Reads Home's own figures, attention items and next trip; no news feed, no model call | IMPLEMENT_INDEPENDENTLY | `tests.test_home_page` PASS and three Home Chrome tests PASS (commit `736ec03`); not heard on the owner's PC |
| Pearl crypto mining; `mining/` (S) | none | Owner: no mining on this PC | EXCLUDE | Not copied or installed |
| PostHog analytics; `analytics/client.py` (S) | `alfred_ai/services/usage_analytics.py`, page and local-answer events | Owner 2026-11-25: use it, never sensitive data, ALFRED decides. Sends whenever `ALFRED_POSTHOG_PROJECT_KEY` is set (EU or US PostHog Cloud only); allowlist: page route name, answer topic, fast/main model, rounded seconds, thinking, web used. One random ID per PC, no person profile, no GeoIP. `ALFRED_USAGE_ANALYTICS=false` stops it | IMPLEMENT_INDEPENDENTLY | No upstream code; `tests.test_usage_analytics` 5 PASS; no live PostHog project checked |
| Docker code interpreter, shell and sandbox tools (C) | none | Owner: Docker not required | EXCLUDE | Not copied |
| Skill marketplace, A2A, messaging channels (C) | none | Untrusted community code; outbound messages need per-action approval | EXCLUDE | Not copied |
