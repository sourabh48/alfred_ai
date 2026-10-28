# ALFRED 2.0 execution

Updated 2026-10-27. Canonical development: `development/alfred-integrated` in
`F:/ALFRED_DEV/post-audit`. Recovery source `4b012a2`; clean and synchronized.
The 143 requirements and their acceptance remain in PROJECT_STATUS; the 13
extension IDs below are the existing requirements ledger, not 13 new baseline
capabilities. Coordination rows add no requirements. Baseline75/143; extensions0/13.

## Current checkpoint — CI-OPT (2026-10-29)

P0 CI optimization overrides queue selection before D3; Travel/financial evidence
and all143 baseline/13 extension requirements remain intact (75/143,0/13).
CI-OPT-01: one repository workflow RETAIN, no obsolete workflow proven, none
removed. Managed Pages stays untouched. Workflow disposition and metrics are in
CI_PIPELINE_STATE; EXECUTION_STATE owns exact continuation.

CI-OPT-02: per-test/phase measurement and deterministic3-way Windows sharding;
151 IDs assigned49/51/51 exactly once using measured durations. Three concurrent
bounded Chrome isolation cases, aggregate and35 focused contracts PASS. Stable selenium aggregate
retains canonical proof names; native/Linux/financial/privacy/recovery/DPAPI and
accessibility coverage remains required. Pip cache keys include requirements and
constraints, no private/runtime data. CI-OPT-03 retains distinct master/PR/manual
contexts and uses SHA/event/ref-aware non-cancelling concurrency.

Before hosted Selenium36m32 (1959s tests,202s pip); local profile27m26 had one
timeout, followed by an unchanged focused PASS; the failed receipt is preserved.
After runtime/cache savings UNMEASURED pending hosted exact-head execution. The
original D1 real API wait is retained, not simulated away. Independent/manual/
production acceptance still pending. After CI-OPT reconciliation: D3-A native/
offline, D3-B restart/crash, D3-C backup/restore/install, D4 review/CI, D5 readiness.

## Previous checkpoint — D2-C (2026-10-29)

Recovery/runtime source: `dff017383d16362da0313c8b16eb81eca0d5e03e`, clean and
synchronized before this batch. PR #20 DRAFT/unmerged, submitted reviews and
approvals both zero. Run 40742137700: Windows/Linux SUCCESS, Selenium FAIL
(151 cases, one stale-element error in D1 savings setup). The fixture mistook an
already-present income value for reload completion; it now waits for the old form
to be replaced. No application runtime, assertion or per-test wait change.

Continuation at `84a56fdb9d1f00746fd61dac52802f3a3ebc59d0`: run 40754201960
Windows/Linux SUCCESS, Selenium CANCELLED. GitHub annotation confirms the 45-minute
job limit; 136 passing progress markers and no E/F markers precede interruption,
without final suite proof. The outer Selenium budget is now 60 minutes, justified
by that measured cutoff. Full coverage, per-test waits, no-skip proof validation,
quotas and other jobs are unchanged. Nine runner/workflow contract checks PASS;
new exact-head CI is required. Cancellation is not acceptance.

The first local rerun passed that point but hit the real API quota during rapid
synthetic actions. Both quota failures are retained. D1 now allows the actual
configured rolling API window before its financial phase, leaving background
polling and production quotas active. This is real fixture pacing, not a timeout
increase, cache reset or clock bypass. Final repair validation/push/CI closure is in
EXECUTION_STATE and `artifacts/travel-d2c-20261029`.

Final paced batch: 3 actual Chrome cases PASS (D1 again 7/7, plus two savings
regressions), 2 real quota regressions PASS. Migration/inventory PASS. D2-C evidence
reconciliation LOCAL_VERIFIED; no unchanged D2-B audit/backend rerun or new formal
acceptance. Fresh exact-head CI remains required; manual/review gates stay open.

### Cumulative D2 security/accessibility matrix

Runtime source for every row: exact `dff017383d16362da0313c8b16eb81eca0d5e03e`.
The 12 backend paths in A and both JS/CSS hashes in B match the current tree.
This batch changes fixtures/trackers and the outer CI budget only; a fresh commit
still requires its own CI.
PASS means the bounded synthetic checks listed below, not complete WCAG, live
provider/account, production or independent approval. AXE PASS means zero violations
in the four global desktop/390px light/dark audits; its color-contrast incomplete
item is retained. Contrast separates computed supported samples from manual work.

| FEATURE | SECURITY | PRIVACY | KEYBOARD | AXE | CONTRAST | SCREEN READER | EVIDENCE | ACCEPTANCE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Itinerary editing/undo | PASS | PASS | PASS, bounded edits/order/undo | PASS | PASS computed; PENDING manual | PENDING NVDA | A, B, I, E1 | BLOCKED |
| Private organizer | PASS | PASS | PASS, list/link/unlink/focus | PASS | PASS computed; PENDING manual | PENDING NVDA | A, B, I, E2 | BLOCKED |
| Packing | PASS | PASS | PASS, add/edit/check/remove | PASS | PASS computed; PENDING manual | PENDING NVDA | A, B, I, E3 | BLOCKED |
| Opt-in local reminders | PASS | PASS | PASS, consent/forms; native widget manual PENDING | PASS | PASS computed; PENDING manual | PENDING NVDA | A, B, I, E3 | BLOCKED |
| PDF/GPX/ICS exports | PASS | PASS | PASS, explicit download/error controls | PASS | PASS computed; PENDING manual | PENDING NVDA | A, B, I, E4 | BLOCKED |
| Current affordability | PASS | PASS | PASS, bounded scenario controls | PASS | PASS computed; PENDING manual | PENDING NVDA | A, B, I, F | BLOCKED |
| Future savings | PASS | PASS | PASS, scenario/scroll controls | PASS | PASS computed; PENDING manual | PENDING NVDA | A, B, I, F | BLOCKED |

Evidence keys (local ignored artifacts; no private receipts uploaded):

- **A:** `artifacts/travel-d2a-20261028/{local-acceptance,native-security-review}.json`;
  backend review/source at `2391b45362b717c6dfc522648bb2103d0ba9aaa7`, unchanged
  through dff0173. Real owner/auth/CSRF/revoked-session/private-error matrix and
  unmodified 60/min write quota, CAS/replay/consent, sanitizer/provider regressions.
- **B:** `artifacts/travel-d2b-20261028/local-acceptance.json`, exact dff0173;
  `contrast-final/user-data/travel-d2-accessibility.json`,
  `keyboard-final/user-data/travel-d2-keyboard-complete.json` and regression receipts.
  Nine unique Chrome/five backend checks; 555 light/575 dark computed samples per
  view, zero failures, 19 light/9 dark exclusions. Labels, focus/restoration,
  announcements/error semantics, reduced motion, no overflow, auth/stale/offline
  states covered. Exclusions/native widgets/manual perception remain uncertified.
- **I:** D1 `2391b45362b717c6dfc522648bb2103d0ba9aaa7`,
  `artifacts/travel-d1-20261028/local-acceptance.json`: seven integrated journeys,
  real encrypted original, independent PDF/XML/ICS parsers, restart/replay and
  finance snapshots. D2-C reruns only its confirmed failing browser case and
  affected savings helpers; `artifacts/travel-d2c-20261029/ci-failure.json` preserves
  the exact CI trace/artifact digest. This is not packaged/device-loss acceptance.
- **E1/E2:** editor `1fa74491f19892cff9b8b6bc94ca9cf7924d75e3` and organizer source
  `61bd9bc35ff3a228fa7e2ddc9b109bb11dcfc1c3`; respective
  `artifacts/travel-{editor,organizer}-20261027/local-acceptance.json` and push receipts.
- **E3:** packing `6817fa863e95c34e93a9cae121100024f55d8ff7`, reminders
  `a799b31ec59ace8806460345c6f3de78c7274476`;
  `artifacts/travel-{packing,reminders}-20261027/local-acceptance.json`.
- **E4/F:** exports `ebcbda32ee6dd046e290372c8c4539f54394fbf5`,
  `artifacts/travel-exports-b4-20261028/local-acceptance.json`; financial C4
  `45b2b2b142e94275395650bcbf7a745948d73a9a`,
  `artifacts/travel-c4-20261028/local-acceptance.json`. C1–C4 source/reconciliation
  evidence preserves matching verified currency/Decimal arithmetic, reserve/goal/
  EMI/transfer identity, stale-source abstention and no canonical financial writes.

Across all rows, ownership/session/CSRF and explicit consent remain enforced;
document/download responses stay private, no-store and revision-bound. Reminders
remain opt-in/in-app only. No external private disclosure, inferred FX/currency,
automatic booking/trading or canonical financial mutations are authorized.
Provider fixtures do not prove live routing/availability or motorcycle legality.

### TRAVEL2-001–005 acceptance decision

| Extension | Documented bounded contract reconciled | LOCAL_VERIFIED | CI_PASSED at current cumulative source | Remaining acceptance | FORMALLY_ACCEPTED |
| --- | --- | --- | --- | --- | --- |
| TRAVEL2-001 | Stable IDs, activity/stop edits/order, undo/history, CAS/retry, preserved state and stale-estimate invalidation | YES, E1+A+B+I | NO: dff0173 failed; 84a56fd cancelled; fresh head pending | REVIEW_PENDING; MANUAL_ACCEPTANCE_PENDING; D3/D4 recovery/review evidence | NO |
| TRAVEL2-002 | Owned encrypted originals, link/unlink/expiry/reopen, no false booking or metadata after auth loss | YES, E2+A+B+I | NO: same current gate | REVIEW_PENDING; MANUAL_ACCEPTANCE_PENDING; D3/D4 | NO |
| TRAVEL2-003 | Packing CRUD/IDs/reopen plus opt-in UTC/DST/CAS/cancel/idempotent late local delivery/restart | YES, E3+A+B+I | NO: same current gate | REVIEW_PENDING; MANUAL_ACCEPTANCE_PENDING; native picker/recovery acceptance | NO |
| TRAVEL2-004 | Private PDF, truthful GPX, date/time/DST/UID-correct ICS, independent parsers and same-trip stale/auth safeguards | YES, E4+A+B+I | NO: same current gate | REVIEW_PENDING; MANUAL_ACCEPTANCE_PENDING; full cumulative CI | NO |
| TRAVEL2-005 | Read-only C1–C4 current/future money reconciliation, explicit assumptions, cutoffs, stale/currency abstention | YES, F+A+B+I | NO: same current gate | REVIEW_PENDING; MANUAL_ACCEPTANCE_PENDING; D3/D4 | NO |

All five also remain **PRODUCTION_PENDING**. Historical green CI (including editor
1fa7449 and C4 45b2b2b) is source-specific, not current cumulative acceptance.
Same-harness Codex scoped reviews are not human/genuinely independent approval;
GitHub PR #20 has zero submitted reviews/approvals. D2-C records these blockers,
does not self-approve or promote any extension. No baseline/extension double count:
75/143 and 0/13 unchanged. NEXT after local closure: D3 Windows/offline/restart/
recovery, then D4 independent review/exact-head CI and D5 readiness without deploy.

## Previous checkpoint — D2-B (2026-10-28)

Recovered synchronized `d877145`; PR #20 DRAFT/unmerged. Run 40736288039 Linux
SUCCESS; Windows/Selenium IN_PROGRESS at recovery. D2-A evidence preserved.
D2-B LOCAL_VERIFIED: 9 unique actual Chrome cases PASS (2 new + 7 affected
regressions), 5 backend/live-HTTP checks PASS. Four 1440/390px light/dark Axe audits
have zero violations; Axe color-contrast remains incomplete. Computed contrast
checks include actual placeholder colors and input boundaries: 555 light / 575
dark samples per view, zero failures. Gradient/opacity/native-widget and manual
perceptual acceptance remain pending; disabled controls have contrast exemptions.

Reproduced and corrected focus loss after reminder consent, missing input keyboard
outlines and low-contrast input borders (examples 1.66 light / 1.01 dark). Existing
Travel action boundary restores focus/forms after rerender, chooses reload after
removal/disabled Undo, respects moved focus and announces successful actions.
Three scoped CSS rules restore 3px outlines and contrast using existing colors.
Keyboard consent/packing/editor/organizer/error flows, reduced motion, offline,
stale revisions, auth loss and financial draft privacy passed. No backend/finance
or provider/security policy changes; no D1 rerun. Catalog rendering uses synthetic
boundary fixtures; real encrypted D1 evidence is retained.

Closure and exact source: EXECUTION_STATE and `artifacts/travel-d2b-20261028`.
Prior CI remains Linux SUCCESS, Windows/Selenium IN_PROGRESS; new commits require
their own CI. Manual owner sheet below stays PENDING; no NVDA session or human
approval invented. D2-C is NEXT; D3–D5 queued, 75/143 and 0/13 unchanged.

## Previous checkpoint — D2-A (2026-10-28)

D2-A security negatives LOCAL_VERIFIED: 3 cross-action matrix checks, 23 targeted
regressions and 1 profile check PASS (27 unique backend/profile checks). Owner,
auth, CSRF, revoked session, private cache, no-write, escaping and provider
boundaries covered. The real 60/min quota and Retry-After are enforced without
clock/policy changes; existing GET exemption unchanged. Initial quota fixture
miscounted setup's POST; corrected using consumed slots, failed receipt preserved.

CI 40730644845: Linux Career case failed after reload; source correctly refuses
submission until resume selection is ready. Fixture waits for enabled controls
and a new analysis, preserving score/abstention/security assertions and timeouts.
Exact Career Chrome case PASS locally; fresh Linux/new-head CI still required.
Windows SUCCESS, Selenium last observed IN_PROGRESS. No runtime changes or D1 rerun.

Source-only delegated Codex same-harness review of 12 backend paths CLEAN; fixture
summary only, not human/external/cumulative independent approval. Final privacy,
push and exact-head CI receipts are referenced by EXECUTION_STATE. PR #20 stays
DRAFT / NOT MERGE READY. D2-B browser/Axe/contrast/reduced-motion checks are NEXT;
D2-C reconciliation queued. Counts stay 75/143 and 0/13; formal gates pending.

### Pending owner accessibility sheet — complete during D2-B/C

No manual screen-reader session has been performed. Automated source review and
prior Axe evidence do not fill the observed-result column below.

Owner procedure: on Windows, start NVDA (normally Ctrl+Alt+N) and open an isolated
synthetic saved trip. Use Tab/Shift+Tab, Enter/Space and arrow keys without a mouse;
NVDA+Tab reports the focused control. Check names, states and spoken save/error/
late-delivery updates, including after rerender, conflict and expired sessions.
Repeat at desktop/390px in both themes and with Windows animation effects off.
For manual contrast, inspect foreground/background at the weakest gradient/image
position, placeholders, focus rings and input boundaries. Record normal text 4.5:1,
large text 3:1 and active control/focus boundaries 3:1; disabled controls are exempt.
Record the tester/date, actual observation and PASS/FAIL only after performing it.
All rows below remain PENDING; automated Chrome evidence is recorded separately.

| Screen | Action | Expected result | Observed result | Status |
| --- | --- | --- | --- | --- |
| Itinerary editor | Keyboard add/edit/move/undo and conflict recovery | Named controls, visible focus, retained draft; NVDA announces “Itinerary updated” and recalculation warning | Not run manually | PENDING |
| Private organizer | Tab link/open/unlink and return focus | Owner original opens; focus returns; “Private document choices updated” / “Private document references updated; originals are unchanged” announced | Not run manually | PENDING |
| Packing | Keyboard add/check/uncheck/remove | Item labels and checkbox states; “Packing checklist saved” and changed packed count announced | Not run manually | PENDING |
| Reminders | Opt in/edit/cancel, use native date/time picker and hear late delivery | Named consent/timezone/fold controls; “Local reminders enabled for this trip” / disabled-and-cancelled status, validation errors and “Delivered late” announced | Not run manually | PENDING |
| PDF/GPX/ICS | Keyboard export and failed download retry | Named actions; “Saved itinerary [format] downloaded. Keep the local copy private”; stale/session errors announced, focus retained | Not run manually | PENDING |
| Affordability/savings | Read sources, edit what-if and trigger stale evidence | Current/projected distinction; “Current evidence checked. No financial record was changed” and source-change/reconfirmation status announced | Not run manually | PENDING |
| All Travel panels | Session expiry/reload and ownership transition | Private state/error feedback handled safely,focus recoverable | Not run manually | PENDING |
| All themes/layouts | 1440/390px light/dark, reduced motion, contrast review | No overflow, visible focus, sufficient contrast, no essential motion | Not run manually | PENDING |

## Previous checkpoint — D1 integrated Travel (2026-10-28)

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
- [ ] D2 — D2-A/B/C LOCAL_VERIFIED; manual/review/fresh-CI gates pending; D3 NEXT after local closure.
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
| TRAVEL2-001 — desktop itinerary editing/undo | Manual stops plus implemented desktop CRUD/reorder/undo/history and safe persistence | Formal extension acceptance; broader upstream UI equivalence unclaimed | TRAVEL-03 accepted; TRAVEL-04 bounded manual slice | P1 /2–3 slices | Full bounded edit/reorder/undo/save/reopen flow; unrelated data preserved; conflicts visible; no stale route/cost claim | 180 unique backend;4 Chrome;2 global desktop Axe; JS/migration/privacy gates | artifacts/travel-editor-20261027/local-acceptance.json; exact1fa7449 CI40421447655 PASS | LOCAL_VERIFIED; current cumulative CI/review/manual gates pending (D2-C matrix above); FORMALLY_ACCEPTED NO; NEXT D3 after local closure |
| TRAVEL2-002 — private booking/document organizer | Owned trip JSON and existing encrypted corpus now support private links/original access/expiry/unlink/reopen | Newest-head CI and formal extension acceptance; broader booking workflow unclaimed | TRAVEL-04, DOC-06 accepted slices | P2 /bounded slice complete | Owner-only originals and source dates; no inferred availability or booking writes; no private metadata after auth loss | 12 unique backend across repairs;5 Chrome incl editor regression;2 global desktop Axe; privacy | Source61bd9bc; artifacts/travel-organizer-20261027/local-acceptance.json, source-preflight/release.json, push.json and ci.json | LOCAL_VERIFIED; current cumulative CI/review/manual gates pending (D2-C matrix above); FORMALLY_ACCEPTED NO; NEXT D3 after local closure |
| TRAVEL2-003 — packing/reminders | Private packing plus explicit opt-in durable local reminders,UTC/DST validation,CRUD/cancel/reschedule,atomic in-app occurrence delivery and restart/replay safety | Newest-head CI and full extension mandatory acceptance; independent screen-reader remains pending | TRAVEL-04 accepted slice; existing DurableSqliteHuey/native UTC scheduler | P2 /01 and02 locally complete | Owner-only progress and delivery; stale/idempotent/cancel/late/offline/restart correctness; no external send/global activation | Current56 unique backend/queue incl affected regressions;6 Chrome;4 actual1440/390 light/dark Axe; prior packing evidence reused | artifacts/travel-reminders-20261027/local-acceptance.json and source/push/CI receipts; exact source in EXECUTION_STATE | LOCAL_VERIFIED; current cumulative CI/review/manual gates pending (D2-C matrix above); FORMALLY_ACCEPTED NO; NEXT D3 after local closure |
| TRAVEL2-004 — private PDF/GPX/ICS exports | Owned trip/evidence/map structures | Explicit validated source-preserving export | TRAVEL-04/17, owner export consent | P2 /2–3 slices | Correct coordinates/timezones/escaping; preserve expiry/unknowns; no public sharing | File parsers and malformed inputs; desktop export | Existing Travel evidence; extension pending | LOCAL_VERIFIED; current cumulative CI/review/manual gates pending (D2-C matrix above); FORMALLY_ACCEPTED NO; NEXT D3 after local closure |
| TRAVEL2-005 — reserve/goal-aware affordability | Canonical baseline,C1–C4 engine/UI/future scenarios and cross-module reconciliation | Formal independent/manual/exact-headCI acceptance | FIN-05/06/07 evidence; FIN-15 migration stays gated | P1 /C1–C4 bounded local complete | Verified same-currency only,no inferred INR/FX,double counting or canonical writes; incomplete data never certified Affordable | C4 batch92backend/regressions,2Chrome,4globalAxe;canonical/import/repayment/source/owner/restart/no-writes | artifacts/travel-c4-20261028;source/push/CI in EXECUTION_STATE | LOCAL_VERIFIED; current cumulative CI/review/manual gates pending (D2-C matrix above); FORMALLY_ACCEPTED NO; NEXT D3 after local closure |
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
