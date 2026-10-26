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
| CAREER-03/SCOPE-01 normalized feed leads | LOCAL_ACCEPTED90%; 95% after validated push, exact-head CI pending | development/career-discovery-evidence-20261026 / base d5cc181; resolve source from tests/test_career_discovery_acceptance.py after commit | Separate draft PR to development; exact PR/source/run resolved in artifacts/career-discovery-d5cc181/handoff.json | Backend66 PASS; actual Chrome recovery/unsafe links/owner flow and four overlapping Axe audits zero violations; both-theme contrast>=4.5; metadata12/migration drift PASS; clean source privacy proof before push | Third reserved candidate; full CAREER-03/live-provider acceptance unaccepted; no fourth submission; retarget/reconcile tracker conflicts safely on integration |

PR17 owner-merged into development asd5cc181, source503b848; policy bounded100%
and exact-head CI40300637754 PASS. Not a master merge. Masterc47fed9 unchanged.
Older PR16 source8f505a3 run40295889832 cancellation/403 retry is historical,
superseded by its new d5cc181 run. No repeated denied action or unchanged suite run.

Candidate cap3 includes PR16, PR18 and this Career section. One coding scope only.
Domain source independent; shared tracker conflicts must preserve latest IDs and
accepted evidence. Further candidate selection requires capacity or a safe repair.
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
