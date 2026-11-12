# ALFRED reference migration matrix

Owner request 2026-11-07 ("Build a better ALFRED 2.0"). This file records **how** each useful reference
feature reaches ALFRED (method, phase, state). Inspection depth, test paths and detailed gaps stay in
[UPSTREAM_REFERENCE_MATRIX.md](UPSTREAM_REFERENCE_MATRIX.md); slice evidence stays in
[ALFRED_2_0_EXECUTION.md](ALFRED_2_0_EXECUTION.md) and [EXECUTION_STATE.md](EXECUTION_STATE.md).
The 143 original IDs and 13 extensions are unchanged by this file. Implemented is not accepted.

Workspace found: `F:\ALFRED\alfred_ai` on `master` (the brief's `F:\ALFRED_DEV\post-audit` does not exist;
`F:\ALFRED_DEV\nightly-catchup` is a separate preserved worktree).

## Pinned references

| Key | Repository / branch | Commit | License | Stack | Dependency boundary |
| --- | --- | --- | --- | --- | --- |
| A | [LosaLosSantos/aurelio-finance](https://github.com/LosaLosSantos/aurelio-finance) main | 821049126efc6c0993f2ee1dcd8879eb7d7ed917 | MIT | Python 3.12, FastAPI, SQLAlchemy, React | No second server or database; calculations re-written in Django/Decimal |
| T | [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) main | e8f5503e9b86d5c2710b0c76b1f686703968c9df | Apache-2.0 | Python 3.11, LangGraph, LangChain | Needs yfinance>=1.7 and pandas>=3.0.6; ALFRED pins yfinance 0.2.36, so no install |
| R | [liketrek/TREK](https://github.com/liketrek/TREK) main | d4da05bbc93bcfa9668e7a8f4e5384b788452418 | AGPL-3.0 | TypeScript, NestJS, React | Ideas only; no source, bundle or asset copied |
| C | [career-ops-hq/career-ops](https://github.com/career-ops-hq/career-ops) main | 4df3d0525a0a466f6b08928a7c3bd23946cb410f | MIT | Node 22+, optional Go dashboard | Workflows ported to Python; no Node runtime |
| J | [open-jarvis/OpenJarvis](https://github.com/open-jarvis/OpenJarvis) main | f21d902f4d3bd7f0f3f138f1a4613019a394b549 (2026-11-06) | Apache-2.0 | Python | **3.0 only.** Repository metadata pinned; source, dependencies, telemetry and Windows behaviour not yet inspected (UNVERIFIED) |

Methods: DIRECT_REUSE (install or vendor the upstream component), PYTHON_PORT (TS/JS logic rewritten in
Python), DJANGO_ADAPT (Python logic re-homed onto Django models), JS_UI_ADAPT (browser interaction),
REBUILD (useful idea, source unsuitable or copyleft, written independently), REJECT.
States: PLANNED, IMPLEMENTING, TESTED (local synthetic tests pass, not accepted), ACCEPTED, BLOCKED.

## 2.0 features

| ID | Ref | Feature | ALFRED equivalent | Gap | Method and why | Target and tests | Pri | State |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M-W1 | A `planning.py` | Required return for a goal | `apps/budgets/money.py` `required_annual_return`, `GET /api/budgets/goals/<id>/plan/` | Owner saw only months left and no-growth monthly need | DJANGO_ADAPT: small Python bisection, rewritten in Decimal | Known answers, bands, bad input, owner 404, no writes; `tests/test_goal_required_return.py` 3 PASS | P1 | TESTED |
| M-W2 | A `sizing.py` idea | Loan prepayment and loan-vs-invest what-if | `apps/loans` (no simulator before this slice) | No interest-saved, tenure-cut or opportunity-cost view | REBUILD: amortization is standard maths; Aurelio has no loan module to adapt | `apps/loans/services/prepayment.py`, `GET /api/loans/<id>/prepayment/`, Prepayment what-if on the Loans page. Known answers (1,00,000 at 12% for 12 months: EMI 8,884.88), EMI-below-interest, closing prepayment, invest-at-loan-rate equals prepay, canonical liquid-cash runway, missing balance refused, owner 404, no writes; `tests/test_loan_prepayment.py` 6 PASS | P1 | TESTED |
| M-W3 | A positions/snapshots | Dated snapshot reconciliation, net-worth history | `financial_intelligence.resolve_canonical_financial_baseline` | Anchors and post-anchor events | DJANGO_ADAPT | WEALTH2-003; needs schema and owner approval | P2 | PLANNED |
| M-W4 | A `composition.py` | Fund look-through and overlap | `portfolio_intelligence` | Owner-uploaded monthly fund portfolio file (owner decision 2026-11-12) | DJANGO_ADAPT | WEALTH2-001 | P2 | PARTIAL (slice 1: in-memory look-through; slice 2: saved parsed portfolios, investments 0008; slice 3: multi-fund workbooks by owner choice) |
| M-W5 | A advisor | AI explanation of results | Local Ollama grounding services | LLM must explain only computed values | REBUILD | WEALTH2-004 | P2 | PLANNED |
| M-I1 | T memory/settlement/reflection | Dated rating, settlement vs benchmark, lessons recalled before the next call | `ResearchDecision`, `apps/investments/research_views.py`, Research journal UI | Watchlist had no decision history | DJANGO_ADAPT: logic is small; upstream store is plain SQLite outside owner isolation | Outcome/alpha maths, validation, settle-once, lesson-only edit, recall 5+3, owner isolation, data reset, guarded migration; `tests/test_research_journal.py` 6 PASS | P1 | TESTED; migration investments 0007 owner-approved and applied 2026-11-06 |
| M-I2 | T analysts/researchers/risk | Bull/bear/valuation/risk packet | `portfolio_intelligence` watchlist, review alerts | No structured case for and against | REBUILD deterministic first; DIRECT_REUSE blocked by the yfinance/pandas conflict and remote LLM defaults. Unblock found: T `dataflows/vendors/yahoo/fundamentals.py` reads free annual statements through yfinance, which ALFRED already ships (0.2.36); its point-in-time rule withholds undated present-day snapshots for past dates | INVEST2-001: evidence-only packet from dated statements and price history, missing-evidence list, no price targets, no orders | P1 | TESTED, not accepted (2026-11-07 slice: `apps/investments/services/research_packet.py` and `/api/investments/research/packet/` build the dated bull/bear screens, P/E only when statement and price currencies match and profit is positive, owner-scoped portfolio weight, missing evidence and options, with no writes. Independent challenge also TESTED, not accepted: `research_challenge.py` and `/api/investments/research/packet/challenge/` send only the server-rebuilt packet's dated points to the fixed local Ollama model, keep objections that cite a real point and state no number, and label them as hypotheses; only this owner-started call waits up to 120 s, because the CPU-only model writes about 3 tokens a second on this PC. 14 backend tests, 1 Chrome test and a real local-model run with synthetic data (54 s, 3 objections, none dropped) pass) (data source available: 2026-11-07 probe of Yahoo's dated annual fundamentals-timeseries endpoint for a public symbol returned period-end dated values with their own currency (INFY.NS reports USD), without a session token, so it can use ALFRED's pinned HTTPS boundary instead of yfinance's own network stack) |
| M-I3 | T backtest | Time-respecting evaluation | None | Needs dated owner decisions or point-in-time data | REBUILD | Journal settlements (M-I1) are the first honest outcome record | P2 | PLANNED |
| M-I4 | T orders | Broker execution | None | Not wanted | REJECT | No trading | — | REJECT |
| M-C1 | C `templates/states.yml`, `modes/followup.md` | Application stages and follow-up cadence | `apps/career/services/application_tracker.py`, `/api/career/job-analyses/<id>/application/`, `/api/career/follow-ups/` | Outcomes existed; no dated stage history or due follow-ups | PYTHON_PORT | Cadence, cold leads, date rules, CAS 409, owner isolation; `tests/test_career_applications.py` | P1 | TESTED |
| M-C2 | C `modes/oferta.md` reuse rule | Stale match after resume change, resume version diff | `match_freshness`, `/api/career/resumes/compare/` | Old matches looked current after a new resume | PYTHON_PORT | Exact skill/role/experience delta; same test module, 7 PASS total | P1 | TESTED |
| M-C3 | C `modes/triage.md` | First-pass 1-5 score and PASS/MARGINAL/FAIL | `apps/career/services/application_kit.py` `triage`, `/api/career/job-analyses/<id>/triage/`, Career page Application kit | No triage | PYTHON_PORT (pin 775861b, MIT): role 35 %, pay 25 %, location 25 %, CV match 15 %; unknown terms drop out and rescale; -0.5 per red flag; hard disqualifier caps 2.5; priority company passes; pay compared only in the brief's currency (Decimal, no FX) | `tests/test_career_application_kit.py`; Chrome + axe light/dark | P1 | TESTED |
| M-C4 | C `modes/text.md`, `ats.md`, `cover.md`, `email.md` | ATS plain-text CV, cover letter, six email drafts | `apps/career/services/application_kit.py` `tailored_cv`, `cover_letter`, `email_draft`; `/api/career/job-analyses/<id>/kit/`; printable page `/career/job-analyses/<id>/tailored-cv/` (browser Save as PDF) | No generation | PYTHON_PORT: deterministic; only verbatim CV lines (achievements ranked by job terms, sections copied unchanged), JD terms missing from the CV listed separately, gaps stay bracketed; nothing sent or stored; no PDF dependency | Same module and Chrome test | P1 | TESTED |
| M-C5 | C apply/scan automation | Mass apply, CLI, Node dashboard | — | Not wanted | REJECT | No submissions or recruiter messages | — | REJECT |
| M-C6 | C `modes/offer-prep.md` | Offer clause walk, lawyer questions, items to raise, pay gaps | `apps/career/services/application_kit.py` `offer_prep`, `/api/career/job-analyses/<id>/offer-prep/` | No offer reading | PYTHON_PORT: quotes clauses by the upstream ten-part taxonomy, never a verdict; text addressed to an AI is flagged; offer text not stored; pay gaps in Decimal, same currency only | Same module and Chrome test | P2 | TESTED |
| M-C7 | C `modes/patterns.md` | Funnel, score versus outcome, recurring gaps | `apps/career/services/application_kit.py` `patterns`, `/api/career/patterns/` | No outcome analysis | PYTHON_PORT: needs 5 sent applications; awaiting replies are not rejections; no recommended threshold or automatic change | Same module and Chrome test | P2 | TESTED |
| M-R1 | R planner | Itinerary edit/undo, packing/reminders, PDF/GPX/ICS, affordability | TRAVEL2-001..005 in `apps/mobility/services/travel/` | Already implemented | REBUILD (AGPL) | Waiting for owner checks and exact-head CI | P1 | TESTED |
| M-R2 | R routing | Motorcycle restrictions, measured detours | `restrictions.py`, `providers/routing.py` | ORS routes cars only, so motorcycle legality stayed UNKNOWN | REBUILD: TREK's default is the free FOSSGIS Valhalla server, whose `motorcycle` profile follows OpenStreetMap motorcycle access tags and avoids motorways on request | `ValhallaRouting` (opt-in `TRAVEL_VALHALLA_URL`), chosen for motorcycle trips; reports which avoidances were actually met; `tests/test_travel_valhalla.py` 5 PASS. Owner's ORS key added 2026-11-07 to the private runtime config; one synthetic check (Bengaluru to Mysuru, 142.9 km road) returned 200 | P1 | TESTED; real trips in the owner's app not yet checked |
| M-R3 | R collaboration, public share, PWA | — | — | Not wanted | REJECT | Owner exclusion | — | REJECT |

## 3.0 features (not started; owner will share the 3.0 plan)

| ID | Ref | Feature | Method | State |
| --- | --- | --- | --- | --- |
| M-J1 | J | Model routing, hardware detection, local inference tuning | DIRECT_REUSE only if it beats ALFRED's Ollama routing on Windows with no telemetry | PLANNED (3.0) |
| M-J2 | J | Tool registry, permissions, persistent tasks, orchestration | DIRECT_REUSE or REBUILD after source and licence review | PLANNED (3.0) |
| M-J3 | J | Evaluation and resource monitoring | DIRECT_REUSE candidate | PLANNED (3.0) |

## Benchmarks

No before/after benchmark was run for M-W1, M-W2, M-I1, M-C1, M-C2 or M-R2: they add views that did not exist, so the
baseline is "not available". Their evidence is the known-answer tests named above. Ranking, forecasting and
recommendation changes (M-C3, M-I2, M-I3) must record thresholds here before evaluation.

## Provider order (owner 2026-11-07: "keep free one main and paid as fallback")

Routing: motorcycle trips try Valhalla, then openrouteservice, then Google Routes; other trips try openrouteservice, then
Valhalla, then Google. Place lookup tries Open-Meteo, then Google Places only when Open-Meteo is unavailable or finds
nothing. Google is capped in ALFRED at 40 calls a day and 400 a month per API, well under Google's free monthly use, and its
routes carry no line because Google's terms forbid its content on a non-Google map. `tests/test_travel_valhalla.py` 9 PASS.

## Blocked items rechecked against the references (2026-11-07)

| Earlier blocker | What the references offer | Result |
| --- | --- | --- |
| Verified road routing needed a key | TREK uses the free FOSSGIS Valhalla server; the owner also supplied an ORS key | Unblocked in source (M-R2); needs a restart and the owner's own trip check |
| Motorcycle legality unknown | Valhalla motorcycle profile honours OSM access tags | Improved to "OpenStreetMap access tags", still not signage or closures |
| Stock fundamentals had no free source | TradingAgents reads yfinance statements | Source available for INVEST2-001 |
| Live hotel, flight, train and bus availability | None of the four has free live inventory; TREK only stores bookings | Still blocked (paid or partner APIs) |
| Fund look-through holdings | Aurelio's composition needs a holdings provider it does not ship for Indian funds | Still blocked |
| OpenAI model choice | TradingAgents defaults to paid remote models | Not adopted; local Ollama stays the default |
