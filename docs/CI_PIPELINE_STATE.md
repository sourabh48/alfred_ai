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
| UPSTREAM-POLICY / sprint contract | CI_PASSED100%; MERGE_BLOCKED | development/upstream-policy-20261026 / 503b84864cc9f61f8f254c8436e4b0183d04e513 | 8f505a3; depends on unmerged PR16 bootstrap/execution docs | Draft #17; exact-head run40300637754 PASS; Windows121497359610/Selenium121497359953/Linux121497360147 success | 12 metadata/CI-ref-isolation PASS, zero skips; four pinned repo identities/licenses/source-test catalog; privacy0; no upstream integration claimed; Chrome/money N/A (policy only) | Same master gates; stack target development/alfred-integrated, not master-independent | Not merged | Preserve source/run; policy closure in yahoo/policy-ci-pass.json; do not transfer green CI to new Yahoo source |
| INV-05 / SCOPE-02 Yahoo observation integrity | COMMITTED_PUSHED95%; BLOCKED_EXTERNAL / CI_NOT_SUBMITTED | development/inv05-yahoo-evidence-20261026 / c60c807faac3f7c269a9041eb8d88abf67a5ac0c implementation; later docs checkpoint resolved from EXECUTION_STATE | 503b848 / PR17 then PR16; explicitly stacked | No PR/run assigned: connector creation403, authenticated browser disconnected/native pipe absent, gh absent; yahoo/handoff.json records exact refs | 80 backend +12 metadata PASS; one unique Chrome +4 overlapping Axe audits zero violations; both-theme contrast; Decimal/ownership/outage/expiry/recovery; source privacy0 | Restore existing authenticated browser or owner creates prepared scoped draft; reviews/protection/Pages/dependency gates remain; full INV-05 unaccepted | Not merged | Submit prepared compare link/pr-draft.json; exact-head CI then gates; no fourth candidate and no repeated denied action |

Candidate limit now includes PR16, policy PR17 and the Yahoo section's reserved
third slot. New branches must retain an exact independently reviewable
base. When eventual master contains prerequisites, retarget and revalidate rather
than transplanting dependent commits or rewriting accepted history.

Resolved policy handoff: PR **17**, draft, source **503b84864cc9f61f8f254c8436e4b0183d04e513**,
base development/alfred-integrated at8f505a3; run **40300637754 PASS**, bounded policy100%.
PR creation connector403 was resolved through the already signed-in browser UI;
no permissions/credentials changed. Exact metadata in policy-handoff.json.

Active third candidate: **INV-05/SCOPE-02**, COMMITTED_PUSHED95% on
development/inv05-yahoo-evidence-20261026, pinned base503b848 / PR17 dependency.
Sourcec60c807 pushed/remote verified, privacy0; PR creation externally blocked, no CI run submitted. Resume through the exact compare link in EXECUTION_STATE. Retarget/revalidate only after
prerequisites reach master. Candidate capacity is now reserved at three; do not
submit a fourth while these integration blockers persist.

PR16 targeted Selenium retry request was denied **403 (Actions write unavailable)**.
No retry was queued. Owner/authorized maintainer must rerun cancelled job121481723278;
successful native/Linux jobs are preserved. Do not repeatedly retry denied access.

## Current reconciliation — after owner merged PR17

- PR17 confirmed merged **into development/alfred-integrated**, merge d5cc181faae5c61d6de65f00ce21375ce73de33b, source503b848. Policy exact-head run40300637754 PASS retained; development merge has identical treeefc4263eaab7f213c4b479ef6c5ebfd0530549d7. Local integration fast-forwarded; master unchangedc47fed9. Do not label this MERGED_VERIFIED on master.
- PR16 now has sourced5cc181, fresh run40324546766 CI_PENDING. Earlier8f505a3 cancellation and failed retry403 above are historical; no inherited green check. Required master reviews/protection/Pages gates remain unresolved.
- Yahoo scope95%, unchanged sourcec60c807 / checkpoint8679824; all8 accepted Git blobs and four receipt hashes preserved (raw EOL hashes changed on checkout). Existing signed-in browser restored. Submit separate draft from development/inv05-yahoo-evidence-20261026 **against development/alfred-integrated atd5cc181**, not the now-merged policy branch. Actual post-recovery source/PR/run in yahoo/post-pr17/handoff.json; CI_PENDING only after submission.
- Outstanding integration capacity: PR16 plus Yahoo =2/3. PR17 closed; old candidate-cap/browser-blocker text above is historical. Current coding/integration remains INV-05/SCOPE-02; next queued CAREER-03 has not started. Do not make an unrelated push to a running PR.


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
