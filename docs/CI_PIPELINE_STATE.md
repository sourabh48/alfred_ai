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

| Task / scope | State / local completion | Source branch / SHA | Base / dependency | PR / CI | Local acceptance | Review / integration gates | Merge / post-merge | Recovery |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cumulative integration; includes INV-02 scopes, INV-05/SCOPE-01 and earlier sections | CI_PENDING after cancellation; INV-05/SCOPE-01 accepted100% at79a26ae | development/alfred-integrated / 8f505a3f5fc553e9b1664e3f5827044c76eebb54 | master c47fed95f919859aa62f1875512e3cb8452f2d48 | #16; run40295889832 native121481722900 and Linux121481723333 PASS, Selenium121481723278 CANCELLED; one targeted retry requested, result in policy handoff receipt | Accepted source79a26ae CI40292154135 all three PASS;56 backend +11 metadata,one Chrome/4 overlapping Axe;privacy0;prior INV-02 retained | MERGE_BLOCKED: cancellation is not PASS; reviews0/protection403/Pages approval absent/full cumulative diff review | Not merged; no merge SHA/post-merge acceptance | Reconcile retry at natural checkpoint; do not append unrelated sections or rerun successful jobs |
| UPSTREAM-POLICY / sprint contract | LOCAL_ACCEPTED90%; CI_PENDING95% after push | development/upstream-policy-20261026 / resolve commit touching this row | 8f505a3; depends on unmerged PR16 bootstrap/execution docs | Resolve PR by unique source branch; actual PR/run recorded in ignored `artifacts/sprint-8f505a3/policy-handoff.json` after creation | 12 metadata/CI-ref-isolation PASS, zero skips; four pinned repo identities/licenses/source-test catalog; no upstream integration claimed; Chrome/money N/A (policy only) | Same master gates; stack target development/alfred-integrated, not master-independent | Not merged | Push once and open scoped stacked PR; next independent section records assigned PR/run IDs without restarting this PR |

Candidate limit currently includes PR16 plus policy section; next selected feature
may use the third slot. New branches must retain an exact independently reviewable
base. When eventual master contains prerequisites, retarget and revalidate rather
than transplanting dependent commits or rewriting accepted history.

PR16 targeted Selenium retry request was denied **403 (Actions write unavailable)**.
No retry was queued. Owner/authorized maintainer must rerun cancelled job121481723278;
successful native/Linux jobs are preserved. Do not repeatedly retry denied access.

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
