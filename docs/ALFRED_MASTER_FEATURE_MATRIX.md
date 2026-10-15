# ALFRED authoritative feature matrix

Post-audit progress and requirement overrides are recorded in
[PROJECT_STATUS.md](PROJECT_STATUS.md). AWS activation is withdrawn by the user;
R2 is the non-AWS implementation candidate, still unimplemented/unapproved.
The 143-row audit snapshot below is preserved; do not regenerate it to report fixes.
M17 post-audit development retires the unrouted self-improve/voice prototypes and
legacy plaintext OAuth setup. Their source links below refer to the historical
M15 commit; retirement is not delivery of AI Council or voice functionality.

Audit date: 2026-10-15. Public/production source: `3932f391aa4eed7b3200ad3b034f7991435e01e4`.

This matrix inventories the scope restated by the user, not automatic authorization to implement every proposed feature. Original chats outside this session are unavailable; their exact wording remains UNKNOWN. Historical plans and source establish implementation history, not invented user approval. No percentages certify completion.

`COMPLETE_VERIFIED` means the stated bounded technical capability has exact-source synthetic/historical evidence. It does **not** mean real-account, provider, model accuracy, clean-PC or device-loss acceptance. Implementation status and those acceptance columns are separate. Current source was inspected read-only; production service health was not observed. M20/M21 development is separate and unfinished.

Full explicit fields are in the [machine-readable matrix](../artifacts/audit/alfred-master-feature-matrix.json). The [whole-project audit](../artifacts/audit/ALFRED_WHOLE_PROJECT_AUDIT_20261015.md) defines evidence and severity; use the [roadmap](ALFRED_COMPLETION_ROADMAP.md) for execution order.

## Status counts

- COMPLETE_VERIFIED: 61
- IMPLEMENTED_NOT_ACCEPTED: 29
- PARTIALLY_IMPLEMENTED: 34
- NOT_IMPLEMENTED: 11
- BLOCKED_APPROVAL: 5
- BLOCKED_EXTERNAL: 3

## Feature index

| ID | Capability | Status | Priority |
| --- | --- | --- | --- |
| FIN-01 | Dashboard, income, expenses and fixed obligations | COMPLETE_VERIFIED | P2 |
| FIN-02 | Disposable cash flow and savings capacity | COMPLETE_VERIFIED | P2 |
| FIN-03 | Net worth, liquid cash and account snapshots | COMPLETE_VERIFIED | P2 |
| FIN-04 | Financial health and historical spending indicators | IMPLEMENTED_NOT_ACCEPTED | P2 |
| FIN-05 | Budget management, utilization and affordability | PARTIALLY_IMPLEMENTED | P2 |
| FIN-06 | Persisted savings goals and progress workflow | NOT_IMPLEMENTED | P2 |
| FIN-07 | Cash-flow forecasting | PARTIALLY_IMPLEMENTED | P2 |
| FIN-08 | Expense categorization and merchant correction learning | COMPLETE_VERIFIED | P2 |
| FIN-09 | Bank accounts and statement imports | COMPLETE_VERIFIED | P2 |
| FIN-10 | Account-scoped duplicate detection and fingerprints | COMPLETE_VERIFIED | P2 |
| FIN-11 | Transfer legs and cross-account financial relationships | COMPLETE_VERIFIED | P2 |
| FIN-12 | Financial reconciliation | COMPLETE_VERIFIED | P2 |
| FIN-13 | Financial export and correction | PARTIALLY_IMPLEMENTED | P2 |
| FIN-14 | Money storage across every domain | PARTIALLY_IMPLEMENTED | P1 |
| FIN-15 | Canonical currency persistence and multi-currency aggregation | NOT_IMPLEMENTED | P1 |
| FIN-16 | Tax calculations and source-backed eligibility | PARTIALLY_IMPLEMENTED | P2 |
| FIN-17 | Credit bureau reports and official score access | PARTIALLY_IMPLEMENTED | P2 |
| LOAN-01 | EMI, schedules, outstanding and repayment metrics | COMPLETE_VERIFIED | P2 |
| LOAN-02 | Loan PDF import and repayment statement parsing | COMPLETE_VERIFIED | P2 |
| LOAN-03 | Loan payment detection and review | COMPLETE_VERIFIED | P2 |
| LOAN-04 | Foreclosure and prepayment scenarios | COMPLETE_VERIFIED | P2 |
| LOAN-05 | Closure extraction, verification and evidence status | COMPLETE_VERIFIED | P2 |
| LOAN-06 | Multi-loan aggregation and consolidation | COMPLETE_VERIFIED | P2 |
| LOAN-07 | Loan forecasting and cross-module liabilities | IMPLEMENTED_NOT_ACCEPTED | P2 |
| LOAN-08 | Broad real-document/lender acceptance | IMPLEMENTED_NOT_ACCEPTED | P2 |
| INV-01 | Portfolio register, valuation and allocation | COMPLETE_VERIFIED | P2 |
| INV-02 | Investment PDF imports and corrections | IMPLEMENTED_NOT_ACCEPTED | P2 |
| INV-03 | Returns and planning projections | IMPLEMENTED_NOT_ACCEPTED | P2 |
| INV-04 | Risk classification and recommendations | PARTIALLY_IMPLEMENTED | P2 |
| INV-05 | AMFI/Yahoo market evidence and historical performance | IMPLEMENTED_NOT_ACCEPTED | P2 |
| INV-06 | Long-term investment planning | PARTIALLY_IMPLEMENTED | P2 |
| INV-07 | Persistent portfolio alerts | PARTIALLY_IMPLEMENTED | P2 |
| INV-08 | Investment contribution to net worth | COMPLETE_VERIFIED | P2 |
| DOC-01 | Bounded PDF/image upload and OCR | COMPLETE_VERIFIED | P2 |
| DOC-02 | Bank/loan/investment extraction and classification | IMPLEMENTED_NOT_ACCEPTED | P2 |
| DOC-03 | Confidence, metadata and provenance | COMPLETE_VERIFIED | P2 |
| DOC-04 | Field corrections, visual review and retry | COMPLETE_VERIFIED | P2 |
| DOC-05 | Document deduplication and source lineage | COMPLETE_VERIFIED | P2 |
| DOC-06 | General searchable document knowledge | PARTIALLY_IMPLEMENTED | P2 |
| DOC-07 | AI Q&A over arbitrary financial documents | NOT_IMPLEMENTED | P2 |
| DOC-08 | Loan closure document Q&A and abstention | COMPLETE_VERIFIED | P2 |
| DOC-09 | Document deletion and retention | PARTIALLY_IMPLEMENTED | P2 |
| AI-01 | Ollama local inference | COMPLETE_VERIFIED | P2 |
| AI-02 | Ollama embeddings and similarity retrieval | COMPLETE_VERIFIED | P2 |
| AI-03 | Persistent encrypted memory/index/journal | COMPLETE_VERIFIED | P2 |
| AI-04 | Owner isolation and memory access | COMPLETE_VERIFIED | P2 |
| AI-05 | Verification, confidence and provenance separation | COMPLETE_VERIFIED | P2 |
| AI-06 | Deduplication, relevance and insufficient-evidence abstention | COMPLETE_VERIFIED | P2 |
| AI-07 | Memory corrections, feedback and conflict safety | COMPLETE_VERIFIED | P2 |
| AI-08 | Delete/reset/retention and resurrection protection | COMPLETE_VERIFIED | P2 |
| AI-09 | Conversation UI, provider status and evidence cards | COMPLETE_VERIFIED | P2 |
| AI-10 | Persistent general conversation history | NOT_IMPLEMENTED | P2 |
| AI-11 | Financial grounding and numeric/currency suppression | COMPLETE_VERIFIED | P2 |
| AI-12 | Cross-module personal reasoning | PARTIALLY_IMPLEMENTED | P2 |
| AI-13 | Offline/model-outage behavior and consent fallback | COMPLETE_VERIFIED | P2 |
| AI-14 | Background learning pipeline | IMPLEMENTED_NOT_ACCEPTED | P2 |
| AI-15 | Model registry and serving readiness | IMPLEMENTED_NOT_ACCEPTED | P2 |
| AI-16 | Retrieval/model quality and drift monitoring | PARTIALLY_IMPLEMENTED | P2 |
| AI-17 | Autonomous user task execution | NOT_IMPLEMENTED | P2 |
| AI-18 | Voice assistant | PARTIALLY_IMPLEMENTED | P2 |
| OPENAI-01 | Responses API request/response adapter | COMPLETE_VERIFIED | P2 |
| OPENAI-02 | Model compatibility and current price review | PARTIALLY_IMPLEMENTED | P1 |
| OPENAI-03 | Encrypted key provisioning and owner consent | COMPLETE_VERIFIED | P2 |
| OPENAI-04 | Privacy classification and sensitive-data filtering | COMPLETE_VERIFIED | P2 |
| OPENAI-05 | Daily token and monetary spending caps | COMPLETE_VERIFIED | P2 |
| OPENAI-06 | Fallback, timeout, redacted diagnostics and UI | COMPLETE_VERIFIED | P2 |
| OPENAI-07 | Real paid-provider acceptance | BLOCKED_APPROVAL | P2 |
| SYNC-01 | Provider-neutral mock sync protocol | COMPLETE_VERIFIED | P2 |
| SYNC-02 | AWS S3 adapter, SigV4 and permission checks | IMPLEMENTED_NOT_ACCEPTED | P2 |
| SYNC-03 | Startup/periodic/bounded shutdown sync | COMPLETE_VERIFIED | P2 |
| SYNC-04 | Offline durable retry and interrupted upload recovery | COMPLETE_VERIFIED | P2 |
| SYNC-05 | Authenticated versioned encrypted snapshots | COMPLETE_VERIFIED | P2 |
| SYNC-06 | Concurrent conflict detection and ownership | COMPLETE_VERIFIED | P2 |
| SYNC-07 | Tombstones, revocation and remote pruning | COMPLETE_VERIFIED | P2 |
| SYNC-08 | Trusted high-water checkpoint | COMPLETE_VERIFIED | P2 |
| SYNC-09 | Portable keys and independent multi-device/device-loss recovery | BLOCKED_APPROVAL | P1 |
| SYNC-10 | Real provider activation, costs and IAM acceptance | BLOCKED_APPROVAL | P2 |
| SYNC-11 | Full application/cloud backup | NOT_IMPLEMENTED | P2 |
| TRAVEL-01 | Conversational discovery and saved preferences | COMPLETE_VERIFIED | P2 |
| TRAVEL-02 | Source-backed new destinations and novelty | IMPLEMENTED_NOT_ACCEPTED | P2 |
| TRAVEL-03 | Large candidate pools, show-more batches and comparison | PARTIALLY_IMPLEMENTED | P2 |
| TRAVEL-04 | Multiple destinations and day-wise itineraries | PARTIALLY_IMPLEMENTED | P2 |
| TRAVEL-05 | Budget summaries and estimates | COMPLETE_VERIFIED | P2 |
| TRAVEL-06 | Motorbike/pillion and vehicle-aware planning | COMPLETE_VERIFIED | P2 |
| TRAVEL-07 | Scenic and truly alternative routes | PARTIALLY_IMPLEMENTED | P2 |
| TRAVEL-08 | Expressway avoidance and motorcycle road restrictions | PARTIALLY_IMPLEMENTED | P2 |
| TRAVEL-09 | Route corridor stops and real detour distance | PARTIALLY_IMPLEMENTED | P2 |
| TRAVEL-10 | Camping and attraction discovery | IMPLEMENTED_NOT_ACCEPTED | P2 |
| TRAVEL-11 | Hotel live availability | BLOCKED_EXTERNAL | P2 |
| TRAVEL-12 | Flight live availability | BLOCKED_EXTERNAL | P2 |
| TRAVEL-13 | Train live seat/fare/waitlist inventory | BLOCKED_EXTERNAL | P2 |
| TRAVEL-14 | Bus live inventory | NOT_IMPLEMENTED | P2 |
| TRAVEL-15 | Live permits and road closure confirmation | PARTIALLY_IMPLEMENTED | P2 |
| TRAVEL-16 | Weather, horizons and replanning | COMPLETE_VERIFIED | P2 |
| TRAVEL-17 | GeoJSON mapping and optional tiles | COMPLETE_VERIFIED | P2 |
| TRAVEL-18 | Google Maps API integration and offline map packages | NOT_IMPLEMENTED | P2 |
| TRAVEL-19 | Photos, GPS/date inference and trip galleries | IMPLEMENTED_NOT_ACCEPTED | P2 |
| TRAVEL-20 | Video management and social Travel profile | NOT_IMPLEMENTED | P2 |
| TRAVEL-21 | Freshness, cache, quotas and safe external HTTP | COMPLETE_VERIFIED | P2 |
| TRAVEL-22 | Provider telemetry retention and selective invalidation | PARTIALLY_IMPLEMENTED | P1 |
| TRAVEL-23 | API budgets and provider terms compliance | IMPLEMENTED_NOT_ACCEPTED | P2 |
| CAREER-01 | Resume upload, extraction and review | COMPLETE_VERIFIED | P2 |
| CAREER-02 | Skill-gap and recruiter/JD matching | IMPLEMENTED_NOT_ACCEPTED | P2 |
| CAREER-03 | Job discovery and recommendations | IMPLEMENTED_NOT_ACCEPTED | P2 |
| CAREER-04 | Recruiter email/attachment processing | PARTIALLY_IMPLEMENTED | P2 |
| CAREER-05 | Application and opportunity outcome tracking | IMPLEMENTED_NOT_ACCEPTED | P2 |
| CAREER-06 | Salary/location evidence and progression | IMPLEMENTED_NOT_ACCEPTED | P2 |
| CAREER-07 | Interview preparation | PARTIALLY_IMPLEMENTED | P2 |
| CAREER-08 | Predictive career forecasting and timing | PARTIALLY_IMPLEMENTED | P2 |
| FAMILY-01 | Family relationships and invitation lifecycle | COMPLETE_VERIFIED | P2 |
| FAMILY-02 | Explicit financial opt-in and revocation | COMPLETE_VERIFIED | P2 |
| FAMILY-03 | Invitation throttling and concurrent acceptance | COMPLETE_VERIFIED | P2 |
| FAMILY-04 | Cross-account isolation | COMPLETE_VERIFIED | P2 |
| FAMILY-05 | Relationship alignment and family growth | IMPLEMENTED_NOT_ACCEPTED | P2 |
| FAMILY-06 | Behavioral signals and personalization | IMPLEMENTED_NOT_ACCEPTED | P2 |
| FAMILY-07 | Financial/health/relocation risk intelligence | IMPLEMENTED_NOT_ACCEPTED | P2 |
| BIKE-01 | Vehicle profiles and Hunter 350 catalog support | IMPLEMENTED_NOT_ACCEPTED | P2 |
| BIKE-02 | Service records, fuel and costs | IMPLEMENTED_NOT_ACCEPTED | P2 |
| BIKE-03 | Maintenance prediction and condition tracking | PARTIALLY_IMPLEMENTED | P2 |
| BIKE-04 | Insurance/service documents and invoice review | IMPLEMENTED_NOT_ACCEPTED | P2 |
| BIKE-05 | Spare parts and service recommendations | PARTIALLY_IMPLEMENTED | P2 |
| BIKE-06 | Travel integration and vehicle net-worth relationship | COMPLETE_VERIFIED | P2 |
| COUNCIL-01 | Multiple ML inference roles and registry routing | IMPLEMENTED_NOT_ACCEPTED | P2 |
| COUNCIL-02 | Planning/coding/review/security multi-agent application | NOT_IMPLEMENTED | P2 |
| COUNCIL-03 | Experimental self-improvement engine | PARTIALLY_IMPLEMENTED | P1 |
| COUNCIL-04 | Persistent tasks, conflicts and usage-limit recovery | PARTIALLY_IMPLEMENTED | P2 |
| COUNCIL-05 | AI development budget and human Git approval | NOT_IMPLEMENTED | P2 |
| RUNTIME-01 | Native launcher, tray, worker and scheduler | COMPLETE_VERIFIED | P1 |
| RUNTIME-02 | Restart persistence and local data isolation | COMPLETE_VERIFIED | P2 |
| RUNTIME-03 | Windows sign-in and sustained scheduled observation | IMPLEMENTED_NOT_ACCEPTED | P2 |
| RUNTIME-04 | Portable package and static assets | COMPLETE_VERIFIED | P2 |
| RUNTIME-05 | Install/upgrade/uninstall on separate PC | IMPLEMENTED_NOT_ACCEPTED | P2 |
| RUNTIME-06 | Offline startup and local model prerequisites | IMPLEMENTED_NOT_ACCEPTED | P2 |
| RUNTIME-07 | Local backup, encrypted restore and rollback | COMPLETE_VERIFIED | P2 |
| RUNTIME-08 | Off-device/device-loss disaster recovery | BLOCKED_APPROVAL | P1 |
| RUNTIME-09 | Filesystem protection of private DB/config | PARTIALLY_IMPLEMENTED | P1 |
| RUNTIME-10 | Session/CSRF/auth/upload/HTTP/diagnostic safeguards | COMPLETE_VERIFIED | P2 |
| RUNTIME-11 | Dependency security and reproducible builds | PARTIALLY_IMPLEMENTED | P1 |
| RUNTIME-12 | GitHub CI and branch/source protection | PARTIALLY_IMPLEMENTED | P1 |
| RUNTIME-13 | M20 automated source/finance/privacy/backup gates | PARTIALLY_IMPLEMENTED | P1 |
| RUNTIME-14 | M21 rehearsal, failure injection and rollback acceptance | PARTIALLY_IMPLEMENTED | P1 |
| RUNTIME-15 | Local/LAN hosting and optional Docker stack | IMPLEMENTED_NOT_ACCEPTED | P2 |
| RUNTIME-16 | Real-account and manual accessibility acceptance | BLOCKED_APPROVAL | P1 |

## Evidence and acceptance detail

Common real-account status is PENDING: no normal existing-account visual acceptance was performed. Local-only features have no external-provider requirement. Provider-dependent rows explicitly override that status. Source and test links below are public; no private runtime record is included.

Linked test files identify associated coverage; their presence does not claim every
test was rerun. The audit's execution ledger lists the exact seven fresh modules
and historical gate scopes. Missing capabilities do not become tested merely
because their parent domain has a test suite.

### Personal finance

#### FIN-01 — Dashboard, income, expenses and fixed obligations

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py).
- API/UI: /expenses/; /api/expenses/ (see urls.py).
- Models/storage: User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Canonical baseline distinguishes measured, entered, inferred and unavailable values; complete transaction history is not assumed.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Retain reconciliation and complete real-account visual acceptance.

#### FIN-02 — Disposable cash flow and savings capacity

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py).
- API/UI: /expenses/; /api/expenses/ (see urls.py).
- Models/storage: User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Capacity is an estimate based on recorded history/obligations, not an automatic future income guarantee.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Keep canonical baseline as the single calculation path.

#### FIN-03 — Net worth, liquid cash and account snapshots

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py).
- API/UI: /expenses/; /api/expenses/ (see urls.py).
- Models/storage: User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Entered account values are snapshots; partial imports do not establish an audited ledger.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Accept with the owner's actual account and snapshots.

#### FIN-04 — Financial health and historical spending indicators

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py).
- API/UI: /expenses/; /api/expenses/ (see urls.py).
- Models/storage: User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Indicators are bounded heuristic summaries; predictive accuracy is not established.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Label heuristics and evaluate against reviewed outcomes.

#### FIN-05 — Budget management, utilization and affordability

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py), [apps/budgets/models.py](../apps/budgets/models.py), [apps/budgets/serializers.py](../apps/budgets/serializers.py), [apps/budgets/services/budget_intelligence.py](../apps/budgets/services/budget_intelligence.py).
- API/UI: /expenses/; /api/expenses/ (see urls.py).
- Models/storage: User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Budget money remains FloatField; serializer rejects nonfinite amounts. City/category assumptions are not universal facts.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Convert remaining money under a rehearsed migration and preserve affordability assumptions.

#### FIN-06 — Persisted savings goals and progress workflow

- Status: **NOT_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py).
- API/UI: /expenses/; /api/expenses/ (see urls.py).
- Models/storage: User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: No dedicated goal model or end-to-end goal management route found; savings capacity is not goal persistence.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Confirm goal requirements; add owner goals only after currency/money decisions.

#### FIN-07 — Cash-flow forecasting

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py), [apps/budgets/services/budget_intelligence.py](../apps/budgets/services/budget_intelligence.py), [apps/ml_engine/models/expense_forecaster.py](../apps/ml_engine/models/expense_forecaster.py).
- API/UI: /expenses/; /api/expenses/ (see urls.py).
- Models/storage: User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py), [tests/test_ml_training_orchestrator.py](../tests/test_ml_training_orchestrator.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Forecast and expense-LSTM fallback exist; sufficient genuine outcomes and calibrated forecast quality are unverified.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Evaluate chronological holdouts and label forecast uncertainty.

#### FIN-08 — Expense categorization and merchant correction learning

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py), [apps/expenses/services/transaction_intelligence.py](../apps/expenses/services/transaction_intelligence.py).
- API/UI: /expenses/; /api/expenses/ (see urls.py).
- Models/storage: User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py), [tests/test_parser_adaptive_learning.py](../tests/test_parser_adaptive_learning.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Parser/history heuristics require review on new layouts; corrections do not prove classifier accuracy.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Continue reviewed synthetic and authorized document-family acceptance.

#### FIN-09 — Bank accounts and statement imports

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py), [apps/expenses/services/statement_import.py](../apps/expenses/services/statement_import.py), [apps/expenses/services/statement_lifecycle.py](../apps/expenses/services/statement_lifecycle.py).
- API/UI: /expenses/; /api/expenses/ (see urls.py).
- Models/storage: User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py), [tests/test_statement_columns.py](../tests/test_statement_columns.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Actual balances must be reconciled against full bank evidence; OCR availability can require review.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Complete real-document and real-account acceptance.

#### FIN-10 — Account-scoped duplicate detection and fingerprints

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py), [apps/expenses/services/transaction_intelligence.py](../apps/expenses/services/transaction_intelligence.py).
- API/UI: /expenses/; /api/expenses/ (see urls.py).
- Models/storage: User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py), [tests/test_expense_money_identity.py](../tests/test_expense_money_identity.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Fingerprint schema and cross-account distinctions are preserved by money migrations.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Reject any unexplained fingerprint changes.

#### FIN-11 — Transfer legs and cross-account financial relationships

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py), [apps/expenses/services/financial_relationships.py](../apps/expenses/services/financial_relationships.py).
- API/UI: /expenses/; /api/expenses/ (see urls.py).
- Models/storage: User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py), [tests/test_financial_relationships.py](../tests/test_financial_relationships.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Detected relationships are evidence/confidence driven; unresolved transfers need owner review.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Keep transfers separate from income/living spend.

#### FIN-12 — Financial reconciliation

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py).
- API/UI: /expenses/; /api/expenses/ (see urls.py).
- Models/storage: User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Historical synthetic/deployment reconciliation passed; current private rows were not reread in this audit.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Use approved private-copy reconciliation during the next release.

#### FIN-13 — Financial export and correction

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py), [apps/reports/services.py](../apps/reports/services.py).
- API/UI: /expenses/; /api/expenses/ (see urls.py).
- Models/storage: User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py), [tests/test_user_data_acceptance.py](../tests/test_user_data_acceptance.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Statement/expense correction and report paths exist; one comprehensive portable structured financial export is not demonstrated.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Define formats and owner redaction; reuse existing reports rather than duplicate registers.

#### FIN-14 — Money storage across every domain

- Status: **PARTIALLY_IMPLEMENTED**; priority P1.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py), [apps/users/models.py](../apps/users/models.py), [apps/users/serializers.py](../apps/users/serializers.py), [apps/budgets/models.py](../apps/budgets/models.py), [apps/career/models.py](../apps/career/models.py), [apps/mobility/models.py](../apps/mobility/models.py).
- API/UI: /expenses/; /api/expenses/ (see urls.py).
- Models/storage: User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Core Expense/BankAccount/Investment/Loan amounts are Decimal; User, Budget, Career and Mobility money tail remains float.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Complete remaining finite-input guards, then scoped Decimal migration rehearsals.

#### FIN-15 — Canonical currency persistence and multi-currency aggregation

- Status: **NOT_IMPLEMENTED**; priority P1.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py).
- API/UI: /expenses/; /api/expenses/ (see urls.py).
- Models/storage: User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Legacy INR convention exists; finance models generally lack currency codes. AI correctly labels currency unrecorded; no proven FX ledger.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Decide currency ownership, migration/backfill and historical rate policy separately.

#### FIN-16 — Tax calculations and source-backed eligibility

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py), [apps/ml_engine/services/tax_policy.py](../apps/ml_engine/services/tax_policy.py), [apps/ml_engine/services/tax_optimizer.py](../apps/ml_engine/services/tax_optimizer.py).
- API/UI: /expenses/; /api/expenses/ (see urls.py).
- Models/storage: User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py), [tests/test_tax_policy.py](../tests/test_tax_policy.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Dated tax policy supports deterministic arithmetic; effective dates, deduction eligibility and reviewed actual tax cases remain acceptance dependencies.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Confirm current-year authoritative policy and conditional eligibility; do not infer deductions.

#### FIN-17 — Credit bureau reports and official score access

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py), [apps/integrations/services/credit_report_parser.py](../apps/integrations/services/credit_report_parser.py), [apps/integrations/services/credit_score_tracker.py](../apps/integrations/services/credit_score_tracker.py).
- API/UI: /expenses/; /api/expenses/ (see urls.py).
- Models/storage: User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py), [tests/test_credit_report_upload.py](../tests/test_credit_report_upload.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: Official bureau integration BLOCKED_EXTERNAL; uploaded reports synthetic/dated acceptance only.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Uploaded bureau evidence and clearly labelled estimates exist; authenticated bureau pulls/contracts are not accepted.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Keep estimates distinct; obtain approved bureau access before live pulls.

### Loans and liabilities

#### LOAN-01 — EMI, schedules, outstanding and repayment metrics

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/loans/services/loan_intelligence.py](../apps/loans/services/loan_intelligence.py), [apps/loans/models.py](../apps/loans/models.py), [apps/loans/urls.py](../apps/loans/urls.py).
- API/UI: /loans/; /api/loans/ (see urls.py).
- Models/storage: Loan, LoanPaymentHistory, LoanImportDocument, LoanClosureDocument, LoanForeclosureSnapshot.
- Tests: [tests/test_loan_money_runtime.py](../tests/test_loan_money_runtime.py), [tests/test_loan_lifecycle_and_reports.py](../tests/test_loan_lifecycle_and_reports.py), [tests/test_loan_foreclosure_money.py](../tests/test_loan_foreclosure_money.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Rates/tenure assumptions and missing history remain explicit; monetary persistence uses Decimal.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Keep lender reconciliation and real-statement acceptance.

#### LOAN-02 — Loan PDF import and repayment statement parsing

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/loans/services/loan_intelligence.py](../apps/loans/services/loan_intelligence.py), [apps/loans/models.py](../apps/loans/models.py), [apps/loans/urls.py](../apps/loans/urls.py), [apps/loans/services/loan_pdf_parser.py](../apps/loans/services/loan_pdf_parser.py).
- API/UI: /loans/; /api/loans/ (see urls.py).
- Models/storage: Loan, LoanPaymentHistory, LoanImportDocument, LoanClosureDocument, LoanForeclosureSnapshot.
- Tests: [tests/test_loan_money_runtime.py](../tests/test_loan_money_runtime.py), [tests/test_loan_lifecycle_and_reports.py](../tests/test_loan_lifecycle_and_reports.py), [tests/test_loan_diagnostics.py](../tests/test_loan_diagnostics.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Layout-specific parsing can require review; safe diagnostics hide historical/current parser internals.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Expand authorized real layouts without weakening M14 resource budgets.

#### LOAN-03 — Loan payment detection and review

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/loans/services/loan_intelligence.py](../apps/loans/services/loan_intelligence.py), [apps/loans/models.py](../apps/loans/models.py), [apps/loans/urls.py](../apps/loans/urls.py), [apps/loans/services/payment_review.py](../apps/loans/services/payment_review.py).
- API/UI: /loans/; /api/loans/ (see urls.py).
- Models/storage: Loan, LoanPaymentHistory, LoanImportDocument, LoanClosureDocument, LoanForeclosureSnapshot.
- Tests: [tests/test_loan_money_runtime.py](../tests/test_loan_money_runtime.py), [tests/test_loan_lifecycle_and_reports.py](../tests/test_loan_lifecycle_and_reports.py), [tests/test_loan_related_money_runtime.py](../tests/test_loan_related_money_runtime.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Heuristic matching is reviewable; subscription false positives can be reversed.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Preserve settlement allocations and no-double-post tests.

#### LOAN-04 — Foreclosure and prepayment scenarios

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/loans/services/loan_intelligence.py](../apps/loans/services/loan_intelligence.py), [apps/loans/models.py](../apps/loans/models.py), [apps/loans/urls.py](../apps/loans/urls.py), [apps/loans/services/loan_foreclosure_service.py](../apps/loans/services/loan_foreclosure_service.py).
- API/UI: /loans/; /api/loans/ (see urls.py).
- Models/storage: Loan, LoanPaymentHistory, LoanImportDocument, LoanClosureDocument, LoanForeclosureSnapshot.
- Tests: [tests/test_loan_money_runtime.py](../tests/test_loan_money_runtime.py), [tests/test_loan_lifecycle_and_reports.py](../tests/test_loan_lifecycle_and_reports.py), [tests/test_loan_foreclosure_money.py](../tests/test_loan_foreclosure_money.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Fees and payoff must come from reviewed lender evidence, not guessed quotes.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Keep hypothetical scenarios separate from posting.

#### LOAN-05 — Closure extraction, verification and evidence status

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/loans/services/loan_intelligence.py](../apps/loans/services/loan_intelligence.py), [apps/loans/models.py](../apps/loans/models.py), [apps/loans/urls.py](../apps/loans/urls.py), [apps/loans/services/loan_closure_parser.py](../apps/loans/services/loan_closure_parser.py).
- API/UI: /loans/; /api/loans/ (see urls.py).
- Models/storage: Loan, LoanPaymentHistory, LoanImportDocument, LoanClosureDocument, LoanForeclosureSnapshot.
- Tests: [tests/test_loan_money_runtime.py](../tests/test_loan_money_runtime.py), [tests/test_loan_lifecycle_and_reports.py](../tests/test_loan_lifecycle_and_reports.py), [tests/test_loan_verification.py](../tests/test_loan_verification.py), [tests/test_loan_verification_api.py](../tests/test_loan_verification_api.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Uploaded closure evidence is not automatically verified solely because parsing succeeded.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Accept actual lender evidence under owner review.

#### LOAN-06 — Multi-loan aggregation and consolidation

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/loans/services/loan_intelligence.py](../apps/loans/services/loan_intelligence.py), [apps/loans/models.py](../apps/loans/models.py), [apps/loans/urls.py](../apps/loans/urls.py).
- API/UI: /loans/; /api/loans/ (see urls.py).
- Models/storage: Loan, LoanPaymentHistory, LoanImportDocument, LoanClosureDocument, LoanForeclosureSnapshot.
- Tests: [tests/test_loan_money_runtime.py](../tests/test_loan_money_runtime.py), [tests/test_loan_lifecycle_and_reports.py](../tests/test_loan_lifecycle_and_reports.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Consolidation is an authorized application workflow; assistant cannot silently execute it.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Retain original loan lineage and cash-flow tests.

#### LOAN-07 — Loan forecasting and cross-module liabilities

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/loans/services/loan_intelligence.py](../apps/loans/services/loan_intelligence.py), [apps/loans/models.py](../apps/loans/models.py), [apps/loans/urls.py](../apps/loans/urls.py).
- API/UI: /loans/; /api/loans/ (see urls.py).
- Models/storage: Loan, LoanPaymentHistory, LoanImportDocument, LoanClosureDocument, LoanForeclosureSnapshot.
- Tests: [tests/test_loan_money_runtime.py](../tests/test_loan_money_runtime.py), [tests/test_loan_lifecycle_and_reports.py](../tests/test_loan_lifecycle_and_reports.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Projection is amortization/assumption based, not a calibrated personal prediction.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Verify real payment histories and forecast uncertainty.

#### LOAN-08 — Broad real-document/lender acceptance

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/loans/services/loan_intelligence.py](../apps/loans/services/loan_intelligence.py), [apps/loans/models.py](../apps/loans/models.py), [apps/loans/urls.py](../apps/loans/urls.py).
- API/UI: /loans/; /api/loans/ (see urls.py).
- Models/storage: Loan, LoanPaymentHistory, LoanImportDocument, LoanClosureDocument, LoanForeclosureSnapshot.
- Tests: [tests/test_loan_money_runtime.py](../tests/test_loan_money_runtime.py), [tests/test_loan_lifecycle_and_reports.py](../tests/test_loan_lifecycle_and_reports.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Synthetic parser/closure tests and older reviewed documents do not cover every lender/layout.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Run an approved redacted/private-copy lender acceptance corpus.

### Investments

#### INV-01 — Portfolio register, valuation and allocation

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/investments/services/portfolio_intelligence.py](../apps/investments/services/portfolio_intelligence.py), [apps/investments/models.py](../apps/investments/models.py), [apps/investments/urls.py](../apps/investments/urls.py).
- API/UI: /investments/; /api/investments/ (see urls.py).
- Models/storage: Investment; optional external evidence.
- Tests: [tests/test_investment_money.py](../tests/test_investment_money.py), [tests/test_investment_projection.py](../tests/test_investment_projection.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Values can be entered snapshots; cached external quotes have freshness metadata.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Accept owner portfolio and reconcile to broker evidence.

#### INV-02 — Investment PDF imports and corrections

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/investments/services/portfolio_intelligence.py](../apps/investments/services/portfolio_intelligence.py), [apps/investments/models.py](../apps/investments/models.py), [apps/investments/urls.py](../apps/investments/urls.py).
- API/UI: /investments/; /api/investments/ (see urls.py).
- Models/storage: Investment; optional external evidence.
- Tests: [tests/test_investment_money.py](../tests/test_investment_money.py), [tests/test_investment_projection.py](../tests/test_investment_projection.py), [tests/test_document_center_and_statement_import.py](../tests/test_document_center_and_statement_import.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Parser/import/review exists; generalized broker layout accuracy is not established.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Add independently reviewed layouts; preserve Decimal identity.

#### INV-03 — Returns and planning projections

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/investments/services/portfolio_intelligence.py](../apps/investments/services/portfolio_intelligence.py), [apps/investments/models.py](../apps/investments/models.py), [apps/investments/urls.py](../apps/investments/urls.py).
- API/UI: /investments/; /api/investments/ (see urls.py).
- Models/storage: Investment; optional external evidence.
- Tests: [tests/test_investment_money.py](../tests/test_investment_money.py), [tests/test_investment_projection.py](../tests/test_investment_projection.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Projection assumptions and inflation influence estimates; not guaranteed investment returns.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Use disclosed assumptions and actual outcome evaluation.

#### INV-04 — Risk classification and recommendations

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/investments/services/portfolio_intelligence.py](../apps/investments/services/portfolio_intelligence.py), [apps/investments/models.py](../apps/investments/models.py), [apps/investments/urls.py](../apps/investments/urls.py).
- API/UI: /investments/; /api/investments/ (see urls.py).
- Models/storage: Investment; optional external evidence.
- Tests: [tests/test_investment_money.py](../tests/test_investment_money.py), [tests/test_investment_projection.py](../tests/test_investment_projection.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Allocation/watchlist logic is heuristic, supported by available sources; suitability accuracy is unverified.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Define risk evidence and acceptance; never present as certified advice.

#### INV-05 — AMFI/Yahoo market evidence and historical performance

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/investments/services/portfolio_intelligence.py](../apps/investments/services/portfolio_intelligence.py), [apps/investments/models.py](../apps/investments/models.py), [apps/investments/urls.py](../apps/investments/urls.py).
- API/UI: /investments/; /api/investments/ (see urls.py).
- Models/storage: Investment; optional external evidence.
- Tests: [tests/test_investment_money.py](../tests/test_investment_money.py), [tests/test_investment_projection.py](../tests/test_investment_projection.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: Source implemented; current real-live acceptance NOT_RUN.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Adapters/cache/provenance exist; no fresh authorized provider request was made in this audit.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Validate provider terms, quote age and account limits.

#### INV-06 — Long-term investment planning

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/investments/services/portfolio_intelligence.py](../apps/investments/services/portfolio_intelligence.py), [apps/investments/models.py](../apps/investments/models.py), [apps/investments/urls.py](../apps/investments/urls.py).
- API/UI: /investments/; /api/investments/ (see urls.py).
- Models/storage: Investment; optional external evidence.
- Tests: [tests/test_investment_money.py](../tests/test_investment_money.py), [tests/test_investment_projection.py](../tests/test_investment_projection.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Growth scenarios exist; owner-specific goals, full portfolio risk calibration and currency policy are incomplete.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Reuse projection engine when implementing approved goals.

#### INV-07 — Persistent portfolio alerts

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/investments/services/portfolio_intelligence.py](../apps/investments/services/portfolio_intelligence.py), [apps/investments/models.py](../apps/investments/models.py), [apps/investments/urls.py](../apps/investments/urls.py).
- API/UI: /investments/; /api/investments/ (see urls.py).
- Models/storage: Investment; optional external evidence.
- Tests: [tests/test_investment_money.py](../tests/test_investment_money.py), [tests/test_investment_projection.py](../tests/test_investment_projection.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Dashboard observations/watchlists exist; verified alert thresholds, delivery and lifecycle are not demonstrated.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Define owner opt-in alert workflow and freshness rejection.

#### INV-08 — Investment contribution to net worth

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/investments/services/portfolio_intelligence.py](../apps/investments/services/portfolio_intelligence.py), [apps/investments/models.py](../apps/investments/models.py), [apps/investments/urls.py](../apps/investments/urls.py).
- API/UI: /investments/; /api/investments/ (see urls.py).
- Models/storage: Investment; optional external evidence.
- Tests: [tests/test_investment_money.py](../tests/test_investment_money.py), [tests/test_investment_projection.py](../tests/test_investment_projection.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Canonical investment totals feed the baseline; unknown currency is not silently converted.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Preserve source amounts and reconciliation.

### Document intelligence

#### DOC-01 — Bounded PDF/image upload and OCR

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_ai/services/document_extraction.py](../alfred_ai/services/document_extraction.py), [alfred_ai/services/document_review.py](../alfred_ai/services/document_review.py), [alfred_ai/views.py](../alfred_ai/views.py), [static/js/documents.js](../static/js/documents.js), [alfred_ai/services/upload_limits.py](../alfred_ai/services/upload_limits.py).
- API/UI: /documents/; document-center actions in alfred_ai/urls.py.
- Models/storage: Module-owned upload records; DocumentParserLearningMemory; no universal document-knowledge model.
- Tests: [tests/test_document_extraction.py](../tests/test_document_extraction.py), [tests/test_document_review_and_retry.py](../tests/test_document_review_and_retry.py), [tests/test_upload_limits.py](../tests/test_upload_limits.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: OCR requires supported binaries; missing OCR degrades to review. Raw payloads are not safe log content.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Accept more layouts and native OCR availability.

#### DOC-02 — Bank/loan/investment extraction and classification

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_ai/services/document_extraction.py](../alfred_ai/services/document_extraction.py), [alfred_ai/services/document_review.py](../alfred_ai/services/document_review.py), [alfred_ai/views.py](../alfred_ai/views.py), [static/js/documents.js](../static/js/documents.js).
- API/UI: /documents/; document-center actions in alfred_ai/urls.py.
- Models/storage: Module-owned upload records; DocumentParserLearningMemory; no universal document-knowledge model.
- Tests: [tests/test_document_extraction.py](../tests/test_document_extraction.py), [tests/test_document_review_and_retry.py](../tests/test_document_review_and_retry.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Dedicated parsers and source-kind classification exist; comprehensive accuracy across arbitrary documents is unproven.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Maintain field-level reviewed fixtures and provenance.

#### DOC-03 — Confidence, metadata and provenance

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_ai/services/document_extraction.py](../alfred_ai/services/document_extraction.py), [alfred_ai/services/document_review.py](../alfred_ai/services/document_review.py), [alfred_ai/views.py](../alfred_ai/views.py), [static/js/documents.js](../static/js/documents.js).
- API/UI: /documents/; document-center actions in alfred_ai/urls.py.
- Models/storage: Module-owned upload records; DocumentParserLearningMemory; no universal document-knowledge model.
- Tests: [tests/test_document_extraction.py](../tests/test_document_extraction.py), [tests/test_document_review_and_retry.py](../tests/test_document_review_and_retry.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Parser confidence is not proof that an extracted fact is true; verification remains separate.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Preserve source/version/field review distinction.

#### DOC-04 — Field corrections, visual review and retry

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_ai/services/document_extraction.py](../alfred_ai/services/document_extraction.py), [alfred_ai/services/document_review.py](../alfred_ai/services/document_review.py), [alfred_ai/views.py](../alfred_ai/views.py), [static/js/documents.js](../static/js/documents.js).
- API/UI: /documents/; document-center actions in alfred_ai/urls.py.
- Models/storage: Module-owned upload records; DocumentParserLearningMemory; no universal document-knowledge model.
- Tests: [tests/test_document_extraction.py](../tests/test_document_extraction.py), [tests/test_document_review_and_retry.py](../tests/test_document_review_and_retry.py), [tests/test_document_retry_integrity.py](../tests/test_document_retry_integrity.py), [tests/test_document_review_browser.py](../tests/test_document_review_browser.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Corrections update supported module records; stale retries cannot overwrite newer accepted edits.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Retain browser and integrity regressions.

#### DOC-05 — Document deduplication and source lineage

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_ai/services/document_extraction.py](../alfred_ai/services/document_extraction.py), [alfred_ai/services/document_review.py](../alfred_ai/services/document_review.py), [alfred_ai/views.py](../alfred_ai/views.py), [static/js/documents.js](../static/js/documents.js).
- API/UI: /documents/; document-center actions in alfred_ai/urls.py.
- Models/storage: Module-owned upload records; DocumentParserLearningMemory; no universal document-knowledge model.
- Tests: [tests/test_document_extraction.py](../tests/test_document_extraction.py), [tests/test_document_review_and_retry.py](../tests/test_document_review_and_retry.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Module identities differ; not a universal semantic document deduplication service.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Preserve account/source fingerprints.

#### DOC-06 — General searchable document knowledge

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_ai/services/document_extraction.py](../alfred_ai/services/document_extraction.py), [alfred_ai/services/document_review.py](../alfred_ai/services/document_review.py), [alfred_ai/views.py](../alfred_ai/views.py), [static/js/documents.js](../static/js/documents.js).
- API/UI: /documents/; document-center actions in alfred_ai/urls.py.
- Models/storage: Module-owned upload records; DocumentParserLearningMemory; no universal document-knowledge model.
- Tests: [tests/test_document_extraction.py](../tests/test_document_extraction.py), [tests/test_document_review_and_retry.py](../tests/test_document_review_and_retry.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Document hub can inspect module records; no unified searchable encrypted full-document knowledge index is demonstrated.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Add permission-aware ingestion only after a scoped document-Q&A decision.

#### DOC-07 — AI Q&A over arbitrary financial documents

- Status: **NOT_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_ai/services/document_extraction.py](../alfred_ai/services/document_extraction.py), [alfred_ai/services/document_review.py](../alfred_ai/services/document_review.py), [alfred_ai/views.py](../alfred_ai/views.py), [static/js/documents.js](../static/js/documents.js), [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py).
- API/UI: /documents/; document-center actions in alfred_ai/urls.py.
- Models/storage: Module-owned upload records; DocumentParserLearningMemory; no universal document-knowledge model.
- Tests: [tests/test_document_extraction.py](../tests/test_document_extraction.py), [tests/test_document_review_and_retry.py](../tests/test_document_review_and_retry.py), [tests/test_document_grounding_acceptance.py](../tests/test_document_grounding_acceptance.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Hybrid grounding currently accepts owned memories and verified loan closure projections, not arbitrary PDF/OCR corpora.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Implement bounded reviewed ingestion/citations in a separate milestone.

#### DOC-08 — Loan closure document Q&A and abstention

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_ai/services/document_extraction.py](../alfred_ai/services/document_extraction.py), [alfred_ai/services/document_review.py](../alfred_ai/services/document_review.py), [alfred_ai/views.py](../alfred_ai/views.py), [static/js/documents.js](../static/js/documents.js), [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py).
- API/UI: /documents/; document-center actions in alfred_ai/urls.py.
- Models/storage: Module-owned upload records; DocumentParserLearningMemory; no universal document-knowledge model.
- Tests: [tests/test_document_extraction.py](../tests/test_document_extraction.py), [tests/test_document_review_and_retry.py](../tests/test_document_review_and_retry.py), [tests/test_document_grounding_acceptance.py](../tests/test_document_grounding_acceptance.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Structured verified closure fields only; deleted/stale/conflicting evidence is rejected or abstained.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Do not advertise general document reasoning.

#### DOC-09 — Document deletion and retention

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_ai/services/document_extraction.py](../alfred_ai/services/document_extraction.py), [alfred_ai/services/document_review.py](../alfred_ai/services/document_review.py), [alfred_ai/views.py](../alfred_ai/views.py), [static/js/documents.js](../static/js/documents.js), [alfred_ai/services/upload_privacy.py](../alfred_ai/services/upload_privacy.py).
- API/UI: /documents/; document-center actions in alfred_ai/urls.py.
- Models/storage: Module-owned upload records; DocumentParserLearningMemory; no universal document-knowledge model.
- Tests: [tests/test_document_extraction.py](../tests/test_document_extraction.py), [tests/test_document_review_and_retry.py](../tests/test_document_review_and_retry.py), [tests/test_upload_privacy_retention.py](../tests/test_upload_privacy_retention.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Owner deletion/raw cleanup switches exist; native vault retention/backups have separate policies. Non-native DEBUG media served a synthetic file anonymously; native owner media is protected. Actual live exposure not tested.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Unify disclosed retention across raw uploads, metadata, indexes and recovery.

### ALFRED intelligence

#### AI-01 — Ollama local inference

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- API/UI: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py.
- Models/storage: User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Installed local model/digest and bounded response validation; actual availability can change.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Recheck local model as operational acceptance, not paid fallback.

#### AI-02 — Ollama embeddings and similarity retrieval

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js), [apps/ml_engine/services/local_embeddings.py](../apps/ml_engine/services/local_embeddings.py).
- API/UI: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py.
- Models/storage: User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Local embed vector validation and relevant retrieval exist; real personalized quality still needs outcomes.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Maintain semantic benchmark and abstention fixtures.

#### AI-03 — Persistent encrypted memory/index/journal

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- API/UI: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py.
- Models/storage: User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py), [tests/test_memory_privacy.py](../tests/test_memory_privacy.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Application-layer memory encryption is not encryption of every financial SQLite file; Windows recovery key portability remains separate.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Preserve at-rest/index protection and independently recoverable keys.

#### AI-04 — Owner isolation and memory access

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- API/UI: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py.
- Models/storage: User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Memories are owner scoped; family finance consent does not grant memory sharing.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Test revoked permissions independently.

#### AI-05 — Verification, confidence and provenance separation

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js), [apps/ml_engine/services/memory_learning.py](../apps/ml_engine/services/memory_learning.py).
- API/UI: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py.
- Models/storage: User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py), [tests/test_memory_learning.py](../tests/test_memory_learning.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: AI hypotheses never become canonical financial authority; reviewed/user-confirmed states have schema mapping.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Keep human confirmation distinct from source verification.

#### AI-06 — Deduplication, relevance and insufficient-evidence abstention

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- API/UI: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py.
- Models/storage: User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py), [tests/test_memory_learning.py](../tests/test_memory_learning.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Quality assertions cover synthetic memory queries, not broad real-world model accuracy.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Grow reviewed relevance evaluation without private uploads.

#### AI-07 — Memory corrections, feedback and conflict safety

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js), [apps/ml_engine/services/memory_learning.py](../apps/ml_engine/services/memory_learning.py).
- API/UI: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py.
- Models/storage: User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Stale edits conflict rather than overwrite; accept/reject review actions exist.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Preserve drafts, provenance and supersession.

#### AI-08 — Delete/reset/retention and resurrection protection

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- API/UI: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py.
- Models/storage: User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py), [tests/test_memory_privacy.py](../tests/test_memory_privacy.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Tombstones/key revocation/trusted checkpoints protect current restore; historical recoverable backups may retain prior data.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Never promise irreversible historic erasure.

#### AI-09 — Conversation UI, provider status and evidence cards

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- API/UI: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py.
- Models/storage: User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py), [tests/test_intelligence_ui.py](../tests/test_intelligence_ui.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Session-local conversation display; status does not imply real OpenAI access.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Perform normal real-account UI acceptance.

#### AI-10 — Persistent general conversation history

- Status: **NOT_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- API/UI: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py.
- Models/storage: User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: New-conversation action clears current UI; no dedicated persisted general chat model/event history demonstrated. Travel messages are separate.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Add encrypted owner history with retention and migration/recovery plan.

#### AI-11 — Financial grounding and numeric/currency suppression

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- API/UI: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py.
- Models/storage: User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py), [tests/test_intelligence_currency.py](../tests/test_intelligence_currency.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Six canonical finance metrics use controlled Decimal source cards, currency=None when unrecorded; prose financial numbers are suppressed.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Reuse boundary when adding further tools.

#### AI-12 — Cross-module personal reasoning

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- API/UI: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py.
- Models/storage: User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Finance baseline, Travel preferences, verified closure evidence and general owned memories are supported; not all module histories.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Add approved read-only canonical tools one at a time.

#### AI-13 — Offline/model-outage behavior and consent fallback

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- API/UI: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py.
- Models/storage: User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Ollama outage yields safe local state; cloud does not silently activate.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Recheck drafts/retry and public-consent paths.

#### AI-14 — Background learning pipeline

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js), [apps/ml_engine/training/orchestrator.py](../apps/ml_engine/training/orchestrator.py), [apps/ml_engine/services/memory_learning.py](../apps/ml_engine/services/memory_learning.py).
- API/UI: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py.
- Models/storage: User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py), [tests/test_ml_training_orchestrator.py](../tests/test_ml_training_orchestrator.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Candidate extraction/evaluation and scheduled training paths exist; genuine outcome sufficiency is model dependent.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Run sustained eligible training with consent and reviewed outcomes.

#### AI-15 — Model registry and serving readiness

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js), [apps/ml_engine/core/alfred_registry.py](../apps/ml_engine/core/alfred_registry.py), [apps/ml_engine/training/quality.py](../apps/ml_engine/training/quality.py).
- API/UI: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py.
- Models/storage: User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py), [tests/test_ml_readiness.py](../tests/test_ml_readiness.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Registry/sample/quality/freshness gating exists; fallback/heuristic models are not calibrated trained intelligence.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Validate each model against genuine held-out outcomes.

#### AI-16 — Retrieval/model quality and drift monitoring

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- API/UI: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py.
- Models/storage: User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Synthetic retrieval evaluation/readiness exists; sustained drift, calibrated errors and chronological production quality are not established.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Define evaluation cohorts and model-specific drift criteria.

#### AI-17 — Autonomous user task execution

- Status: **NOT_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- API/UI: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py.
- Models/storage: User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Current assistant is read-only; no approved general autonomous mutations, planner/executor or financial action agent.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Confirm scope and human approval policy before implementation.

#### AI-18 — Voice assistant

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js), [apps/ml_engine/services/voice_assistant.py](https://github.com/sourabh48/alfred_ai/blob/3932f391aa4eed7b3200ad3b034f7991435e01e4/apps/ml_engine/services/voice_assistant.py).
- API/UI: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py.
- Models/storage: User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Legacy service imports optional external speech libraries and has no demonstrated routed UI/caller.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Retire orphan code or integrate local speech with explicit privacy consent.

### Optional OpenAI

#### OPENAI-01 — Responses API request/response adapter

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/memory_reasoning.py](../apps/ml_engine/services/memory_reasoning.py), [apps/ml_engine/api/memory.py](../apps/ml_engine/api/memory.py), [alfred_ai/settings.py](../alfred_ai/settings.py).
- API/UI: Memory reasoning/policy API; operator key configuration command.
- Models/storage: Owner reasoning policy and encrypted key; atomic local budget reservations.
- Tests: [tests/test_memory_reasoning.py](../tests/test_memory_reasoning.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: DISABLED; paid acceptance NOT_RUN.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Pinned endpoint, schema/model/usage validation and bounded public-query adapter are synthetic tested; no paid acceptance.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Keep real access OFF until separately approved.

#### OPENAI-02 — Model compatibility and current price review

- Status: **PARTIALLY_IMPLEMENTED**; priority P1.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/memory_reasoning.py](../apps/ml_engine/services/memory_reasoning.py), [apps/ml_engine/api/memory.py](../apps/ml_engine/api/memory.py), [alfred_ai/settings.py](../alfred_ai/settings.py).
- API/UI: Memory reasoning/policy API; operator key configuration command.
- Models/storage: Owner reasoning policy and encrypted key; atomic local budget reservations.
- Tests: [tests/test_memory_reasoning.py](../tests/test_memory_reasoning.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: Official documentation reviewed 2026-10-15; no account availability call.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Pinned gpt-4.1-mini-2025-04-14 is deprecated; documented retirement 2027-01-14. Verified $0.40/$1.60 per million still matches code.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Select/test replacement with current official rates before enabling; no silent model switch.

#### OPENAI-03 — Encrypted key provisioning and owner consent

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/memory_reasoning.py](../apps/ml_engine/services/memory_reasoning.py), [apps/ml_engine/api/memory.py](../apps/ml_engine/api/memory.py), [alfred_ai/settings.py](../alfred_ai/settings.py).
- API/UI: Memory reasoning/policy API; operator key configuration command.
- Models/storage: Owner reasoning policy and encrypted key; atomic local budget reservations.
- Tests: [tests/test_memory_reasoning.py](../tests/test_memory_reasoning.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Masked operator provisioning plus owner policy and per-request public consent; no browser key leakage.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Use account-scoped approved keys; never expand to private financial content.

#### OPENAI-04 — Privacy classification and sensitive-data filtering

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/memory_reasoning.py](../apps/ml_engine/services/memory_reasoning.py), [apps/ml_engine/api/memory.py](../apps/ml_engine/api/memory.py), [alfred_ai/settings.py](../alfred_ai/settings.py).
- API/UI: Memory reasoning/policy API; operator key configuration command.
- Models/storage: Owner reasoning policy and encrypted key; atomic local budget reservations.
- Tests: [tests/test_memory_reasoning.py](../tests/test_memory_reasoning.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Public-only boundary rejects sensitive context; store:false is not a zero-retention promise.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Explain provider monitoring retention and keep private queries local.

#### OPENAI-05 — Daily token and monetary spending caps

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/memory_reasoning.py](../apps/ml_engine/services/memory_reasoning.py), [apps/ml_engine/api/memory.py](../apps/ml_engine/api/memory.py), [alfred_ai/settings.py](../alfred_ai/settings.py).
- API/UI: Memory reasoning/policy API; operator key configuration command.
- Models/storage: Owner reasoning policy and encrypted key; atomic local budget reservations.
- Tests: [tests/test_memory_reasoning.py](../tests/test_memory_reasoning.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Atomic upper-bound reservations include failure costs; current-day price-review gate and strict usage validation.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Reverify pricing/model caps before approved paid tests.

#### OPENAI-06 — Fallback, timeout, redacted diagnostics and UI

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/memory_reasoning.py](../apps/ml_engine/services/memory_reasoning.py), [apps/ml_engine/api/memory.py](../apps/ml_engine/api/memory.py), [alfred_ai/settings.py](../alfred_ai/settings.py).
- API/UI: Memory reasoning/policy API; operator key configuration command.
- Models/storage: Owner reasoning policy and encrypted key; atomic local budget reservations.
- Tests: [tests/test_memory_reasoning.py](../tests/test_memory_reasoning.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Ollama-first, no uncontrolled automatic paid retries; UI availability is not billing authorization.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Accept actual configured provider only under approval.

#### OPENAI-07 — Real paid-provider acceptance

- Status: **BLOCKED_APPROVAL**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/memory_reasoning.py](../apps/ml_engine/services/memory_reasoning.py), [apps/ml_engine/api/memory.py](../apps/ml_engine/api/memory.py), [alfred_ai/settings.py](../alfred_ai/settings.py).
- API/UI: Memory reasoning/policy API; operator key configuration command.
- Models/storage: Owner reasoning policy and encrypted key; atomic local budget reservations.
- Tests: [tests/test_memory_reasoning.py](../tests/test_memory_reasoning.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: BLOCKED_APPROVAL
- Production: Real access intentionally DISABLED.
- Limitations: Not authorized; no real request made.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Obtain model/provider consent and bounded synthetic-only spending authorization.

### Encrypted intelligence synchronization

#### SYNC-01 — Provider-neutral mock sync protocol

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- API/UI: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks.
- Models/storage: Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Mock transport proves encrypted protocol behavior, not real remote service acceptance.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Keep mock receipts explicitly synthetic.

#### SYNC-02 — AWS S3 adapter, SigV4 and permission checks

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- API/UI: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks.
- Models/storage: Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: Synthetic S3 server only; no real account acceptance.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: AWS endpoint/account ownership restrictions; not arbitrary Azure/Drive/S3-compatible endpoint support. IAM/account unselected.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Select private AWS location and approve synthetic live tests.

#### SYNC-03 — Startup/periodic/bounded shutdown sync

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- API/UI: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks.
- Models/storage: Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py), [tests/test_memory_sync_runtime.py](../tests/test_memory_sync_runtime.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Native lifecycle and local retry state are tested; no real remote upload occurred.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Accept lifecycle under authorized provider faults.

#### SYNC-04 — Offline durable retry and interrupted upload recovery

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- API/UI: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks.
- Models/storage: Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Local-first changes and bounded retries preserve dirty state.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Exercise real provider disconnects only after approval.

#### SYNC-05 — Authenticated versioned encrypted snapshots

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- API/UI: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks.
- Models/storage: Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Client-authenticated ciphertext; immutable application snapshots differ from bucket object versioning.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Keep crypto/schema/version/size checks.

#### SYNC-06 — Concurrent conflict detection and ownership

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- API/UI: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks.
- Models/storage: Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Conditional writes, owner prefixes and validated events; real multi-device race acceptance pending.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Run two synthetic devices under approved provider.

#### SYNC-07 — Tombstones, revocation and remote pruning

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- API/UI: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks.
- Models/storage: Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Deletion propagation/checkpoint prevents resurrection; historical backups may retain revoked data.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Disclose retained snapshots/keys and test approved pruning.

#### SYNC-08 — Trusted high-water checkpoint

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- API/UI: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks.
- Models/storage: Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Separately protected checkpoint required for remote rollback detection; a copied DPAPI blob is not a portable key.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Accept new-profile key/checkpoint recovery separately.

#### SYNC-09 — Portable keys and independent multi-device/device-loss recovery

- Status: **BLOCKED_APPROVAL**; priority P1.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- API/UI: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks.
- Models/storage: Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Device-loss recovery UNVERIFIED; M15 waiver is not a PASS.
- Limitations: Profile-independent key/archive restore is unverified; cancelled passphrase flow and release-specific M15 waiver stay scoped.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: User selects a genuinely portable secure recovery method; do not restart cancelled dialogs.

#### SYNC-10 — Real provider activation, costs and IAM acceptance

- Status: **BLOCKED_APPROVAL**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- API/UI: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks.
- Models/storage: Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: BLOCKED_APPROVAL
- Production: Real cloud synchronization DISABLED.
- Limitations: Real sync remains disabled; region/bucket/account and spending/least-privilege acceptance not selected.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Obtain provider selection and separate synthetic-only authorization.

#### SYNC-11 — Full application/cloud backup

- Status: **NOT_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- API/UI: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks.
- Models/storage: Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Memory sync does not synchronize canonical Django databases/media/config or raw SQLite/WAL.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Keep approved application backup tooling separate from memory protocol.

### Travel

#### TRAVEL-01 — Conversational discovery and saved preferences

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Structured intent/state and correction rules, not unconstrained generative Travel reasoning.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Preserve state history and explicit confirmed preferences.

#### TRAVEL-02 — Source-backed new destinations and novelty

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Dynamic Wikivoyage/provider discovery and saved history exist; absent visits are not proof of never visiting.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Accept actual intended destinations/sources under current terms.

#### TRAVEL-03 — Large candidate pools, show-more batches and comparison

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Current ranked output is typically limit=3; broader 20–30 candidate/show-more flow not demonstrated.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Implement bounded persisted pools/batches and exclude repeated rejected destinations.

#### TRAVEL-04 — Multiple destinations and day-wise itineraries

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Structured selected destination/day edits exist; general ordered multi-stop routing and itinerary optimization is incomplete.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Reuse Travel state and route evidence for approved multi-stop scope.

#### TRAVEL-05 — Budget summaries and estimates

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/costs.py](../apps/mobility/services/travel/costs.py), [apps/mobility/services/travel/money.py](../apps/mobility/services/travel/money.py).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Live quote, estimate, unknown and cached data remain distinct; legacy INR convention and scenario assumptions.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Keep canonical recorded spend separate from quoted planning costs.

#### TRAVEL-06 — Motorbike/pillion and vehicle-aware planning

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Profile and trip constraints affect planning; safety/road legality cannot be guaranteed by a car route.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Accept normal rider/pillion scenarios and honest limits.

#### TRAVEL-07 — Scenic and truly alternative routes

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/providers/routing.py](../apps/mobility/services/travel/providers/routing.py).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: ORS normalizes possible features but request does not generate alternative_routes; scenic ranking is incomplete.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Implement bounded alternatives/selection with route provenance.

#### TRAVEL-08 — Expressway avoidance and motorcycle road restrictions

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Highway avoidance is broader than expressways; motorcycle_legal/closures remain UNKNOWN.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Use verified restrictions or abstain; do not label car routing bike-legal.

#### TRAVEL-09 — Route corridor stops and real detour distance

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/discovery.py](../apps/mobility/services/travel/discovery.py).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Current sampled crow-flight corridor ranking is not verified road-detour distance.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Add bounded road-network detours and uncertain labels.

#### TRAVEL-10 — Camping and attraction discovery

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/providers/places.py](../apps/mobility/services/travel/providers/places.py).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: OSM/wiki POIs are not bookable camping availability or verified opening hours.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Accept freshness/provenance; leave booking claims unavailable.

#### TRAVEL-11 — Hotel live availability

- Status: **BLOCKED_EXTERNAL**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/providers/accommodation.py](../apps/mobility/services/travel/providers/accommodation.py).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: REQUIRES_CREDENTIALS/CONTRACT; NOT_REAL_LIVE_TESTED.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Duffel Stays adapter exists but account/service rights and live authorization are missing.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Select provider/contract and approve limited synthetic traveler queries.

#### TRAVEL-12 — Flight live availability

- Status: **BLOCKED_EXTERNAL**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/providers/transport.py](../apps/mobility/services/travel/providers/transport.py).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: REQUIRES_CREDENTIALS/CONTRACT; NOT_REAL_LIVE_TESTED.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Duffel Flights adapter exists, intentionally disabled without approved access; research links are not offers.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Authorize provider and capped synthetic availability acceptance.

#### TRAVEL-13 — Train live seat/fare/waitlist inventory

- Status: **BLOCKED_EXTERNAL**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/providers/transport.py](../apps/mobility/services/travel/providers/transport.py).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: IndianRailProvider returns unavailable; pasted timetables are USER_PROVIDED, seat inventory UNKNOWN.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Obtain authorized contract/API; no scraping.

#### TRAVEL-14 — Bus live inventory

- Status: **NOT_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/links.py](../apps/mobility/services/travel/links.py).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Link-outs exist; no live bus booking/inventory adapter is demonstrated.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Confirm approved provider before building live integration.

#### TRAVEL-15 — Live permits and road closure confirmation

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/providers/permits.py](../apps/mobility/services/travel/providers/permits.py).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Dated official references exist; no verified live permit availability or closure service.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Maintain reviewed effective-date references and unknown state.

#### TRAVEL-16 — Weather, horizons and replanning

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/providers/weather.py](../apps/mobility/services/travel/providers/weather.py).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Forecast horizon and stale/unknown guards are implemented; free service limits/terms apply.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Validate permitted service and current dates.

#### TRAVEL-17 — GeoJSON mapping and optional tiles

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/mapping.py](../apps/mobility/services/travel/mapping.py).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Local route geometry works without tiles; public tile use requires policy/attribution.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Keep tile requests explicit and no offline bulk download.

#### TRAVEL-18 — Google Maps API integration and offline map packages

- Status: **NOT_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Map link-outs/Leaflet are not authenticated Google Maps integration or offline tile bundles.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Confirm product/provider choice and storage rights before implementation.

#### TRAVEL-19 — Photos, GPS/date inference and trip galleries

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel_media.py](../apps/mobility/services/travel_media.py).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: TripPhoto and EXIF review exist; inferred locations need user confirmation.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Accept authorized media layouts without publishing location.

#### TRAVEL-20 — Video management and social Travel profile

- Status: **NOT_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Image/gallery paths do not establish video ingestion or an Instagram-style publish/privacy lifecycle.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Confirm local/private versus public scope before adding models.

#### TRAVEL-21 — Freshness, cache, quotas and safe external HTTP

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/cache.py](../apps/mobility/services/travel/cache.py), [alfred_ai/services/public_http.py](../alfred_ai/services/public_http.py).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py), [tests/test_travel_http.py](../tests/test_travel_http.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Existing provider states/source labels and bounded transport reject unsafe destinations; live provider status remains independent.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Maintain T02/T12 and M14 protections.

#### TRAVEL-22 — Provider telemetry retention and selective invalidation

- Status: **PARTIALLY_IMPLEMENTED**; priority P1.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/cache.py](../apps/mobility/services/travel/cache.py).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: TravelProviderRequest persists without production cleanup; current quotas and active work constrain deletion.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Complete T09/M16 deterministic retention and dependency-aware refresh.

#### TRAVEL-23 — API budgets and provider terms compliance

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js).
- API/UI: /mobility/; travel routes in apps/mobility/urls.py.
- Models/storage: TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Application quotas/paid opt-ins/storage flags exist; provider-specific plan rights and current account limits need acceptance.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Use current register and contract-specific approval.

### Career

#### CAREER-01 — Resume upload, extraction and review

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/career/services/job_intelligence.py](../apps/career/services/job_intelligence.py), [apps/career/services/resume_intelligence.py](../apps/career/services/resume_intelligence.py), [apps/career/urls.py](../apps/career/urls.py), [static/js/career.js](../static/js/career.js).
- API/UI: /career/; /api/career/ (see urls.py).
- Models/storage: CareerProfile, CareerResume, CareerResumeLearningMemory, CareerJobAnalysis.
- Tests: [tests/test_career_resume_upload.py](../tests/test_career_resume_upload.py), [tests/test_career_recruiter_and_evidence.py](../tests/test_career_recruiter_and_evidence.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: OCR/layout diversity still needs acceptance; protected diagnostics/resource budgets are implemented.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Expand authorized reviewed CV corpus.

#### CAREER-02 — Skill-gap and recruiter/JD matching

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/career/services/job_intelligence.py](../apps/career/services/job_intelligence.py), [apps/career/services/resume_intelligence.py](../apps/career/services/resume_intelligence.py), [apps/career/urls.py](../apps/career/urls.py), [static/js/career.js](../static/js/career.js).
- API/UI: /career/; /api/career/ (see urls.py).
- Models/storage: CareerProfile, CareerResume, CareerResumeLearningMemory, CareerJobAnalysis.
- Tests: [tests/test_career_resume_upload.py](../tests/test_career_resume_upload.py), [tests/test_career_recruiter_and_evidence.py](../tests/test_career_recruiter_and_evidence.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Parsed skills and bounded fit rules exist; not calibrated universal recruitment prediction.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Validate reviewed outcomes and source references.

#### CAREER-03 — Job discovery and recommendations

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/career/services/job_intelligence.py](../apps/career/services/job_intelligence.py), [apps/career/services/resume_intelligence.py](../apps/career/services/resume_intelligence.py), [apps/career/urls.py](../apps/career/urls.py), [static/js/career.js](../static/js/career.js).
- API/UI: /career/; /api/career/ (see urls.py).
- Models/storage: CareerProfile, CareerResume, CareerResumeLearningMemory, CareerJobAnalysis.
- Tests: [tests/test_career_resume_upload.py](../tests/test_career_resume_upload.py), [tests/test_career_recruiter_and_evidence.py](../tests/test_career_recruiter_and_evidence.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Remotive/Arbeitnow/RemoteOK feeds and JSON-LD/Greenhouse/Lever/Workday/Ashby parsers exist; geography/coverage is limited.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Validate actual permitted sources and location coverage.

#### CAREER-04 — Recruiter email/attachment processing

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/career/services/job_intelligence.py](../apps/career/services/job_intelligence.py), [apps/career/services/resume_intelligence.py](../apps/career/services/resume_intelligence.py), [apps/career/urls.py](../apps/career/urls.py), [static/js/career.js](../static/js/career.js), [apps/integrations/services/email_integration.py](../apps/integrations/services/email_integration.py).
- API/UI: /career/; /api/career/ (see urls.py).
- Models/storage: CareerProfile, CareerResume, CareerResumeLearningMemory, CareerJobAnalysis.
- Tests: [tests/test_career_resume_upload.py](../tests/test_career_resume_upload.py), [tests/test_career_recruiter_and_evidence.py](../tests/test_career_recruiter_and_evidence.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Manual recruiter/JD intake works; automatic mail access is not an accepted integrated workflow.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Reuse encrypted token model; retire plaintext legacy OAuth writer.

#### CAREER-05 — Application and opportunity outcome tracking

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/career/services/job_intelligence.py](../apps/career/services/job_intelligence.py), [apps/career/services/resume_intelligence.py](../apps/career/services/resume_intelligence.py), [apps/career/urls.py](../apps/career/urls.py), [static/js/career.js](../static/js/career.js).
- API/UI: /career/; /api/career/ (see urls.py).
- Models/storage: CareerProfile, CareerResume, CareerResumeLearningMemory, CareerJobAnalysis.
- Tests: [tests/test_career_resume_upload.py](../tests/test_career_resume_upload.py), [tests/test_career_recruiter_and_evidence.py](../tests/test_career_recruiter_and_evidence.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: CareerJobAnalysis/outcome contract tracks opportunities; no universal applicant-tracking/automatic apply service.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Accept owner corrections and genuine outcome lineage.

#### CAREER-06 — Salary/location evidence and progression

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/career/services/job_intelligence.py](../apps/career/services/job_intelligence.py), [apps/career/services/resume_intelligence.py](../apps/career/services/resume_intelligence.py), [apps/career/urls.py](../apps/career/urls.py), [static/js/career.js](../static/js/career.js), [apps/career/services/projection_engine.py](../apps/career/services/projection_engine.py).
- API/UI: /career/; /api/career/ (see urls.py).
- Models/storage: CareerProfile, CareerResume, CareerResumeLearningMemory, CareerJobAnalysis.
- Tests: [tests/test_career_resume_upload.py](../tests/test_career_resume_upload.py), [tests/test_career_recruiter_and_evidence.py](../tests/test_career_recruiter_and_evidence.py), [tests/test_career_projection_confidence.py](../tests/test_career_projection_confidence.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Salary-bearing evidence/geo scope exists; sparse evidence must be labelled. Career salary storage remains float.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Review currency/unit normalization and expand approved evidence.

#### CAREER-07 — Interview preparation

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/career/services/job_intelligence.py](../apps/career/services/job_intelligence.py), [apps/career/services/resume_intelligence.py](../apps/career/services/resume_intelligence.py), [apps/career/urls.py](../apps/career/urls.py), [static/js/career.js](../static/js/career.js).
- API/UI: /career/; /api/career/ (see urls.py).
- Models/storage: CareerProfile, CareerResume, CareerResumeLearningMemory, CareerJobAnalysis.
- Tests: [tests/test_career_resume_upload.py](../tests/test_career_resume_upload.py), [tests/test_career_recruiter_and_evidence.py](../tests/test_career_recruiter_and_evidence.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Study recommendations exist; no demonstrated interactive verified interview-coach workflow.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Confirm desired local coaching scope and reuse skill gaps.

#### CAREER-08 — Predictive career forecasting and timing

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/career/services/job_intelligence.py](../apps/career/services/job_intelligence.py), [apps/career/services/resume_intelligence.py](../apps/career/services/resume_intelligence.py), [apps/career/urls.py](../apps/career/urls.py), [static/js/career.js](../static/js/career.js).
- API/UI: /career/; /api/career/ (see urls.py).
- Models/storage: CareerProfile, CareerResume, CareerResumeLearningMemory, CareerJobAnalysis.
- Tests: [tests/test_career_resume_upload.py](../tests/test_career_resume_upload.py), [tests/test_career_recruiter_and_evidence.py](../tests/test_career_recruiter_and_evidence.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Heuristic/model-backed modes and confidence exist; calibrated genuine future outcome accuracy is unverified.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Collect consenting outcomes and evaluate chronological holdout.

### Family, relationships and risk

#### FAMILY-01 — Family relationships and invitation lifecycle

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/family/services.py](../apps/family/services.py), [apps/family/models.py](../apps/family/models.py), [apps/family/urls.py](../apps/family/urls.py).
- API/UI: /family/; family relationship/financial-sharing APIs.
- Models/storage: Dependent, FamilyAccountLink; owner-scoped financial baseline.
- Tests: [tests/test_family_account_links.py](../tests/test_family_account_links.py), [tests/test_family_invitation_throttling.py](../tests/test_family_invitation_throttling.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Accepted relationships alone do not authorize financial sharing.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Complete normal user invite/revoke acceptance.

#### FAMILY-02 — Explicit financial opt-in and revocation

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/family/services.py](../apps/family/services.py), [apps/family/models.py](../apps/family/models.py), [apps/family/urls.py](../apps/family/urls.py), [apps/family/migrations/0004_financial_sharing_opt_in.py](../apps/family/migrations/0004_financial_sharing_opt_in.py).
- API/UI: /family/; family relationship/financial-sharing APIs.
- Models/storage: Dependent, FamilyAccountLink; owner-scoped financial baseline.
- Tests: [tests/test_family_account_links.py](../tests/test_family_account_links.py), [tests/test_family_invitation_throttling.py](../tests/test_family_invitation_throttling.py), [tests/test_family_consent_migration.py](../tests/test_family_consent_migration.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: family.0004 reset historical grants OFF at M14 deployment; owner consent governs shared summaries.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Never equate relationship membership with consent.

#### FAMILY-03 — Invitation throttling and concurrent acceptance

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/family/services.py](../apps/family/services.py), [apps/family/models.py](../apps/family/models.py), [apps/family/urls.py](../apps/family/urls.py).
- API/UI: /family/; family relationship/financial-sharing APIs.
- Models/storage: Dependent, FamilyAccountLink; owner-scoped financial baseline.
- Tests: [tests/test_family_account_links.py](../tests/test_family_account_links.py), [tests/test_family_invitation_throttling.py](../tests/test_family_invitation_throttling.py), [tests/test_family_invitation_atomic.py](../tests/test_family_invitation_atomic.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Existing account-isolated atomic throttles apply independently of authorization.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Preserve 429/no-mutation/expiry regressions.

#### FAMILY-04 — Cross-account isolation

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/family/services.py](../apps/family/services.py), [apps/family/models.py](../apps/family/models.py), [apps/family/urls.py](../apps/family/urls.py).
- API/UI: /family/; family relationship/financial-sharing APIs.
- Models/storage: Dependent, FamilyAccountLink; owner-scoped financial baseline.
- Tests: [tests/test_family_account_links.py](../tests/test_family_account_links.py), [tests/test_family_invitation_throttling.py](../tests/test_family_invitation_throttling.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Family financial summaries require consent; personal memories/documents remain owner scoped.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Retain revoked/foreign-ID negative tests.

#### FAMILY-05 — Relationship alignment and family growth

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/family/services.py](../apps/family/services.py), [apps/family/models.py](../apps/family/models.py), [apps/family/urls.py](../apps/family/urls.py), [apps/family/views.py](../apps/family/views.py), [apps/relationship/services/relationship_intelligence.py](../apps/relationship/services/relationship_intelligence.py).
- API/UI: /family/; family relationship/financial-sharing APIs.
- Models/storage: Dependent, FamilyAccountLink; owner-scoped financial baseline.
- Tests: [tests/test_family_account_links.py](../tests/test_family_account_links.py), [tests/test_family_invitation_throttling.py](../tests/test_family_invitation_throttling.py), [tests/test_investment_and_relationship_advisory.py](../tests/test_investment_and_relationship_advisory.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Grounded inputs plus bounded model blend; 8% family projection is already labelled heuristic, not guaranteed.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Evaluate outcomes rather than reopen an already-labelled assumption.

#### FAMILY-06 — Behavioral signals and personalization

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/family/services.py](../apps/family/services.py), [apps/family/models.py](../apps/family/models.py), [apps/family/urls.py](../apps/family/urls.py), [apps/behavioral/services.py](../apps/behavioral/services.py).
- API/UI: /family/; family relationship/financial-sharing APIs.
- Models/storage: Dependent, FamilyAccountLink; owner-scoped financial baseline.
- Tests: [tests/test_family_account_links.py](../tests/test_family_account_links.py), [tests/test_family_invitation_throttling.py](../tests/test_family_invitation_throttling.py), [tests/test_behavioral_linkage.py](../tests/test_behavioral_linkage.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Manual signals and derived pressure maps exist; clinical/personal prediction accuracy not established.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Obtain consent and labelled outcomes; avoid medical certainty.

#### FAMILY-07 — Financial/health/relocation risk intelligence

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/family/services.py](../apps/family/services.py), [apps/family/models.py](../apps/family/models.py), [apps/family/urls.py](../apps/family/urls.py), [apps/risk/services/risk_intelligence.py](../apps/risk/services/risk_intelligence.py).
- API/UI: /family/; family relationship/financial-sharing APIs.
- Models/storage: Dependent, FamilyAccountLink; owner-scoped financial baseline.
- Tests: [tests/test_family_account_links.py](../tests/test_family_account_links.py), [tests/test_family_invitation_throttling.py](../tests/test_family_invitation_throttling.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Risk scores mix history, heuristic weights and external context; not calibrated diagnosis/prediction.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Document confidence and evaluate actual outcomes.

### Bike and mobility

#### BIKE-01 — Vehicle profiles and Hunter 350 catalog support

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/bike_service_intelligence.py](../apps/mobility/services/bike_service_intelligence.py), [apps/mobility/services/bike_catalog.py](../apps/mobility/services/bike_catalog.py), [apps/mobility/urls.py](../apps/mobility/urls.py).
- API/UI: /bike-service/ and /api/mobility/; supported routes in root URLs.
- Models/storage: BikeProfile, BikeServiceRecord, FuelRefillLog, BikeIssueReport, BikeDocument, BikeConditionSnapshot.
- Tests: [tests/test_mobility_vehicle_dashboard.py](../tests/test_mobility_vehicle_dashboard.py), [tests/test_vehicle_accounting.py](../tests/test_vehicle_accounting.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Catalog and profile defaults exist; official current model/service variants need acceptance.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Verify manufacturer/model data and owner's actual vehicle.

#### BIKE-02 — Service records, fuel and costs

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/bike_service_intelligence.py](../apps/mobility/services/bike_service_intelligence.py), [apps/mobility/services/bike_catalog.py](../apps/mobility/services/bike_catalog.py), [apps/mobility/urls.py](../apps/mobility/urls.py).
- API/UI: /bike-service/ and /api/mobility/; supported routes in root URLs.
- Models/storage: BikeProfile, BikeServiceRecord, FuelRefillLog, BikeIssueReport, BikeDocument, BikeConditionSnapshot.
- Tests: [tests/test_mobility_vehicle_dashboard.py](../tests/test_mobility_vehicle_dashboard.py), [tests/test_vehicle_accounting.py](../tests/test_vehicle_accounting.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: CRUD/mileage/history exist; monetary amounts remain float in Mobility models.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Complete financial-tail migration and reviewed actual logs.

#### BIKE-03 — Maintenance prediction and condition tracking

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/bike_service_intelligence.py](../apps/mobility/services/bike_service_intelligence.py), [apps/mobility/services/bike_catalog.py](../apps/mobility/services/bike_catalog.py), [apps/mobility/urls.py](../apps/mobility/urls.py).
- API/UI: /bike-service/ and /api/mobility/; supported routes in root URLs.
- Models/storage: BikeProfile, BikeServiceRecord, FuelRefillLog, BikeIssueReport, BikeDocument, BikeConditionSnapshot.
- Tests: [tests/test_mobility_vehicle_dashboard.py](../tests/test_mobility_vehicle_dashboard.py), [tests/test_vehicle_accounting.py](../tests/test_vehicle_accounting.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Rules, condition snapshots and optional service model exist; prediction quality is unverified.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Evaluate real service outcomes; label intervals/part-life assumptions.

#### BIKE-04 — Insurance/service documents and invoice review

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/bike_service_intelligence.py](../apps/mobility/services/bike_service_intelligence.py), [apps/mobility/services/bike_catalog.py](../apps/mobility/services/bike_catalog.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [apps/mobility/services/bike_document_ai.py](../apps/mobility/services/bike_document_ai.py).
- API/UI: /bike-service/ and /api/mobility/; supported routes in root URLs.
- Models/storage: BikeProfile, BikeServiceRecord, FuelRefillLog, BikeIssueReport, BikeDocument, BikeConditionSnapshot.
- Tests: [tests/test_mobility_vehicle_dashboard.py](../tests/test_mobility_vehicle_dashboard.py), [tests/test_vehicle_accounting.py](../tests/test_vehicle_accounting.py), [tests/test_bike_document_parser.py](../tests/test_bike_document_parser.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Extraction, relevance checks and linked service updates exist; layout/identity review is essential.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Accept approved real documents and no-duplicate service posting.

#### BIKE-05 — Spare parts and service recommendations

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/bike_service_intelligence.py](../apps/mobility/services/bike_service_intelligence.py), [apps/mobility/services/bike_catalog.py](../apps/mobility/services/bike_catalog.py), [apps/mobility/urls.py](../apps/mobility/urls.py).
- API/UI: /bike-service/ and /api/mobility/; supported routes in root URLs.
- Models/storage: BikeProfile, BikeServiceRecord, FuelRefillLog, BikeIssueReport, BikeDocument, BikeConditionSnapshot.
- Tests: [tests/test_mobility_vehicle_dashboard.py](../tests/test_mobility_vehicle_dashboard.py), [tests/test_vehicle_accounting.py](../tests/test_vehicle_accounting.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Model/class heuristics and suggestions exist; no verified live price/parts-inventory service.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Use authoritative compatibility and mark estimates.

#### BIKE-06 — Travel integration and vehicle net-worth relationship

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/mobility/services/bike_service_intelligence.py](../apps/mobility/services/bike_service_intelligence.py), [apps/mobility/services/bike_catalog.py](../apps/mobility/services/bike_catalog.py), [apps/mobility/urls.py](../apps/mobility/urls.py).
- API/UI: /bike-service/ and /api/mobility/; supported routes in root URLs.
- Models/storage: BikeProfile, BikeServiceRecord, FuelRefillLog, BikeIssueReport, BikeDocument, BikeConditionSnapshot.
- Tests: [tests/test_mobility_vehicle_dashboard.py](../tests/test_mobility_vehicle_dashboard.py), [tests/test_vehicle_accounting.py](../tests/test_vehicle_accounting.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Vehicle utility/valuation assumptions and route wear affect existing baseline/planner; no guaranteed road legality.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Keep confirmed profile inputs and canonical reconciliation.

### AI Council and developer intelligence

#### COUNCIL-01 — Multiple ML inference roles and registry routing

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/core/alfred_registry.py](../apps/ml_engine/core/alfred_registry.py), [apps/ml_engine/self_improve/advanced_engine.py](https://github.com/sourabh48/alfred_ai/blob/3932f391aa4eed7b3200ad3b034f7991435e01e4/apps/ml_engine/self_improve/advanced_engine.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py).
- API/UI: ML runtime status; no routed self-improvement/coding-council API.
- Models/storage: AdaptiveModelState/AdaptiveTrainingRun; Codex skills are tools outside the application.
- Tests: [tests/test_ml_readiness.py](../tests/test_ml_readiness.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Inference adapters are specialized predictions, not development planning/coding/review agents.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Describe current registry accurately.

#### COUNCIL-02 — Planning/coding/review/security multi-agent application

- Status: **NOT_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/core/alfred_registry.py](../apps/ml_engine/core/alfred_registry.py), [apps/ml_engine/self_improve/advanced_engine.py](https://github.com/sourabh48/alfred_ai/blob/3932f391aa4eed7b3200ad3b034f7991435e01e4/apps/ml_engine/self_improve/advanced_engine.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py).
- API/UI: ML runtime status; no routed self-improvement/coding-council API.
- Models/storage: AdaptiveModelState/AdaptiveTrainingRun; Codex skills are tools outside the application.
- Tests: [tests/test_ml_readiness.py](../tests/test_ml_readiness.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Codex skills/hooks and inference routing do not form a working product AI Council.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Confirm original role/approval scope; build separately only after core completion.

#### COUNCIL-03 — Experimental self-improvement engine

- Status: **PARTIALLY_IMPLEMENTED**; priority P1.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/core/alfred_registry.py](../apps/ml_engine/core/alfred_registry.py), [apps/ml_engine/self_improve/advanced_engine.py](https://github.com/sourabh48/alfred_ai/blob/3932f391aa4eed7b3200ad3b034f7991435e01e4/apps/ml_engine/self_improve/advanced_engine.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py).
- API/UI: ML runtime status; no routed self-improvement/coding-council API.
- Models/storage: AdaptiveModelState/AdaptiveTrainingRun; Codex skills are tools outside the application.
- Tests: [tests/test_ml_readiness.py](../tests/test_ml_readiness.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: advanced_engine imports absent patch_generator; SelfImproveAPI is not routed.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: M17 must quarantine/retire or implement through a separately approved safe design.

#### COUNCIL-04 — Persistent tasks, conflicts and usage-limit recovery

- Status: **PARTIALLY_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/core/alfred_registry.py](../apps/ml_engine/core/alfred_registry.py), [apps/ml_engine/self_improve/advanced_engine.py](https://github.com/sourabh48/alfred_ai/blob/3932f391aa4eed7b3200ad3b034f7991435e01e4/apps/ml_engine/self_improve/advanced_engine.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py).
- API/UI: ML runtime status; no routed self-improvement/coding-council API.
- Models/storage: AdaptiveModelState/AdaptiveTrainingRun; Codex skills are tools outside the application.
- Tests: [tests/test_ml_readiness.py](../tests/test_ml_readiness.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Development Markdown checkpoints and runtime queues exist; persistent multi-agent task ownership/conflict resolution is absent.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Reuse checkpoint conventions, not a second hidden autonomous Git system.

#### COUNCIL-05 — AI development budget and human Git approval

- Status: **NOT_IMPLEMENTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [apps/ml_engine/core/alfred_registry.py](../apps/ml_engine/core/alfred_registry.py), [apps/ml_engine/self_improve/advanced_engine.py](https://github.com/sourabh48/alfred_ai/blob/3932f391aa4eed7b3200ad3b034f7991435e01e4/apps/ml_engine/self_improve/advanced_engine.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py).
- API/UI: ML runtime status; no routed self-improvement/coding-council API.
- Models/storage: AdaptiveModelState/AdaptiveTrainingRun; Codex skills are tools outside the application.
- Tests: [tests/test_ml_readiness.py](../tests/test_ml_readiness.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Product-level council has no demonstrated policy engine; operator release approvals are distinct.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Require exact-SHA approvals, sandbox tests and no force pushes if council approved.

### Windows, deployment and release

#### RUNTIME-01 — Native launcher, tray, worker and scheduler

- Status: **COMPLETE_VERIFIED**; priority P1.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec).
- API/UI: /health/native/; local launcher/tray; operator CLI.
- Models/storage: Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Historical native acceptance passed; initial health failed, later /health/live/ 200 and native 404 on runserver. Actual data/worker identity remains unconfirmed.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Diagnose current availability under a separately authorized operational task.

#### RUNTIME-02 — Restart persistence and local data isolation

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec).
- API/UI: /health/native/; local launcher/tray; operator CLI.
- Models/storage: Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Native data-directory and durable queue survive tested process restarts; not proof of a fresh Windows profile restore.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Keep explicit restored-runtime selection.

#### RUNTIME-03 — Windows sign-in and sustained scheduled observation

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec).
- API/UI: /health/native/; local launcher/tray; operator CLI.
- Models/storage: Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Startup registration and process tests exist; real sign-in and full sustained eligible cleanup/training still need evidence.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Run operator acceptance separately without automatic production restart.

#### RUNTIME-04 — Portable package and static assets

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec).
- API/UI: /health/native/; local launcher/tray; operator CLI.
- Models/storage: Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Fresh exact M15 package source/assets/screenshots had dated acceptance; installer/fresh-PC remain distinct.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Use pinned source/package manifest, not old build reuse.

#### RUNTIME-05 — Install/upgrade/uninstall on separate PC

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec), [scripts/verify_windows_installer.py](../scripts/verify_windows_installer.py).
- API/UI: /health/native/; local launcher/tray; operator CLI.
- Models/storage: Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py), [tests/test_windows_setup.py](../tests/test_windows_setup.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Installer scripts/verifier exist; clean-PC lifecycle and preserved-data upgrade are unaccepted.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: M21 synthetic clean-PC lifecycle evidence.

#### RUNTIME-06 — Offline startup and local model prerequisites

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec).
- API/UI: /health/native/; local launcher/tray; operator CLI.
- Models/storage: Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Local-first app works without paid/cloud providers; installed Ollama/models and OCR dependencies vary by host.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Accept a new host without network and disclose unavailable model/OCR states.

#### RUNTIME-07 — Local backup, encrypted restore and rollback

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec), [scripts/verify_private_recovery.py](../scripts/verify_private_recovery.py), [scripts/prepare_encrypted_recovery.ps1](../scripts/prepare_encrypted_recovery.ps1).
- API/UI: /health/native/; local launcher/tray; operator CLI.
- Models/storage: Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py), [tests/test_private_recovery_verifier.py](../tests/test_private_recovery_verifier.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Dated independent local pre-M15 restore/rehearsal passed; no new backup or live DB read in this audit.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Require fresh approved consistent backup before future promotion.

#### RUNTIME-08 — Off-device/device-loss disaster recovery

- Status: **BLOCKED_APPROVAL**; priority P1.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec).
- API/UI: /health/native/; local launcher/tray; operator CLI.
- Models/storage: Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: UNVERIFIED, not PASS.
- Limitations: HDD copy user reported; portable independent key/restore unverified. Historical M15 waiver does not extend to future releases.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Wait for explicit recoverable method/acceptance without repeated cancelled dialogs.

#### RUNTIME-09 — Filesystem protection of private DB/config

- Status: **PARTIALLY_IMPLEMENTED**; priority P1.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec).
- API/UI: /health/native/; local launcher/tray; operator CLI.
- Models/storage: Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Read-only ACL review found Authenticated Users/local Users read grants; DB has plaintext SQLite header. No exploitation or secret values observed.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Plan owner/SYSTEM ACL remediation with authorized maintenance and rollback.

#### RUNTIME-10 — Session/CSRF/auth/upload/HTTP/diagnostic safeguards

- Status: **COMPLETE_VERIFIED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec), [alfred_ai/services/public_http.py](../alfred_ai/services/public_http.py), [alfred_ai/services/upload_limits.py](../alfred_ai/services/upload_limits.py), [apps/loans/diagnostics.py](../apps/loans/diagnostics.py).
- API/UI: /health/native/; local launcher/tray; operator CLI.
- Models/storage: Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py), [tests/test_api_session_security.py](../tests/test_api_session_security.py), [tests/test_upload_limits.py](../tests/test_upload_limits.py), [tests/test_loan_diagnostics.py](../tests/test_loan_diagnostics.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: M14 completed controls remain in exact M15 source; do not restart resolved endpoint audits.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Keep relevant security regressions and deployment isolation.

#### RUNTIME-11 — Dependency security and reproducible builds

- Status: **PARTIALLY_IMPLEMENTED**; priority P1.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec), [requirements.txt](../requirements.txt), [constraints/windows-py312.txt](../constraints/windows-py312.txt).
- API/UI: /health/native/; local launcher/tray; operator CLI.
- Models/storage: Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Django 6.0.8 has subsequent 6.0.9 security patch; pip check passes but does not establish security. Build-tool availability/locks need follow-up.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: M18/19 scoped security upgrade plus fresh package and constraints verification.

#### RUNTIME-12 — GitHub CI and branch/source protection

- Status: **PARTIALLY_IMPLEMENTED**; priority P1.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec), [.github/workflows/browser-regression.yml](../.github/workflows/browser-regression.yml).
- API/UI: /health/native/; local launcher/tray; operator CLI.
- Models/storage: Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: PR/manual browser workflow exists; Pages run is not backend acceptance. Fresh M15 backend CI/required checks not confirmed.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: M20 publish approved CI changes and verify actual remote checks.

#### RUNTIME-13 — M20 automated source/finance/privacy/backup gates

- Status: **PARTIALLY_IMPLEMENTED**; priority P1.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec), [artifacts/audit/ALFRED_MASTER_AUDIT_CONTINUATION.md](../artifacts/audit/ALFRED_MASTER_AUDIT_CONTINUATION.md).
- API/UI: /health/native/; local launcher/tray; operator CLI.
- Models/storage: Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Prior combined 65 tests plus overlapping later narrow runs; audit reproduced 2 gate gaps. No final full gate result.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Separate feature/m20-release-gates worktree; NOT integrated/deployed.
- Limitations: Development-only 0052410 has partial focused evidence; full gate interrupted. Synthetic ignored-file overwrite and JSON credential misses are confirmed.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Repair identified gates, run complete bounded validation, freeze exact candidate.

#### RUNTIME-14 — M21 rehearsal, failure injection and rollback acceptance

- Status: **PARTIALLY_IMPLEMENTED**; priority P1.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec), [artifacts/audit/ALFRED_MASTER_AUDIT_CONTINUATION.md](../artifacts/audit/ALFRED_MASTER_AUDIT_CONTINUATION.md).
- API/UI: /health/native/; local launcher/tray; operator CLI.
- Models/storage: Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Code/helper tests present; no complete actual M21 acceptance receipt.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Development-only orchestration; product acceptance NOT_RUN.
- Limitations: M20 branch contains orchestration/tests; full native/browser/packaged rehearsal was not executed. Real acceptance remains open.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Complete M20 safeguards then disposable rehearsal/failure matrix and human acceptance.

#### RUNTIME-15 — Local/LAN hosting and optional Docker stack

- Status: **IMPLEMENTED_NOT_ACCEPTED**; priority P2.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec), [docker-compose.local.yml](../docker-compose.local.yml), [docs/LOCAL_HOSTING.md](../docs/LOCAL_HOSTING.md).
- API/UI: /health/native/; local launcher/tray; operator CLI.
- Models/storage: Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py), [tests/test_local_stack_ops.py](../tests/test_local_stack_ops.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Loopback/local native is current target; Compose/Celery profiles exist but do not prove present sustained Docker acceptance.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Keep local privacy; no new public cloud hosting wiring.

#### RUNTIME-16 — Real-account and manual accessibility acceptance

- Status: **BLOCKED_APPROVAL**; priority P1.
- Requirement provenance: Current user audit scope A–M, 2026-10-15. Historic original conversation unavailable unless linked implementation/backlog supplies provenance; implementation authorization is separate.
- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec).
- API/UI: /health/native/; local launcher/tray; operator CLI.
- Models/storage: Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py), [tests/test_user_data_browser.py](../tests/test_user_data_browser.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Real account: PENDING; no normal existing-account visual acceptance performed by this audit.
- Real provider: NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Production: Implementation, when present, is in deployed source 3932f391; current service health was not observed.
- Limitations: Synthetic Chrome/HTTP success does not replace normal sign-in, screen-reader and actual account checks.
- Dependencies: Existing owner/session controls; canonical data availability; acceptance plan.
- Next action: Owner signs in normally under acceptance checklist; no password in chat.
