# ALFRED 2.0 execution

Updated 2026-10-27. Canonical development: `development/alfred-integrated` in
`F:/ALFRED_DEV/post-audit`. Recovery source `4b012a2`; clean and synchronized.
The 143 requirements and their acceptance remain in PROJECT_STATUS; the 13
extension IDs below are the existing requirements ledger, not 13 new baseline
capabilities. Coordination rows add no requirements. Baseline75/143; extensions0/13.

## Current checkpoint — D1 integrated Travel (2026-10-28)

D1 LOCAL_VERIFIED:7/7 bounded native-Windows journeys on the same owned saved trip,
with one actual API/service integration case and one complete Chrome case. Creation/
save/reopen,editor CRUD/order/undo/retry/conflict/source invalidation,real encrypted
private organizer/original/unlink preservation,packing/local reminder consent/
reschedule/cancel/late dedupe,independent PDF/GPX/ICS consistency and offline retry,
current/future same-currency finance/correction/no-writes,cold-process persistence
and owner/auth boundaries PASS. Two child Django processes reuse only synthetic
persisted tripDB/vault;second sweep retains exactly one visible late occurrence.
3unique checksPASS(backend1,Chrome1,profile1);milestones/reruns not double-counted.
Source runtime unchanged:reuse fine-grained45b2b2b evidence and exactCI40692181959
SUCCESS. New test/profile/docs HEAD still requires freshCI. Fixture clock models
reading time between journeys while real rate-limit policy stays unchanged;not a
wallclock/load benchmark. Child vault-path/readiness/envelope fixture corrections
and failed receipts retained. No application defect/runtime change was required.
JS/migrationPASS;GraphifyAST and source/privacy/push/CI closure in EXECUTION_STATE.
PR20DRAFT/NOT_MERGE_READY,75/143 and0/13 unchanged. D2 NEXT afterCI;D3–D5/manual/
independent/real-account/production acceptance remainpending. No full capability or
live route/cost/booking acceptance,no financial writes/FX/deployment.
## Previous checkpoint — TRAVEL2-005/C4 (2026-10-28)

C4 LOCAL_VERIFIED financial reconciliation:actual imports/transfer identity/linked
repayments,canonical same-currency Decimal/current-versus-projected funds,reserve/
goal separation,negativeflow/cutoffs/corrections,owner/privacy and read-only full
financial/user/history/fingerprint snapshots. Two fresh Django processes reopen
only synthetic testDB with identical C1/C2/C3/no DBhash change;no security bypass.
Reproduced/fixed source provenance gap:parser/review/file corrections now invalidate
C1/C2/C3. Reused existing statement owner/evidence guards;batched proofs and local
conflict indexes remove per-row queries,file hash once per batch. Query-growth and
single-record equivalence PASS;wallclock large-history timing remains unmeasured.
92unique backend/regressions,2actual Chrome,4global light/dark desktop/narrow Axe
zero violations. Native scoped same-harness finalreview CLEAN,fixtures-summary.
JS/migration PASS;finalsource/privacy/push/CI closure in EXECUTION_STATE.
CI40687948479 LinuxPASS;Windows/Selenium observedpending atd71;C4 needs freshCI.
PR20 DRAFT/NOT_MERGE_READY. LOCAL_VERIFIED yes;CI_PASSED newestHEADpending;
INDEPENDENT_REVIEWED scopednative only,cumulative/externalpending;FORMALLY_ACCEPTED
no;PRODUCTION_VALIDATED no. Manualcontrast/screen-reader,real-account/packaged/
cleanPC/production acceptance remainpending.75/143 and0/13 preserved. D1 NEXT after
CI reconciliation;D2–D5 unchanged. No financial writes,FX,migrations or deployment.
## Previous checkpoint — TRAVEL2-005/C3 (2026-10-28)

C3 LOCAL_VERIFIED/FORMAL_ACCEPTANCE_PENDING:read-only futuredate engine/API and
existing dashboard integration. Explicit verified income/effectiveperiod,currency,
unpaid monthly EMI schedule,additional goals and capped contribution;three owner
reviewed scenarios. Tomorrow-to-exclusive-departure calendar accrual and exact
Decimal rounding;current cash separated from uncertain projections. Protected
reserve/existing goals once,negativecashflow retained,no FX/register/model writes.
Required monthly saving is an estimated lower bound,not guaranteed affordability.
Native scoped review corrected irregular final EMI omission and in-flight GET draft
loss;final runtime CLEAN,sameharness/fixtures-summary. Actual Axe narrow-scroll
accessibility defect fixed;keyboard scroll and fourglobal1440/390light/dark views
PASS,contrast incomplete/manual screen-reader pending.41unique backend/profile,
8unique Chrome accepted incrementally;failed/rerun evidence retained,no doublecount.
Linux40682997546 fixture rootcause corrected (Windows-only memory prime);actual
Linux rerun/newest CI pending. Windows originalrunPASS,Seleniumpending. PR20returned
DRAFT/NOT_MERGE_READY;final source/privacy/push/CI receipts in EXECUTION_STATE.
C4 NEXT after exact-headCI reconciliation.75/143 and0/13 unchanged;formal/manual/
cumulative independent/real-account/production gates remain;no merge or deployment.
## Previous checkpoint — TRAVEL2-005/C2 (2026-10-28)

C2 LOCAL_VERIFIED pending finalsource/push/CI closure:owned saved-trip dashboard/
CSRF API reuses unchanged C1. Explicit verified currency/all7amounts,completeness/
disjoint allocations;one-month essential/EMI split,manual additional savings,
trip+extra contingency,protected/available funds/headroom/shortfall. Four labels
are scenario-only:Affordablepositive,Tightexactzero,OverBudgetnegative,Insufficient
Datawhenincomplete. No canonical writes,inferred INR/FX,model/schema/provider change.
Saved estimate/currency shown separately,unverified and never copied into scenario.
Fresh source/session/saved-content checks,visible30s/focus revalidation,stale409,
private/pagehide/authloss clearing. Native review corrected cross-trip draftcarry
and disabled-input draftloss;same-trip drafts retain values with renewed confirmation.
33unique backend/profile checks PASS;final6Chrome PASS(4C2+2affectedTravel),4global
desktop/narrow light/dark Axe zero violations;fresh capture update in EXECUTION_STATE.
Migration/JS PASS;native scoped review CLEAN(sameharness/tests-summary). Manual
screen-reader/incomplete contrast,cumulative independent/real-account/production
and newest exact-head CI remain gates. Baseline75/143,extensions0/13 unchanged.

### Previous C1/CI-recovery checkpoint (historical)

CONTINUE CI→C2:recovered cleand0c15d7;PR20 actual headdevelopment→master verified,
converted to DRAFT,NOT_MERGE_READY.40599527246 Windows/LinuxPASS,Selenium3failures.
Inspected exact logs,HTML,3screenshots. Private-history cold-vault503 no longer
blocks canonical source browsing;one bounded read retry,failed history leaves
questions blocked. Synthetic fixture primes vault. Auth-loss test revokes actual
server session instead of racing renewed cookies;reminder fixture waits enabled
final form.4unique Chrome cases PASS including new repeated-history-outage case;
first new hidden-detail assertion corrected,failed evidence retained. No timeout/
coverage/security weakening. Source/privacy/push/newCI closure in EXECUTION_STATE.
C2 selected next;C3/C4,D1–D5 remain separate.75/143,0/13 unchanged.

C1 read-only backend service implemented,17focused cases PASS. Exact canonical
one-month essential/EMI split,gross owner-confirmed spendable cash,disjoint emergency
reserve/savings/trip/extra contingency,available funds/headroom/shortfall. All seven
amounts need explicit verified matching currency,owner completeness/disjointness and
current owner/content/day revision. No inferred INR/FX,float money,income/asset/debt
double count,financial writes,schema/provider change or certified recommendation.
Unknown/unresolved/future/stale evidence fails closed;C1 conservatively requires
today's cash sync/current-month direct living-spend evidence,with observation dates.
Per-input existing money bound retained;derived totals are not clipped. Native
fresh-context scoped review CLEAN,same harness/tests-summary;64affected shared
regressions PASS.17C1+64regressions+10CI contract=91unique checks;original80-case
batch's sole misplaced C1fixture assertion corrected,final17C1PASS,failed evidence
retained/reruns not double-counted. Clean Axe setup/migration drift PASS. Chrome0run/1skip,
notPASS. Graphify query/update Windows Application Control blocked,no bypass.
CI repair57d4150 pushed;40596279652 IN_PROGRESS only. DraftPR creation403/422 blocked,
body/URL preserved. Final source/privacy/push/CI closure in EXECUTION_STATE;75/143,
0/13 unchanged,manual/external/formal/production gates preserved. C2–C4 not executed.

## Previous checkpoint — TRAVEL2-004/B4 (2026-10-28)

Latest NEXT recovery226c4f2:CI40569336516 FAIL,Windows/Linux PASS,Selenium139cases/
oneerror missing Axe asset. Selenium setup now prepares the same pinned4.13.0
hash-checked licensed tool;10CI/profile contract tests and clean-asset setup PASS.
Local Chrome driver unavailable(0run/1skip),not PASS;fresh exact-head CI required.
Owner-authorized draftPR creation blocked:connector403,Git-credential API422;
body/creation URL in EXECUTION_STATE and artifacts/travel-c1-20261028/pr.json.
C1 selected after rootcause repair;C2–C4 deferred. Counters unchanged.

Recoveredca66861 clean/synchronized. PDF40552102098 SUCCESS exactd08395f and
GPX40556530802 SUCCESS exactce0f019 verified;ICS40561358942 checkedONCEin_progress
exactca66861. Those states belong only to their SHAs. B4 new source needs freshCI.
One same owned trip passes independent PDF/GPX/ICS parsing,expired/unknown evidence,
stop order/supported dates,explicit DST times,save/reopen/edit/order/undo/stale/auth/
CSRF/failed-retry/missing/injection/preservation checks. No invented GPX times,
roads/tracks;one-off ICS timing is not a saved PDF departure. No trip/financial
writes,external requests,private-corpus access or permanent server export copy.
Only existing authentication-session bookkeeping writes occur;private metadata
preserved,real-account acceptance unperformed. Earlier unit/parser/bounds evidence
reused by source hash;PDF/GPX core and frontend unchanged.

Combined review reproduced/fixed real ICS first-edit UID drift. Canonical editor
IDs are prepared read-only from saved data and owned session identity;first edit
retains every event UID. Old id-less ICS imports have old UIDs;cross-version dedup
unverified,originals preserved. Final16 backend/profile PASS(5B4+10ICS+1profile),
2actualChrome workflows PASS acrossallformats/offline+WANblock/retry/auth/stale,
4global1440/390light/dark Axe zero violations,remainingcontrastmanual. Cached
GPXofficialXSD PASS;native fresh-context runtime CLEAN,sameharness/fixtures-summary;
migration/profile PASS,JS reused byhash,GraphifyAST11592/32422/509. Failed fixture/
regression evidence retained. Evidence artifacts/travel-exports-b4-20261028 and
ci-repair-ac05515/travel-b4-*.json. Source/privacy/push/new CI closure in EXECUTION_STATE.

| Acceptance state | Current evidence |
|---|---|
| LOCAL_VERIFIED | YES for bounded B1–B4;new B4/fix tests above |
| CI_PASSED | Original B1/B2 only;B3 observed pending,new fix/current HEAD pending |
| INDEPENDENT_REVIEWED | Fresh native reviewer CLEAN,same harness;no outside human/model sign-off claimed |
| FORMALLY_ACCEPTED | NO;latest-head CI and manual screen-reader/incomplete contrast acceptance outstanding |
| PRODUCTION_VALIDATED | NO;owner/live-account/packaged/production evidence separately unperformed |

Baseline75/143;extensions0/13. TRAVEL2-004 remains unpromoted and broader Travel
acceptance remains separate. Safe development closure permits NEXT C1 while
external/formal gates remain pending;do not require approval for ordinary read-only coding.

Verified implementation source **ebcbda32ee6dd046e290372c8c4539f54394fbf5**;clean source/history privacy,
dependency/migration preflight PASS,zero findings. Final tracker-only HEAD proof:
artifacts/travel-exports-b4-20261028/source-checkpoint/<HEAD>/release.json,push.json
and ci.json. Matching closure permits NEXT C1 despite pending external/formal gates;
latest-head CI remains pending,no extension or production approval.

## Persistent remaining Travel phases

- [x] B1 — PDF local tests and CI passed atd08395f;core evidence reused.
- [x] B2 — GPX local tests and CI passed atce0f019;core evidence reused.
- [ ] B3 — ICS local tests passed;ca66861CI observed in_progress,new UID fix needs new exact-head CI.
- [ ] B4 — Combined exports LOCAL_VERIFIED;FORMAL_ACCEPTANCE_PENDING,closure in EXECUTION_STATE.
- [x] C1 — LOCAL_VERIFIED deterministic backend,17focused/64regression checks;formal/CI gates pending,closure in EXECUTION_STATE.
- [x] P0 — Three Selenium failures locally repaired,4unique Chrome cases PASS.
- [ ] P0 — Newest exact-head CI and cumulative PR review readiness;PR20 DRAFT/NOT_MERGE_READY.
- [x] C2 — LOCAL_VERIFIED explainable saved-trip what-if UI/API;formal/CI acceptance pending.
- [x] C3 — LOCAL_VERIFIED future-date engine/UI;exact-headCI/formal gates pending.
- [x] C4 — LOCAL_VERIFIED reconciliation;formal/CI/manual acceptance remains pending.
- [x] D1 — LOCAL_VERIFIED7/7 integrated native-Windows journeys;freshCI/formal gates pending.
- [ ] D2 — NEXT after CI reconciliation:privacy/security/accessibility.
- [ ] D3 — Native Windows/offline/recovery validation.
- [ ] D4 — Exact-head CI and independent review.
- [ ] D5 — Production-readiness report,without deployment.

C1–C4 UNBLOCKED for scoped read-only development:explicit matching currency,
Decimal calculations,no inferred currency/INR/FX,no reserve/debt double counting,
no canonical financial writes,explicit INSUFFICIENT_DATA outcomes. FIN-15 currency
migration and production remain separately blocked. All protection/review gates
preserved. The checkboxes above are bounded phase evidence,not extension acceptance.

### Previous locally verified Travel work

- MODE NEXT TRAVEL2-003/SCOPE-02 recovered44f952b clean; CI40485342191 checked
  once,in_progress/not PASS. Reminder scope LOCAL_VERIFIED: saved-trip JSON,
  explicit per-trip opt-in/out,CRUD/cancel/reschedule,DST gap/fold/UTC validation,
  existing native Huey periodic/replay integration,atomic/idempotent in-app delivery,
  late labels and closed-trip suppression. No global activation/external delivery.
-56 unique backend/queue cases (18 reminder+9 packing+19 editor/organizer+10 queue),
 6 unique Chrome and4 actual1440/390 light/dark global Axe audits accepted across
  retained failures/repairs. Native runtime review clean,fixtures summary-reviewed.
  JS/migration/dependency/Graphify AST11455/31904/513 PASS. Exact source/evidence and
  privacy/push/newest-head CI closure are in EXECUTION_STATE and reminder artifacts.

- MODE NEXT selected TRAVEL2-003/SCOPE-01 at cleanc521a6d. CI40482166662 checked
  once/pending; TRAVEL2-002 retains CI_PENDING. Private packing is LOCAL_VERIFIED
  in existing saved-plan JSON, automatic local persistence, UUIDs/50-item bound,
  duplicate/owner/CSRF/CAS checks and preserved progress across both plan saves,
  reopened/cold-process reads, itinerary/day/stop/undo and document changes.
-29 unique backend cases (10 packing+19 affected regressions),5 unique Chrome
  workflows and4 global Axe audits at actual1440/390 CSS pixels, light/dark,
  zero violations. JS/migration PASS; native source review clean, tests summary-
  reviewed. Graphify AST11384/31653/522. Failed receipts retained and repaired
  selectively; reruns overlap. Packing artifacts bind exact source/privacy/push/CI.
  Manual screen-reader/incomplete Axe color checks and production remain pending.

- TRAVEL2-001 LOCAL_VERIFIED, formal acceptance CI_PENDING. Existing owned session/
  plan JSON and manual multi-stop API now support desktop activity CRUD, pointer/
  keyboard activity/stop moves, stable IDs, undo/history, retry/CAS revision safety,
  saved reopen and explicit old-estimate invalidation. No replacement planner.
- PR16 was OPEN at recovery, then GitHub reports it MERGED externally by
  sourabh48 at2026-10-26T23:18:16Z, mastera2274aa. PR CI40414777100 at4b012a2 PASS.
  This execution did not merge/change master or authorize deployment. Master's
  tree exactly matches tested4b012a2. After publishing editor source6e816b1, normal
  development merge9ae82ae incorporates master ancestry with IDENTICAL editor
  tree; no source conflicts or test rerun needed. Local masterc47fed9 and frozen
 4aa7ac70 remain unchanged. Receipt external-master-reconciliation.json under
  artifacts/travel-editor-20261027. No automatic replacement PR; future master
  integration still requires explicit gates/authorization and full current review.
- Validation:180 unique backend tests accepted across batch and focused repairs;
  4 actual Chrome workflows and2 desktop light/dark global Axe audits PASS, no
  skips/violations. Initial179-test batch had14 synthetic429 failures; isolated
  editor12 PASS, affected legacy subset11 PASS, final legacy-identity case1 PASS.
  The legacy case still compares every saved field and now verifies unique new
  read-time identity metadata. Counts overlap and are not additive. Explicit rate-
  limit regression still returns429. Bad rerun-label diagnostic retained/counts0.
- Native review fixes (drag markers, LAN UUID, collision-safe IDs, chat/research
  revisions, original safety/source panels) all rechecked clean; tests/fixtures
  summary-reviewed. No external model review/disclosure. JS, migration drift and
  generated inventory PASS. AST Graphify11314 nodes/31358 edges/523 communities.
- Receipts: `artifacts/travel-editor-20261027/local-acceptance.json`, browser-final,
  accessibility.json and ci-repair-ac05515/travel-editor-*.json. Source/history
  privacy and normal development push must be verified after this commit at the
  resolved HEAD; `artifacts/travel-editor-20261027/source-preflight/release.json`
  and push.json bind that closure. No formal extension promotion yet;0/13.
- TRAVEL2-002 bounded organizer LOCAL_VERIFIED: existing private PDF/text links,
  fingerprint/expiry validation, original access, unlink/reopen and CAS/idempotence.
  Originals stay in the encrypted corpus; no second copy or booking inference.
  Undo/unrelated trip state survives link changes. No-store responses, pagehide/
  auth-loss clearing and identity/revision guards protect private metadata; confirmed
  chat acknowledgements survive visibility changes without duplicate retries.
- Organizer validation:12 unique backend cases accepted across10 passing cases in
  travel-organizer-backend-corrected.json plus2 repaired original-path cases;
  includes real isolated DPAPI original-byte streaming/unlink preservation.
  Final5 actual Chrome workflows PASS including editor regression;2 desktop
  light/dark Axe audits zero violations and captures inspected. Native runtime
  review clean; tests summary-reviewed, no outside model. JS/inventory PASS;
  no migration/dependency changes. Graphify AST11345/31512/530 PASS. Failures retained,
  reruns overlap; manual screen-reader/incomplete Axe checks remain unverified.
- PR16 externally merged; no open PRs. Exact editor checkpoint1fa7449 manual
  CI40421447655 PASS. This does not validate the new organizer HEAD. Source commit
  resolves with `git log -1 --format=%H -- apps/mobility/services/travel/documents.py`;
  artifacts/travel-organizer-20261027/{local-acceptance.json,source-preflight/release.json,
  push.json,ci.json} bind final closure. Formal extensions0/13, baseline75/143.
- Organizer source61bd9bc35ff3a228fa7e2ddc9b109bb11dcfc1c3 passed exact clean
  source/history privacy (zero findings), dependency/migration preflight and normal
  development push. CI dispatch accepted204, pending outcome. This final checkpoint
  changes only the two trackers; runtime-identical local evidence is reused.
  source-checkpoint/<HEAD>/release.json, push.json and ci.json in the organizer artifacts
  bind the final checkpoint HEAD's preflight/push/new exact-head CI.
- Packing verified source6817fa863e95c34e93a9cae121100024f55d8ff7 clean source/
  history privacy/dependency/migration preflight PASS,zero findings. This final
  checkpoint changes only three trackers; passing runtime evidence is reused.
  artifacts/travel-packing-20261027/{source-checkpoint/<HEAD>/release.json,push.json,ci.json}
  bind final checkpoint candidate/ref/CI closure. No master/deployment action.
- Reminder sourcea799b31ec59ace8806460345c6f3de78c7274476 clean source/history
  privacy,dependency/migration preflight PASS,zero findings. This final checkpoint
  changes only three trackers; runtime evidence is reused. Reminder artifacts
  source-checkpoint/<HEAD>/release.json,push.json and ci.json bind final candidate/ref/CI.
- NEXT ACTION: after matching privacy/push PASS/new CI dispatch, READY_FOR_NEXT;
  check final-head ci.json once at next milestone,then reconcile full-extension
  gates and select tracker-authorized TRAVEL2-004/SCOPE-01 private export. No auto
  task selection in MODE NEXT. Missing closure means CONTINUE_REQUIRED; no reruns.
- Editor6e816b1 exact source/history/privacy/dependency/migration preflight PASS,
  zero findings, and normal development push succeeded. Post-push master drift was
  detected and reconciled as above. Final reconciliation/checkpoint closure uses
  source-after-master/release.json, push.json and ci.json in the editor directory;
  require their candidate SHA to match the final checkpoint. CI runs independently.
- No external AI disclosure, automatic trading, provider activation, live database,
  cloud, mobile/collaborative Travel or deployment. Ollama is optional only through
  a demonstrated bounded delegation path; none is needed for this deterministic unit.

## Dependency reconciliation (selection, not acceptance waivers)

Order remains FIN-07 → INV-07 → DOC-02 → DOC-06 → DOC-07 → AI-15 → AI-16 → AI-12 →
TRAVEL-03 → TRAVEL-04 → TRAVEL-07 → TRAVEL-08 → TRAVEL-09 → TRAVEL-15 → CAREER-04 →
CAREER-07 → CAREER-08 → remaining unblocked work. Revisit the first actionable
unaccepted scope at selection; never redo its accepted slice.

| Existing ID | Existing evidence / unresolved work | Resolution for this selection |
| --- | --- | --- |
| FIN-07 | Synthetic chronological planning accepted; genuine predictive accuracy partial | Real-outcome quality unavailable; no forecast dependency in manual edits |
| INV-07 | Bounded local alert lifecycle accepted; monetary rules partial | FIN-CURRENCY/valuation approval gate retained; no financial alert changes |
| DOC-02 / DOC-06 | COMPLETE_VERIFIED in bounded extraction/local corpus scopes | Reuse, do not rerun or enlarge claims |
| DOC-07 | Selected-source/full-context slices exist; arbitrary comprehension/independent quality partial | Full-quality work deferred with its evidence gate; manual editor consumes no document/model output |
| AI-15 / AI-16 | Readiness, evaluation and safeguards exist; genuine independent model/cohort quality missing | No model promotion, calibration or threshold waiver; editor deterministic |
| AI-12 | Bounded owned-memory/grounding exists; general cross-module intelligence partial | Manual editor does not require this expansion |
| TRAVEL-03 | Candidate pools/show-more/comparison COMPLETE_VERIFIED | Preserve accepted behavior |
| TRAVEL-04 | Accepted manual2–5 stop/reorder/day/save slice; richer editor partial | TRAVEL2-001 is the selected missing desktop/revision slice |
| TRAVEL-07/08/09/15 | Bounded route/reference evidence exists; live legality, scenic/detour/permit claims partial | Preserve these gates; edited routes/costs must be recomputed or explicitly invalidated |
| CAREER-04/07/08 | Discovery/geography/recruiter/resume foundations exist; mail/coaching/genuine outcomes partial | Resume after selected Travel module; never infer salary as actual income |

Evidence and exact acceptance for every baseline ID remain in its PROJECT_STATUS
section. This is the owner's explicit independent manual-editor prerequisite
exception, not a claim that unresolved earlier capabilities are complete.

## Deduplicated task register

Effort is a bounded engineering estimate, not elapsed-time or completion evidence.
Evidence `pending` means no full-story acceptance. Existing receipts are local
synthetic evidence unless their tracker explicitly says otherwise.

| ID / description | Existing implementation | Missing work | Dependencies | Priority / effort | Acceptance criteria | Tests | Evidence | Status / next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CAREER2-001 — resume-version comparison and stale JD decisions | Owned resumes, matching and outcomes | Exact owned version deltas and stale-decision invalidation | CAREER-01/02 | P2 /2–3 slices | Source/version citations and corrections remain owner-scoped; old JD decisions invalidate after changes | Backend version/owner/citation; desktop compare/correct/reopen | Existing Career tracker; full extension pending | QUEUED; inspect version comparison gap after Travel module; coaching remains baseline CAREER-07 |
| CAREER2-002 — reviewable application workflow | Recruiter/JD/discovery/geography and owned documents | Source-backed drafts and attachment/revision review | CAREER-04/05, DOC-06, AI-15 | P2 /2–4 slices | Stale proposals/attachments rejected; no implicit sending | API owner/CSRF/stale/retry; Chrome review | Career Discovery/Geography receipts; extension pending | QUEUED; preserve no-send boundary |
| TRAVEL2-001 — desktop itinerary editing/undo | Manual stops plus implemented desktop CRUD/reorder/undo/history and safe persistence | Formal extension acceptance; broader upstream UI equivalence unclaimed | TRAVEL-03 accepted; TRAVEL-04 bounded manual slice | P1 /2–3 slices | Full bounded edit/reorder/undo/save/reopen flow; unrelated data preserved; conflicts visible; no stale route/cost claim | 180 unique backend;4 Chrome;2 global desktop Axe; JS/migration/privacy gates | artifacts/travel-editor-20261027/local-acceptance.json; exact1fa7449 CI40421447655 PASS | LOCAL_VERIFIED/CI_PASSED at1fa7449; no automatic full-story promotion |
| TRAVEL2-002 — private booking/document organizer | Owned trip JSON and existing encrypted corpus now support private links/original access/expiry/unlink/reopen | Newest-head CI and formal extension acceptance; broader booking workflow unclaimed | TRAVEL-04, DOC-06 accepted slices | P2 /bounded slice complete | Owner-only originals and source dates; no inferred availability or booking writes; no private metadata after auth loss | 12 unique backend across repairs;5 Chrome incl editor regression;2 global desktop Axe; privacy | Source61bd9bc; artifacts/travel-organizer-20261027/local-acceptance.json, source-preflight/release.json, push.json and ci.json | COMMITTED_PUSHED/CI_PENDING; reconcile exact final HEAD at next milestone |
| TRAVEL2-003 — packing/reminders | Private packing plus explicit opt-in durable local reminders,UTC/DST validation,CRUD/cancel/reschedule,atomic in-app occurrence delivery and restart/replay safety | Newest-head CI and full extension mandatory acceptance; independent screen-reader remains pending | TRAVEL-04 accepted slice; existing DurableSqliteHuey/native UTC scheduler | P2 /01 and02 locally complete | Owner-only progress and delivery; stale/idempotent/cancel/late/offline/restart correctness; no external send/global activation | Current56 unique backend/queue incl affected regressions;6 Chrome;4 actual1440/390 light/dark Axe; prior packing evidence reused | artifacts/travel-reminders-20261027/local-acceptance.json and source/push/CI receipts; exact source in EXECUTION_STATE | LOCAL_VERIFIED/CI_PENDING after push; full extension UNACCEPTED,0/13 |
| TRAVEL2-004 — private PDF/GPX/ICS exports | Owned trip/evidence/map structures | Explicit validated source-preserving export | TRAVEL-04/17, owner export consent | P2 /2–3 slices | Correct coordinates/timezones/escaping; preserve expiry/unknowns; no public sharing | File parsers and malformed inputs; desktop export | Existing Travel evidence; extension pending | B1–B4 LOCAL_VERIFIED;fresh CI/manual acceptance pending,FORMALLY_ACCEPTED NO. C1 read-only NEXT;no extension promotion |
| TRAVEL2-005 — reserve/goal-aware affordability | Canonical baseline,C1–C4 engine/UI/future scenarios and cross-module reconciliation | Formal independent/manual/exact-headCI acceptance | FIN-05/06/07 evidence; FIN-15 migration stays gated | P1 /C1–C4 bounded local complete | Verified same-currency only,no inferred INR/FX,double counting or canonical writes; incomplete data never certified Affordable | C4 batch92backend/regressions,2Chrome,4globalAxe;canonical/import/repayment/source/owner/restart/no-writes | artifacts/travel-c4-20261028;source/push/CI in EXECUTION_STATE | C1–C4 LOCAL_VERIFIED;newest CI/manual/independent/formal gates pending,NEXT D1;extension0/13 |
| INVEST2-001 — analyst/bull/bear/valuation/risk packet | Owned portfolio, AMFI/Yahoo evidence and local routing | Compatible pinned TradingAgents graph adapter and independent challenge | INV-04, AI-15/16, source/dependency/provider clearance | P2 /4–6 slices | Dated sourced arguments/unknowns; bounded tools; no private disclosure/orders | Isolated compatibility; point-in-time/leakage/cancel; desktop review | UPSTREAM_REFERENCE_MATRIX T pin; engine adoption pending | QUEUED; test component isolation, do not bulk-install conflicting dependencies |
| INVEST2-002 — watchlist thesis/decision versions | Holdings and local review alerts | Owned research/watchlist histories separate from positions | INV-01/07; non-monetary scope first | P2 /2–3 slices | Instrument identity, stale thesis detection and explicit decisions; zero holdings writes | API history/owner/freshness; Chrome reopen | Existing investment/alert evidence; extension pending | QUEUED; select independent non-monetary scope after higher priorities |
| WEALTH2-001 — fund look-through/overlap | Canonical portfolio and dated market evidence | Shared source-dated company/sector/country/currency exposure and opaque portions | INV-01/04, FIN-15, approved instrument/source policy | P2 /3–4 slices | Reconciled weights; unknown exposure explicit; no invented price/FX | Deterministic overlap/completeness/owner; desktop drill-down | Aurelio reference map; extension pending | QUEUED; inspect approved source availability |
| WEALTH2-002 — fingerprinted proposal cards | Existing reviewed-source and confirmation patterns | Shared stale-safe cross-module proposal confirmation | FIN-12, DOC-06, AI-12 | P2 /3 slices | Dependency changes reject stale proposal; only approved confirmation acts | Fingerprints/replay/owner/CSRF; Chrome correction | Canonical contracts map; extension pending | QUEUED; no financial write without approved contract |
| WEALTH2-003 — snapshot reconciliation | Canonical net worth, expenses, loans and investments | Dated institution/asset anchors, post-anchor events/dividend/recurring provenance | FIN-03/11/12/15, INV-01, currency policy | P1 /3–5 slices | Strict cutoff, transfer/null/dividend identity; no historical rewrite | Decimal cutoff/double-count/replay; desktop provenance | Finance baseline evidence; extension pending | BLOCKED_APPROVAL for monetary policy; prepare approved read-only scope |
| WEALTH2-004 — public analyst/private challenger | Existing owner/evidence/local routing boundaries | Distinct minimal public-research and confidential local-context packets | AI-04/12, DOC-06, consent policy | P2 /2–3 slices | Adversarial leakage/role/source/owner tests; no implicit cloud disclosure | Packet contracts/malicious sources; desktop consent | Integration architecture; extension pending | QUEUED; use local synthetic packets first |
| CORE (coordination) — canonical financial intelligence | Canonical Decimal baseline/projections and accepted FIN-05 | Reserve/goal/currency/snapshot contracts once approved; shared adapters | FIN-06/07/15, FIN-CURRENCY | P1 /contract-specific | One canonical arithmetic path; read-only scenarios never actual money | Existing financial baseline/money/reconciliation suites | Baseline ID receipts own acceptance | BLOCKED_APPROVAL for missing contracts; no duplicate finance engine |
| LOCAL (coordination) — Ollama intelligence | Existing local provider/registry, deadlines and evaluation | Genuine quality evidence and demonstrated bounded delegation, where useful | AI-15→16→12; authorized cohorts | P1 /evidence-dependent | Local default, bounded cancellation, source-grounded abstention; no invented calibration | Existing model/cohort/privacy/timeout suites; optional isolated synthetic smoke | AI-15/16 receipts; broad quality pending | PARTIAL; no model activation/promotion as a shortcut |
| DESKTOP/RELEASE (coordination) — integration and release | Django desktop UI, Chrome/Axe, release/privacy/native gates | Per-slice desktop acceptance and separately authorized cumulative release | Domain acceptance, reviews, CI, rollback, Pages authorization | P1 /per slice | Owner/session/CSRF, keyboard/pointer, source/financial/privacy regression; exact newest HEAD; explicit release approval | Focused backend/Chrome/Axe, JS, migration, privacy; package only when selected | PR16 and per-source receipts | ACTIVE validation; never treat development integration as deployment |

## TRAVEL2-003/SCOPE-02 — implemented bounded local contract

Inspected native_settings.HUEY (DurableSqliteHuey,UTC,fsync,periodic threads),
native_tasks.py's UTC db_periodic_task schedules, durable_queue.py's atomic claims/
REPLAY_SAFE allowlist, background.py's local adapter and investment review-alert
opt-in/revision lifecycle. Existing Django timezone.now/is_aware/make_aware helpers
are reusable; current Travel EXIF naive conversion is not a DST scheduling policy.

Reuse saved-trip private JSON for an explicit enabled=false-by-default reminder
record: UUID,revision,owner-selected IANA zone/local time,validated UTC due instant,
status and an in-app delivery record. Standard-library ZoneInfo round-trip validation
must reject nonexistent local times and require an explicit choice for ambiguous
times; do not infer a user's zone from the server or naive datetime. Persist the
schedule before claiming success. A bounded local Huey periodic due sweep queries
opted-in trips; atomically CAS/lock the trip and write one UUID-keyed in-app delivery
with its delivered_at/status in the same database transaction. This gives one durable
visible result after restart without a separate external-delivery side effect.
Explicit cancel/reschedule uses the same revision/CAS; completed/cancelled trips
produce no delivery. Repeat due sweeps after restart/offline must be idempotent;
record late delivery honestly. Register/review replay safety if using the durable
queue's recovery path. No private task arguments/logs, external notifications,
email,SMS,paid provider or cloud. Tests must cover DST gap/fold,timezone changes,
stale/cancel-vs-due races,duplicate/restart replay and real Chrome opt-in/reopen.
The above design is now implemented in travel/reminders.py and travel_reminders.js.
The native minute task/replay allowlist use no private arguments. Due batches rotate
through100 eligible trips using an optional local-cache pagination cursor; corrupt
records remain intact,while cache I/O/SQLite/timeout failure falls back to safe
idempotent replay. The authoritative schedule,consent,revision,request receipts and
delivery records remain in trip JSON. No task activation or consent is inferred
for existing trips; records are created only by explicit owner mutations. Full
extension0/13 until exact-head CI/mandatory acceptance gates pass. No deployment.

## Reference boundaries and continuation

TREK is product inspiration for independently authored Django behavior; no AGPL
source/assets copied. TradingAgents engine reuse requires component license and
isolated dependency compatibility first. Aurelio is an algorithm/concept reference,
not a second runtime or canonical finance store. Pinned sources/dispositions are in
UPSTREAM_REFERENCE_MATRIX and ALFRED_2_0_INTEGRATION_ARCHITECTURE.

On continuation, read only this checkpoint and PROJECT_STATUS's active checkpoint,
verify actual refs/PRs, then perform NEXT ACTION. Record exact source/test receipts;
update the affected task row and checkpoint once per completed unit. Do not rewrite
the register or repeat passing scopes merely to recover context.
