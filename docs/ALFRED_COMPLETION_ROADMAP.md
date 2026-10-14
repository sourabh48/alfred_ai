# ALFRED completion roadmap

Authoritative audit: [whole-project findings](../artifacts/audit/ALFRED_WHOLE_PROJECT_AUDIT_20261015.md); [feature matrix](ALFRED_MASTER_FEATURE_MATRIX.md). Baseline 3932f391aa4eed7b3200ad3b034f7991435e01e4, 2026-10-15. M14 and bounded M15 development are complete/deployed. Full product acceptance is not complete.

## Preserve established milestone meanings

The existing deep-review backlog and inspected post-release roadmap define M16 as Travel retention/selective refresh, M17 as experimental self-improve cleanup, M18–M19 as dependency/build reproducibility and packaging follow-ups, M20 as CI/release governance and M21 as real-environment acceptance. None is silently renumbered here.

M20 development exists at 0052410 on feature/m20-release-gates; it is not a new blank project. M21 helper orchestration exists there, but full acceptance is not executed. The older roadmap contains no demonstrated M16–M19 prerequisite edge requiring all those features before release-gate engineering. Specific security/dependency fixes can precede an accepted candidate without redefining milestones.

## Priority/dependency sequence

| Order | Work unit | Reuse | Required evidence | Dependency/status |
| --- | --- | --- | --- | --- |
| 0 | Operational acceptance: current availability and Windows data ACLs | native health/launcher and current recovery plan | Approved diagnosis; owner/service access, foreign-account denial, service health | P1; live changes require separate authorization |
| 1 | FIN-SAFE: finite User money inputs | UserSerializer, Budget finite guard | NaN/Infinity/overflow → 400/no mutation; canonical regression | Confirmed correctness defect; isolated engineering first |
| 2 | M18 security dependency patch | requirements/Windows constraints/build scripts | Current official advisory applicability; clean env, focused security gate, fresh package | Django 6.0.9 follow-up; not a replay of completed M01A |
| 3 | Finish M20 source/privacy safeguards | existing release_gate/validation/recovery/promotion | Ignored operator collisions rejected; JSON credentials detected; no mutations on rejection | Confirmed unfinished-gate defects |
| 4 | Finish M20 integrated validation and CI | existing house backend/browser/native/backup commands | Exact SHA manifests, actual full gate, privacy, restore, dry-run, approved remote CI | Local PASS ≠ remote; no auto push/deploy |
| 5 | M21 disposable/real-environment acceptance | existing release_acceptance, native/package verifier | Full rehearsal, failure injection, rollback, clean-PC lifecycle; normal real account separately | Depends on safe M20; missing external approvals remain explicit |
| 6 | M16 / T09 retention then refresh | TravelProviderRequest/State/cache/research | Quotas/current work retained; deterministic cleanup/restart; selective invalidation | No provider rebuild; synthetic providers |
| 7 | M17 experimental-path cleanup | existing call graph, package inventory | Unreachable broken import/token writer quarantined or removed safely; callers/package tests | No autonomous council added by cleanup |
| 8 | M19 packaging reproducibility | established native package/installer and constraints | Repeat builds/manifests, no private data, clean-PC acceptance | Depends on M18 and relevant M21 findings |
| 9 | FIN-MONEY remaining M13 domains | existing money migration/rehearsal pattern | Decimal tail, independent financial comparisons, forward/reverse/recovery | Core M13A–D remain complete; separate scoped migrations |
| 10 | FIN-CURRENCY explicit currency design | authoritative source cards/legacy INR convention | Approved schema/backfill/FX/date/rounding policy and multi-currency tests | Separate decision; never invent historical currency |
| 11 | AI-HISTORY encrypted owner conversations | M15 MemoryStore/UI/retention/checkpoint | New-session history, correction/deletion/restart and no leakage | Schema/storage design; no plaintext chat index |
| 12 | AI-GROUND richer read-only tools and document evidence | hybrid source_context, document hub/review | Owned canonical expense/budget/portfolio tools; source citations, stale/conflict/injection abstention | Depends on money/currency and reviewed ingestion; no silent writes |
| 13 | AI-QUALITY genuine model evaluation | registry/training/readiness and MemoryLearning.evaluate | Chronological holdouts, sufficient consenting labels, calibrated uncertainty/drift | No fabricated training/accuracy claims |
| 14 | TRAVEL-GAPS route/discovery/multi-stop | typed state, safe provider/cache, geometry | Pools/batches, true alternates, corridor road detours, uncertainty and edit persistence | Approved routing provider/key acceptance as applicable |
| 15 | APPROVED-PROVIDERS OpenAI/S3/Travel | completed adapters/consent/caps | Provider/account selection, least privilege, current pricing/terms, synthetic live acceptance | Separate approvals; remains OFF until then |
| 16 | Product follow-ups goals/export/alerts/career/bike/media | existing canonical/report/domain services | Each defined feature's owner/API/UI/tests and actual acceptance | Confirm original scope; avoid parallel registers |
| 17 | AI-COUNCIL if explicitly confirmed | skills/checkpoints/registry, not broken self-improve | Sandboxed roles/task state, budgets, exact Git human approvals, recovery | Design decision; not implied by current inference adapters |

Operational work may run alongside safe source engineering only under its own authority. Do not stop production for development checks. The audit does not authorize any live repair.

## M20 implementation completion

Existing branch already implements many Git, isolated test, financial backup, deterministic decision/waiver, dry-run and controlled promotion helpers. Preserve them and fix only confirmed gaps:

1. Protect candidate additions colliding with ignored/untracked/operator paths; capture/recheck immutable manifests at approval and promotion.
2. Structured/quoted secret scanning with exact test-fixture exclusions; do not print matches.
3. Preserve exact candidate/baseline IDs, append-only evidence, failure codes and waiver scope. Historic M15 recovery waiver does not apply to M20.
4. Finish targeted and full actual execution, including package manifest source match. NOT_RUN must remain blocking when required.
5. Prove genuine independent restore, money/fingerprint/family comparisons, safe rollback/schema incompatibility refusal.
6. Run M21 test-environment orchestration and verify services/browser rather than merely mocking those calls.
7. Prepare CI PR/master trigger/check recommendations; GitHub publish/settings need approval and actual run evidence.

Definition of done: all required local release gates have traceable receipts; every injected failure blocks mutation; no ignored operator overwrite; no scanner false PASS; complete actual Windows/browser/package evidence; remote CI is either separately verified or explicitly BLOCKED, never implicitly PASS.

## M21 acceptance completion

Rehearse source → backup → restore → approval checkpoint → disposable promotion → startup → browser → restart → rollback/failure recovery. Cover invalid SHA, dirty/diverged Git, omitted/corrupt backup volume, missing key, failed restore, canonical mismatch, migration drift, worker failure, model outage, browser failure, interrupted deployment, absent approval and remote divergence.

Existing-account visual acceptance, clean second-PC install/upgrade/uninstall/sign-in and device-loss archive/key restoration are separate outcomes. A synthetic clone is not the real account; hash matches are not decryption. Do not change credentials to manufacture acceptance.

## Financial/product work boundaries

Complete finite validation before remaining money-storage migrations. Preserve snapshot/identity/fingerprint/transfer/payment lineage. Currency must be sourced and persisted under an approved backfill policy; retain honest unknowns for old records. Do not use LLM arithmetic for balances, loans, tax or investments.

Savings goals, structured export, portfolio alerts, richer career coaching and video/social scope must have owner workflows and explicit approval/provenance. Current audit scope restatement is not blanket external service activation or social publication authority.

## Provider activation boundaries

- OpenAI: public queries only, local-first; current pinned model retirement requires a model/pricing decision. No private finances/memory upload and no paid request without explicit capped approval.
- AWS S3: dedicated private owner namespaces, key/checkpoint recoverability, IAM/account checks, synthetic events only for initial live acceptance. No raw SQLite/WAL/SHM.
- Travel: actual enabled/contract rights and account quotas, freshness expiry and unavailable states. No unauthorized rail/bus/provider scraping. Maps/POI data are not live booking inventory.
- Email/bureau: encrypted token/account consent, source contract and attachment limits; legacy helpers cannot be used as production onboarding.
- Device-loss recovery: no cancelled dialogs, no plaintext key export and no waiver inheritance.

## Session and release discipline

At each unit: read actual branch/checkpoint → inspect callers → implement smallest complete correction → focused tests → atomic commit → save exact result/next command. Full combined gates belong to stabilized candidates, not every CSS/doc edit.

Develop → Test → Integrate → Package → Backup → Approve → Promote → Verify → Push.

Keep one pinned integrated candidate per bounded release, preserve frozen evidence and operator data. Deployment, migrations, GitHub push/settings, paid inference/private cloud uploads and key operations require separate explicit authority. Future feature branches must not accumulate indefinitely once their release is accepted.

## Completion dependencies and unknowns

Full original product wording for some proposed features is inaccessible. Confirm requirements before adding autonomous execution, publicly social media, automatic job applications, offline map datasets or expansive financial advice. User-specific model efficacy, provider contracts, currency history and privacy/recovery preferences are not resolved by source inspection.

Use the [executable master prompt](../artifacts/audit/ALFRED_MASTER_COMPLETION_CODEX_PROMPT.md), not an old backlog checkbox, to continue. Each acceptance result records commit/date/environment/data/provider and actual observation.
