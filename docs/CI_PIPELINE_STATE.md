# Development CI and integration pipeline

Updated2026-10-26. The owner selected one canonical development branch and one
integration PR. This ledger records delivery; PROJECT_STATUS owns143 original IDs,
requirements own intent, the queue selects features, and EXECUTION_STATE owns coding.
13 extensions remain separate. Full capability acceptance is never inferred from a slice.

## Permanent simplified workflow

- **development/alfred-integrated** is the only canonical development branch.
- Keep **PR #16: development/alfred-integrated -> master**. Do not automatically
  create one GitHub PR per minor section. PR18/19 are existing sources awaiting gates.
- Use temporary local branches/worktrees when independent development or conflict
  reconciliation requires isolation. Validate sources, dependencies and overlapping
  behavior, then integrate locally verified features only as permitted by all checks,
  independent/project reviews and GitHub protections/rulesets. Never bypass a gate
  through a direct push or a cumulative merge.
- Long CI runs independently; continue eligible safe coding in another worktree.
  Reconcile at selection, local acceptance, push, pre-merge and handoff, without
  idle-polling. A new development HEAD needs new consolidated validation before master.
  Keep coverage/cancellation policy unless measured evidence justifies a reviewed change.
- Preserve source SHAs, receipts and rollback evidence. Close superseded PRs only
  after verified integration. Keep source branches until containment and rollback
  are confirmed; never delete unmerged or dirty branches/worktrees.
- States remain SELECTED -> IMPLEMENTING -> LOCAL_TESTING -> LOCAL_ACCEPTED ->
  COMMITTED_PUSHED -> CI_PENDING -> CI_PASSED/CI_FAILED -> MERGE_BLOCKED/MERGE_READY
  -> MERGED -> POST_MERGE_VERIFYING -> MERGED_VERIFIED. CI_PENDING is at most95%.
  A local preparation branch is not an additional accepted development branch.

## Source-bound lane reconciliation

| Scope | Exact source / base | CI and local receipts | Integration state / blocker |
| --- | --- | --- | --- |
| Upstream adoption policy / PR17 | 503b848 /8f505a3 | run40300637754 PASS | Already merged into developmentd5cc181 by owner; no master merge |
| INV-02 accepted scopes / AMFI | 8907f28,45a91a7,79a26ae | Original detailed receipts in PROJECT_STATUS/EXECUTION_STATE; preserve accepted bounds | Present in canonicald5cc181; parent INV-02/INV-05 still unaccepted |
| Cumulative PR16 | d5cc181faae5c61d6de65f00ce21375ce73de33b /masterc47fed9 | exact run40324546766 PASS | OPEN; full cumulative independent review and explicit master/Pages authorization absent; newest future HEAD must rerun CI |
| Yahoo PR18 | daed068adef0ce1ea091dc5efe08d52068f1b77f /d5cc181 | exact run40325761619 PASS;80 backend/12 metadata/one Chrome/four overlapping Axe/privacy0; original post-audit/artifacts/sprint-8f505a3/yahoo/post-pr17/handoff.json | OPEN/READY; mandatory independent project review absent (0); merge stopped |
| Discovery PR19 | d8f57bead981abc2647fcc0f94aee2c57550a87b /d5cc181 | run40336191319 CANCELLED; Windows/Linux PASS, Selenium121618292489 exceeded30m0s; fresh exact-source local66 backend PASS; original Chrome/Axe/privacy retained | OPEN/DRAFT95%; CI incomplete, retry403 Actions write unavailable, independent review0; merge stopped |
| Geography | implementation1c5f11ec9c2f4f476562af0de619f0068cd031df, checkpointdc96b19b03f61409f8803a2928d0e907c8c18292 /d5cc181 | Original56 backend/12 metadata/one Chrome/four overlapping Axe/privacy0; no CI | No PR; diverges from Discovery. Both reconciled on local candidate only; review/new exact-head validation required |
| Local reconciliation candidate | preparation/alfred-consolidation-20261026; merges c3e0fbd,060fda8,52c71ff; final documentation HEAD resolved from Git | 309 backend,19 metadata,3 original Chrome/12 overlapping Axe PASS; migration/system and source ancestry/test containment PASS; AST11,237 nodes; final clean source/history privacy receipt in EXECUTION_STATE | Local only; not pushed, not canonical integration. No exact-head remote CI; Stage7 is not reached |

## Verified governance and publication boundary

Authenticated read-only REST on2026-10-26: both branch protection endpoints returned
**404 Branch not protected**; repository rulesets and effective branch rules returned
**[]**. No protection changed. All PR16/18/19 review lists and review threads are empty.
AGENTS independently requires project review, so an unprotected branch or mergeable:true
is not permission to bypass it. Owner/reviewer must supply the required independent review.

PR19 check annotation explicitly states **The job has exceeded the maximum execution
time of30m0s**. One targeted retry request returned **403 Resource not accessible by
integration**; no retry queued. Owner/authorized maintainer must repair/revalidate CI.
No timeout, sharding, cancellation or coverage setting was changed. Fresh local66 tests
are source-bound backend evidence, not replacement Selenium CI.

Pages is **legacy master:/docs**, public at https://sourabh48.github.io/alfred_ai/.
Master integration needs explicit publishing authorization for the full consolidated
diff, all mandatory checks/reviews, privacy/security, dependencies and rollback gates.
Development integration is not production deployment. Pages/app deployment, provider
activation and private-data uploads are not authorized by source consolidation.

No GitHub/canonical merge or closure was performed. Do not close PR18/19 until source
containment and permitted integration are verified; no branches or worktrees deleted.
Recovery refs/bundle/API evidence: F:/ALFRED_DEV/consolidation-recovery-20261026.
Detailed deliberate conflict resolution and containment: [CONSOLIDATION_STATE](CONSOLIDATION_STATE.md).
