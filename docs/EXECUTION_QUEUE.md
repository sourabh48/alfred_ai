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
| 1 | A | FIN-06 — Persisted savings goals and progress workflow | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: INR savings goals with Decimal progress implemented 2026-11-06; owner approved migration budgets 0003; owner check in the app remains |
| 2 | A | FIN-13 — Financial export and correction | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: owner account check PASS 2026-11-06; CI PASS at e8ef8f4 (run 42185812614); a fresh-package check remains |
| 3 | A | LOAN-07 — Loan forecasting and cross-module liabilities | IMPLEMENTED_NOT_ACCEPTED | P2 / L | FIN-07 | B/P; U if affected; MONEY if changed | BLOCKED_DEPENDENCY: FIN-07 |
| 4 | A | LOAN-08 — Broad real-document/lender acceptance | IMPLEMENTED_NOT_ACCEPTED | P2 / L | DOC-02 | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: independent lender/document acceptance corpus |
| 5 | A | INV-02 — Investment PDF imports and corrections | IMPLEMENTED_NOT_ACCEPTED | P2 / L | DOC-02, DOC-04, FIN-14 | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: broader broker/layout/OCR and authorized real-account corpus; bounded receipts in EXECUTION_STATE |
| 6 | A | INV-05 — AMFI/Yahoo market evidence and historical performance | IMPLEMENTED_NOT_ACCEPTED | P2 / L | INV-01 | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: bounded AMFI/Yahoo receipts in EXECUTION_STATE; remaining live terms/quota, authorized provider and real-account evidence absent; full capability unaccepted |
| 7 | A | DOC-09 — Document deletion and retention | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: delete now removes orphaned stored files 2026-11-06 (118 tests PASS); owner check with a synthetic document remains |
| 8 | A | AI-10 — Persistent general conversation history | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_APPROVAL: private-history activation remains off |
| 9 | A | AI-14 — Background learning pipeline | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: eligible consented training and reviewed outcomes |
| 10 | A | AI-15 — Model registry and serving readiness | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: genuine per-model held-out outcomes |
| 11 | A | AI-17 — Autonomous user task execution | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: propose-then-confirm savings-goal actions implemented 2026-11-06 (owner decision); owner check remains |
| 12 | A | AI-18 — Voice assistant | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: offline Speak (Whisper base) and Read aloud (Piper VCTK) implemented 2026-11-06 with owner-approved downloads; owner check remains |
| 13 | A | CAREER-07 — Interview preparation | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: interview preparation panel from the saved job match 2026-11-06 (73 backend + Chrome PASS); owner check remains |
| 14 | A | TRAVEL-20 — Video management and social Travel profile | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: private trip videos implemented 2026-11-06; owner approved and applied migration mobility 0014; owner check in the app remains |
| 15 | A | RUNTIME-11 — Dependency security and reproducible builds | IMPLEMENTED_NOT_ACCEPTED | P1 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: separate-user and clean-PC installs; owner accepted the diskcache residual risk 2026-11-05 |
| 16 | A | RUNTIME-14 — M21 rehearsal, failure injection and rollback acceptance | IMPLEMENTED_NOT_ACCEPTED | P1 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: same-host synthetic M21 rehearsal PASS at 10203a3 on G:; separate PC, normal account and device-loss acceptance open |
| 17 | A | RUNTIME-03 — Windows sign-in and sustained scheduled observation | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: sustained sign-in/scheduler observation |
| 18 | A | RUNTIME-05 — Install/upgrade/uninstall on separate PC | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: independent Windows PC acceptance |
| 19 | A | RUNTIME-06 — Offline startup and local model prerequisites | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: offline independent-host kit on a separate PC; same-host packaged checks 35/35 |
| 20 | A | RUNTIME-15 — Local/LAN hosting and optional Docker stack | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: same-host Compose run PASS at 49d622e; second LAN device, host restart and sustained schedule open |
| 21 | B | FIN-15 — Canonical currency persistence and multi-currency aggregation | PARTIALLY_IMPLEMENTED | P1 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: investments currency slice 2026-11-06 (FX off); owner approved and applied migration investments 0006 (backup F:/ALFRED_BACKUPS/pre-fin15-migration-20261106); owner check, then banking, loans, income, budgets and travel remain |
| 22 | B | FIN-07 — Cash-flow forecasting | PARTIALLY_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: on the owner's data the prior range held in 6 of 9 walk-forward months and income evidence is missing; no accuracy claim |
| 23 | B | FIN-16 — Tax calculations and source-backed eligibility | PARTIALLY_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: tax year 2026-27 rules and the notice-only Budget check implemented; page check on the owner app PASS 2026-11-06; CI PASS at e8ef8f4; reviewed actual tax cases (income unverified) remain |
| 24 | B | INV-04 — Risk classification and recommendations | PARTIALLY_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: assumed-age advice removed and guidance labelled 2026-11-06; reviewed risk-evidence definition and owner check remain |
| 25 | B | INV-06 — Long-term investment planning | PARTIALLY_IMPLEMENTED | P2 / L | FIN-06, FIN-15 | B/P; U if affected; MONEY if changed | BLOCKED_DEPENDENCY: FIN-06, FIN-15 |
| 26 | B | INV-07 — Persistent portfolio alerts | PARTIALLY_IMPLEMENTED | P2 / L | FIN-15 | B/P; U if affected; MONEY if changed | BLOCKED_DEPENDENCY: FIN-15 |
| 27 | B | DOC-07 — AI Q&A over arbitrary financial documents | PARTIALLY_IMPLEMENTED | P2 / L | DOC-06 | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: bounded whole-extraction Q&A accepted; 111 document tests re-run PASS 2026-11-06; OCR, longer originals and an independent quality corpus remain |
| 28 | B | AI-12 — Cross-module personal reasoning | PARTIALLY_IMPLEMENTED | P2 / L | AI-15, AI-16 | B/P; U if affected; MONEY if changed | BLOCKED_DEPENDENCY: AI-15, AI-16 |
| 29 | B | AI-16 — Retrieval/model quality and drift monitoring | PARTIALLY_IMPLEMENTED | P2 / L | AI-15 | B/P; U if affected; MONEY if changed | BLOCKED_DEPENDENCY: AI-15 |
| 30 | B | CAREER-04 — Recruiter email/attachment processing | PARTIALLY_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_APPROVAL: manual recruiter intake accepted; automatic mailbox access needs approved provider access and a reviewed integration |
| 31 | B | CAREER-08 — Predictive career forecasting and timing | PARTIALLY_IMPLEMENTED | P2 / L | CAREER-07, AI-15, AI-16 | B/P; U if affected; MONEY if changed | BLOCKED_DEPENDENCY: CAREER-07, AI-15, AI-16 |
| 32 | B | TRAVEL-04 — Multiple destinations and day-wise itineraries | PARTIALLY_IMPLEMENTED | P2 / L | TRAVEL-03 | B/P; U if affected; MONEY if changed | BLOCKED_APPROVAL: verified inter-stop routing needs an approved routing key (TRAVEL_ORS_API_KEY not configured); manual itineraries accepted |
| 33 | B | TRAVEL-07 — Scenic and truly alternative routes | PARTIALLY_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: bounded alternative-route choice accepted; independently reviewed scenic/legal route evidence absent |
| 34 | B | TRAVEL-08 — Expressway avoidance and motorcycle road restrictions | PARTIALLY_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: owner-reviewed restriction references accepted; independently authenticated route-applicable restrictions absent |
| 35 | B | TRAVEL-09 — Route corridor stops and real detour distance | PARTIALLY_IMPLEMENTED | P2 / L | TRAVEL-07 | B/P; U if affected; MONEY if changed | BLOCKED_APPROVAL: straight-line stop distance labelled 2026-11-06; road-network detours need an approved routing key |
| 36 | B | TRAVEL-15 — Live permits and road closure confirmation | PARTIALLY_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: no verified live permit or closure service; dated references shown stale with UNKNOWN confidence |
| 37 | B | BIKE-03 — Maintenance prediction and condition tracking | PARTIALLY_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EVIDENCE: part windows and evidence score labelled 2026-11-06; prediction quality needs real logged service outcomes |
| 38 | B | BIKE-05 — Spare parts and service recommendations | PARTIALLY_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: cost figures labelled estimates 2026-11-06; authoritative part compatibility and live prices need a manufacturer or dealer source |
| 39 | B | OPENAI-02 — Model compatibility and current price review | PARTIALLY_IMPLEMENTED | P1 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_APPROVAL: OpenAI stays off; pinned model retires 2027-01-14; replacement choice waits for approval to enable |
| 40 | B | SYNC-02 — Non-AWS encrypted object adapter (AWS withdrawn) | PARTIALLY_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: Cloudflare R2 encrypted adapter built 2026-11-06, tested against a synthetic signed server only; owner creates a free R2 bucket and bucket-scoped token in config/local.env, then a live sync check |
| 41 | B | RUNTIME-12 — GitHub CI and branch/source protection | PARTIALLY_IMPLEMENTED | P1 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: CI runs on each master push and is read via the public API; branch protection needs signed-in GitHub access |
| 42 | C | FIN-17 — Credit bureau reports and official score access | BLOCKED_EXTERNAL | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: see canonical decision |
| 43 | C | TRAVEL-11 — Hotel live availability | BLOCKED_EXTERNAL | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: see canonical decision |
| 44 | C | TRAVEL-12 — Flight live availability | BLOCKED_EXTERNAL | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: see canonical decision |
| 45 | C | TRAVEL-13 — Train live seat/fare/waitlist inventory | BLOCKED_EXTERNAL | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_EXTERNAL: see canonical decision |
| 46 | C | OPENAI-07 — Real paid-provider acceptance | BLOCKED_APPROVAL | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_APPROVAL: see canonical decision |
| 47 | C | SYNC-09 — Portable keys and independent multi-device/device-loss recovery | BLOCKED_APPROVAL | P1 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_APPROVAL: see canonical decision |
| 48 | C | SYNC-10 — Real provider activation, costs and IAM acceptance | BLOCKED_APPROVAL | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_APPROVAL: see canonical decision |
| 49 | C | RUNTIME-08 — Off-device/device-loss disaster recovery | BLOCKED_APPROVAL | P1 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_APPROVAL: see canonical decision |
| 50 | C | RUNTIME-16 — Real-account and manual accessibility acceptance | BLOCKED_APPROVAL | P1 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_APPROVAL: see canonical decision |
| 51 | D | TRAVEL-14 — Bus live inventory | NOT_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_APPROVAL: owner left the choice to Claude 2026-11-06; kept deferred because no free official bus inventory source exists and live booking stays off; links to verified bus websites remain |
| 52 | D | TRAVEL-18 — Google Maps API integration and offline map packages | NOT_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_APPROVAL: Google configuration/credentials and offline map scope |
| 53 | D | SYNC-11 — Full application/cloud backup | NOT_IMPLEMENTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | READY_FOR_SCOPED_INSPECTION |
| 54 | A | COUNCIL-01 — Multiple ML inference roles and registry routing | IMPLEMENTED_NOT_ACCEPTED | P2 / L | Scoped source/evidence inspection | B/P; U if affected; MONEY if changed | BLOCKED_APPROVAL: owner agreed to local auto-training 2026-11-06; it takes effect when the owner presses Approve Auto-Training in their app, then held-out outcomes follow |
| 55 | B | COUNCIL-02 — Planning/coding/review/security multi-agent application | PARTIALLY_IMPLEMENTED | P2 / L | COUNCIL-01 | B/P; U if affected; MONEY if changed | BLOCKED_DEPENDENCY: COUNCIL-01 |
| 56 | B | COUNCIL-04 — Persistent tasks, conflicts and usage-limit recovery | PARTIALLY_IMPLEMENTED | P2 / L | COUNCIL-02 | B/P; U if affected; MONEY if changed | BLOCKED_DEPENDENCY: COUNCIL-02 |
| 57 | B | COUNCIL-05 — AI development budget and human Git approval | PARTIALLY_IMPLEMENTED | P2 / L | COUNCIL-04 | B/P; U if affected; MONEY if changed | BLOCKED_DEPENDENCY: COUNCIL-04 |
| 58 | D | COUNCIL-03 — Experimental self-improvement engine | NOT_IMPLEMENTED | P1 / L | COUNCIL-05 | B/P; U if affected; MONEY if changed | BLOCKED_DEPENDENCY: COUNCIL-05 |

**Next eligible for `next` or active `sprint`: SYNC-11.**

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
| OPENAI-01 | Responses API request/response adapter | COMPLETE_VERIFIED |
| OPENAI-03 | Encrypted key provisioning and owner consent | COMPLETE_VERIFIED |
| OPENAI-04 | Privacy classification and sensitive-data filtering | COMPLETE_VERIFIED |
| OPENAI-05 | Daily token and monetary spending caps | COMPLETE_VERIFIED |
| OPENAI-06 | Fallback, timeout, redacted diagnostics and UI | COMPLETE_VERIFIED |
| SYNC-01 | Provider-neutral mock sync protocol | COMPLETE_VERIFIED |
| SYNC-03 | Startup/periodic/bounded shutdown sync | COMPLETE_VERIFIED |
| SYNC-04 | Offline durable retry and interrupted upload recovery | COMPLETE_VERIFIED |
| SYNC-05 | Authenticated versioned encrypted snapshots | COMPLETE_VERIFIED |
| SYNC-06 | Concurrent conflict detection and ownership | COMPLETE_VERIFIED |
| SYNC-07 | Tombstones, revocation and remote pruning | COMPLETE_VERIFIED |
| SYNC-08 | Trusted high-water checkpoint | COMPLETE_VERIFIED |
| RUNTIME-01 | Native launcher, tray, worker and scheduler | COMPLETE_VERIFIED |
| RUNTIME-09 | Filesystem protection of private DB/config | COMPLETE_VERIFIED |
| RUNTIME-13 | M20 automated source/finance/privacy/backup gates | COMPLETE_VERIFIED |
| RUNTIME-02 | Restart persistence and local data isolation | COMPLETE_VERIFIED |
| RUNTIME-04 | Portable package and static assets | COMPLETE_VERIFIED |
| RUNTIME-07 | Local backup, encrypted restore and rollback | COMPLETE_VERIFIED |
| RUNTIME-10 | Session/CSRF/auth/upload/HTTP/diagnostic safeguards | COMPLETE_VERIFIED |

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
