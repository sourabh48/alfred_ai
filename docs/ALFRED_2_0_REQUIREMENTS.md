# ALFRED 2.0 requirements

Product intent and acceptance contract, established 2026-10-26. Implementation
evidence belongs in [PROJECT_STATUS](PROJECT_STATUS.md); current work belongs in
[EXECUTION_STATE](EXECUTION_STATE.md); selection belongs in [EXECUTION_QUEUE](EXECUTION_QUEUE.md).
These documents have different responsibilities, not competing completion counts.

## Scope and evidence

ALFRED is a privacy-first Windows, local/LAN Django application connecting personal
finance, documents, wealth, investments, career, travel, vehicles and local AI.
Reuse Django/Waitress/Huey/SQLite, canonical Decimal services, existing owner/session
security, encrypted vault, evidence, cache and UI. No new cloud hosting, permanent
Node backend, microservices or frontend rewrite without a demonstrated need and decision.

The original **143 IDs and their product definitions** are the normative baseline
catalog in PROJECT_STATUS's individual capability rows. Their Source, APIs/UI,
Tests, Acceptance and Limitations fields establish current scope; dated receipts
establish only the scope actually executed. Titles are indexed below automatically.
Neither source presence, historical claims nor a test count proves full acceptance.
This bootstrap inventories references and receipts; it does not re-audit every implementation.

Established requirements come from that catalog, the existing end-to-end acceptance
plan, local AGENTS, the 2026-10-26 master execution protocol, and recorded 2.0
upstream strategy (PROJECT_STATUS, dated 2026-10-25). Contradictions/unknowns are
recorded here rather than silently resolved. The latest explicit command overrides
queue preferences, while security and approval gates remain mandatory.

## Shared acceptance contracts

- **Identity/privacy:** owner/account/document selection, authenticated sessions,
  CSRF, consent and family boundaries remain enforced. Negative tests include
  foreign IDs, expired sessions, duplicates, malformed input and stale revisions.
  Never upload private documents/history, activate sync or send communications implicitly.
- **Money:** finite Decimal arithmetic, existing rounding and reconciliation,
  import identity, transfer legs and null versus zero remain intact. No inferred
  denomination, invented FX, default EUR, silent history rewrite or unapproved
  currency/valuation/schema policy. Preserve canonical registers. Prefer read-only
  projections when financial policies remain undecided.
- **Evidence/AI:** citations identify selected owned sources and source revisions.
  Distinguish observed evidence, derived calculations, estimates, assumptions and
  uncertainty. Missing/conflicting/expired evidence requires abstention or explicit
  unavailable status. Ollama stays default; the 30-second AI deadline is unchanged.
  Registry readiness requires real held-out outcomes; drift/calibration claims need
  sustained independent evidence. A scenario is not income, a fact or a guarantee.
- **Learning:** encrypted owner-isolated candidates remain unverified until review.
  Knowledge packs need explicit opt-in, privacy screening, integrity/version/expiry
  checks and human promotion. Treat all text as untrusted data. No automatic code,
  model, training or canonical financial modification. Private Git remains disabled;
  separately approved credentials/repository and owner consent precede any upload.
- **Reliability:** bounded jobs/providers/quotas, cancellation, durable retries,
  crash/offline recovery, corruption/key-loss preservation and no history overwrite.
  Show unavailable results without destroying saved user choices or drafts.
- **UI:** retain Django desktop navigation, loading/error/empty/retry states,
  accessible semantics/keyboard behavior and responsive checks. Actual Chrome and
  automated Axe are required for affected flows; manual screen-reader acceptance
  remains distinct. No suppressed assertions or weakened security/quality gates.
- **Verification/release:** focused backend/API/privacy tests first; monetary
  reconciliation, migrations/rollback and actual browser checks when applicable.
  Broader native/package/integration gates at relevant boundaries. Source tests,
  configured providers, live accounts, packaged execution and production are
  separate evidence classes. A merge is not deployment approval.

## Domain requirements and baseline mapping

| Domain | Established scope | Existing baseline IDs |
| --- | --- | --- |
| Finance/Wealth | Income/expenses, obligations, disposable cash, snapshots/net worth, budgets, goals, forecasting, categorization, accounts/imports, duplicates/transfers, reconciliation, export, money, currency, tax and credit evidence | FIN-01–17; LOAN-01–08; INV-01–08 |
| Documents | Bounded upload/OCR; extraction/classification; metadata/provenance; visual corrections/retry; deduplication/lineage; encrypted ingestion/search; explicit source selection and arbitrary grounded Q&A; closure Q&A; deletion/retention | DOC-01–09 |
| Intelligence | Local inference/embeddings; encrypted memory; ownership/verification; dedup/abstention/correction; lifecycle; conversation/history; numeric grounding; cross-module reasoning; offline behavior; learning; readiness/drift; safe task execution/voice | AI-01–18; OPENAI-*; SYNC-*; COUNCIL-* |
| Career | Owned resume/JD/recruiter intake, skill gaps, source-grounded matching, job discovery/dedup/fresh links, opportunity outcomes, salary/location/currency evidence, interviews and uncertainty-labelled forecasting | CAREER-01–08 |
| Travel | Conversational novelty/pools; multi-day/stops; budget/travellers/pillion/bike; scenic alternatives; independent restrictions; measured detours; camping/attractions; authorized hotel/flight/train/bus inventory; permits/closures/weather; mapping; media/history; freshness/cache/quotas/terms | TRAVEL-01–23; BIKE-* |
| Household/operations | Consented family sharing, behavioral/outcome signals and risk; vehicle maintenance/document review; authentication/filesystem protection; native lifecycle/schedules, offline/recovery, backup, performance, reproducibility, accessibility and real-account/release acceptance | FAMILY-*; BIKE-*; RUNTIME-* |

Career preferences include Bengaluru and Java/Spring Boot/AWS as **configurable
search interests**, not AWS runtime/cloud activation or a fixed user identity.
Existing CAREER-03/06 own matching/market acceptance. Resume versions, recruiter
drafts/attachments and outcome feedback reuse the current owned document pipeline.
Sending email/messages, applications or resumes always needs explicit confirmation.

Travel never equates car routes with bike legality, geometric offsets with road
detours, cached links with live inventory, or research leads with permits/bookings.
Day edits, chosen routes, budgets, maps, save/reopen and offline recovery must agree.
Google Maps needs approved configuration and preserves existing fallback. Earlier
requirements include private document organizers, packing/reminders and PDF/GPX/ICS
exports. Group size/pillion budgeting is required; collaboration, invitations,
shared trip permissions, group settlements, public sharing and mobile-specific
development are excluded. Video/history work must stay private, without social publication.

Investment includes Indian stocks/ETFs/mutual funds and supported instruments,
price/fundamental/news/valuation evidence, performance/allocation/concentration,
screening/watchlists, SIP/goals, thesis/event alerts, bull/bear/risk challenge and
explainable buy/hold/avoid research. Backtests/walk-forward/provenance precede
performance claims. Ideas are separate from holdings. No automatic orders/brokerage,
guaranteed returns or invented market facts; paid feeds/credentials remain gated.

Wealth adapts read-only institution/asset snapshots and strictly post-snapshot
events only where reconciliation supports them; includes emergency funds,
obligations/goals, career-income scenarios, reserve-aware sizing, look-through,
dividends/recurring plans, unpriced/opaque assets and provenance/completeness on
values. Estimated salary/returns/unconfirmed offers never become actual cash.
Analyst/risk roles and confidential personal context remain separated. Confirmed
proposal cards reject stale dependency fingerprints before any authorized write.

## Upstream strategy and approval decisions

- **Career Ops:** exact repository identity is unknown. Defer only repository-
  dependent conversion; do not guess an unrelated project. Existing Django Career
  development remains eligible. No permanent Node backend.
- **TREK:** https://github.com/liketrek/TREK — recorded AGPL-3.0 review; independent
  Django implementation only. No code/assets copying without licensing approval.
- **TradingAgents:** https://github.com/TauricResearch/TradingAgents — recorded
  Apache-2.0/version 0.7.0 review. Component-specific attribution/dependencies must
  be checked again before reuse. Recorded pandas/yfinance conflicts preclude bulk
  installation. Prefer compatible Python/Ollama; no automatic trades/paid activation.
- **Aurelio:** https://github.com/losalossantos/aurelio-finance — recorded MIT,
  **reference only**, no runtime integration. Inspect relevant public docs/source/
  tests before selecting any algorithm; adapt against canonical ALFRED calculations.
  This bootstrap selects no new upstream algorithm or code.
- Currency/FX/historical denomination/valuation contract remains **unapproved**.
  Existing INR-labelled native estimates do not authorize global denomination policy.
- Production/live migrations, irreversible financial changes, Pages/protection,
  merge without independent approval/checks, private disclosure/history/Git uploads,
  paid/new credentials, brokerage, privileged runtime/driver/model changes,
  destructive Git/files/backups and security/AI threshold weakening require approval.
- Unknown: current independent-PC/manual screen-reader/product accuracy outcomes,
  live booking/provider coverage, sustained drift and portable key/device-loss
  recovery. No approval or success may be inferred from missing evidence.

## Dependency matrix

These are explicit data/safety dependencies, not invented technical prerequisites
from an older preferred ordering. A bounded accepted sub-contract is not full-ID
verification. Later-phase prerequisite work needs a recorded exception and `next`.

| Task | Prerequisites | Additional gate/scope |
| --- | --- | --- |
| LOAN-07 | FIN-07 | Genuine chronological outcomes before predictive claims |
| LOAN-08 | DOC-02 | Approved independent document/lender acceptance evidence |
| INV-02 | DOC-02, DOC-04, FIN-14 | Existing currency/import identity only; no FX policy change |
| INV-05 | INV-01 | Existing provider terms/source freshness; live access needs authorization |
| DOC-06 | DOC-02 | Reuse accepted encrypted corpus; do not rebuild |
| DOC-07 | DOC-06 | Full-context/held-out/OCR gaps; no fabricated document facts |
| AI-16 | AI-15 | Independent held-out and sustained drift evidence |
| AI-12 | AI-15, AI-16 | Canonical arithmetic; separate unaccepted predictive claims |
| INV-06 | FIN-06, FIN-15 | Goals and approved currency/valuation rules |
| INV-07 | FIN-15 | Monetary alerts gated; preserve accepted opt-in nonmonetary reminders |
| CAREER-03 | CAREER-02 | Configurable role/location; legitimate links and freshness |
| CAREER-06 | CAREER-02 | Dated salary/source/currency; no predictive accuracy assumption |
| CAREER-08 | CAREER-07, AI-15, AI-16 | Reviewed career outcomes and uncertainty |
| TRAVEL-04 | TRAVEL-03 | Inter-stop route evidence still differs from estimated ordering |
| TRAVEL-09 | TRAVEL-07 | Bounded accepted route-identity contract can be reused; legality stays UNKNOWN |
| COUNCIL-02 | COUNCIL-01 | Model routing before wider orchestration |
| COUNCIL-04 | COUNCIL-02 | Persistent recovery/continuation contracts |
| COUNCIL-05 | COUNCIL-04 | Governance, budget and explicit authority |
| COUNCIL-03 | COUNCIL-05 | Human review, evaluated improvement; no autonomous production edits |

## Separate 2.0 extension stories

Overlaps above stay in the original 143. The 13 stories below define **additional
acceptance scope**, not 13 asserted missing implementations. All are UNACCEPTED;
inspect existing partial components when selected. Shared services count once.
Acceptance also requires applicable shared contracts/backend/Chrome/security.

| Extension | New acceptance beyond baseline | Baseline dependencies | Done evidence |
| --- | --- | --- | --- |
| CAREER2-001 | Compare owned resume versions and invalidate stale JD decisions against exact version deltas | CAREER-01, CAREER-02 | Version/citation/UI/correction/ownership workflows |
| CAREER2-002 | Recruiter response drafts with attachment manifest and explicit send confirmation | CAREER-04, CAREER-05 | Review/stale attachment/retry tests; zero implicit send/disclosure |
| TRAVEL2-001 | Desktop drag-and-drop day editor retaining user edits and undo/revision safety | TRAVEL-04 | Real pointer/keyboard edit, reordering and save/reopen |
| TRAVEL2-002 | Private trip booking/document organizer | TRAVEL-04, DOC-06 | Owned upload/link/expiry/deletion flows; no booking inference |
| TRAVEL2-003 | Trip packing checklist and durable opt-in reminders | TRAVEL-04 | Idempotent lifecycle/timezone/offline and UI checks |
| TRAVEL2-004 | Source-preserving private PDF, GPX and ICS trip exports | TRAVEL-04, TRAVEL-17 | Validated files, scope/expiry/timezone and explicit export confirmation |
| TRAVEL2-005 | Canonical reserve/obligation/goal-aware trip affordability | FIN-05, FIN-06, FIN-07, FIN-15, TRAVEL-05 | Decimal reconciliation and explainable read-only trade-offs; approvals first |
| INVEST2-001 | Bounded analyst/bull/bear/valuation/risk research packet with independent challenge | INV-04, AI-15, AI-16 | Evidence/uncertainty/portfolio scope tests; no automatic order |
| INVEST2-002 | Watchlist thesis versions and research decisions distinct from owned holdings | INV-01, INV-07 | Identity/freshness/stale-thesis and no-holding-write workflows |
| WEALTH2-001 | Shared ETF/fund look-through and overlap by company/sector/country/currency, including opaque exposure | INV-01, INV-04, FIN-15 | Source-dated weights/completeness; no invented pricing/FX; shared Investment use |
| WEALTH2-002 | Fingerprinted cross-module AI proposal/confirmation cards | FIN-12, DOC-06, AI-12 | Dependency change rejects stale proposals; approved confirmation only |
| WEALTH2-003 | Read-only institution/asset reconciliation using strictly post-snapshot events, dividends and recurring-plan provenance | FIN-03, FIN-11, FIN-12, INV-01, FIN-15 | Double-count/null/transfer/cutoff tests; no historical rewrite |
| WEALTH2-004 | Separate public research analyst and confidential personal-context challenger packets | AI-04, AI-12, DOC-06 | Adversarial leakage/ownership/role/source tests; no implicit cloud disclosure |

## Original baseline intent index

Generated titles only; exact acceptance and evidence remain with each canonical ID.

<!-- BEGIN BASELINE INTENT INDEX -->
| Original ID | Product intent |
| --- | --- |
| FIN-01 | Dashboard, income, expenses and fixed obligations |
| FIN-02 | Disposable cash flow and savings capacity |
| FIN-03 | Net worth, liquid cash and account snapshots |
| FIN-04 | Financial health and historical spending indicators |
| FIN-05 | Budget management, utilization and affordability |
| FIN-06 | Persisted savings goals and progress workflow |
| FIN-07 | Cash-flow forecasting |
| FIN-08 | Expense categorization and merchant correction learning |
| FIN-09 | Bank accounts and statement imports |
| FIN-10 | Account-scoped duplicate detection and fingerprints |
| FIN-11 | Transfer legs and cross-account financial relationships |
| FIN-12 | Financial reconciliation |
| FIN-13 | Financial export and correction |
| FIN-14 | Money storage across every domain |
| FIN-15 | Canonical currency persistence and multi-currency aggregation |
| FIN-16 | Tax calculations and source-backed eligibility |
| FIN-17 | Credit bureau reports and official score access |
| LOAN-01 | EMI, schedules, outstanding and repayment metrics |
| LOAN-02 | Loan PDF import and repayment statement parsing |
| LOAN-03 | Loan payment detection and review |
| LOAN-04 | Foreclosure and prepayment scenarios |
| LOAN-05 | Closure extraction, verification and evidence status |
| LOAN-06 | Multi-loan aggregation and consolidation |
| LOAN-07 | Loan forecasting and cross-module liabilities |
| LOAN-08 | Broad real-document/lender acceptance |
| INV-01 | Portfolio register, valuation and allocation |
| INV-02 | Investment PDF imports and corrections |
| INV-03 | Returns and planning projections |
| INV-04 | Risk classification and recommendations |
| INV-05 | AMFI/Yahoo market evidence and historical performance |
| INV-06 | Long-term investment planning |
| INV-07 | Persistent portfolio alerts |
| INV-08 | Investment contribution to net worth |
| DOC-01 | Bounded PDF/image upload and OCR |
| DOC-02 | Bank/loan/investment extraction and classification |
| DOC-03 | Confidence, metadata and provenance |
| DOC-04 | Field corrections, visual review and retry |
| DOC-05 | Document deduplication and source lineage |
| DOC-06 | General searchable document knowledge |
| DOC-07 | AI Q&A over arbitrary financial documents |
| DOC-08 | Loan closure document Q&A and abstention |
| DOC-09 | Document deletion and retention |
| AI-01 | Ollama local inference |
| AI-02 | Ollama embeddings and similarity retrieval |
| AI-03 | Persistent encrypted memory/index/journal |
| AI-04 | Owner isolation and memory access |
| AI-05 | Verification, confidence and provenance separation |
| AI-06 | Deduplication, relevance and insufficient-evidence abstention |
| AI-07 | Memory corrections, feedback and conflict safety |
| AI-08 | Delete/reset/retention and resurrection protection |
| AI-09 | Conversation UI, provider status and evidence cards |
| AI-10 | Persistent general conversation history |
| AI-11 | Financial grounding and numeric/currency suppression |
| AI-12 | Cross-module personal reasoning |
| AI-13 | Offline/model-outage behavior and consent fallback |
| AI-14 | Background learning pipeline |
| AI-15 | Model registry and serving readiness |
| AI-16 | Retrieval/model quality and drift monitoring |
| AI-17 | Autonomous user task execution |
| AI-18 | Voice assistant |
| OPENAI-01 | Responses API request/response adapter |
| OPENAI-02 | Model compatibility and current price review |
| OPENAI-03 | Encrypted key provisioning and owner consent |
| OPENAI-04 | Privacy classification and sensitive-data filtering |
| OPENAI-05 | Daily token and monetary spending caps |
| OPENAI-06 | Fallback, timeout, redacted diagnostics and UI |
| OPENAI-07 | Real paid-provider acceptance |
| SYNC-01 | Provider-neutral mock sync protocol |
| SYNC-02 | Non-AWS encrypted object adapter (AWS withdrawn) |
| SYNC-03 | Startup/periodic/bounded shutdown sync |
| SYNC-04 | Offline durable retry and interrupted upload recovery |
| SYNC-05 | Authenticated versioned encrypted snapshots |
| SYNC-06 | Concurrent conflict detection and ownership |
| SYNC-07 | Tombstones, revocation and remote pruning |
| SYNC-08 | Trusted high-water checkpoint |
| SYNC-09 | Portable keys and independent multi-device/device-loss recovery |
| SYNC-10 | Real provider activation, costs and IAM acceptance |
| SYNC-11 | Full application/cloud backup |
| TRAVEL-01 | Conversational discovery and saved preferences |
| TRAVEL-02 | Source-backed new destinations and novelty |
| TRAVEL-03 | Large candidate pools, show-more batches and comparison |
| TRAVEL-04 | Multiple destinations and day-wise itineraries |
| TRAVEL-05 | Budget summaries and estimates |
| TRAVEL-06 | Motorbike/pillion and vehicle-aware planning |
| TRAVEL-07 | Scenic and truly alternative routes |
| TRAVEL-08 | Expressway avoidance and motorcycle road restrictions |
| TRAVEL-09 | Route corridor stops and real detour distance |
| TRAVEL-10 | Camping and attraction discovery |
| TRAVEL-11 | Hotel live availability |
| TRAVEL-12 | Flight live availability |
| TRAVEL-13 | Train live seat/fare/waitlist inventory |
| TRAVEL-14 | Bus live inventory |
| TRAVEL-15 | Live permits and road closure confirmation |
| TRAVEL-16 | Weather, horizons and replanning |
| TRAVEL-17 | GeoJSON mapping and optional tiles |
| TRAVEL-18 | Google Maps API integration and offline map packages |
| TRAVEL-19 | Photos, GPS/date inference and trip galleries |
| TRAVEL-20 | Video management and social Travel profile |
| TRAVEL-21 | Freshness, cache, quotas and safe external HTTP |
| TRAVEL-22 | Provider telemetry retention and selective invalidation |
| TRAVEL-23 | API budgets and provider terms compliance |
| CAREER-01 | Resume upload, extraction and review |
| CAREER-02 | Skill-gap and recruiter/JD matching |
| CAREER-03 | Job discovery and recommendations |
| CAREER-04 | Recruiter email/attachment processing |
| CAREER-05 | Application and opportunity outcome tracking |
| CAREER-06 | Salary/location evidence and progression |
| CAREER-07 | Interview preparation |
| CAREER-08 | Predictive career forecasting and timing |
| FAMILY-01 | Family relationships and invitation lifecycle |
| FAMILY-02 | Explicit financial opt-in and revocation |
| FAMILY-03 | Invitation throttling and concurrent acceptance |
| FAMILY-04 | Cross-account isolation |
| FAMILY-05 | Relationship alignment and family growth |
| FAMILY-06 | Behavioral signals and personalization |
| FAMILY-07 | Financial/health/relocation risk intelligence |
| BIKE-01 | Vehicle profiles and Hunter 350 catalog support |
| BIKE-02 | Service records, fuel and costs |
| BIKE-03 | Maintenance prediction and condition tracking |
| BIKE-04 | Insurance/service documents and invoice review |
| BIKE-05 | Spare parts and service recommendations |
| BIKE-06 | Travel integration and vehicle net-worth relationship |
| COUNCIL-01 | Multiple ML inference roles and registry routing |
| COUNCIL-02 | Planning/coding/review/security multi-agent application |
| COUNCIL-03 | Experimental self-improvement engine |
| COUNCIL-04 | Persistent tasks, conflicts and usage-limit recovery |
| COUNCIL-05 | AI development budget and human Git approval |
| RUNTIME-01 | Native launcher, tray, worker and scheduler |
| RUNTIME-02 | Restart persistence and local data isolation |
| RUNTIME-03 | Windows sign-in and sustained scheduled observation |
| RUNTIME-04 | Portable package and static assets |
| RUNTIME-05 | Install/upgrade/uninstall on separate PC |
| RUNTIME-06 | Offline startup and local model prerequisites |
| RUNTIME-07 | Local backup, encrypted restore and rollback |
| RUNTIME-08 | Off-device/device-loss disaster recovery |
| RUNTIME-09 | Filesystem protection of private DB/config |
| RUNTIME-10 | Session/CSRF/auth/upload/HTTP/diagnostic safeguards |
| RUNTIME-11 | Dependency security and reproducible builds |
| RUNTIME-12 | GitHub CI and branch/source protection |
| RUNTIME-13 | M20 automated source/finance/privacy/backup gates |
| RUNTIME-14 | M21 rehearsal, failure injection and rollback acceptance |
| RUNTIME-15 | Local/LAN hosting and optional Docker stack |
| RUNTIME-16 | Real-account and manual accessibility acceptance |
<!-- END BASELINE INTENT INDEX -->
