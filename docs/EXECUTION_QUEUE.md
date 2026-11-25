# ALFRED execution queue

Generated from canonical status rows and the requirements dependency matrix. Regenerate with
`python scripts/project_execution.py --write`; check without changes using `--check`.
Use the configured SDK. No network, provider activation or feature execution occurs.

**Selection:** `next` selects one task; explicit `sprint` continuously selects eligible scopes.
`continue` resumes EXECUTION_STATE; `status` is read-only. Finish or explicitly defer
local work first; CI_PENDING may coexist with independent IMPLEMENTING work.
Phase A → B → C → D; module-by-module inside each phase. Skip an actually blocked
item with its exact reason; do not call its acceptance complete. Later-phase
prerequisite exceptions need a recorded reason. Accepted baseline rows are never requeued.
Owner decision 2026-11-05: COUNCIL tasks are queued after all other modules.

Effort bands are preliminary scope estimates, not measured durations: S = bounded existing path;
M = multi-path acceptance; L = broader integration, outcomes or external environment.
Value P0/P1/P2/P3 is the recorded tracker priority, not an invented confidence score.
B = backend/API; U = actual affected Chrome/accessibility; P = privacy/ownership/CSRF;
MONEY = Decimal/reconciliation if monetary behavior changes. Add native/package/live
gates where the canonical scope requires them. Full criteria/limitations/evidence remain
in [PROJECT_STATUS](PROJECT_STATUS.md); product intent is in [requirements](ALFRED_2_0_REQUIREMENTS.md).

| Order | Phase | Task / module | Status | Value / effort | Prerequisites | Required acceptance | Readiness / blocker |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | A | FIN-15 — Canonical currency persistence and multi-currency aggregation | IMPLEMENTED_NOT_ACCEPTED | P1 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: all six FIN-15 domains implemented and every currency migration (through users 0006) applied to the owner runtime; calculations never use FX, display-only approximate figures in the viewer currency added 2026-11-07 (ECB via Frankfurter); owner checks in the app pending |
| 2 | A | FIN-06 — Persisted savings goals and progress workflow | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: INR savings goals with Decimal progress implemented 2026-11-06; owner approved migration budgets 0003; owner check in the app remains |
| 3 | A | LOAN-07 — Loan forecasting and cross-module liabilities | IMPLEMENTED_NOT_ACCEPTED | P2 / L | FIN-07 | B/P; U if affected; MONEY if changed | BLOCKED_DEPENDENCY: FIN-07 |
| 4 | A | LOAN-08 — Broad real-document/lender acceptance | IMPLEMENTED_NOT_ACCEPTED | P2 / L | DOC-02 | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: six dummy lender layouts read field by field after label fixes 2026-11-14 (synthetic); real lender documents remain |
| 5 | A | INV-02 — Investment PDF imports and corrections | IMPLEMENTED_NOT_ACCEPTED | P2 / L | DOC-02, DOC-04, FIN-14 | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: dummy Groww, CAMS and Kite tables with lakh grouping read and reconciled 2026-11-14 (synthetic); OCR and real-account corpus remain |
| 6 | A | INV-04 — Risk classification and recommendations | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: assumed-age advice removed 2026-11-06; beginner Start-here picks and Hold/Review/Sell for owned AMFI funds added 2026-11-14 (synthetic tests); owner check remains |
| 7 | A | INV-05 — AMFI/Yahoo market evidence and historical performance | IMPLEMENTED_NOT_ACCEPTED | P2 / L | INV-01 | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: fund holdings with an AMFI code and units revalue twice daily from AMFI NAV and Home reports the change (2026-11-14, synthetic tests); owner check with a real fund remains |
| 8 | A | INV-06 — Long-term investment planning | IMPLEMENTED_NOT_ACCEPTED | P2 / L | FIN-06, FIN-15 | B/P; U if affected; MONEY if changed | BLOCKED_DEPENDENCY: FIN-06, FIN-15 |
| 9 | A | INV-07 — Persistent portfolio alerts | IMPLEMENTED_NOT_ACCEPTED | P2 / L | FIN-15 | B/P; U if affected; MONEY if changed | BLOCKED_DEPENDENCY: FIN-15 |
| 10 | A | DOC-09 — Document deletion and retention | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: delete removes orphaned stored files 2026-11-06 and now confirms Deleted 2026-11-14; owner check with a synthetic document remains |
| 11 | A | AI-10 — Persistent general conversation history | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: chats kept until deleted and on by default since 2026-11-14 (owner decision); owner check of the chat list remains |
| 12 | A | AI-14 — Background learning pipeline | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: eligible consented training and reviewed outcomes |
| 13 | A | AI-15 — Model registry and serving readiness | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: genuine per-model held-out outcomes |
| 14 | A | AI-17 — Autonomous user task execution | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: propose-then-confirm savings-goal actions 2026-11-06; six task bots propose daily on Huey and act only on Confirm 2026-11-14 (synthetic, Chrome PASS); owner check remains |
| 15 | A | AI-18 — Voice assistant | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: offline Speak (Whisper) and Read aloud (Piper) 2026-11-06; stops on a pause, reads long answers whole and hands-free conversation 2026-11-14 (Chrome PASS); owner check remains |
| 16 | A | CAREER-04 — Recruiter email/attachment processing | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_APPROVAL: manual recruiter intake accepted; automatic mailbox access needs approved provider access and a reviewed integration |
| 17 | A | CAREER-07 — Interview preparation | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: interview preparation panel 2026-11-06; one-question-at-a-time mock interview with offline voice and local-AI comments 2026-11-14 (Chrome PASS); owner check remains |
| 18 | A | TRAVEL-04 — Multiple destinations and day-wise itineraries | IMPLEMENTED_NOT_ACCEPTED | P2 / L | TRAVEL-03 | B/P; U if affected; MONEY if changed | BLOCKED_APPROVAL: Google Routes is the only router since 2026-11-14 (two-wheeler, distance and time, no line drawn); verified inter-stop routing needs the owner Google key and a real-trip check; manual itineraries accepted |
| 19 | A | TRAVEL-09 — Route corridor stops and real detour distance | IMPLEMENTED_NOT_ACCEPTED | P2 / L | TRAVEL-07 | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: road detours for the top three sights from one Google Routes call each through the stop, 2026-11-14 (synthetic tests, Chrome PASS); a live check with the owner Google key and a real trip remains |
| 20 | A | TRAVEL-18 — Google Maps API integration and offline map packages | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: Google maps and places and offline country maps (OpenStreetMap via Protomaps, size shown before download) built 2026-11-13; owner live check with the Google key and a country download remain |
| 21 | A | TRAVEL-20 — Video management and social Travel profile | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: private trip videos implemented 2026-11-06; owner approved and applied migration mobility 0014; owner check in the app remains |
| 22 | A | OPENAI-02 — Model compatibility and current price review | IMPLEMENTED_NOT_ACCEPTED | P1 / M | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | OWNER_ACTION: OpenAI dropped 2026-11-19; Gemini with each person’s own free key; confirm the configured model and free-tier limits with a live key |
| 23 | A | OPENAI-04 — Privacy classification and sensitive-data filtering | IMPLEMENTED_NOT_ACCEPTED | P2 / M | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | READY_FOR_SCOPED_INSPECTION |
| 24 | A | OPENAI-05 — Daily token and monetary spending caps | IMPLEMENTED_NOT_ACCEPTED | P2 / M | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | READY_FOR_SCOPED_INSPECTION |
| 25 | A | OPENAI-06 — Fallback, timeout, redacted diagnostics and UI | IMPLEMENTED_NOT_ACCEPTED | P2 / M | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | READY_FOR_SCOPED_INSPECTION |
| 26 | A | SYNC-09 — Portable keys and independent multi-device/device-loss recovery | IMPLEMENTED_NOT_ACCEPTED | P1 / M | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | READY_FOR_SCOPED_INSPECTION |
| 27 | A | RUNTIME-08 — Off-device/device-loss disaster recovery | IMPLEMENTED_NOT_ACCEPTED | P1 / M | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | READY_FOR_SCOPED_INSPECTION |
| 28 | A | RUNTIME-14 — M21 rehearsal, failure injection and rollback acceptance | IMPLEMENTED_NOT_ACCEPTED | P1 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: same-host synthetic M21 rehearsal PASS at 10203a3 on G:; owner chose the encrypted R2 cloud backup (SYNC-11) as the off-device copy on 2026-11-14, not yet configured (owner R2 bucket, keys, portable key); separate PC, normal account and device-loss acceptance open |
| 29 | A | RUNTIME-16 — Real-account and manual accessibility acceptance | IMPLEMENTED_NOT_ACCEPTED | P1 / M | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | READY_FOR_SCOPED_INSPECTION |
| 30 | A | RUNTIME-03 — Windows sign-in and sustained scheduled observation | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: startup never registered on the owner PC (source checkout had no packaged exe); script now falls back to the checkout pythonw 2026-11-14; real sign-in observation remains |
| 31 | B | FIN-07 — Cash-flow forecasting | PARTIALLY_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: on the owner's data the prior range held in 6 of 9 walk-forward months and income evidence is missing; no accuracy claim |
| 32 | B | FIN-16 — Tax calculations and source-backed eligibility | PARTIALLY_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: tax year 2026-27 rules and the notice-only Budget check implemented; page check on the owner app PASS 2026-11-06; CI PASS at e8ef8f4; reviewed actual tax cases (income unverified) remain |
| 33 | B | DOC-07 — AI Q&A over arbitrary financial documents | PARTIALLY_IMPLEMENTED | P2 / L | DOC-06 | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: bounded whole-extraction Q&A accepted; 111 document tests re-run PASS 2026-11-06; OCR, longer originals and an independent quality corpus remain |
| 34 | B | AI-12 — Cross-module personal reasoning | PARTIALLY_IMPLEMENTED | P2 / L | AI-15, AI-16 | B/P; U if affected; MONEY if changed | BLOCKED_DEPENDENCY: AI-15, AI-16 |
| 35 | B | AI-16 — Retrieval/model quality and drift monitoring | PARTIALLY_IMPLEMENTED | P2 / L | AI-15 | B/P; U if affected; MONEY if changed | BLOCKED_DEPENDENCY: AI-15 |
| 36 | B | CAREER-08 — Predictive career forecasting and timing | PARTIALLY_IMPLEMENTED | P2 / L | CAREER-07, AI-15, AI-16 | B/P; U if affected; MONEY if changed | BLOCKED_DEPENDENCY: CAREER-07, AI-15, AI-16 |
| 37 | B | TRAVEL-07 — Scenic and truly alternative routes | PARTIALLY_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: bounded alternative-route choice accepted; independently reviewed scenic/legal route evidence absent |
| 38 | B | TRAVEL-08 — Expressway avoidance and motorcycle road restrictions | PARTIALLY_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: owner-reviewed restriction references accepted; independently authenticated route-applicable restrictions absent |
| 39 | B | TRAVEL-15 — Live permits and road closure confirmation | PARTIALLY_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: no verified live permit or closure service; dated references shown stale with UNKNOWN confidence |
| 40 | B | BIKE-03 — Maintenance prediction and condition tracking | PARTIALLY_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: part windows and evidence score labelled 2026-11-06; prediction quality needs real logged service outcomes |
| 41 | B | BIKE-05 — Spare parts and service recommendations | PARTIALLY_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: cost figures labelled estimates 2026-11-06; authoritative part compatibility and live prices need a manufacturer or dealer source |
| 42 | B | RUNTIME-12 — GitHub CI and branch/source protection | PARTIALLY_IMPLEMENTED | P1 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_APPROVAL: CI runs on each master push; owner-approved ruleset 27070437 (2026-11-12) blocks master deletion and force push; required status checks are unset because finished work is pushed straight to master and need an owner decision |
| 43 | C | TRAVEL-11 — Hotel live availability | BLOCKED_EXTERNAL | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: see canonical decision |
| 44 | C | TRAVEL-12 — Flight live availability | BLOCKED_EXTERNAL | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: see canonical decision |
| 45 | C | TRAVEL-13 — Train live seat/fare/waitlist inventory | BLOCKED_EXTERNAL | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: see canonical decision |
| 46 | C | SYNC-02 — Non-AWS encrypted object adapter (AWS withdrawn) | BLOCKED_EXTERNAL | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: see canonical decision |
| 47 | C | SYNC-10 — Real provider activation, costs and IAM acceptance | BLOCKED_EXTERNAL | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: see canonical decision |
| 48 | C | SYNC-11 — Full application/cloud backup | BLOCKED_EXTERNAL | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: see canonical decision |
| 49 | D | TRAVEL-14 — Bus live inventory | NOT_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_APPROVAL: owner left the choice to Claude 2026-11-06; kept deferred because no free official bus inventory source exists and live booking stays off; links to verified bus websites remain |
| 50 | A | COUNCIL-03 — Experimental self-improvement engine | IMPLEMENTED_NOT_ACCEPTED | P1 / L | COUNCIL-05 | B/P; U if affected; MONEY if changed | BLOCKED_DEPENDENCY: COUNCIL-05 |
| 51 | A | COUNCIL-01 — Multiple ML inference roles and registry routing | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_APPROVAL: owner agreed to local auto-training 2026-11-06; it takes effect when the owner presses Approve Auto-Training in their app, then held-out outcomes follow |
| 52 | B | COUNCIL-02 — Planning/coding/review/security multi-agent application | PARTIALLY_IMPLEMENTED | P2 / L | COUNCIL-01 | B/P; U if affected; MONEY if changed | BLOCKED_DEPENDENCY: COUNCIL-01 |
| 53 | B | COUNCIL-04 — Persistent tasks, conflicts and usage-limit recovery | PARTIALLY_IMPLEMENTED | P2 / L | COUNCIL-02 | B/P; U if affected; MONEY if changed | BLOCKED_DEPENDENCY: COUNCIL-02 |
| 54 | B | COUNCIL-05 — AI development budget and human Git approval | PARTIALLY_IMPLEMENTED | P2 / L | COUNCIL-04 | B/P; U if affected; MONEY if changed | BLOCKED_DEPENDENCY: COUNCIL-04 |

**Next eligible for `next` or active `sprint`: OPENAI-04.**

## Accepted baseline — excluded from execution

| ID | Capability | Status |
| --- | --- | --- |
| FIN-14 | Money storage across every domain | COMPLETE_VERIFIED |
| FIN-01 | Dashboard, income, expenses and fixed obligations | COMPLETE_VERIFIED |
| FIN-02 | Disposable cash flow and savings capacity | COMPLETE_VERIFIED |
| FIN-03 | Net worth, liquid cash and account snapshots | COMPLETE_VERIFIED |
| FIN-04 | Financial health and historical spending indicators | COMPLETE_VERIFIED |
| FIN-05 | Budget management, utilization and affordability | COMPLETE_VERIFIED |
| FIN-08 | Expense categorization and merchant correction learning | COMPLETE_VERIFIED |
| FIN-09 | Bank accounts and statement imports | COMPLETE_VERIFIED |
| FIN-10 | Account-scoped duplicate detection and fingerprints | COMPLETE_VERIFIED |
| FIN-11 | Transfer legs and cross-account financial relationships | COMPLETE_VERIFIED |
| FIN-12 | Financial reconciliation | COMPLETE_VERIFIED |
| FIN-13 | Financial export and correction | COMPLETE_VERIFIED |
| LOAN-01 | EMI, schedules, outstanding and repayment metrics | COMPLETE_VERIFIED |
| LOAN-02 | Loan PDF import and repayment statement parsing | COMPLETE_VERIFIED |
| LOAN-03 | Loan payment detection and review | COMPLETE_VERIFIED |
| LOAN-04 | Foreclosure and prepayment scenarios | COMPLETE_VERIFIED |
| LOAN-05 | Closure extraction, verification and evidence status | COMPLETE_VERIFIED |
| LOAN-06 | Multi-loan aggregation and consolidation | COMPLETE_VERIFIED |
| INV-01 | Portfolio register, valuation and allocation | COMPLETE_VERIFIED |
| INV-03 | Returns and planning projections | COMPLETE_VERIFIED |
| INV-08 | Investment contribution to net worth | COMPLETE_VERIFIED |
| DOC-01 | Bounded PDF/image upload and OCR | COMPLETE_VERIFIED |
| DOC-02 | Bank/loan/investment extraction and classification | COMPLETE_VERIFIED |
| DOC-03 | Confidence, metadata and provenance | COMPLETE_VERIFIED |
| DOC-04 | Field corrections, visual review and retry | COMPLETE_VERIFIED |
| DOC-05 | Document deduplication and source lineage | COMPLETE_VERIFIED |
| DOC-06 | General searchable document knowledge | COMPLETE_VERIFIED |
| DOC-08 | Loan closure document Q&A and abstention | COMPLETE_VERIFIED |
| AI-01 | Ollama local inference | COMPLETE_VERIFIED |
| AI-02 | Ollama embeddings and similarity retrieval | COMPLETE_VERIFIED |
| AI-03 | Persistent encrypted memory/index/journal | COMPLETE_VERIFIED |
| AI-04 | Owner isolation and memory access | COMPLETE_VERIFIED |
| AI-05 | Verification, confidence and provenance separation | COMPLETE_VERIFIED |
| AI-06 | Deduplication, relevance and insufficient-evidence abstention | COMPLETE_VERIFIED |
| AI-07 | Memory corrections, feedback and conflict safety | COMPLETE_VERIFIED |
| AI-08 | Delete/reset/retention and resurrection protection | COMPLETE_VERIFIED |
| AI-09 | Conversation UI, provider status and evidence cards | COMPLETE_VERIFIED |
| AI-11 | Financial grounding and numeric/currency suppression | COMPLETE_VERIFIED |
| AI-13 | Offline/model-outage behavior and consent fallback | COMPLETE_VERIFIED |
| CAREER-01 | Resume upload, extraction and review | COMPLETE_VERIFIED |
| CAREER-02 | Skill-gap and recruiter/JD matching | COMPLETE_VERIFIED |
| CAREER-03 | Job discovery and recommendations | COMPLETE_VERIFIED |
| CAREER-05 | Application and opportunity outcome tracking | COMPLETE_VERIFIED |
| CAREER-06 | Salary/location evidence and progression | COMPLETE_VERIFIED |
| TRAVEL-22 | Provider telemetry retention and selective invalidation | COMPLETE_VERIFIED |
| TRAVEL-01 | Conversational discovery and saved preferences | COMPLETE_VERIFIED |
| TRAVEL-02 | Source-backed new destinations and novelty | COMPLETE_VERIFIED |
| TRAVEL-03 | Large candidate pools, show-more batches and comparison | COMPLETE_VERIFIED |
| TRAVEL-05 | Budget summaries and estimates | COMPLETE_VERIFIED |
| TRAVEL-06 | Motorbike/pillion and vehicle-aware planning | COMPLETE_VERIFIED |
| TRAVEL-10 | Camping and attraction discovery | COMPLETE_VERIFIED |
| TRAVEL-16 | Weather, horizons and replanning | COMPLETE_VERIFIED |
| TRAVEL-17 | GeoJSON mapping and optional tiles | COMPLETE_VERIFIED |
| TRAVEL-19 | Photos, GPS/date inference and trip galleries | COMPLETE_VERIFIED |
| TRAVEL-21 | Freshness, cache, quotas and safe external HTTP | COMPLETE_VERIFIED |
| TRAVEL-23 | API budgets and provider terms compliance | COMPLETE_VERIFIED |
| FAMILY-01 | Family relationships and invitation lifecycle | COMPLETE_VERIFIED |
| FAMILY-02 | Explicit financial opt-in and revocation | COMPLETE_VERIFIED |
| FAMILY-03 | Invitation throttling and concurrent acceptance | COMPLETE_VERIFIED |
| FAMILY-04 | Cross-account isolation | COMPLETE_VERIFIED |
| FAMILY-05 | Relationship alignment and family growth | COMPLETE_VERIFIED |
| FAMILY-06 | Behavioral signals and personalization | COMPLETE_VERIFIED |
| FAMILY-07 | Financial/health/relocation risk intelligence | COMPLETE_VERIFIED |
| BIKE-01 | Vehicle profiles and Hunter 350 catalog support | COMPLETE_VERIFIED |
| BIKE-02 | Service records, fuel and costs | COMPLETE_VERIFIED |
| BIKE-04 | Insurance/service documents and invoice review | COMPLETE_VERIFIED |
| BIKE-06 | Travel integration and vehicle net-worth relationship | COMPLETE_VERIFIED |
| OPENAI-01 | Gemini generateContent request/response adapter | COMPLETE_VERIFIED |
| OPENAI-03 | Encrypted key provisioning and owner consent | COMPLETE_VERIFIED |
| OPENAI-07 | Real provider acceptance with the owner's free Gemini key | COMPLETE_VERIFIED |
| SYNC-01 | Provider-neutral mock sync protocol | COMPLETE_VERIFIED |
| SYNC-03 | Startup/periodic/bounded shutdown sync | COMPLETE_VERIFIED |
| SYNC-04 | Offline durable retry and interrupted upload recovery | COMPLETE_VERIFIED |
| SYNC-05 | Authenticated versioned encrypted snapshots | COMPLETE_VERIFIED |
| SYNC-06 | Concurrent conflict detection and ownership | COMPLETE_VERIFIED |
| SYNC-07 | Tombstones, revocation and remote pruning | COMPLETE_VERIFIED |
| SYNC-08 | Trusted high-water checkpoint | COMPLETE_VERIFIED |
| RUNTIME-01 | Native launcher, tray, worker and scheduler | COMPLETE_VERIFIED |
| RUNTIME-09 | Filesystem protection of private DB/config | COMPLETE_VERIFIED |
| RUNTIME-11 | Dependency security and reproducible builds | COMPLETE_VERIFIED |
| RUNTIME-13 | M20 automated source/finance/privacy/backup gates | COMPLETE_VERIFIED |
| RUNTIME-02 | Restart persistence and local data isolation | COMPLETE_VERIFIED |
| RUNTIME-04 | Portable package and static assets | COMPLETE_VERIFIED |
| RUNTIME-05 | Install/upgrade/uninstall on separate PC | COMPLETE_VERIFIED |
| RUNTIME-06 | Offline startup and local model prerequisites | COMPLETE_VERIFIED |
| RUNTIME-07 | Local backup, encrypted restore and rollback | COMPLETE_VERIFIED |
| RUNTIME-10 | Session/CSRF/auth/upload/HTTP/diagnostic safeguards | COMPLETE_VERIFIED |
| RUNTIME-15 | Local/LAN hosting and optional Docker stack | COMPLETE_VERIFIED |

## Owner-descoped — excluded from execution

| ID | Capability | Status |
| --- | --- | --- |
| FIN-17 | Credit bureau reports and official score access | OWNER_DESCOPED |

## Separate 2.0 extensions — after authorized baseline closure

Inspect existing reuse/gaps before implementing each of the 13 defined stories.
Dependencies refer to original IDs; shared look-through is counted once, not per consumer.

| ID | Scope | Prerequisites | Acceptance | Status | Evidence |
| --- | --- | --- | --- | --- | --- |
| CAREER2-001 | Compare owned resume versions and invalidate stale JD decisions against exact version deltas | CAREER-01, CAREER-02 | Version/citation/UI/correction/ownership workflows | UNACCEPTED | No full-story acceptance recorded. |
| CAREER2-002 | Recruiter response drafts with attachment manifest and explicit send confirmation | CAREER-04, CAREER-05 | Review/stale attachment/retry tests; zero implicit send/disclosure | UNACCEPTED | No full-story acceptance recorded. |
| TRAVEL2-001 | Desktop drag-and-drop day editor retaining user edits and undo/revision safety | TRAVEL-04 | Real pointer/keyboard edit, reordering and save/reopen | UNACCEPTED | No full-story acceptance recorded. |
| TRAVEL2-002 | Private trip booking/document organizer | TRAVEL-04, DOC-06 | Owned upload/link/expiry/deletion flows; no booking inference | UNACCEPTED | No full-story acceptance recorded. |
| TRAVEL2-003 | Trip packing checklist and durable opt-in reminders | TRAVEL-04 | Idempotent lifecycle/timezone/offline and UI checks | UNACCEPTED | No full-story acceptance recorded. |
| TRAVEL2-004 | Source-preserving private PDF, GPX and ICS trip exports | TRAVEL-04, TRAVEL-17 | Validated files, scope/expiry/timezone and explicit export confirmation | UNACCEPTED | No full-story acceptance recorded. |
| TRAVEL2-005 | Canonical reserve/obligation/goal-aware trip affordability | FIN-05, FIN-06, FIN-07, FIN-15, TRAVEL-05 | Decimal reconciliation and explainable read-only trade-offs; approvals first | UNACCEPTED | No full-story acceptance recorded. |
| INVEST2-001 | Bounded analyst/bull/bear/valuation/risk research packet with independent challenge | INV-04, AI-15, AI-16 | Evidence/uncertainty/portfolio scope tests; no automatic order | UNACCEPTED | No full-story acceptance recorded. |
| INVEST2-002 | Watchlist thesis versions and research decisions distinct from owned holdings | INV-01, INV-07 | Identity/freshness/stale-thesis and no-holding-write workflows | UNACCEPTED | No full-story acceptance recorded. |
| WEALTH2-001 | Shared ETF/fund look-through and overlap by company/sector/country/currency, including opaque exposure | INV-01, INV-04, FIN-15 | Source-dated weights/completeness; no invented pricing/FX; shared Investment use | UNACCEPTED | No full-story acceptance recorded. |
| WEALTH2-002 | Fingerprinted cross-module AI proposal/confirmation cards | FIN-12, DOC-06, AI-12 | Dependency change rejects stale proposals; approved confirmation only | UNACCEPTED | No full-story acceptance recorded. |
| WEALTH2-003 | Read-only institution/asset reconciliation using strictly post-snapshot events, dividends and recurring-plan provenance | FIN-03, FIN-11, FIN-12, INV-01, FIN-15 | Double-count/null/transfer/cutoff tests; no historical rewrite | UNACCEPTED | No full-story acceptance recorded. |
| WEALTH2-004 | Separate public research analyst and confidential personal-context challenger packets | AI-04, AI-12, DOC-06 | Adversarial leakage/ownership/role/source tests; no implicit cloud disclosure | UNACCEPTED | No full-story acceptance recorded. |
