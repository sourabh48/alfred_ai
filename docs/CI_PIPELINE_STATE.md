# Development CI and integration pipeline

## CI-OPT-04 hosted reconciliation — 2026-10-29

Exact b0bf1e6 run40779797725 FAILED Windows/backend and Linux/portable, while all
three Windows Selenium shards and stable selenium aggregate succeeded.151 tests
executed/passed once,49/51/51,zero skips; SHA-bound raw/aggregate proofs and artifact
digests retained under artifacts/ci-opt04-20261029. Required check names, sharding,
cache keys, Windows DPAPI/security/privacy/financial/accessibility remain intact.

| Hosted measurement | Seconds / result |
| --- | --- |
| Shard jobs0/1/2 |1265 /886 /960; SUCCESS |
| Aggregate job / browser critical path |10 /1277 (21m17); SUCCESS |
| Prior unsharded Selenium |2192 (36m32);41.74% one-run browser reduction |
| Full failed workflow / native / Linux |1899 (run start to completion) /1897 /247; no whole-pipeline PASS |
| Native backend step / actual1542-case suite |1674 /1638.399; per-case timings absent |
| Pip cache / installs |Restored all5 jobs; native178s, shards218/168/176s; Linux apt+pip71s. Causal cache effect UNMEASURED |

Windows root cause: two stale workflow fixtures still target the old selenium
body/cancellation policy. Reproduced one FAIL/one ERROR, then corrected contracts
retain pinned Axe/hash/order and require all3 Windows shards plus non-cancelling
SHA/event/ref/manual separation. Linux statement-reimport fixture timed out before
persistence; screenshot shows selected file/no feedback, consistent with a click
during summary hydration/form animation. Wait for actual page readiness before
native click; keep all financial/upload assertions and timeouts. Local affected
Chrome PASS; real Linux confirmation remains pending fresh CI.

66 focused contracts and22 unique Chrome cases PASS locally (portable21 plus
shared upload-helper regression).151-case discovery/assignment and independent
strict validation of downloaded hosted aggregate PASS; all6 artifact hashes verified.
Built-in Django --durations20 now records native test
timings through strict privacy-safe ID/numeric-only logging; no full-suite slowest
claim before rerun. Native is the measured bottleneck. No speculative optimization,
quota bypass, assertion weakening or workflow deletion. New source/PR/CI closure
receipts: artifacts/ci-opt04-20261029. PR20 remains DRAFT/NOT MERGE READY.

## CI-OPT-01 workflow disposition — 2026-10-29

Source base25f028d; PR #20 DRAFT/unmerged. Exactly one file exists under
.github/workflows. No workflow is proven obsolete; removed: NONE.

| Workflow / file | Triggers | Jobs / check names | Unique responsibilities | Disposition |
| --- | --- | --- | --- | --- |
| Browser Regression / browser-regression.yml | master push; path-filtered PR; manual dispatch | native-windows, selenium, linux-secure-failure; three additional selenium-shards checks | Windows DPAPI/full backend+financial+privacy preflight/native HTTP/backup/recovery/accessibility; complete browser suite split across Windows; Linux fail-closed + portable browser | RETAIN; original three check identities preserved, selenium now fail-closed aggregate |
| GitHub-managed pages-build-deployment / dynamic/pages/pages-build-deployment | GitHub Pages service; no source YAML in this checkout | Managed by GitHub, separate publication context | Existing Pages publishing | BLOCKED_REVIEW for any change; retain untouched, do not invoke/deploy |

Recent runs40771632812 (SUCCESS),40754201960 (45m Selenium cutoff),40742137700
(Selenium fixture failure),40692181959 (success) all belong to Browser Regression
and their exact source SHAs. Detailed API/protection/run receipts are local under
artifacts/ci-opt-20261029; no rule is changed or assumed waived when unavailable.
The master push and PR events validate distinct integration contexts. Development
push has no trigger, so it does not duplicate PR validation. Manual diagnostics
remain intentional. No workflow_call or overlapping repository workflow exists.

Stable native-windows/selenium/linux-secure-failure checks must remain. Any future
Selenium shards must feed the selenium aggregate fail-closed; no missing/skipped/
duplicate tests, stale SHA evidence or relaxed privacy/native checks are accepted.
Pip caches explicitly hash requirements.txt and constraints/*.txt. They contain
package downloads only, never private/runtime state. Native and Linux commands
are unchanged. Test/tool path filters now include all tests and browser tooling.
Concurrency includes workflow/event/ref/SHA; no in-progress cancellation, and
manual diagnostics are distinct. No development push/PR duplicate is introduced.

### Measured baseline and shard contract

| Measurement | Evidence / value |
| --- | --- |
| Hosted unsharded before | Exact25f028d run40771632812 SUCCESS: Selenium2192s (36m32), tests1959s, pip202s, Chrome setup12s; native1816s and Linux279s |
| Local timing baseline | Full151 collected/executed,1646.39s;150PASS/1timeout, retained. Unchanged focused financial-source recheck PASS. Passing per-case timings in tests/browser_durations.json; slowest20 in artifacts/ci-opt-20261029 |
| Local phase observations | DB setup10.156s; browser startup2.079s; UserData login321.105s/setUp286.746s; document login16.312s; artifacts46.655s; real API-window wait60.016s. Phases overlap, not additive; lifecycle overhead is separate |
| Deterministic assignments | 151 IDs exactly once;49/51/51. LPT uses measured durations with test-ID tie breaks; unknown/invalid durations fail closed and must be measured |
| Executed isolation check | Three concurrent bounded Windows/Chrome cases PASS, including encrypted private original access. Separate SQLite/data/media/cache/browser processes; aggregate PASS. Not a full151 after benchmark |
| After / saved time / cache effect | UNMEASURED until new hosted pipeline completes; no extrapolation from plan weights or smoke sample |
| Residual critical path | Native job already1816s; D1 real rate-window wait retained. Fixture scopes/security/crypto are unchanged, no artificial integration clock or raised quotas |

Every shard discovers the full intended inventory before selecting its measured
assignment. Reports contain selected/execution IDs, outcomes, timings, checkout
and PR-head source SHA, run/platform and isolation metadata. The aggregate verifies
the manifest, every row exactly once, zero skips/failures, every Windows shard job
successful, matching source/run, independent runtime/DB/media/local caches and
matching driver-summary hashes. Incomplete/cancelled/missing artifacts fail it.
No job can inherit another SHA's pass. Matrix fail-fast is false so evidence from
every shard survives. Windows DPAPI semantics are exercised by the original tests.

The stable selenium job emits browser_regression_summary.ci-chrome.json plus the
generic summary in browser-regression-artifacts only after validating every shard.
This is an explicitly aggregated proof, preserving existing readiness consumers.
Raw screenshots/reports remain in browser-regression-artifacts-shard-{0,1,2}.
Branch protection endpoints returned404; authenticated effective branch rules and
rulesets are empty. No rule was changed or waived; project approval gates remain.
actionlint is not installed; local YAML/runner contracts do not prove hosted success.
Final focused contracts:35 PASS; three concurrent bounded Chrome cases and the
aggregate PASS. Closure source/preflight/push/PR/new exact-head CI receipts live in
artifacts/ci-opt-20261029; prior source SUCCESS never certifies the new pipeline.

Runtime improvement/cache effects remain UNMEASURED until actual observations.
Keep D1/D2/C1–C4 evidence and the D3-A/B/C → D4 → D5 continuation unchanged.

**2026-10-27 current state:** the owner closed all PRs and explicitly directed
development consolidation/push. The combined source now contains fc2a4d2 and6fc1e54;
402 backend tests, nine Chrome workflows and16 affected-page Axe audits passed
with the documented targeted repairs. No PR is created/reopened. Authenticated
development protection/effective rules are empty; no rule changed or bypassed.
Remote CI remains separate and is not claimed green; master/publication gates
remain mandatory. PROJECT_STATUS's active checkpoint and exact-head receipts own
the latest merge/push state. The following2026-10-26 ledger is historical.

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
