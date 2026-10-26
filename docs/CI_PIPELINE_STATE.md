# Section CI and integration pipeline

Updated 2026-10-26. This is the delivery lane ledger, not a competing feature queue.
EXECUTION_STATE owns active coding; PROJECT_STATUS owns 143 IDs and acceptance;
13 extension stories remain separate. Explicit `sprint` is active for this execution.

## Protocol

- `continue`: resume current unfinished work/integration; finished scope stays done.
- `next`: one selected section, local acceptance/push/checkpoint, then stop.
- `sprint`: select eligible independent sections continuously while CI runs;
  reconcile at selection, local test completion, push, pre-merge and handoff.
- `status`: read-only. Do not claim background execution after the session stops.
- One active coding scope and maximum **three** outstanding candidates, including
  PR #16. Isolated source branches/PRs; explicitly stacked bases where required.
  Never push unrelated work into an already testing cumulative PR.
- LOCAL_ACCEPTED/COMMITTED_PUSHED/CI_PENDING are not full acceptance (at most 95%).
  CI_PASSED plus complete scoped evidence may reach 100%; parent ID stays unchanged.
- States: SELECTED, IMPLEMENTING, LOCAL_TESTING, LOCAL_ACCEPTED,
  COMMITTED_PUSHED, CI_PENDING, CI_PASSED, CI_FAILED, MERGE_BLOCKED, MERGE_READY,
  MERGED, POST_MERGE_VERIFYING, MERGED_VERIFIED, BLOCKED_EXTERNAL, BLOCKED_APPROVAL.
  CI state and merge blocker are separate fields, not conflated.

## Candidates / source-bound evidence

| Task/scope | State/progress | Source/base | PR/CI | Evidence | Merge blockers/recovery |
| --- | --- | --- | --- | --- | --- |
| Cumulative development integration | MERGE_BLOCKED | development/alfred-integrated d5cc181 / masterc47fed9 | PR16 open; exact-head run40324546766 SUCCESS, master review/protection/Pages gates unresolved | Prior accepted INV-02/AMFI/policy receipts preserved; no inherited green from another SHA | Cumulative diff, exact CI, independent review/protection and explicit Pages publication authorization; no master merge |
| INV-05/SCOPE-02 Yahoo integrity | CI_PASSED100%; MERGE_BLOCKED | development/inv05-yahoo-evidence-20261026 daed068 / developmentd5cc181 | PR18 READY/open; run40325761619 PASS; Linux121581905200/Selenium121581905333/Windows121581905400 success | Preserved80 backend/12 metadata/one Chrome/four overlapping Axe/source privacy0; exact source/blobs/receipts match; parent INV-05 unaccepted | Reviews0, applicable protection/rules visibility; source remains on sibling branch; do not push unrelated changes or transfer its CI to Career |
| CAREER-03/SCOPE-01 normalized feed leads | CI_PENDING95% | development/career-discovery-evidence-20261026 d8f57be / base d5cc181 | PR19 DRAFT/open; exact run40336191319 pending, Linux121618291730 PASS, Windows121618292237/Selenium121618292489 running at recovery | Backend66/metadata12/one Chrome/four overlapping Axe/privacy0 preserved; exact handoff under post-audit artifacts/career-discovery-d5cc181 | Review/protection gates; no source changes or unrelated push |
| CAREER-03/SCOPE-02 location restrictions (LOCAL ONLY) | LOCAL_ACCEPTED90%; 95% only after validated commit/push; CI_NOT_SUBMITTED | development/career-geography-20261026 / base d5cc181; isolated F:/ALFRED_DEV/career-geography | No PR/CI; source checkpoint push allowed, NOT a fourth submitted candidate | Backend56, metadata12, one Chrome/four overlapping Axe PASS; source/privacy proof required before push; receipts in this worktree artifacts/career-location-d5cc181 and ci-repair-ac05515 | Owner explicitly permits safe local work at cap3; no fourth PR until capacity frees; source independent of sibling code, shared-file integration needs compatibility checks |

PR17 owner-merged into development asd5cc181, source503b848; policy bounded100%
and exact-head CI40300637754 PASS. Not a master merge. Masterc47fed9 unchanged.
Older PR16 source8f505a3 run40295889832 cancellation/403 retry is historical,
superseded by its new d5cc181 run. No repeated denied action or unchanged suite run.

Candidate cap3 includes PR16, PR18 and PR19. One coding scope only.
Domain source independent; shared tracker conflicts must preserve latest IDs and
accepted evidence. Owner explicitly authorizes an isolated local scope at cap3;
it is not submitted as another candidate until capacity becomes available.
## CI isolation evidence

`.github/workflows/browser-regression.yml` currently groups by
`alfred-release-${{ github.workflow }}-${{ github.ref }}` and cancels in-progress
pull-request runs for that ref. PR16 uses `refs/pull/16/merge`; a distinct PR has a
different ref/group, so its push does not share PR16's cancellation group. This
configuration comparison is not a claim that two newly submitted runs have passed.
No concurrency/cancellation, timeout, runner, sharding or coverage change is made.
Existing GitHub tools handle milestone reconciliation; no new scheduler is needed.

## Merge / publication gates

The owner's latest automatic-section-merge policy supersedes the old manual-only
rule. It does not waive independent/project reviews, protected-branch requirements,
exact-head CI, privacy/security, rollback, dependency or publishing authorization.
Protection endpoint currently returns403; Pages/rules endpoints are unavailable
through the connected tool. Required GitHub rules cannot be inferred from an empty
review list or `mergeable: true`. Owner/reviewer must resolve visibility/governance.

Only browser-regression.yml is tracked under .github/workflows. GitHub's dynamic
Pages workflow previously published master c47fed9 in run **40197771097**; existing
site source includes docs/index.html and docs/guide/index.html, unchanged by the
current cumulative diff. Settings source remains unverified. Separate explicit
authorization to republish the existing public documentation site has been
requested; silence is not approval. No Pages setting, publication or app deployment
is performed here. No automatic merge until every gate is proven.

After an allowed merge, record actual PR/merge SHA, verify source containment and
master CI, safely synchronize preserving other branches/worktrees, then mark
MERGED_VERIFIED. Failed post-merge checks require investigation/approved recovery.
Never fake a check, force-push, bypass protection or treat a queued merge as merged.
