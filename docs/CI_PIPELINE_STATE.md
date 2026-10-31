# Development CI and integration pipeline

## Current D4 native-windows repair — 2026-10-31

State COMMITTED_PUSHED/CI_PENDING after push; closure in
artifacts/d4-native-repair-20261031/checkpoint.json. Nothing below is a green claim.

- Exact run40978060971 at 626c5bc FAILED: native-windows step "Backend and recovery"
  (00:13:44-00:30:55 UTC); five other jobs SUCCESS. It is not green, and its healthy jobs
  transfer to no successor. Job log and proof artifact need authentication, which was
  not available or bypassed, so the failing test ID at that run stays UNVERIFIED by log.
- Root cause reproduced at exact 626c5bc: `test_seven_integrated_journeys` set its reminder
  to midnight UTC on the local date plus one. Effective TIME_ZONE is Django's default
  America/Chicago, so that instant is already past from 00:00 to 05:00 UTC (06:00 in
  winter) and the API correctly returns 400. The failing CI step ran inside that window;
  the 11 native successes in the last 14 runs did not (ad31 ended 37 seconds into it). The
  application was correct; the test depended on time of day.
- Repair is test-only: anchor the reminder to the current instant, and do not start within
  two minutes of local midnight. Before: 1 failure at 01:50 UTC. After: 20 Travel journey and
  reminder cases PASS at 01:52 UTC, inside the window, zero skips. Same change as sibling
  branch `fix/two-backend-tests-20261031` (015e714); that branch itself is not merged.
- Local exact-source allow-list 1569 ran while other suites loaded the host: 12 not passing,
  so NOT a green local gate. The Travel case above; 10 KnowledgeGit errors at the 5s Git
  deadline; one probe-runner timeout. Those 11 passed when rerun alone (14 cases, Travel the
  only failure). Fresh CI owns the gate result.
- NEW HIGH, reproduced, NOT fixed, OWNER_DECISION: no setting overrides America/Chicago.
  At 01:51 UTC on 31 Oct `timezone.localdate()` returned 30 Oct. For an India-based owner
  "today" is a day behind from 00:00 to 10:30 IST (11:30 in winter) across 64 call sites,
  including the Expense `transaction_date` default, budgets, loans and month windows. Changing
  it moves financial date boundaries; entries already made in that window are ambiguous and
  must not be silently reinterpreted or migrated.
- Lower gate risks retained: EXPENSIVE_GLOBAL reached 113 of its 120/hour test budget in the
  allow-list; `manage.py test` discovers 2271 cases against 1569 in the gate, and cases outside
  the gate include a real README contract failure and more 429s when run together.

## Previous D4 exact-head failure repair — 2026-10-30

ad31ca3/run40973869637 FAILED: raw151 unique/149 PASS/2 errors/zero skips,
shards49/51/51; all five available ZIP digests/source parent/tree binding verified
before repair. Native-windows,Linux,shard2 SUCCESS; shards0/1 and aggregate FAILED.
Undo SPACE targeted disabled control before list-refresh finally; packing test
only deleted a cookie which an in-flight authorized response renewed. Both
reproduced deterministically with bounded actual Windows Chrome response barriers.
Fix tests only: visible/enabled wait before real SPACE; revoke exact server Session
and remove configured cookie, preserving empty private DOM and revocation assertions.
No production runtime,workflow,quota,timeout,skip or151-ID inventory change.
Controlled before2 errors→after2 PASS; normal affected6 Chrome PASS,zero skips.
Raw artifacts/intermediate harness failure retained; D1–D3 receipts unchanged.
New commit requires its own six-job/raw artifact closure, not inherited ad31 green.
Exact source/run/checkpoint: artifacts/d4-ci-repair-20261030/checkpoint.json.
PR20 NOT_DRAFT/unmerged: OWNER_ACTION_REQUIRED, supported draft restore forbidden;
no auth/browser workaround. Independent/manual/dependency and D3-C external gates
remain blocked;75/143,0/13 unchanged. No merge,Pages/deploy,production mutation
or backup deletion.

## Previous D4 parser repair / review package — 2026-10-30

Retained exact c28700d CI40931513318: all6 SUCCESS; six ZIP digests and source/
merge-parent/tree binding verified; backend1562/zero skips, browser151 unique/
49-51-51/zero skips-failures, native22/Linux21 PASS. D1–D3 and c287 portable20/
backup8 receipts remain source-bound in artifacts/d3c-20261029; no unchanged
suite reruns. Real corrected-source package acceptance is PENDING.

D4 adds text-only JSON decoding before read and bounded8192character/64token
Accept negotiation for two reproduced HIGH availability issues. Final27 affected
API/session/Career/Loan/public-HTTP tests PASS, including explicit JSON parser
overrides/route-wide pre-read rejection; earlier60-case attempt failed2 API cases/5 subcases,
retained;49 other affected Travel/upload/UI cases passed and are not re-run.
Runtime source changed: new HEAD requires its own six-job CI/artifact closure,
not c287 green. Current SHA/run/state: artifacts/d4-20261030/checkpoint.json.
First candidateae6e0fe/run40971199795:shard0 D1 journey errored at direct packing
input send_keys (ElementNotInteractable); failed artifact12940099979 digest
verified before repair. Existing enabled/visible click helper now synchronizes
the test with the awaited document/list refresh. No assertion/timeouts/coverage
weakened; source runtime unchanged. Successor source requires new exact-head CI;
keep failed run/evidence and all healthy jobs rather than relabelling/retrying blindly.
Targeted actual Chrome D1 journey PASS1/zero skips, all7 journey assertions kept;
unchanged production API guards retain27 focused/4 native HTTP proofs atae6.
Workflow PR path filters may start all six on push; do not manually repeat or
cancel healthy coverage. Expected backend1569 must be verified from raw evidence.

[Review/check identities](D4_PR20_REVIEW.md) distinguish six observed workflow
contexts from unavailable master-protection configuration. PR20 zero reviews/
threads, draft/unmerged; no required-check or approval waiver. Independent request
prepared only; outside auth unavailable, PR-write403 not retried through other
credentials. Formal release remains BLOCKED: dependency advisory triage, current
installer/failure/rollback/clean-PC/device-loss/real-account/manual accessibility,
protection visibility and independent acceptance.75/143,0/13 unchanged; no merge,
Pages/deployment/production migration/operator mutation or backup deletion.

## Previous D3-C package recovery repair / D4 — 2026-10-29

Exact290e857/run40925777403 results remain bound to that source.139 focused cases
and native backup8 PASS; portable290 build PASS, but real packaged restart FAILED
after17 successful checks on a retained hot vault rollback journal. Original stopped
runtime and all evidence preserved. Minimal existing-file RW schema check permits
normal SQLite recovery;75 memory/privacy/corpus/platform tests PASS,zero skips,
plus successful recovery of a protected failed-runtime copy.

D4 cumulative source review found and reproduced planner reminder close/reopen
revival; existing cancellation helper fixes it in the status transaction.33 backend/
2 Chrome PASS,zero skips,151 IDs unchanged. Same-harness re-review clean; outside
Claude authentication unavailable, human approval absent. Formal release BLOCKED.
Latest exact source/preflight/push/package/native/new-CI pointers live in
artifacts/d3c-20261029/checkpoint.json and EXECUTION_STATE. Newest source requires
fresh exact-head six-job CI and portable execution;290 green/build cannot transfer.
75/143,0/13; PR20 DRAFT/unmerged. Installer/compiler and independent/clean-PC/real-
account/device-loss/manual/production gates remain pending. No merge/publication.

## Previous D3-C source closure — 2026-10-29

Source base906e187, exact run40882826087 all6 SUCCESS; verified closure/artifacts
in artifacts/d3b-20261029/head-ci-closure. D3-A/B evidence is preserved unchanged.
D3-C real isolated native backup/restore8 checks PASS, child/launcher exits0,
stopped status/locks verified without rescue. A confirmed restore-publication defect
is fixed with private retained staging and verified atomic no-replace publication.
Focused contracts and source/native receipts are owned by EXECUTION_STATE and
artifacts/d3c-20261029/checkpoint.json. Linux CI retains all existing checks and adds
the3 portable publication tests; exact new Linux execution remains pending.

The new clean checkpoint requires fresh exact-head CI and a fresh portable build/
executable proof. Do not transfer older green or package provenance. Current
commit/push/CI/package evidence lives under artifacts/d3c-20261029; no additional
source commit is needed merely to replace a pending receipt with observed results.
Installer/failed install-update/package rollback remain PENDING without Inno Setup/
current installer. Clean-PC/real-account/device-loss/manual accessibility and
independent release approval remain distinct. Owner-selected D4 cumulative review/
release-gate verification follows bounded D3-C closure.75/143,0/13 unchanged;
PR20 DRAFT/unmerged,NOT MERGE READY. No master/Pages/deploy/operator-data action.

## Previous CI closure / D3-B recovery validation — 2026-10-29

Exact source `a3f52e1c316ffd3d921ad0ee52e48bdbd370aba8`, run40873685637,
attempt1: all6 required jobs SUCCESS. Tested merge checkout
`9384ae6222cb70071b623fc8cc35bbfc09e52785` contains the source parent and has
the identical tree. Receipt: artifacts/d3b-20261029/ci-closure/closure.json.

All6 downloaded artifact ZIP SHA-256 digests verified before safe extraction.
Strict raw-proof revalidation confirms151 unique Selenium cases executed and
passed exactly once,49/51/51,zero failures/skips; hosted aggregate matches the
revalidated JSON. Windows backend1545 PASS,exit0,zero skips,1253.774s; hosted
native22 checks PASS. Linux portable21 PASS,zero skips. Existing suites were not
rerun for this closure; every result above belongs only to exact source a3f52e1.

Observed job durations: native1601s; shards0/1/2 985/897/869s; Linux257s;
aggregate8s. Selenium critical path995s (16m35); workflow start through last
completed job1603s (26m43),API update1604s. These are one-run observations;
no controlled performance or release acceptance is inferred.

D3-A local verification and exact-head hosted CI closure are retained. D3-B is
LOCAL_VERIFIED: final native recovery15 checks PASS with child AND launcher exits0,
owned shutdown/locks verified without rescue;5 controlled crashes and23 lifecycle
commands. Direct WAL visibility proves0/1 occurrences at both worker boundaries;
replay/acknowledgement,3 SQLite integrity checks,DPAPI/vault,Chrome session/owner/
privacy and unchanged money PASS. Runner7/focused125/affected fence1 tests PASS,
zero skips. Final evidence: artifacts/d3b-20261029/native-final and persisted-state.json.
The first passing recovery candidate/source remains preserved separately;
overlapping runs are not added. Final LOCAL_VERIFIED is bounded local acceptance,
not hosted CI for the new source or formal release acceptance.
EXECUTION_STATE owns the exact stage; artifacts/d3b-20261029 owns recovery,
wrapper/source-binding and CI receipts. Changed development source requires fresh
exact-head CI; do not inherit a3f52e1 green. Baseline75/143 and extensions0/13
remain unchanged. PR20 DRAFT/unmerged,NOT MERGE READY; no master,Pages,deployment,
release,real-account mutation or recovery-file cleanup. Clean-PC/manual/
independent/production gates and D3-C/D4/D5 remain separate and pending.

## Previous CI closure / D3-A local verification — 2026-10-29

Exact source `ebdc84ba8e9f38c8f03ef2f35353bb80c29ce88a`, run40839776242,
attempt1: all6 jobs SUCCESS (native-windows, linux-secure-failure, three Windows
Selenium shards and selenium aggregate). Tested merge checkout
`effe5dbc695e652a4dfa0a5331ba3185f69bda98` contains the source parent and has the
same source tree. Receipt: artifacts/d3a-20261029/ci-closure/closure.json.

All6 downloaded artifact ZIP SHA-256 digests verified. Strict revalidation of the
raw shard reports proves151 unique Selenium cases executed and passed exactly
once,49/51/51,zero failures/skips; hosted aggregate matches revalidation. Windows
backend1544 PASS,zero skips, suite1353.836s; hosted native verification PASS.
Linux portable21 PASS,zero skips. No browser/backend suites were rerun for this
CI evidence closure, and these checks apply only to the exact source above.

Observed job durations: native1753s; shards0/1/2 887/913/1118s; Linux279s;
aggregate9s. Selenium critical path1130s (18m50); workflow start through API
completion1757s (29m17). These are one-run observations, not controlled benchmark
results. Earlier failed-run evidence remains in the historical sections below.

D3-A actual Windows native/offline Travel journey is LOCAL_VERIFIED with isolated
synthetic data:11 checks PASS including owned shutdown; native module16 PASS,
zero skips. Successful JSON and PowerShell stderr-wrapper diagnostics are recorded
in EXECUTION_STATE; artifacts/d3a-20261029 owns receipts. New checkpoint source
requires fresh CI; source/preflight/push/PR/run closure pointers are in EXECUTION_STATE.
A changed source
requires fresh exact-head CI; hosted success does not close local offline,
packaged/installer, clean-PC, manual accessibility, independent review,
real-account or production acceptance. Baseline75/143 and extensions0/13 remain
unchanged. PR20 remains DRAFT/unmerged, NOT MERGE READY; no master, Pages,
deployment or release action is authorized by this evidence.

## Repair run40834940011 — 2026-10-29

Recovered ce9c5fe, clean/synchronized. Exact run40834940011 FAILED; Linux and
shards0/1 PASS, native/backend and shard2 FAIL. Artifact ZIP digests verified under
artifacts/ci-40834940011.151 tests executed:150 PASS,1 error,zero skips. Aggregate
correctly rejected the failed matrix; all3 reports present, no accounting defect.

Native sole1543-case error: oversized chunked real-transport test. Sanitized hosted
logs omit traceback; controlled real Windows test reproduces10053 when terminal0
follows early413. Fixture sends the same129 actual payload bytes, then reads413
before terminal framing; declared-length/chunked413 assertions/limits/timeouts
remain.34 upload regressions PASS. Production transport is unchanged.

Shard2 candidate-pagination failure is a confirmed application snapshot race:
session data was read before worker completion, terminal research status after it.
Two-thread SQLite test FAIL before fix; shared atomic/select_for_update payload
snapshot passes default and file-backed IMMEDIATE tests. No provider work under
the lock; owner/CSRF/revision boundaries unchanged.7 candidate tests,81 affected
HTTP/security/runner/aggregate contracts and2 Chrome journeys PASS. Backend total
122 unique cases; repeated IMMEDIATE test is not double-counted. Full151 shards,
49/51/51 assignment, required checks/cache/quota/DPAPI/accessibility stay intact.

Failed-run timings: full1452s, native1347s (backend1543 cases1132.717s), shards
0/1/2 737/1438/1157s, Linux267s, aggregate9s. Native slowest20 are now retained;
observations do not certify a successful whole-pipeline performance gate.
New source/preflight/push/PR/CI receipts: artifacts/ci-40834940011. PR20 DRAFT,
NOT MERGE READY; D3-A waits for every required newest-source job to pass.

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
