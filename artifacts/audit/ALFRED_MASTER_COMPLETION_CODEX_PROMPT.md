# Executable Codex master completion prompt for ALFRED

**Execution override, 2026-10-15:** The audit is complete. Resume committed
post-audit implementation from docs/PROJECT_STATUS.md; do not re-audit/regenerate
the matrix. AWS is completely decommissioned by the user and may not be activated.
Preserve neutral crypto/sync; R2 is a candidate only, subject to the provider
register's unresolved private-permission/recovery contract and separate account
approval. This override supersedes all AWS/S3 activation proposals below.

Use the prompt below as the next implementation session's instruction. It is derived from the code-verified 2026-10-15 audit, not a generic wishlist. It authorizes isolated engineering/diagnostics within confirmed scope only; it does not authorize production operations, account changes, providers or publication.

---

You are Codex continuing ALFRED AI. Implement the remaining confirmed product work incrementally, with evidence and durable commits. Do not audit the entire project again and do not rebuild completed M14/M15 controls.

## Verified baseline and required first commands

Production/public master last independently verified:
3932f391aa4eed7b3200ad3b034f7991435e01e4.

Main installation: F:\ALFRED\alfred_ai.
Private database: F:\ALFRED\restored-runtime\db.sqlite3.
Local pre-M15 recovery: F:\ALFRED_BACKUPS\m15-prepromotion-20261015-000251.
Audit worktree: F:\ALFRED_DEV\alfred-master-audit.
Audit branch: audit/alfred-master-completion-20261015.
Read actual audit HEAD/checkpoint; do not assume a later docs commit is product source.
Existing M20 branch: feature/m20-release-gates, last reviewed at
0052410bcc6726c6881713002902fd9c1ae7bc59 in F:\ALFRED_DEV\m20-release-gates.

Run read-only Git state/worktree checks, then read:
AGENTS.md;
artifacts/audit/ALFRED_MASTER_AUDIT_CONTINUATION.md;
artifacts/audit/CODEX_CONTINUATION_STATE.md;
artifacts/audit/ALFRED_WHOLE_PROJECT_AUDIT_20261015.md;
docs/ALFRED_MASTER_FEATURE_MATRIX.md;
docs/ALFRED_COMPLETION_ROADMAP.md;
docs/ALFRED_EXTERNAL_INTEGRATIONS.md;
docs/ALFRED_END_TO_END_ACCEPTANCE.md.

Obtain PyCharm's configured Python SDK before toolchain commands. Use Graphify scoped queries when its graph exists; AST-only update in the development worktree after code changes. Do not update production graph/source.

Inspect branch collisions before creating isolated work. Preserve unfinished M20 history; do not cherry-pick already integrated M15 changes. Reconcile actual code against the named finding before editing.

## Non-negotiable boundaries

- Do not stop/restart production, mutate live financial data/database, overwrite operator files, rotate/export keys, delete backups or change runtime settings without explicit operation-specific approval.
- No paid OpenAI, real cloud/private upload or authenticated provider call without selected provider/account and explicit bounded authorization.
- No GitHub master push, branch protection setting change, force-push/reset of operator source or silent production migration.
- No cancelled passphrase dialogs and no plaintext recovery-key workaround. HDD copy is user reported; device-loss recovery UNVERIFIED under a M15-only waiver. Future releases do not inherit that waiver.
- Synthetic fixtures and disposable DB/media/queues only. Never sync raw SQLite/WAL/SHM or financial documents through memory cloud.
- Keep Ollama-first and real OpenAI/cloud OFF. Assistant memory/hypotheses never replace canonical Django financial models.
- Existing user credentials are entered normally, never requested in chat. Credential repair requires explicit approval and preserves the account/history.
- Confirm inaccessible original requirements before adding autonomous actions, social publication, offline map datasets or broad provider automation.

Initial audit checks found no response on 8000/missing historic PIDs; a later read-only poll found /health/live/ 200 and /health/native/ 404 on runserver. Native DB/worker identity remains unconfirmed. This is not authority to restart it or start a second listener. Recheck actual availability and prepare separately approved operational acceptance.

## Execution order

Finish one bounded unit, focused test and commit before proceeding. Preserve M16–M21 established meanings; M20 may proceed without finishing unrelated Travel features, but its own financial/security gate defects must be fixed. Do not redefine M17 as an AI Council feature.

### UNIT 0 — separately approved operational closure

Objective: diagnose present service health and private filesystem permissions without inventing historical PASS.

Reuse alfred_native.py, native health/configuration/checkpoint and existing backup/rollback tooling. Audit found broad Authenticated Users/local Users ReadData on db/config and plaintext canonical SQLite.

Prepare owner/SYSTEM-only ACL change with directory/file coverage, captured ACL rollback, operator/service-account readability and synthetic foreign-account denial. Determine disk encryption policy separately. No production permission or startup change before explicit approval.

Acceptance: actual service/config/DB selection/writer status, account boundaries, ACL evidence and rollback. If authorization unavailable, BLOCKED_APPROVAL; continue isolated source work.

### UNIT 1 — FIN-SAFE finite money validation

Objective: close AUD-02, preserving API/financial semantics.

Affected: apps/users/serializers.py, related User APIs/forms, tests/test_user_profile_api.py and existing finance baseline tests. Reuse the finite guard in apps/budgets/serializers.py; do not duplicate fixed Budget behavior.

Reject NaN, Infinity, -Infinity, overflow and invalid bounds for monthly_income/variable_income/rent_or_emi at every write entry. No schema migration merely to reject nonfinite input.

Tests: serializer + authenticated API 400/no mutation, valid zero/large/precision values, owner/CSRF, unchanged canonical metrics. Definition of done: reproducible regression fixed in isolated source with no record changes on rejection and focused gate PASS.

### UNIT 2 — M18 security dependency maintenance

Before UNIT 2, complete **UNIT 1A source/debug media privacy**: AUD-11 proves an
anonymous synthetic file is served by non-native DEBUG media routing. Reuse the
authenticated owner-filtered private_media handler from alfred_ai/native_views.py
in supported source profiles through alfred_ai/urls.py; public static assets are
separate. Test anonymous/foreign-owner denial, owned module-document access,
safe paths/no-store, source/native settings and normal UI file access. No schema
change, real private-file request or production configuration edit is authorized.
Done: both supported profiles enforce media ownership, with focused regressions.
The current runserver observation does not prove its actual DEBUG/media path.

Objective: address current official Django 6.0.9 security advisory relative to deployed 6.0.8.

Affected: requirements.txt, constraints/windows-py312.txt, current CI/native/package dependency handling. Reuse existing supported Python 3.12/environment build strategy; create a separate environment, never install into the running production SDK.

Research current official versions/advisory applicability and compatibility. Do not claim GeoDjango or formset issues affect ALFRED without a relevant path. Review requests/crypto/DRF changes only where evidence warrants; no blind mass upgrade/removal.

Tests: dependency resolution/pip check, Django system/drift checks, request/header/auth/security/financial/import tests, fresh package/static/OCR/model startup. Done: compatible pinned/constraint state plus reproducible evidence and no unapproved new dependency/schema.

### UNIT 3 — complete existing M20 release gate safeguards

Reuse F:\ALFRED_DEV\m20-release-gates scripts/release_gate.py, release_validation.py, release_recovery.py, release_promotion.py and current tests. Read actual file names/checkpoint before edits; no second framework.

A. Operator collision: candidate tracked additions must be compared to target ignored/untracked/protected paths. AUD-04 reproduces ignored config/operator.local.json overwritten during ff despite PASS. Reject before mutation; capture/recheck manifests at approval/promotion, validate path aliases/reparse entries.

B. Privacy classifier: AUD-05 shows quoted JSON access_token evades scanning. Parse/scan relevant structured formats and robust known credential forms; strict path/hash-bound public fixture exceptions; cover intermediate history, binary/source budgets and unusual filenames. Safe findings contain class/reference only, no secret snippets.

C. Decision/approval: exact SHA, baseline, gates, fresh backup, operator manifest, release identifier and scoped time-limited authorization; PASS/FAIL/BLOCKED/NOT_RUN/WAIVED_BY_USER remain distinct. Waivers need explicit release/scope/reason/evidence and never become PASS.

D. Recovery/financial: consistent SQLite supported backup incl WAL state; immutable manifests/hash/size/files, authenticated independent disposable restoration, owner/family/Decimal/fingerprint/transfer/payment comparison. No auto-correction or backup deletion. Distinguish local/off-device/key/device-loss statuses.

E. Promotion: dry-run default, no production mutation from tests, pinned ordinary FF, no silent migrations/dependencies/cloud flags; preserve later writes/evidence and refuse incompatible schema rollback. Resume/interruption must be deterministic.

Tests: exact confirmed ignored-file and quoted-credential reproductions; invalid/dirty/diverged SHA, omitted/corrupt volume, missing key/failed restore, canonical difference, unexpected migration, stale/missing approval, interrupted stage, remote divergence. Each failure must leave original source/private state recoverable.

Done: focused PASS then one actual combined M20 gate with counts/logs and required NOT_RUN clearly blocking. Prior combined 65 helper tests and interrupted full gate are not new final evidence.

### UNIT 4 — M20 CI/governance and M21 acceptance

Reuse .github/workflows/browser-regression.yml, house backend/browser/native/package/recovery scripts and development release_acceptance orchestration. Existing workflow is PR/manual; Pages success is not app CI.

Implement/validate readonly release CI and master/PR triggers without private secrets/providers/data. Prepare required checks/branch protections; publication/settings changes require approval. Record actual remote CI at exact SHA after authorized publication, never infer it from YAML/local tests.

M21: actually run disposable source→financial/privacy→backup→independent restore→report→authorization checkpoint→test-environment promotion→worker/server/browser→restart→completion. Run fault injection and rollback including crashed worker, Ollama outage, browser failure, interruption and schema incompatibility. Prove source/config/private state preserved and rollback errors surfaced.

Fresh package from exact candidate; inspect no private files/secrets, complete offline assets/fonts, light/dark/mobile/keyboard and launcher/tray/worker/scheduler. Clean second-PC install/upgrade/uninstall/sign-in/restart/offline retains synthetic data. Existing normal-account browser acceptance is separate operator execution under docs/ALFRED_END_TO_END_ACCEPTANCE.md.

Done: actual receipts for each applicable environment. If Chrome/native/build tools or a second PC are unavailable, NOT_RUN/BLOCKED, not PASS. M21 cannot be closed with helper mocks alone.

### UNIT 5 — T09 / M16 Travel retention and selective invalidation

Affected: apps/mobility/models.py TravelProviderRequest/State, services/travel/cache.py, travel_research.py, tasks.py and native/Celery schedules; Travel UI caller dependencies.

First deterministic configurable retention: preserve current-month quota requirements, active leases/research and recent/in-progress events; compact only what is safely recoverable/needed. No canonical financial or current evidence deletion. Privacy-safe logs, owner isolation, idempotence and restart safety.

Then dependency-aware invalidation: stay edits do not recompute unrelated routes; route edits don't erase unrelated accepted itinerary data; preserve cache/provider freshness semantics. Reuse existing quotas/circuit/budget helpers.

Tests: clock-boundary/month quotas, restart, interrupted cleanup, per-user events, active rows, stale/cached evidence and unchanged unrelated edits with mocks. Done: bounded retention and measurable selective call avoidance; no provider rebuild.

### UNIT 6 — M17 unsupported experiments / legacy token paths

Affected: apps/ml_engine/self_improve/advanced_engine.py (missing patch_generator), api/views.py unrouted SelfImproveAPI, package module collection; integrations/services/email_integration.py legacy CWD token writer; voice_assistant.py orphan optional external processors.

Trace all callers/import/package inclusion. Remove/quarantine truly unsupported paths safely, or document explicit unsupported state. Preserve supported registry/training gates. Do not silently add new agent or external speech/mail functionality.

If mail is approved later, reuse encrypted EmailConnection, safe token rotation, permission/attachment/resource limits and masked account onboarding. Never call plaintext setup_gmail_oauth. Test imports, package collection, no root token files and no accidental external dispatch.

Done: no unreachable broken experiment in supported runtime and clear supported feature boundaries.

### UNIT 7 — M19 reproducible packaging

Reuse packaging/ALFRED.spec, scripts/package_windows_release.py, installer verifier/launcher and dependency constraints. Follow measured imports/tooling evidence, not blind heavy-stack removals.

Separate runtime/optional training/build tools only with confirmed callers and documented compatibility. Fresh exact-source package manifest, hashes/dependency/static inventory and private-file scan. Repeat build/recovery/upgrade checks. No embedding operator data or credentials.

Done: documented reproducible Windows build and clean-PC lifecycle evidence, using M18/M21 outcomes.

### UNIT 8 — remaining M13 money and currency

Affected money fields: User income/rent; Budget base_budget/inflation_adjusted/spent; CareerProfile.last_salary; Mobility value/income-support/service-cost/fuel-cost/travel-budget/trip-spend/issue-cost/premium fields. Core Loan/Expense/BankAccount/Investment Decimal work remains complete.

Classify money versus rates/measurements; use existing snapshot/money migration/rehearsal patterns. Preserve original values/recovery, identifiers/fingerprints/ref/transfer/loan posting and numeric API compatibility. Finance row updates only through authorized workflow.

Currency is a separate scoped design: authoritative record code or UNKNOWN, approved legacy INR backfill provenance, per-currency totals, explicit dated FX sources/rounding. Never infer currency from model narratives. Keep Decimal strings and controlled cards; unknown currency remains explicit.

Tests: finite/large/cent precision, conversions, forward/reverse/idempotence, independent balance/loan/transfer comparisons, multi-currency/unknown/FX provenance and no LLM numeric override. Done: reviewed migration package, no production application until separately authorized.

### UNIT 9 — encrypted conversation history and richer grounded tools

Reuse M15 hybrid_intelligence.py source_context/present_answer, MemoryStore, api/memory.py, intelligence.js, document center and provenance/conflict/tombstone/checkpoint mechanisms.

A. Persist owner conversations locally encrypted, with bounded history, sensitive classification, provenance/corrections, retention/delete/reset, new-session navigation and restart. Never create a plaintext cache/index or mislabel TravelMessage as assistant history.

B. Add canonical read-only expense/budget/portfolio/loan/Travel tools one at a time. Model cannot calculate balances, write records or invoke arbitrary URLs/actions. Family consent can authorize specific financial summaries only; private memory/document access remains owner scoped.

C. Document knowledge ingestion: reviewable supported source types, structured extraction/provenance, encrypted derived chunks/index, explicit field verification and citations tied to owned live evidence. Respect resource/parser budgets. Stale/deleted/conflicting/injected evidence abstains. No claim of arbitrary document intelligence until accepted.

D. Feedback/correction UI preserves drafts/stale-edit conflict and visibly separates verified facts, user-confirmed facts and AI hypotheses. Finite/currency guards stay at presentation/tool boundary.

Tests: owner/foreign IDs, family revocation, source references, missing evidence, prompt injection, contradictions/numeric claims, expiry/deletion resurrection and offline restart. Schema/storage changes need a separate migration/recovery design.

Done: actual APIs/UI work under synthetic browser and local model acceptance; no private provider uploads.

### UNIT 10 — model quality, forecasting and drift

Affected: training/orchestrator.py, training/quality.py, core/alfred_registry.py, inference_adapters, memory_learning.py and model-specific salary/expense/service/risk/relationship projections.

Collect only consented reviewed labels/outcomes; distinguish parser corrections, AI proposals and independent truth. Define chronological holdouts, leakage guards, baseline comparisons, error metrics, calibrated confidence, sample thresholds and drift/freshness. Existing registry/readiness/fallback code is reused.

Improve only where evaluation shows a gap. A heuristic score/synthetic unit PASS never becomes a claimed prediction accuracy. Family 8% is already labelled heuristic. Financial/model outputs remain planning estimates.

Tests: insufficient samples, malformed/nonfinite labels, missing artifacts, changed model version, stale/drifting data, retraining interruption and local inference. Done: per-model measured quality/limits and fail-closed serving readiness; no autonomous financial mutation.

### UNIT 11 — remaining Travel functionality

Affected: travel_discovery.py, travel/research.py, providers/routing.py, travel_itinerary.py, travel_conversation.py, discovery/mapping, research state/models and travel_planner.js.

- Durable bounded 20–30 candidate pools, batches/show-more, dedupe/rejected/history exclusions and selective enrichment. Current limit=3 is not complete pagination.
- Origin precedence and dynamic-first source diagnostics must be tested against current code, not reopened if already fixed.
- True ORS alternative route requests (validate current official schema), owner route selection persisted and unrelated edits preserved.
- Evidence-based scenic ranking; motorcycle restrictions/closures/expressways remain UNKNOWN without real authority. Highway avoidance is not exact bike legality.
- Sampled corridor discovery plus actual bounded road-network detour calculations; crow-flies is not a verified 50-km road stop.
- Approved general multi-stop/day itinerary order and intelligent clarification, reusing typed trip/pillion/preferences/budgets.
- Layers/markers/route selection on existing maps; explicit tile terms/attribution; no bulk offline or Google Maps API assumptions.
- Photo/EXIF review remains local/owner; videos/social profile require a separate confirmed local-versus-public scope.

Mocks first; verify cost/freshness/unavailable status. Live hotel/flight requires Duffel account/contract approval; rail/bus requires authorized inventory integration, never scraping. Permits/POIs cannot imply live booking/availability.

Tests: candidate 7/restart/history, one-route fallback, conflicting route evidence, 49/51-km road-detour cases, mode/pillion/mobile/map selections, stale providers, edited itinerary and no fictional inventory. Done: bounded supported claims with actual source evidence.

### UNIT 12 — product follow-ups in existing domains

FIN goals/export/alerts: reuse canonical baseline/reports/Budget/Investment; owner-owned goal lifecycle and approved currency schema, versioned redacted export, source-backed opt-in alert thresholds/delivery. No duplicate financial models.

Career: reuse resume/job/recruiter/outcome/evidence parsers. Expand permitted geography/salary sources, attachments through encrypted mail only if approved, interactive local interview coaching and actual outcome-based forecasting. Never auto-apply or invent jobs/salary.

Family/behavior/risk: preserve directional opt-in and owner isolation; improve only with validated consenting outcomes and clear uncertainty. Never present heuristic health/relationship scores as clinical certainty.

Bike: reuse Hunter 350/catalog/profile/service/fuel/document/condition/Travel paths; current manufacturer schedules/part compatibility, reviewed service outcome evaluation and costs after money migration. No live inventory claim without provider.

Media/maps/social/export requirements with inaccessible original wording require confirmation before expansive implementation.

Tests: deterministic financial baseline, owner boundaries, historical record preservation, real-layout evidence and UI actions. Done: each confirmed row's source/API/UI/tests and applicable real acceptance, not a generic dashboard checkbox.

### UNIT 13 — real integrations and optional AI Council decisions

OpenAI: choose a supported replacement before pinned model retirement (2027-01-14 as of audit); verify current official prices/Responses schema/model limits and account permission. Keep encrypted key/owner/public-consent/token and monetary caps, local priority and retention disclosures. Only separately authorized capped synthetic public queries; no private finances.

S3: user selects approved AWS account/bucket/region. Least privilege/private ownership/account prefix/SSE/authenticated client encryption, key/checkpoint recovery, conditional conflicts/retries/deletions/versions. Actual synthetic two-device/startup/periodic/shutdown/offline/interruption restore acceptance. Real activation is a separate approval.

Travel/email/bureau: current contract/license/rates/cache rights and consent. No invented credentials or unauthorized scraping. Unsupported providers stay unavailable and labelled.

AI Council: source has ML adapter roles/skills, not a working planning/coding/review/security application. If original scope is explicitly confirmed, design sandboxed task state, roles/provider routing, tests/conflict/budget/deadline/checkpoint recovery and exact human approval gates for Git/actions. Do not extend broken self-improve into autonomous production changes.

Done: actual provider receipts only after approval; otherwise code can be READY but real acceptance BLOCKED_APPROVAL/EXTERNAL. Never describe mocks as real integration.

## Complete remaining-scope index

Every following row must be resolved through a bounded implementation/acceptance unit above or an explicit owner-approved scope decision. It is not acceptable to omit a gap because its unit is broad. Recheck actual source before editing and update the matrix when evidence changes.

| ID | Capability | Audit status | Required next action |
| --- | --- | --- | --- |
| FIN-04 | Financial health and historical spending indicators | IMPLEMENTED_NOT_ACCEPTED | Label heuristics and evaluate against reviewed outcomes. |
| FIN-05 | Budget management, utilization and affordability | PARTIALLY_IMPLEMENTED | Convert remaining money under a rehearsed migration and preserve affordability assumptions. |
| FIN-06 | Persisted savings goals and progress workflow | NOT_IMPLEMENTED | Confirm goal requirements; add owner goals only after currency/money decisions. |
| FIN-07 | Cash-flow forecasting | PARTIALLY_IMPLEMENTED | Evaluate chronological holdouts and label forecast uncertainty. |
| FIN-13 | Financial export and correction | PARTIALLY_IMPLEMENTED | Define formats and owner redaction; reuse existing reports rather than duplicate registers. |
| FIN-14 | Money storage across every domain | PARTIALLY_IMPLEMENTED | Complete remaining finite-input guards, then scoped Decimal migration rehearsals. |
| FIN-15 | Canonical currency persistence and multi-currency aggregation | NOT_IMPLEMENTED | Decide currency ownership, migration/backfill and historical rate policy separately. |
| FIN-16 | Tax calculations and source-backed eligibility | PARTIALLY_IMPLEMENTED | Confirm current-year authoritative policy and conditional eligibility; do not infer deductions. |
| FIN-17 | Credit bureau reports and official score access | PARTIALLY_IMPLEMENTED | Keep estimates distinct; obtain approved bureau access before live pulls. |
| LOAN-07 | Loan forecasting and cross-module liabilities | IMPLEMENTED_NOT_ACCEPTED | Verify real payment histories and forecast uncertainty. |
| LOAN-08 | Broad real-document/lender acceptance | IMPLEMENTED_NOT_ACCEPTED | Run an approved redacted/private-copy lender acceptance corpus. |
| INV-02 | Investment PDF imports and corrections | IMPLEMENTED_NOT_ACCEPTED | Add independently reviewed layouts; preserve Decimal identity. |
| INV-03 | Returns and planning projections | IMPLEMENTED_NOT_ACCEPTED | Use disclosed assumptions and actual outcome evaluation. |
| INV-04 | Risk classification and recommendations | PARTIALLY_IMPLEMENTED | Define risk evidence and acceptance; never present as certified advice. |
| INV-05 | AMFI/Yahoo market evidence and historical performance | IMPLEMENTED_NOT_ACCEPTED | Validate provider terms, quote age and account limits. |
| INV-06 | Long-term investment planning | PARTIALLY_IMPLEMENTED | Reuse projection engine when implementing approved goals. |
| INV-07 | Persistent portfolio alerts | PARTIALLY_IMPLEMENTED | Define owner opt-in alert workflow and freshness rejection. |
| DOC-02 | Bank/loan/investment extraction and classification | IMPLEMENTED_NOT_ACCEPTED | Maintain field-level reviewed fixtures and provenance. |
| DOC-06 | General searchable document knowledge | PARTIALLY_IMPLEMENTED | Add permission-aware ingestion only after a scoped document-Q&A decision. |
| DOC-07 | AI Q&A over arbitrary financial documents | NOT_IMPLEMENTED | Implement bounded reviewed ingestion/citations in a separate milestone. |
| DOC-09 | Document deletion and retention | PARTIALLY_IMPLEMENTED | Unify disclosed retention across raw uploads, metadata, indexes and recovery. |
| AI-10 | Persistent general conversation history | NOT_IMPLEMENTED | Add encrypted owner history with retention and migration/recovery plan. |
| AI-12 | Cross-module personal reasoning | PARTIALLY_IMPLEMENTED | Add approved read-only canonical tools one at a time. |
| AI-14 | Background learning pipeline | IMPLEMENTED_NOT_ACCEPTED | Run sustained eligible training with consent and reviewed outcomes. |
| AI-15 | Model registry and serving readiness | IMPLEMENTED_NOT_ACCEPTED | Validate each model against genuine held-out outcomes. |
| AI-16 | Retrieval/model quality and drift monitoring | PARTIALLY_IMPLEMENTED | Define evaluation cohorts and model-specific drift criteria. |
| AI-17 | Autonomous user task execution | NOT_IMPLEMENTED | Confirm scope and human approval policy before implementation. |
| AI-18 | Voice assistant | PARTIALLY_IMPLEMENTED | Retire orphan code or integrate local speech with explicit privacy consent. |
| OPENAI-02 | Model compatibility and current price review | PARTIALLY_IMPLEMENTED | Select/test replacement with current official rates before enabling; no silent model switch. |
| OPENAI-07 | Real paid-provider acceptance | BLOCKED_APPROVAL | Obtain model/provider consent and bounded synthetic-only spending authorization. |
| SYNC-02 | AWS S3 adapter, SigV4 and permission checks | IMPLEMENTED_NOT_ACCEPTED | Select private AWS location and approve synthetic live tests. |
| SYNC-09 | Portable keys and independent multi-device/device-loss recovery | BLOCKED_APPROVAL | User selects a genuinely portable secure recovery method; do not restart cancelled dialogs. |
| SYNC-10 | Real provider activation, costs and IAM acceptance | BLOCKED_APPROVAL | Obtain provider selection and separate synthetic-only authorization. |
| SYNC-11 | Full application/cloud backup | NOT_IMPLEMENTED | Keep approved application backup tooling separate from memory protocol. |
| TRAVEL-02 | Source-backed new destinations and novelty | IMPLEMENTED_NOT_ACCEPTED | Accept actual intended destinations/sources under current terms. |
| TRAVEL-03 | Large candidate pools, show-more batches and comparison | PARTIALLY_IMPLEMENTED | Implement bounded persisted pools/batches and exclude repeated rejected destinations. |
| TRAVEL-04 | Multiple destinations and day-wise itineraries | PARTIALLY_IMPLEMENTED | Reuse Travel state and route evidence for approved multi-stop scope. |
| TRAVEL-07 | Scenic and truly alternative routes | PARTIALLY_IMPLEMENTED | Implement bounded alternatives/selection with route provenance. |
| TRAVEL-08 | Expressway avoidance and motorcycle road restrictions | PARTIALLY_IMPLEMENTED | Use verified restrictions or abstain; do not label car routing bike-legal. |
| TRAVEL-09 | Route corridor stops and real detour distance | PARTIALLY_IMPLEMENTED | Add bounded road-network detours and uncertain labels. |
| TRAVEL-10 | Camping and attraction discovery | IMPLEMENTED_NOT_ACCEPTED | Accept freshness/provenance; leave booking claims unavailable. |
| TRAVEL-11 | Hotel live availability | BLOCKED_EXTERNAL | Select provider/contract and approve limited synthetic traveler queries. |
| TRAVEL-12 | Flight live availability | BLOCKED_EXTERNAL | Authorize provider and capped synthetic availability acceptance. |
| TRAVEL-13 | Train live seat/fare/waitlist inventory | BLOCKED_EXTERNAL | Obtain authorized contract/API; no scraping. |
| TRAVEL-14 | Bus live inventory | NOT_IMPLEMENTED | Confirm approved provider before building live integration. |
| TRAVEL-15 | Live permits and road closure confirmation | PARTIALLY_IMPLEMENTED | Maintain reviewed effective-date references and unknown state. |
| TRAVEL-18 | Google Maps API integration and offline map packages | NOT_IMPLEMENTED | Confirm product/provider choice and storage rights before implementation. |
| TRAVEL-19 | Photos, GPS/date inference and trip galleries | IMPLEMENTED_NOT_ACCEPTED | Accept authorized media layouts without publishing location. |
| TRAVEL-20 | Video management and social Travel profile | NOT_IMPLEMENTED | Confirm local/private versus public scope before adding models. |
| TRAVEL-22 | Provider telemetry retention and selective invalidation | PARTIALLY_IMPLEMENTED | Complete T09/M16 deterministic retention and dependency-aware refresh. |
| TRAVEL-23 | API budgets and provider terms compliance | IMPLEMENTED_NOT_ACCEPTED | Use current register and contract-specific approval. |
| CAREER-02 | Skill-gap and recruiter/JD matching | IMPLEMENTED_NOT_ACCEPTED | Validate reviewed outcomes and source references. |
| CAREER-03 | Job discovery and recommendations | IMPLEMENTED_NOT_ACCEPTED | Validate actual permitted sources and location coverage. |
| CAREER-04 | Recruiter email/attachment processing | PARTIALLY_IMPLEMENTED | Reuse encrypted token model; retire plaintext legacy OAuth writer. |
| CAREER-05 | Application and opportunity outcome tracking | IMPLEMENTED_NOT_ACCEPTED | Accept owner corrections and genuine outcome lineage. |
| CAREER-06 | Salary/location evidence and progression | IMPLEMENTED_NOT_ACCEPTED | Review currency/unit normalization and expand approved evidence. |
| CAREER-07 | Interview preparation | PARTIALLY_IMPLEMENTED | Confirm desired local coaching scope and reuse skill gaps. |
| CAREER-08 | Predictive career forecasting and timing | PARTIALLY_IMPLEMENTED | Collect consenting outcomes and evaluate chronological holdout. |
| FAMILY-05 | Relationship alignment and family growth | IMPLEMENTED_NOT_ACCEPTED | Evaluate outcomes rather than reopen an already-labelled assumption. |
| FAMILY-06 | Behavioral signals and personalization | IMPLEMENTED_NOT_ACCEPTED | Obtain consent and labelled outcomes; avoid medical certainty. |
| FAMILY-07 | Financial/health/relocation risk intelligence | IMPLEMENTED_NOT_ACCEPTED | Document confidence and evaluate actual outcomes. |
| BIKE-01 | Vehicle profiles and Hunter 350 catalog support | IMPLEMENTED_NOT_ACCEPTED | Verify manufacturer/model data and owner's actual vehicle. |
| BIKE-02 | Service records, fuel and costs | IMPLEMENTED_NOT_ACCEPTED | Complete financial-tail migration and reviewed actual logs. |
| BIKE-03 | Maintenance prediction and condition tracking | PARTIALLY_IMPLEMENTED | Evaluate real service outcomes; label intervals/part-life assumptions. |
| BIKE-04 | Insurance/service documents and invoice review | IMPLEMENTED_NOT_ACCEPTED | Accept approved real documents and no-duplicate service posting. |
| BIKE-05 | Spare parts and service recommendations | PARTIALLY_IMPLEMENTED | Use authoritative compatibility and mark estimates. |
| COUNCIL-01 | Multiple ML inference roles and registry routing | IMPLEMENTED_NOT_ACCEPTED | Describe current registry accurately. |
| COUNCIL-02 | Planning/coding/review/security multi-agent application | NOT_IMPLEMENTED | Confirm original role/approval scope; build separately only after core completion. |
| COUNCIL-03 | Experimental self-improvement engine | PARTIALLY_IMPLEMENTED | M17 must quarantine/retire or implement through a separately approved safe design. |
| COUNCIL-04 | Persistent tasks, conflicts and usage-limit recovery | PARTIALLY_IMPLEMENTED | Reuse checkpoint conventions, not a second hidden autonomous Git system. |
| COUNCIL-05 | AI development budget and human Git approval | NOT_IMPLEMENTED | Require exact-SHA approvals, sandbox tests and no force pushes if council approved. |
| RUNTIME-03 | Windows sign-in and sustained scheduled observation | IMPLEMENTED_NOT_ACCEPTED | Run operator acceptance separately without automatic production restart. |
| RUNTIME-05 | Install/upgrade/uninstall on separate PC | IMPLEMENTED_NOT_ACCEPTED | M21 synthetic clean-PC lifecycle evidence. |
| RUNTIME-06 | Offline startup and local model prerequisites | IMPLEMENTED_NOT_ACCEPTED | Accept a new host without network and disclose unavailable model/OCR states. |
| RUNTIME-08 | Off-device/device-loss disaster recovery | BLOCKED_APPROVAL | Wait for explicit recoverable method/acceptance without repeated cancelled dialogs. |
| RUNTIME-09 | Filesystem protection of private DB/config | PARTIALLY_IMPLEMENTED | Plan owner/SYSTEM ACL remediation with authorized maintenance and rollback. |
| RUNTIME-11 | Dependency security and reproducible builds | PARTIALLY_IMPLEMENTED | M18/19 scoped security upgrade plus fresh package and constraints verification. |
| RUNTIME-12 | GitHub CI and branch/source protection | PARTIALLY_IMPLEMENTED | M20 publish approved CI changes and verify actual remote checks. |
| RUNTIME-13 | M20 automated source/finance/privacy/backup gates | PARTIALLY_IMPLEMENTED | Repair identified gates, run complete bounded validation, freeze exact candidate. |
| RUNTIME-14 | M21 rehearsal, failure injection and rollback acceptance | PARTIALLY_IMPLEMENTED | Complete M20 safeguards then disposable rehearsal/failure matrix and human acceptance. |
| RUNTIME-15 | Local/LAN hosting and optional Docker stack | IMPLEMENTED_NOT_ACCEPTED | Keep local privacy; no new public cloud hosting wiring. |
| RUNTIME-16 | Real-account and manual accessibility acceptance | BLOCKED_APPROVAL | Owner signs in normally under acceptance checklist; no password in chat. |

## Tests, durable checkpoints and release definition

For each smallest unit:
1. List callers, exports, schemas, config, templates/tests affected.
2. Reproduce the confirmed gap safely; implement the shared smallest complete correction.
3. Run focused synthetic checks; record exact counts/skips/failures, source/date and redacted artifacts.
4. Commit only coherent verified work in isolated branch; no private fixtures/config or generated binary in source.
5. Update continuation with actual branch/HEAD, completed/remaining units, files, tests/failed attempts, external blockers and exact safe next command.
6. Preserve freeze/baseline evidence and don't repeat already complete phases on resume.

After a candidate stabilizes run one actual combined relevant backend/browser/native/package gate. Validate private-file/secret history, isolated migration drift, owner/family controls, canonical financial reconciliation, backup/decrypt/restore and rollback. Mark unavailable environments NOT_RUN. Prepare exact source/dependencies/migrations/config/maintenance/rollback/real-account checklist before requesting promotion approval.

Full completion means all user-confirmed matrix requirements are implemented/verified or explicitly removed from scope by the owner; applicable real-account/provider/model/clean-PC/device-loss acceptance is evidenced; no unexplained financial/privacy defect remains; documentation agrees with source; a frozen release has been packaged/backed up/approved/promoted/verified and separately authorized source publication performed.

No product completion from percentages, mock counts, HTTP 200, copied DPAPI blobs, historical waiver inheritance or old checkmarks.

Start with actual checkpoint and **UNIT 1 finite User input** in an isolated branch, while preparing UNIT 0 approval-bound operational closure. Then repair existing M20 gates and follow the dependency sequence. Execute engineering; do not produce another roadmap instead of code.

Final report each session: actual branch/HEAD/commits, unit status, exact test results, blockers/approvals, unchanged production/data/remote status, checkpoint path and next command.
