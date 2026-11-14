# Development CI and integration pipeline

## Owner checks, route optimiser and think-before-answering to master - 2026-11-14

Owner asked to merge everything to master (2026-11-14). Branch work/email-signin-2026-11-14 in the
owner-decisions-1112 worktree, base origin/master fec7404: the owner checks and email sign-in commits, merged with
feat/travel-route-optimiser (a1e96ef) at 81708a2 and feat/auto-thinking (cf90877, think before answering) at 5361717.
A local full run found a stale Duffel Stays link in PROJECT_STATUS (fixed) and a boundary test that read a model
window learned from this PC's running Ollama (the test now clears that cache first). The owner approved
users 0007_email_identity and investments 0009_fund_units_and_nav (both additive) on 2026-11-14, so the backend
step's `--reviewed-source` names 81708a2. Left out on purpose: feat/skyscanner-link (replaced by the Skyscanner
provider), work/fix-all-2026-11-13 (its hotel links and map-test fix reached master in 7e3cc1b),
work/awie-scrapling-review (Scrapling pilot not before 2026-11-18), the 2026-11-04 WIP manifest and the 2026-11-11
review branches; all stay as they are. Pushed a4c8a64: run 43582300103 CI_FAILED (three Selenium shards on chat
history being on by default and a too-quick speech stop; backend shard 3 failed for a reason not reproduced locally,
offline or with the calendar parser, and job logs need a GitHub sign-in). CI fixes 1d3a858 and 96cdb64 pushed with
the state commit c53f652: run 43593128467 at 96cdb64 CI_PASSED (Linux, four Windows backend shards, native, three
Selenium shards). The owner's app runs master with both migrations applied.

## Final-development audit and CI coverage - 2026-11-13

LOCAL_ACCEPTED, not pushed. Branch work/fix-all-2026-11-13 in the owner-decisions-1112 worktree, base origin/master
3dc51ff (run 43307042381 PASS on that commit only). The backend job now lists 254 labels (was 179); eight files stay
out with reasons in BACKEND_NOT_IN_CI. Local: four backend shards 2,988 tests, no failures (14 skips from the calendar
test parser missing on this PC, in files CI already ran); release validation 78 PASS; tracker check clean. No new
docs file, no migration, no dependency, no workflow change. Blocker: the owner's OK for the push. After the push:
read the exact-HEAD run; a skip or failure in a newly listed file on the hosted runner is the known risk.

## Closing master merge correction - 2026-11-11

Codex single writer; MASTER_MERGE on work/master-review-fixes-20261111 in the
isolated master-review-fixes-20261111 worktree. Code bf49dd4ae168e0d5cab104008c358570b26876ab,
base e276370b724580d184044280e975452269df8bec. Root cache/notes are preserved.
198 focused backend PASS85.731s and8 Chrome PASS93.549s, zero skips, on identical
precommit code blobs. Empty-extraction create/link retains unknown originals;
null retry metadata and owner edits during running workers are covered. Browser
fixtures keep the memory-connection lock only for legacy in-memory test runs;
file-backed requests run concurrently. No timeout/security/production change.

Closing e276370 review completed and caught an introduced empty-original IndexError;
that P2 is fixed and regression-tested in both domains. CI42991191022/a583407
completed FAIL: all backend/native/Linux and two browser shards passed; the last
browser shard timed out loading a source picker behind the obsolete fixture lock.
Neither old checks nor review markers accept this newer source. Current checkpoint
needs clean full-range preflight, Windows runtime check, final delta review and
full exact-head CI. Source/receipt details and exact changed paths: STATE.json and
TEST_EVIDENCE.md; local artifacts/master-merge-20261111/empty-review-final-backend.log
and concurrent-browser-final/. All earlier failures/skips remain retained.

MERGE_BLOCKED pending those gates and explicit final-scope Pages publication
approval. Master/canonical development, owner runtime/data/keys/schema/models and
installation remain unchanged. Baseline85/143 and extensions0/13 unchanged; full
release/real-account/package/3.0 gates stay separate. Continue only this merge.
Next: validate the clean checkpoint HEAD, re-review e276370..HEAD, push preparation
source and dispatch exact-head CI; no PR reopen or master merge without every gate.


## Master merge repair checkpoint - 2026-11-11

LOCAL_ACCEPTED / MERGE_BLOCKED. Code cd2117e8c584a8ddff164fec4ee2eedae2cc1d37,
work/master-review-fixes-20261111; base a583407, master c730360, canonical dev b929775.
No canonical integration, PR reopen, deployment or protection/Pages change.
186 focused backend PASS; Chrome loan/statement PASS plus unchanged investment
PASS alone after retained timeout. Exact receipts, skips, revisions and next command
are in EXECUTION_STATE and ai_progress/STATE.json / TEST_EVIDENCE.md.

Prior exact-source CI42991191022/a583407 is pending at this checkpoint. Never
transfer its checks to the newer source. Current checkpoint needs clean full-range
preflight, final independent review and full exact-head CI before master readiness.
Actual a583407 static review completed; reproduced P3 repairs need delta review.
Pages publishes master:/docs; final concrete documentation scope needs explicit
owner authorization. Full release/owner/package/3.0 gates stay separate.
Rollback: retained source/base commits and all clean preparation worktrees; no owner
runtime or schemas changed. Preserve root cache/dirty notes. Continue only this merge.

## Expiry-aware source review navigation - 2026-11-11

USE-02/expired-review-navigation LOCAL_ACCEPTED / COMMITTED_LOCAL, source
0d34a7e753e783cf602e65b72e978897e64ec8ed, base 801b0c9e2013530374c1da383586197b5837fa61,
work/usability-integration preparation. Exact-source 77 backend/3 Chrome PASS;
source/privacy/dependency/migration preflight and AST graph update PASS. No remote
CI IDs, push, PR, merge or deployment. Canonical development remains
development/alfred-integrated; closed integration PRs untouched. Cumulative review/
protection/authorization/compatibility/release gates remain, no merge-readiness claim.
Rollback: retained parent/source commits and clean detached validation worktree
F:/ALFRED_DEV/usability-expiry-check-0d34a7e; no runtime changes. Both sprint leaves
checkpointed, exact files and evidence in STATE/TEST_EVIDENCE.


## Explicit knowledge readiness - 2026-11-11

USE-02/knowledge-source-readiness LOCAL_ACCEPTED / COMMITTED_LOCAL (not PUSHED):
source 90f1ee90a9487e1d36a88cf9443825f083e0ca60, base d18220443e62dfaa1bbc13d903dc93ece449a5ac,
work/usability-integration preparation. 99 backend/3 Chrome PASS at exact source;
source/privacy/dependency/migration preflight PASS; no remote CI run IDs. GitHub MCP
read-only canonical branch lookup succeeded, no updates. Canonical development remains
development/alfred-integrated; existing closed PRs untouched. Cumulative source/reviews/
protection/owner authorization and full release gates remain, no integration claim.
Rollback: retained parent/source commits and detached clean validation worktree
F:/ALFRED_DEV/usability-knowledge-check-90f1ee9; no runtime changes. Evidence: STATE
and TEST_EVIDENCE. Sprint continues safe preparation, no master/publication action.


## Cancellable domain chat - 2026-11-11

USE-03/cancellable-domain-chat LOCAL_ACCEPTED / COMMITTED_LOCAL on
`work/usability-integration`, final source 83f331994f9d672b852c105bc9970e4296ef794c,
base c1f850e229f5f3d21d9db802d6835a398196c6b5. Five existing local source scopes now
support Stop/retry; domain answers remain fully buffered, with source and financial
validation intact and canonical offline cards supported. Primary 1aee878 has 312
backend/8 Chrome PASS; final 83f3319 has 2 actual Waitress/Ollama PASS, no skips.
Four new Axe audits zero violations/manual contrast open. Final source/privacy/
dependency/migration preflight and AST graph update PASS. No owner runtime/remote/
calculation/schema/dependency/model-policy change; cache edit preserved. Baseline
85/143, extensions 0/13 unchanged. Full USE-03 and owner/CI/independent/package/release/
3.0 gates remain. READY_FOR_NEXT; no next task selected. Exact files/evidence and
next command: docs/ai_progress/STATE.json and TEST_EVIDENCE.md.

## Saved general streaming - 2026-11-11

USE-03/saved-general-streaming LOCAL_ACCEPTED / COMMITTED_LOCAL on
`work/usability-integration`, source `b9688647c776ce818a7ec4d2f218cd63639420a5`,
base `ba5d376df84fa179a9f124ca11198ce97cfd79d0`. Existing transport now serves
consented saved general chat through shared history/context/replay controls.
Transactional cancellation guard and honest completed-save/lost-response recovery
preserve drafts and single-turn retry. Exact-source 269 backend/6 Chrome/2 real
Waitress-Ollama PASS, zero skips; four new Axe audits zero violations/manual contrast
open. Clean source/privacy/dependency/migration preflight and AST graph update PASS.
No owner runtime/remote/schema/dependency/model-policy change; cache edit preserved.
Baseline 85/143 and extensions 0/13 unchanged. Full USE-03 and owner/CI/independent/
package/release/3.0 gates remain. READY_FOR_NEXT; no next task selected. Exact files,
receipts and next command: docs/ai_progress/STATE.json and TEST_EVIDENCE.md.

## Private message search - 2026-11-11

USE-03/private-message-search LOCAL_ACCEPTED / COMMITTED_LOCAL on
`work/usability-integration`, source `d1ba65750f95b1102d4a2cc32cb19c040a48791e`,
base `af2801d54b04acfc69bc39b27cc6bec775e731a1`. Bounded encrypted title/message
search reuses existing history/consent; no plaintext index, provider or excerpts.
Final-source 53 focused backend/6 Chrome PASS; four new Axe audits zero violations,
manual contrast open. Broader 261 backend PASS at b60d809 is recorded separately.
Windows new-process search at capacity PASS in 674ms, not a universal speed claim.
Final clean source/privacy/dependency/migration preflight and AST graph update PASS.
Owner/CI/independent/package/release/3.0 gates remain. No owner runtime or remote
change; cache edit preserved. Baseline 85/143 and extensions 0/13 unchanged.
READY_FOR_NEXT; no next task selected. Exact files, evidence and next instruction:
docs/ai_progress/STATE.json, TEST_EVIDENCE.md and docs/EXECUTION_STATE.md.

## History-outage page-only source recovery - 2026-11-11

USE-03/history-outage-page-only-sources LOCAL_ACCEPTED / COMMITTED_LOCAL on
`work/usability-integration`, source 9abff6e496dd009a6a1a7ef05fbe3dc92707f67d,
base 8d2a78f43aff8fb81e70f39ddae9bdcf63877214. Independent page-only questions work
without history status; metadata retry preserves drafts/consent and conflict/auth guards.
Exact-source 252 backend/5 Chrome PASS; four Axe audits zero violations/manual contrast
open. Real Ollama 1 FAIL in 32.770s at deadline, unchanged retry 1 PASS in 15.814s; both retained.
Clean source/privacy/dependency/migration preflight PASS; full release/CI/owner/package/
independent/3.0 gates remain open. No owner runtime or remote changes; cache edit preserved.
Baseline 85/143, extensions 0/13 unchanged. READY_FOR_NEXT; no next task selected.
Exact files, receipts and next command: docs/ai_progress/STATE.json,
TEST_EVIDENCE.md and docs/EXECUTION_STATE.md.

## Reviewed Career history recovery - 2026-11-11

USE-02/career-history-recovery LOCAL_ACCEPTED / COMMITTED_LOCAL on
`work/usability-integration`, sourcee2deec85ae6b4dd9475b6d785852545cc5496317,
base d33bd9f0884a5a7b7221c7a03315d77a7c363444. Owned preview/confirm/cancel recovers
an unavailable timeline with exact source retention and server-bound single-use review.
Exact-source246 backend/3 Chrome PASS; four recovery Axe audits zero violations/manual
contrast open. Actual private file-SQLite concurrency/new-process confirmation/replay
PASS; clean source/privacy/dependency/migration preflight PASS. Full parent/release/
owner/package/independent/CI/3.0 gates remain open. No owner runtime or remote changes.
Baseline85/143, extensions0/13 unchanged. READY_FOR_NEXT; no new task selected.
Exact files, receipts, limits and next command: docs/ai_progress/STATE.json,
TEST_EVIDENCE.md and docs/EXECUTION_STATE.md. Cache edit preserved.

## Career follow-up integrity - 2026-11-11

USE-04/career-follow-up-integrity LOCAL_ACCEPTED / COMMITTED_LOCAL on
`work/usability-integration`, source5a10279b58a1e6ade4806a3d0225b1a15ddc9d00,
basee9e35b7a62484de2f95292a333fc9a5c58060232. Shared Career history validation
repairs guessed dates/list crashes without rewriting invalid records. Exact-source
261 backend/3 Chrome PASS; four history Axe audits zero violations/manual contrast
open. Clean source/privacy/dependency/migration preflight PASS. No CI/push/PR/merge,
owner-runtime or deployment change. Release/owner/package/independent/3.0 gates
remain open. Baseline85/143, extensions0/13 unchanged. READY_FOR_NEXT, no next task.
Exact files, receipts, limitations and next command: docs/ai_progress/STATE.json,
TEST_EVIDENCE.md and docs/EXECUTION_STATE.md. Cache edit preserved.

## Career application progress - 2026-11-11

USE-04/career-application-progress LOCAL_ACCEPTED / COMMITTED_LOCAL on
`work/usability-integration`, source7643c25426a1bc65dcc92a09bc3d50ad0e8a9d93,
base05ac976828e913239f67c09ad21f15fc08e2262e. Exact-source337 backend/3 Chrome PASS;
four Career Axe audits zero violations/manual contrast open. Clean source/privacy/
dependency/migration preflight PASS. No CI/push/PR/merge/deployment or owner runtime
changes; technical/promotion/owner/package/independent/3.0 gates remain BLOCKED.
Baseline85/143, extensions0/13 unchanged; full USE-04 remains partial. READY_FOR_NEXT,
no next task selected. Exact files, receipts and next command: docs/ai_progress/STATE.json,
docs/ai_progress/TEST_EVIDENCE.md and docs/EXECUTION_STATE.md. Cache edit preserved.

## Local tool registry - 2026-11-11

USE-04/typed-read-only-tool-registry LOCAL_ACCEPTED / COMMITTED_LOCAL at
334db14b6ef51b35ad2d4bb5ac21cd617f7600a7 (base54eb766). Six existing adapters now
pass through typed owner/consent/output/deadline/audit controls and the actual chat UI.
296 backend/5 Chrome/1 real Ollama PASS; clean source/privacy/dependency/migration
preflight PASS. Full USE-04, MCP transport, owner/CI/package/independent/release gates
remain open. No owner runtime or remote change. READY_FOR_NEXT, no further selection.
Exact files/evidence: [STATE](ai_progress/STATE.json), [TEST_EVIDENCE](ai_progress/TEST_EVIDENCE.md).

## Codex continuation checkpoint - 2026-11-10

CODEX_TO_CLAUDE_READY; no agent launched. Preparation branchwork/usability-integration;
latest source30ab4d8ac80c7fabcd5e31aca40edf4f71570b62. Bound actions, offline record
recovery and evidence display are locally accepted within their recorded scopes.
Tests/preflight remain bound to each exact source in [TEST_EVIDENCE](ai_progress/TEST_EVIDENCE.md)
and [HANDOFF](ai_progress/HANDOFF.md); no CI/push/merge/install or owner runtime change.
Typed read-only registry selected next, NOT_IMPLEMENTED. Cache edit preserved;
baseline85/143, extensions0/13 and whole release/owner/3.0 gates unchanged.

## Sprint checkpoint - 2026-11-10 offline record recovery

Codex sole writer; sprint continues on `work/usability-integration`. USE-04/offline-record-overview
LOCAL_ACCEPTED / COMMITTED_LOCAL, sourceebbd0560507706babbea20635ab74ed20b0cc831,
basee2161012e94151d7c7933a1205520193c0b1211a. Supported owned record questions now
retain revalidated canonical cards when local inference fails, without invented
explanations, calculations, cloud disclosure or saved turns. Unsupported/stale/
foreign/expired-session evidence still rejects. Full USE-04 registry/orchestration remains.

Exact-source226 backend PASS108.714s;4 Chrome PASS61.562s (runner wall74.0s);
1 unmocked Ollama PASS10.474s. Four recovery Axe audits zero violations/manual
contrast open; action-audit regression also passes. Clean source/privacy/dependency/
migration preflight PASS; release gates remain BLOCKED. No schema, owner runtime,
key, weights, media, backup, installation or remote changes. Baseline85/143 and
extensions0/13 unchanged. Cache edit/hash preserved. Exact files/receipts: STATE and
TEST_EVIDENCE. Next: reproduce misleading currency formatting of baseline record IDs
in the shared source-card renderer, then apply a bounded presentation repair.

## Sprint checkpoint - 2026-11-10 bound savings-goal actions

Codex is the sole writer; active sprint continues. Preparation branch
`work/usability-integration`, source `0ca216859c8a4f5a75594e0cb88cc625c1abddb1`,
base `378e8ab5b38bf60c0db466b371e4774d0e1d2c72`. USE-05/bound-savings-goal-confirmation
is LOCAL_ACCEPTED / COMMITTED_LOCAL. Existing arbitrary-payload, duplicate replay
and stale-progress overwrite defects were reproduced, then fixed in the shared path.

Server-issued IDs bind exact reviewed fields with a keyed fingerprint in the
existing redacted audit table. Ten-minute expiry, owner/revision checks, transactional
claim/write/receipt, idempotent replay, server cancellation and safe interrupted
retry are enforced. No new financial engine/schema/dependency. Current Budgets
Decimal serializer remains authoritative; no currency policy or external action added.
Older cards without server IDs must be reviewed again. Clearing audit records makes
old IDs unavailable; it cannot re-enable them. The proposal body is not stored in logs.

Exact-source 136 backend PASS (207.856s), three Chrome PASS (37.367s Django test
runtime; runner wall50.281s), four light/dark1440/390 Axe audits zero violations;
gradient contrast/manual review remains. Actual Waitress/file-SQLite simultaneous
confirmation201/200 and process-restart replay200 left one goal/one receipt.
Source/privacy/dependency/migration preflight PASS; no CI/push/PR/merge/deployment.
No owner database/config/key/model/document/backup/installation changes. Cache edit
hash41C88BDBB1C03AD218EDE0190C62C9370C01717842FAE6ADCEE368A6D4E2BAE9 preserved.

Approval gates: owner/package/upgrade/independent/CI and3.0 remain. Baseline85/143,
extensions0/13 unchanged; USE-05 as a whole remains partial. Next executable step:
inspect and reproduce model-outage behavior for existing canonical record overview;
select a bounded USE-04 read-only repair only if grounded in that path. Do not repeat
accepted import/streaming work. Exact files and receipts: STATE/TEST_EVIDENCE.

## Safe answer formatting source - 2026-11-10

Source a74995c94998bfbd3adeb91654554836cb452bb6, base
86243336764bf233c6a2ac439d73513b06c031c3: LOCAL_ACCEPTED / COMMITTED_LOCAL on
work/usability-integration. Exact-source 93 backend PASS (31.390s), four Chrome
PASS (45.569s), one real Chrome/Ollama comparison PASS (10.040s). Four Axe audits
zero violations/manual contrast open. New regular browser cases are in the measured
browser inventory; actual local-model acceptance is separately opt-in. No checks or
skip policy weakened. Source/privacy/dependency/migration preflight PASS; promotion
BLOCKED. No CI IDs, push, PR, merge, install or publication. Owner/independent/manual/
package/upgrade/whole release gates remain. `next` ends READY_FOR_NEXT, no new scope.

## Page-only local streaming source -2026-11-10

Source0712fa2ede3c6fb4051ec3654232e05e0a7d9479, base0842d0e11a2988db2dd2883fbcdca47b7df55f7a:
LOCAL_ACCEPTED / COMMITTED_LOCAL on work/usability-integration.239 exact-source
backend PASS (140.274s),28 caller regressions PASS (12.486s),4 exact-source Chrome
PASS (63.325s),2 actual native Waitress/Ollama PASS (16.387s). New16-case protocol
module is in the existing measured backend shards; real-model acceptance remains
explicit opt-in as before. No required skip/coverage policy weakened. Clean
source/privacy/dependency/migration preflight PASS. Zero automated active-Stop Axe
violations; manual contrast open. No CI IDs/push/PR/merge/installation/publication.
Source acceptance does not pass packaging, owner, independent or release gates;
promotion remains BLOCKED. READY_FOR_NEXT under `continue`; no automatic new scope.

## Usability sprint source -2026-11-10

Sourcec365a38a707d45da87eada1c348fafcfd8da0a04, base1265ff736b78d753a8bf73360b350acc5326a46b:
LOCAL_ACCEPTED / COMMITTED_LOCAL on preparation branchwork/usability-integration.
Four slices: guided readinessa78096e, budgets/fiction contextb535299, private
conversation controlsa173b3e, page dialoguec365a38.194 consolidated backend PASS
(89.900s);3 affected exact-source Chrome PASS (51.857s).2 page-dialogue journeys
and actual Ollama styles/saved/page continuity receipts retained separately; no
summed overlapping counts. Source/privacy/dependency/migration preflight PASS.
No remote CI IDs, push, PR, master integration, installer or deployment. Historical
CI does not validate this source. Native worker/package journeys not rerun for
these UI/read-only/context changes. Owner/independent/manual accessibility/package/
upgrade/release gates remain; promotion BLOCKED. CODEX_TO_CLAUDE_READY is context
continuity only. See current STATE/TEST_EVIDENCE; older stop/next statements below
are historical. No baseline/extension acceptance changed.

## Investment usability source -2026-11-10

Sourceb42988b4ceeab3cfa07dec0a4ad9b345d2f3ec77, base407789e56cba37210938e182c0e44564289374df:
LOCAL_ACCEPTED / COMMITTED_LOCAL on work/usability-integration.272 backend plus45
focused overlapping cases PASS; real Chrome/four Axe audits and native24 PASS,
manual contrast remains open. Final binary-file adapter has focused follow-up
coverage; no new full exact-head CI claim. Clean source/privacy/dependency/migration
preflight PASS. No push, PR, merge, installation or publication. Promotion remains
BLOCKED; owner/independent/package/real-account acceptance still required. Current
continuation completed with READY_FOR_NEXT; no next task automatically selected.


## Loan preservation follow-up ? 2026-11-10

Sourcec2d1517a364d385c7605ac346d3de86a35734326, base2350cad169898ad909209a3bde6dd4ffb2fb8a9b:
LOCAL_ACCEPTED / COMMITTED_LOCAL;86 affected backend/1 actual Chrome PASS.
Clean source/privacy/dependency/migration preflight PASS. No CI dispatched or
integration/publication. Broader215/native22 belongs to88c1df8. All release gates
remain open; CODEX_TO_CLAUDE_READY is context continuity only.


## Loan usability source ? 2026-11-10

Source88c1df826aa14fc56247678cabaa175356d62882, base8926e4209bb63abe64b12c4a58bea4e6fe1bed84:
LOCAL_ACCEPTED / COMMITTED_LOCAL on work/usability-integration.215 backend,2 Chrome,
native22 PASS; clean source/dependency/migration/privacy preflight PASS. No new CI
run ID, push, PR, merge or deployment. Old CI does not validate this diff. Promotion,
owner/package/independent/manual accessibility acceptance remain gated. Codex is
active; next scoped task is investment review, per EXECUTION_STATE and ai_progress.


## ALFRED_USABILITY_INTEGRATION — 2026-11-09

Latest validated source0f3560557d6178c07f07dfeb05c4a975646c3e7b: bounded statement
slice LOCAL_ACCEPTED / COMMITTED_LOCAL;157 backend, actual Chrome/four Axe audits,
native19 PASS. Source/privacy/dependency/migration preflight PASS in clean detached
worktree; first dirty-worktree refusal preserved with no waiver. No CI dispatched
or source pushed. Promotion BLOCKED; no installation/publication/master action.
CODEX_TO_CLAUDE_READY is a context handoff, not CLAUDE_FINAL_REVIEW_READY.

Local source commits cba5b53 and4019ee2 are now recorded; no push or new CI run.
USE-02 statement preview/confirmation is IMPLEMENTING on the same preparation
branch, with synthetic regression validation underway. Active source/state and
single-writer handoff are in docs/ai_progress. Master, installation and publishing
remain untouched; no 3.0 branch is authorized before 2.0 acceptance.

Bounded LOCAL_ACCEPTED on preparation branch `work/usability-integration`, source/base
`a9947bc88d8e96255949c0652892c2cb7d9ab2da` plus scoped working changes.
See the separate usability ledger and EXECUTION_STATE for exact local evidence.
No CI dispatched, no source push/PR/master integration, no reused green claim.
Historical CI PASS at c730360 does not validate this new diff. Native source,
real local synthetic-model acceptance PASS. Local commit attempt failed because
Git author identity is unset; owner identity selection pending. HEAD unchanged;
17-file first slice staged, remaining chat/checkpoint changes unstaged. Existing
operator installation remains untouched. Required release,
owner and independent acceptance gates remain open.

## TRAVEL-20 migration review — 2026-11-06

The owner approved migration `apps/mobility/migrations/0014_trip_video.py` (new empty `TripVideo` table) on
2026-11-06, so the backend step's `--reviewed-source` names the TRAVEL-20 commit `d8a51e3`. Run 42194736278 at
`99b8e8f` (Piper dependency re-pin): CI_PASSED.

## AI-18 dependency review — 2026-11-06

AI-18 adds `piper-tts==1.8.0` (GPL-3.0, run only as a separate program and excluded from the PyInstaller build)
and `pathvalidate==3.3.1` (MIT) to `requirements.txt` and both constraint files. The owner approved Piper on
2026-11-06, so the backend step's `--reviewed-source` names the AI-18 commit. Model files are not in Git; CI tests
run without them (speech buttons stay hidden and the services are mocked).

## FIN-06 migration review — 2026-11-06

CI run 42179590852 at `164d394` failed all four backend shards in preflight (`migrations`): migration
`apps/budgets/migrations/0003_savings_goal.py` was not in the reviewed source `b2f8936`. The owner approved the
migration on 2026-11-06, so the backend step's `--reviewed-source` now names `164d394`. Any later migration or
dependency change is refused again until reviewed. Run 42183546064 at `e990030` then passed shards 0, 2 and 3;
shard 1 failed because `tests/test_remaining_public_http.py` still called the scraper INV-04 removed (the same
cause as the earlier `1a36f53` shard-3 failure). Reproduced from a clean checkout and fixed in the test.
Run 42185812614 at `e8ef8f4`: CI_PASSED (Linux, four Windows backend shards, native, three Selenium shards).

## RUNTIME-11 build pins — 2026-11-05

State LOCAL_ACCEPTED on master, not pushed (push at phase end). `b2f8936` pins PyInstaller's dependencies in
`requirements-build.txt`, a dependency path that preflight fails closed on. After independent review (TECHNICAL_PASS)
the backend step's `--reviewed-source` names `b2f8936`; any later edit to that file is refused again. Its CI is pending.

## Consolidation to master — 2026-11-04

State MERGED, POST_MERGE_VERIFYING. The owner asked for one tested batch to master.

- PR #21, `security/runtime-11-dependencies` at `ca49831`, passed all six checks on that exact head and was merged into
  development as `7ab0572`. CI there has no vulnerability scan or packaging job; those results are local only.
- The batch added RUNTIME-06/09/15 hardening, BIKE-01/04, CAREER-03/06, COUNCIL-01, FAMILY-05/06/07, TRAVEL-02/23 with
  verified booking links, the Windows signing tooling, the project dashboard and the Claude tooling. Older fix branches
  were left out because the batch already holds newer versions of the same commits; all branches are kept in a local bundle.
- Batch tree `192cf9d` (`f8a5ad2`, then `0defab2` with an identical tree): Chrome 156/156 with complete accounting, backend
  2719 run, 0 failures, 196 skipped, no migration changes pending. Not rerun on the batch: SafeDisk backend, drills,
  journeys, local AI and packaging.
- `0defab2` was pushed to development and master as fast-forwards. Pages redeployed the docs Markdown only.
- Post-merge CI on `0defab2`: preflight refused `apps/ml_engine/migrations/0005_adaptivemodelstate_artifact_evidence.py`
  and `constraints/linux-py312.txt`, which the earlier pin did not cover. With the owner's approval both were reviewed:
  the migration only adds an optional JSON field and reverses cleanly; the Linux lock scanned 145 packages with the same
  single open advisory, diskcache PYSEC-2026-2447, and `torch +cpu` not resolvable. The pin now names `0defab2`.

## RUNTIME-11 security branch — 2026-11-04

State COMMITTED_PUSHED/CI_PENDING after its push. Nothing here is a green claim. Base `development/alfred-integrated`
`1d9df25`, and it also contains master `96d4637`. Local evidence is in `docs/RUNTIME_11_EVIDENCE.md`, on `297e180`, the
last product commit; the head adds only documentation. CI starts when the owner opens the draft PR, since no GitHub login
is available here. It tests the dependency changes through `requirements.txt` and `constraints/**`, and preflight pins
`f40190e7ed31401405ecf7f529c521fb450d7864` as reviewed. The independent review is done and its defects fixed. Blockers
for acceptance: exact-head CI, the owner's residual-risk decision, installer runs that Smart App Control blocked on
`297e180`, separate-user install and clean PC.

## Consolidated development candidate — 2026-10-31

State LOCAL_TESTING, then COMMITTED_PUSHED/CI_PENDING after its push. Earlier runs transfer to no commit here.
Master needs exact-head CI, review of the full diff and the published-file check. The owner accepted AI-only review
for this merge and approved pinning `apps/users/migrations/0004_user_monthly_income_basis.py` as reviewed through
`180ea99`; CI's preflight refused it before that, and any later migration still fails closed.

Corrections to earlier entries: `artifacts/*/checkpoint.json` files cited below are local and ignored by
Git, so they do not travel with the repository. The D4 repair they describe is `dd1822f` (`97ecd0d` rewritten with
owner approval to remove attribution, same tree). That push had no independent review, and SEC-01 and the FIN P0
fixes were not on it. No full allow-list ran at it. GitHub shows PR #20 open and not draft.

## Local D4 runtime time zone — 2026-10-31

State LOCAL_ACCEPTED on local branch `fix/ist-time-zone` from 97ecd0d, source commit bd9cc5b. Not pushed,
push not authorized, no CI run. Evidence and remaining owner decision are in EXECUTION_STATE.

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
| Browser Regression / browser-regression.yml | master push; path-filtered PR; manual dispatch | native-windows, selenium, linux-secure-failure; three additional selenium-shards checks; five native-windows-shards checks (four backend shards plus native runtime) | Windows DPAPI/full backend+financial+privacy preflight/native HTTP/backup/recovery/accessibility; complete browser suite split across Windows; Linux fail-closed + portable browser | RETAIN; original three check identities preserved, selenium and native-windows now fail-closed aggregates |
| GitHub-managed pages-build-deployment / dynamic/pages/pages-build-deployment | GitHub Pages service; no source YAML in this checkout | Managed by GitHub, separate publication context | Existing Pages publishing | BLOCKED_REVIEW for any change; retain untouched, do not invoke/deploy |

Recent runs40771632812 (SUCCESS),40754201960 (45m Selenium cutoff),40742137700
(Selenium fixture failure),40692181959 (success) all belong to Browser Regression
and their exact source SHAs. Detailed API/protection/run receipts are local under
artifacts/ci-opt-20261029; no rule is changed or assumed waived when unavailable.
The master push and PR events validate distinct integration contexts. Development
push has no trigger, so it does not duplicate PR validation. Manual diagnostics
remain intentional. No workflow_call or overlapping repository workflow exists.

Stable native-windows/selenium/linux-secure-failure checks must remain. Any future
Selenium or backend shards must feed their aggregate (selenium, native-windows) fail-closed; no missing/skipped/
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

Superseded 2026-11-12: AGENTS.md now owns the flow (a work/* branch in a worktree from master, local commits,
push to master only after a whole phase or a CI fix with the owner's OK). The text below is kept as history.

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
