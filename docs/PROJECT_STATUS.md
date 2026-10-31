# ALFRED Project Status

## Active implementation checkpoint — consolidated development candidate, 2026-10-31

Finished local work consolidated on `dd1822f`: SEC-01, SEC-02, CAREER-06, evidence labels, FIN-01, FIN-02, rupee
text recognition without conversion, and the Asia/Kolkata default. Implemented is not accepted; no requirement is
promoted. The loan verified-balance cutoff stays an owner decision. See EXECUTION_STATE. Baseline75/143,
extensions0/13 unchanged.

Corrections to earlier entries: `artifacts/*/checkpoint.json` files cited below are local and ignored by
Git, so they do not travel with the repository. The D4 repair they describe is `dd1822f` (`97ecd0d` rewritten with
owner approval to remove attribution, same tree). That push had no independent review, and SEC-01 and the FIN P0
fixes were not on it. No full allow-list ran at it. GitHub shows PR #20 open and not draft.

## Previous implementation checkpoint — D4 runtime time zone, 2026-10-31

Owner decided Asia/Kolkata as the default zone with UTC storage. Fixed on local branch
`fix/ist-time-zone`, not pushed, no exact-head CI, so implemented is not accepted. No stored date or
financial record changed. See EXECUTION_STATE for evidence and the remaining owner decision on loan
verified-balance cutoffs. Baseline75/143, extensions0/13 unchanged.

## Previous implementation checkpoint — D4 native-windows repair, 2026-10-31

Exact 626c5bc run40978060971 FAILED native-windows. Reproduced a time-of-day test defect, repaired
test-only; fresh exact-head CI is owned by artifacts/d4-native-repair-20261031/checkpoint.json. New
HIGH: runtime TIME_ZONE is Django's default America/Chicago, so "today" lags for an India-based owner
across 64 call sites; reproduced, unfixed, owner decision required. See EXECUTION_STATE. PR20 open,
NOT_DRAFT, unmerged, zero reviews. Baseline75/143, extensions0/13 unchanged.

## Previous implementation checkpoint — D4 prepared / external gates blocked, 2026-10-30

Read [review package](D4_PR20_REVIEW.md), [owner acceptance](D4_OWNER_ACCEPTANCE.md)
and EXECUTION_STATE. c287 exact CI40931513318 all6 PASS:1562 backend/151 Chrome/
22 native/21 Linux; source/artifact binding verified. D1–D3/native backup8 and
c287 portable20 evidence retained. Two D4 HIGH request-parser work issues were
reproduced and guarded globally without schema/dependency/auth/financial changes;
final27 API/session/Career/Loan/public-HTTP cases PASS, zero skips, including
explicit parser overrides and route-wide pre-read rejection. Existing affected Travel/upload/UI
evidence retained; failed initial60-case/empty-codec-check attempt not relabelled.
Fresh corrected-source CI is required and owned by artifacts/d4-20261030/checkpoint.json.
Residual dependency advisory/independent approval, current installer/failure/
rollback/clean-PC/device-loss/real-account/NVDA/manual contrast/protection visibility
and production remain PENDING/BLOCKED. New corrected package acceptance PENDING;
c287 binary cannot substitute. Baseline75/143,extensions0/13 unchanged; PR20
DRAFT/unmerged. No operator data/runtime,master/Pages/deployment/production
migration or backup deletion. Independent review request prepared, not sent;
outside authentication and GitHub write limitations preserved without bypass.

## Previous implementation checkpoint — D3-C package repair / D4 review, 2026-10-29

D3-C290e857 source/privacy and139 focused contracts PASS; real native backup8 PASS;
exact CI40925777403 remains source-bound. Portable build290 PASS/9789 inspected files.
Actual executable/launcher/Chrome passed17 checks then stopped safely on restart
because readonly vault schema inspection prevented SQLite hot-journal rollback.
Deterministic process-crash regression reproduced it; existing-file mode=rw fixes
recovery without key regeneration, crypto changes, legacy adoption or corruption
replacement.75 focused memory/privacy/corpus/platform cases PASS/zero skips;
protected copy of retained failed runtime now recovers under fixed source.

D4 cumulative same-harness review found planner close/reopen reviving old reminders.
Two before-fix failing status subcases; existing cancellation helper now runs in the
planner transaction.33 affected backend and2 actual Chrome workflows PASS;151 IDs
preserved. Re-review no residual supported defects. Outside Claude authentication
unavailable and approving GitHub reviews absent: independent release approval
remains PENDING. Exact latest refs/build/native/CI/checkpoint: EXECUTION_STATE and
artifacts/d3c-20261029/checkpoint.json. New source requires fresh package/CI, no
inherited green.75/143,0/13 unchanged; PR20 DRAFT/unmerged. Installer/compiler,
failed installation-update/current-installer rollback, clean-PC/real-account/
device-loss/manual/production remain PENDING. No operator data/runtime, master,
Pages, deployment, production migration or backup deletion.

## Previous implementation checkpoint — D3-C bounded local verification, 2026-10-29

Exact906e187 CI40882826087 all6 PASS and D3-A/B recovery evidence are preserved.
D3-C final isolated Windows/Waitress/Huey/SQLite/DPAPI/Chrome drill8 checks PASS,
child/launcher exits0, stopped status/OS locks verified without rescue. Encrypted
backup and independent same-device restore preserve3 databases/6 files, encrypted
private originals and DPAPI keys. Actual restore-process termination leaves no
final destination, retains staging and permits fresh retry. Missing/corrupt archives
and keys, existing destination refusal, restored HTTP/Chrome/restart, owner/CSRF,
SQLite integrity/FK, no duplicate originals/canonical money changes and log privacy PASS.

Confirmed defect: rejected/interrupted extraction previously exposed a partial
destination. Private retained staging plus validation/reconciliation before atomic
no-replace publication fixes it. Regression evidence/review/commands/limitations:
EXECUTION_STATE; artifacts/d3c-20261029; final external synthetic native-final receipt.
Linux CI adds portable no-replace tests without removing existing gates. Fresh
source CI and current portable build/execution stay pending until their artifacts
prove them. Actual installer/failed installation-update/package rollback require
missing Inno Setup/current installer and remain PENDING; unit rollback contracts
are not actual installer acceptance. Clean-PC/real-account/device-loss/manual/
independent release acceptance/production remain PENDING.75/143,0/13 unchanged;
PR20 DRAFT/unmerged. D4 cumulative review/release-gate verification follows bounded
D3-C closure. No operator data/runtime, master/Pages/deploy or backup deletion.

## Previous implementation checkpoint — D3-B LOCAL_VERIFIED, 2026-10-29

Exact a3f52e1 CI40873685637 all6 PASS closed before D3-B. Final isolated real
Windows/Waitress/Huey/SQLite/DPAPI/Chrome recovery drill15 checks PASS, child AND
launcher exits0, stopped runtime/locks verified without rescue. Five controlled
terminations prove web rollback/committed retry, interrupted upload and worker
reminder replay/idempotency. Independent WAL readers distinguish0 uncommitted from
1 committed delivery; no duplicate acknowledgement/delivery/money/originals.
Graceful saved/editor/packing/private-document/export/pending-job preservation,
stale financial409, corrupt/missing key/vault fail-closed handling,3 SQLite integrity
checks, owner/session/CSRF and diagnostic privacy PASS. Final persisted-state proof
confirms2 editor receipts/undo entries,2 stops/edited activities,2 deliveries/1 pending.
Runner7 and focused125 tests PASS/zero skips; affected D3-A fence1 PASS. Native
wrapper now requires trustworthy process exit plus fresh source-bound assertions
and cleanup; original D3-A unknown exit is preserved. No application-policy change.
Evidence/continuation: EXECUTION_STATE and artifacts/d3b-20261029. New checkpoint
requires fresh exact-head CI.75/143,0/13 unchanged; PR20 DRAFT/unmerged; D3-C next
after source/CI closure,D4/D5 queued. Manual/clean-PC/independent/production pending;
PostgreSQL untested. No master/Pages/deployment or operator-data/runtime action.

## Previous implementation checkpoint — D3-A LOCAL_VERIFIED, 2026-10-29

Completed actual isolated Windows/Waitress/SQLite/DPAPI/Huey/Chrome offline Travel
journey:11 checks PASS, including real scheduled reminder delivery/deduplication,
encrypted original and parsed exports, unavailable-model feedback, owner/session/
CSRF boundaries, current/future scenarios with no canonical financial writes and
owned-runtime shutdown. Native module16 PASS,zero skips; previous30 boundary cases
overlap and are not added. Probe/fixture changes only; no application-policy change.
Failed probe receipts preserved. Successful JSON/PowerShell stderr-wrapper detail,
exact source binding and closure commands: EXECUTION_STATE and artifacts/d3a-20261029.
Prior ebdc84b CI40839776242 all6 PASS; new checkpoint needs fresh exact-head CI.
75/143,0/13 unchanged. PR20 DRAFT/unmerged; clean-PC/manual/independent/production
gates pending,PostgreSQL untested. After source/CI closure: READY_FOR_NEXT D3-B;
D3-C,D4,D5 remain queued. No release/master/Pages/deployment actions.

## Previous implementation checkpoint — D3-A started, 2026-10-29

ebdc84b exact CI40839776242 SUCCESS: all6 jobs,151 Selenium cases passed once,
49/51/51,zero skips/failures; backend1544 PASS. Artifact digests and raw source-bound
proof revalidated; workflow29m17, Selenium critical path18m50. No full-suite local
rerun.30 local native/config/DPAPI/ACL/resource-boundary cases PASS; complete actual
native offline Travel journey ACTIVE. Evidence: EXECUTION_STATE and
artifacts/d3a-20261029.75/143,0/13 unchanged; clean-PC/manual/independent/production
gates pending,PostgreSQL untested. D3-B/C,D4/D5 remain queued; no release actions.

## Previous implementation checkpoint — repair run40834940011, 2026-10-29

Recovered ce9c5fe. Exact CI FAILED native oversized-upload fixture and shard2
candidate-pagination journey; Linux/shards0/1 PASS. Aggregate correctly rejected
150/151 PASS,zero skips; no shard-accounting defect. Real Windows early413 framing
race reproduced and fixture corrected without changing limits/assertions. Actual
Travel session/research torn snapshot reproduced with two SQLite threads; shared
atomic/row-lock response fixes it.122 unique backend cases and2 unchanged Chrome
journeys PASS; full151 IDs/49-51-51/check identities preserved. Exact evidence and
new-source CI continuation: EXECUTION_STATE/artifacts/ci-40834940011. Keep75/143,
0/13 and all other roadmaps. D3-A starts only after every required newest-head job PASS.

## Previous implementation checkpoint — CI-OPT-04, 2026-10-29

Hosted b0bf1e6 run40779797725: all151 Selenium PASS exactly once, aggregate SUCCESS;
Windows/Linux FAIL. Browser critical path21m17 versus36m32 (41.74% one-run reduction);
full failed workflow31m39, native31m37 remains bottleneck. Windows workflow contracts
reproduced/repaired; Linux upload readiness fixture correction locally verified,
hosted confirmation pending.66 contracts and22 unique Chrome cases PASS locally;
strict hosted151-case proof revalidation PASS. Built-in native slowest20
timing capture added without weakening privacy or test gates. Exact continuation/
closure: EXECUTION_STATE and artifacts/ci-opt04-20261029. Keep75/143 and0/13.
Next after CI repair checkpoint: D3-A/B/C, D4, D5; other requirements unchanged.

## Previous implementation checkpoint — CI-OPT, 2026-10-29

CI-OPT-01 retains the single unique repository workflow; removed NONE, managed
Pages untouched. CI-OPT-02 adds measured test accounting, pip dependency caching
and3 isolated Windows Selenium shards (151 intended,49/51/51); original check names
remain via fail-closed selenium aggregation. Three bounded concurrent Chrome
isolation cases and35 focused contracts PASS; full hosted after-runtime is UNMEASURED. Before hosted
Selenium36m32; local profiling collected151, with one retained timeout and unchanged
focused PASS. No runtime/security/assertion/DPAPI/financial weakening or quota bypass.
CI-OPT-03 preserves distinct PR/master/manual contexts with SHA/event/ref-aware
concurrency; no dev push duplicate. Check references/metrics: CI_PIPELINE_STATE;
exact source/tests/CI continuation: EXECUTION_STATE and artifacts/ci-opt-20261029.
Keep75/143,68 remaining,0/13. After CI-OPT: D3-A/B/C, D4, D5; other roadmaps retained.

## Previous implementation checkpoint — D2-C, 2026-10-29

Recovered synchronized `dff0173`; PR #20 DRAFT/unmerged, zero reviews/approvals.
Run 40742137700 Windows/Linux PASS, Selenium FAIL: one D1 stale-element error
among 151 cases. Fixture waits for the actual reloaded form, preserving assertions
and timeouts. Local validation exposed dense-fixture 120/min API quota exhaustion;
the fixture allows the configured real rolling window before financial actions,
without resetting quotas, disabling polling or bypassing protection. Validation
and source/push/CI closure are recorded in EXECUTION_STATE.

Final repair validation: 3 Chrome cases PASS, including D1 7/7 and two savings
regressions; 2 real quota backend regressions PASS. Migration/inventory PASS.
D2-C reconciliation LOCAL_VERIFIED; fresh exact-head CI remains separate.

Continuation at84a56fd: run40754201960 Windows/Linux PASS, Selenium CANCELLED
by its confirmed 45-minute job limit (136 passing markers; no final suite proof).
Only the outer Selenium budget changes to60minutes; per-test waits, assertions,
coverage and protection stay unchanged. Nine CI runner/wiring checks PASS.
New source/push/CI closure remains in EXECUTION_STATE; cancellation is not a pass.

Cumulative seven-feature security/privacy/keyboard/Axe/contrast/NVDA matrix and
TRAVEL2-001–005 acceptance decisions now live in ALFRED_2_0_EXECUTION. D2-A backend
and D2-B frontend hashes match dff0173; unchanged evidence reused. Automated Axe,
computed contrast and keyboard PASS are distinct from PENDING manual NVDA/visual
contrast and independent review. Owner sheet names actual expected announcements.
No extension qualifies for formal promotion: 75/143, 68 remaining and 0/13 stay.
D3 recovery follows local closure, D4/D5 remain gated. Other
Finance/Investment/Career/Wealth/local AI requirements are unchanged.

## Previous implementation checkpoint — D2-B, 2026-10-28

D2-B LOCAL_VERIFIED: 9 unique Chrome cases (2 new + 7 affected regressions) and
5 backend/live-HTTP checks PASS. Four 1440/390px light/dark Axe views have zero
violations; computed text/placeholder/control-boundary contrast checks pass.
Fixed reproduced action focus loss, missing keyboard input outlines and inadequate
input border contrast using the existing Travel action boundary and scoped CSS.
Keyboard forms/consent/editor/organizer, error/draft/retry/auth states and reduced
motion verified; no D1 rerun, canonical finance writes or backend policy changes.
Manual NVDA/contrast sheet updated with instructions, all manual rows PENDING.
Source/test/push/CI evidence: EXECUTION_STATE and `artifacts/travel-d2b-20261028`.
PR #20 DRAFT/unmerged; fresh CI and cumulative review remain gates. D2-C NEXT,
D3–D5 queued. Baseline 75/143, 68 remaining and extensions 0/13 unchanged.

## Previous implementation checkpoint — D2-A,2026-10-28

D2-A: 3 cross-action negatives, 23 security regressions and 1 profile check PASS.
Ownership, auth, CSRF, revoked sessions, private errors, no-writes, replay, consent,
output/provider safety and the unchanged write quota covered. Linux CI 40730644845
Career fixture race corrected: wait for resume/select/submit readiness and a new
analysis before original abstention assertions. One targeted Chrome case PASS;
fresh CI pending. Prior Windows SUCCESS; Selenium last observed IN_PROGRESS.
No runtime changes; D1 local 7/7 and C1–C4 evidence retained. Same-harness source
review CLEAN, not external/human/cumulative approval. D2-B accessibility NEXT,
D2-C queued; pending manual owner sheet in ALFRED_2_0_EXECUTION.
PR #20 DRAFT/unmerged. Closure: EXECUTION_STATE and `artifacts/travel-d2a-20261028`.
75/143, 68 remaining and 0/13 unchanged; D2 remains unaccepted. D3–D5, manual,
independent, real-account and production gates preserved.

## Previous implementation checkpoint — D1 integrated Travel,2026-10-28

D1 LOCAL_VERIFIED7/7 bounded native-Windows same-trip journeys:real creation/save/
reopen,editor/doc organizer/packing/reminders,exports and financial reconciliation,
cold-process replay/privacy/ownership. Real encrypted original retained through
unlink and edits;one late delivery across two fresh Django processes;read-only
canonical finance and source-correction invalidation preserved.3unique checksPASS:
backend1(7milestones),Chrome1(same7),profile1. Fixtures model inter-journey reading
time without changing quota/security logic;failed receipts retained. Runtime source
unchanged;reuseC4/earlier tests and45b2b2b exactCI40692181959SUCCESS,newHEADneedsCI.
JS/migrationPASS;final source/privacy/push/CI in EXECUTION_STATE and artifacts/
travel-d1-20261028. PR20DRAFT/unmerged. D2 NEXT;D3–D5/manual/independent/real-account/
production gates remainpending. No new capability acceptance:75/143,68remaining,
0/13 unchanged;all other roadmap rows retained. No real finance/FX/deployment changes.
## Previous implementation checkpoint — TRAVEL2-005/C4,2026-10-28

C4 LOCAL_VERIFIED:cross-module C1/C2/C3 canonical Decimal/import-transfer/repayment
reconciliation,full financial/user/history/fingerprint snapshots,no-DML guards and
actual fresh-process synthetic restart. Fixed reproduced parser/review/file source
provenance invalidation gap;reused owned statement evidence with bounded SQL and
batch-local file hashes.92unique backend/regressions,2Chrome,4globalAxe views zero
violations,scoped native review CLEAN(sameharness,fixtures-summary),migration/JS PASS.
Final source/privacy/push/CI in EXECUTION_STATE and artifacts/travel-c4-20261028.
PR20DRAFT/unmerged/NOT_MERGE_READY. Recovered40687948479LinuxPASS;Windows/Selenium
pending,new source needs ownCI. Formal/cumulative independent/manualcontrast/
screen-reader/real-account/production gates remainpending. No inferred currency/FX,
canonical money/history writes or financial migration.75/143,68remaining,0/13
unchanged. NEXT D1 after CI reconciliation;all other roadmap requirements preserved.
## Previous implementation checkpoint — TRAVEL2-005/C3,2026-10-28

C3 future-date savings engine/privateAPI/dashboard LOCAL_VERIFIED;explicit owner
income/effectiveperiod/currency/EMI schedules/goals/contribution,three documented
scenarios,calendar partialmonths/exclusivecutoff,conservative Decimal math. Current
cash and projections distinct;no guaranteed income,FX,financial writes or migration.
41unique backend/profile and8unique Chrome accepted incrementally;fourglobal Axe
views zero violations,keyboard scrollPASS. Native scoped review CLEAN after final
EMI/draft fixes,sameharness/tests-summary. Failed receipts preserved;no doublecount.
Linux40682997546 rootcause corrected:sharedfixture primed Windows-only private
memory. Windows originalrunPASS,Seleniumpending;new source needs exact-head CI.
PR20returnedDRAFT/NOT_MERGE_READY. Evidence/closure in EXECUTION_STATE and
artifacts/travel-c3-20261028. NEXT C4 after CI reconciliation. Independent/manual
contrast/screen-reader/real-account/production gates remain.75/143,68remaining,
0/13extensions unchanged;localimplementation is not formal acceptance.
## Previous implementation checkpoint — TRAVEL2-005/C2,2026-10-28

C2 saved-trip dashboard/what-if UI/API implemented over unchanged C1. Explicit
matching-currency/all7amount/completeness/disjoint confirmation;exact Decimal cash,
protected reserves/essential/EMI/savings and trip+extra contingency with headroom/
shortfall. Scenario-only Affordable/Tight/OverBudget/InsufficientData;no certified
advice,inferred INR/FX,financial writes or migration. Source dates/completeness,
saved-content/session/source revisions,automatic visible/focus invalidation,
same-trip draft safety and cross-trip/auth/pagehide clearing implemented/tested.
33unique backend/profile checks PASS;final6Chrome PASS,4Axeviews zero violations,
native scoped source review CLEAN(sameharness/fixtures-summary),JS/migration PASS.
CIrepair2577054 pushed/privacyPASS,run40679418199 observed pending;PR20DRAFT,
NOT_MERGE_READY. Exact C2 finalsource/privacy/push/CI closure in EXECUTION_STATE.
Independent/manual contrast/screen-reader/real-account/production remain pending.
All68remaining baseline IDs and13extension statuses preserved:75/143,0/13.

### Previous CI-repair checkpoint (before C2)

CONTINUE CI→C2:PR20 is DRAFT/development→master,NOT_MERGE_READY. Exactd0c15d7
CI40599527246 Windows/LinuxPASS,Selenium3errors. All3original workflows plus new
history-outage case PASS locally(4unique Chrome cases across repairs). Source
picker/history outage isolation and synthetic session/form readiness repaired;
original assertions/timeouts/security retained. Evidence artifacts/travel-c2-
20261028,ci-repair-ac05515/travel-c2-ci-*.json. Fresh exact-head CI remains required.
C2 UI/API next using existing C1;no C3/C4 or formal feature promotion.75/143,0/13.

Current NEXT:TRAVEL2-005/C1 selected after confirmed B4CI missing-Axe setup repair.
CI40569336516 Windows/Linux PASS,Selenium FAIL;fresh-head checks required.
10CI contract tests/clean pinned tool setup PASS;local Chrome0run/1skip(driver
unavailable),not accepted. DraftPR creation403/422 blocked;owner URL and exact
resume state in EXECUTION_STATE. Baseline75/143,extensions0/13 unchanged.

C1 backend implemented:17focused cases PASS,canonical exact Decimal one-month
liquidity/obligations/reserves/goals and trip+extra contingency. Explicit same-currency
owner confirmation/current content revision;unknown/stale/unreconciled data fails
closed,no inferred FX/INR or financial writes. Investment/credit balances and debt
flows cannot inflate spendable funds. Conservative current-day cash/current-month
living-spend evidence and bounded input amounts;no certified advice. Native scoped
runtime review CLEAN(same harness/fixtures-summary),migration drift PASS;64affected
regressions PASS.91unique C1/regression/CI checks accepted across incremental runs;
one new fixture-placement failure retained/repaired(final17PASS),no test double count.
Final source/push/CI closure in EXECUTION_STATE. C2UI/API deferred.

**Canonical original143-capability inventory and acceptance evidence. Updated2026-10-26.**

## Previous implementation checkpoint — TRAVEL2-004/B4,2026-10-28

Bounded combined exports LOCAL_VERIFIED using one owned saved trip and independent
PDF/GPX/ICS parsers. Final16 backend/profile checks PASS(5B4+10affectedICS+1profile),
2actualChrome all-format/offline/retry/stale/auth workflows PASS,4global1440/390
light/dark Axe zero violations. Save/reopen/edit/order/undo,missing/injection/DST/
source expiry and private packing/reminder/organizer metadata preservation covered.
No trip/canonical financial writes,provider/corpus calls or permanent server copies;
existing auth-session refresh only. PDF/GPX core/frontend hashes match old receipts.

Combined native review found/reproduced/fixed ICS UID drift before the first manual
edit. Read-only saved-data canonical identity preparation now retains all UIDs.
Old id-less exported files keep old UIDs;cross-version import dedup unverified,
originals preserved. Final native fresh-context review CLEAN,fixtures summary-only,
same harness;no outside sign-off claimed. Migration/profile/cached official GPX
XSD PASS;GraphifyAST11592/32422/509. Failed diagnostics retained.
Evidence: artifacts/travel-exports-b4-20261028 and ci-repair-ac05515/travel-b4-*.
PDF40552102098/GPX40556530802 verifiedSUCCESS on their originalSHAs;ICS40561358942
checkedONCEin_progress atca66861,new fix/source requires fresh exact-head CI.
LOCAL_VERIFIED YES;CI_PASSED pending latest;INDEPENDENT_REVIEWED native-only;
FORMALLY_ACCEPTED NO;PRODUCTION_VALIDATED NO. Manual screen-reader/incomplete
contrast and owner/live-account/packaged/production evidence remain unperformed.
75/143 and0/13 unchanged;no TRAVEL2-004 or broader Travel promotion. Source/privacy/
push/CI closure in EXECUTION_STATE. After safe B4 closure,NEXT may select C1 read-only
Decimal affordability despite external acceptance gates. Matching currency only,
no inferred FX/INR,no reserve/debt double count,no canonical writes;FIN-15 blocked.
No master,Pages,deployment or backup deletion. Execute no C1 work in this B4 run.

Verified implementation source **ebcbda32ee6dd046e290372c8c4539f54394fbf5**;clean source/history privacy,
dependency/migration preflight PASS,zero findings. Final tracker-only HEAD proof:
artifacts/travel-exports-b4-20261028/source-checkpoint/<HEAD>/release.json,push.json
and ci.json. Matching closure permits NEXT C1 despite pending external/formal gates;
latest-head CI remains pending,no extension or production approval.

## Previous implementation checkpoint — TRAVEL2-004/B3,2026-10-28

ICS LOCAL_VERIFIED: explicit owner/CSRF/revision+saved-content snapshot export,
owner-confirmed dates,exclusive date-only ends,optional explicit export-only
start/end/range,IANA DST gap/fold checks,UTC precise times/local context,stable
opaque UIDs,RFC5545 UTF8 escaping/folding. No inferred times/durations,private
notes/accounts/financial/doclinks,alarms/invitations/subscriptions/cloud/writes.
Existing export privacy UI reused,stale drafts/recovery guarded. No app dependency,
model/migration change;independent MPL2.0 ICAL.js test parser is pinned artifact only.
61unique backend PASS(10ICS+18PDFGPX+33metadata),5uniqueactualChrome PASS(import/
fold/stale/drafts/late/auth/recovery/PDFGPX);4final1440/390 light/dark Axe zero
violations,remainingcontrastmanual. Native runtime CLEAN,fixtures summary-only;
JS/migration PASS;ASTGraphify11571/32325/517. Failed diagnostics retained/repaired.
Evidence: artifacts/travel-ics-20261027 and ci-repair-ac05515/travel-ics-*.
CI40556530802 checkedONCE pendingexactce0f019;source/privacy/push/new exact-head
CI closure is in EXECUTION_STATE. Baseline75/143;extensions0/13 unchanged.
B4 combined export acceptance is NEXT after B3 closure. Manual screen-reader,
real-account and production acceptance pending. No master,publishing or deployment.

Verified implementation source **b7486f3e236bf42c89c66e0f4f3c01aac56b9216**;clean source/history privacy,
dependency/migration preflight PASS,zero findings. Final tracker-only HEAD proof:
artifacts/travel-ics-20261027/source-checkpoint/<HEAD>/release.json,push.json and
ci.json. Matching closure permits READY_FOR_NEXT;fresh exact-head CI remains pending
and source acceptance does not authorize release/production.

## Previous implementation checkpoint — TRAVEL2-004/B2,2026-10-27

GPX LOCAL_VERIFIED: saved-owner-only explicit CSRF/revision export,ordered Decimal
WGS84 coordinates/public source references/aged expiry,source-backed current
selected route geometry only;otherwise waypoint-only explanation. No inferred
roads,return legs,recorded tracks or bike legality. PDF endpoint/privacy lifecycle
reused;private unrelated state excluded,no provider/corpus/financial writes or
new models/migrations/dependencies. Original143 requirements/13 extensions preserved.
51 unique backend PASS(9GPX+9PDF+33CI metadata),4actualChrome workflows PASS including
local file reopen and PDF regressions;4global1440/390 light/dark Axe audits zero
violations. Official GPX1.1 XSD/lxml offline validation PASS for both final sample
files;native runtime recheck CLEAN,fixtures summary-only. JS/migration PASS;
GraphifyAST11522/32138/524. Failed fixture/P2 metadata diagnostics retained/repaired.
Evidence: artifacts/travel-gpx-20261027 and ci-repair-ac05515/travel-gpx-*.
CI40552102098 checkedONCE at exactd08395f:in_progress,not PASS. Source/privacy/push/
new exact-head CI closure is in EXECUTION_STATE. Baseline75/143;extensions0/13.
Manual screen-reader/incomplete contrast,real-account and production acceptance
remain pending. NEXT: finish B2 closure,then verify acceptance and select B3 ICS
on owner NEXT only. No master,publishing,deployment or financial-policy change.

Verified implementation source **d4b5cf05ff29e2a7d333f2b389359692ff4dd883**;clean source/history privacy,
dependency/migration preflight PASS,zero findings. Final tracker-only HEAD proof:
artifacts/travel-gpx-20261027/source-checkpoint/<HEAD>/release.json,push.json and
ci.json. Matching closure means READY_FOR_NEXT;fresh CI remains separate from local
scope verification and release/production approval.

## Previous implementation checkpoint — TRAVEL2-004/B1,2026-10-27

Private saved-itinerary PDF LOCAL_VERIFIED with explicit owner/CSRF/revision
protection,source dates/expiry/unknowns including individual stops,Unicode/wrapping
and bounded output. Costs,packing,reminders,linked originals and unrelated private
state excluded; no provider call,financial write,new dependency or migration.
Focused47 backend/API/CI tests PASS incl9 PDF cases using independent pypdf;
final layout/page-limit2 overlapping PASS. Three actual Chrome workflows PASS;
four1440/390 light/dark global Axe audits zero violations. Native runtime review
CLEAN,fixtures summary-only. JS/migration PASS; Graphify AST11490/32022/521.
Evidence: artifacts/travel-export-20261027 and ci-repair-ac05515/travel-export-*.
Source/privacy/commit/push/new exact-head CI closure is in EXECUTION_STATE.

CI40491012266 exact84902b7 FAILED: native1435 two restart-fixture assumptions,
Linux portable PASS,Selenium CANCELLED30m. Isolated default/file cold-process
repairs2 PASS each,opposing races2 PASS; prior upload helper Chrome1 PASS.
Measured Selenium45m budget reviewed,full suite/checks/protection unchanged.
Fresh exact-head CI,manual screen-reader/incomplete contrast,real-account and
production acceptance remain pending. Baseline75/143;extensions0/13 unchanged.
NEXT: finish current source/privacy/push/CI checkpoint,then READY_FOR_NEXT.
B2 GPX is next only on owner NEXT; no automatic module change or deployment.

Verified implementation source **a0b1fdc2e8a8813bf0ee9d7d6fde4142a2733b53**; clean source/history privacy,
dependency/migration preflight PASS,zero findings. Final tracker-only HEAD is bound
by source-checkpoint/<HEAD>/release.json,push.json and ci.json in the export artifact
directory. Fresh CI remains pending; source acceptance is not release approval.

## Previous implementation checkpoint — TRAVEL2-003/SCOPE-02,2026-10-27

MODE NEXT recovered44f952b clean/synchronized. CI40485342191 checked once:
in_progress, not PASS; prior packing/organizer evidence retained. Durable local
reminders now LOCAL_VERIFIED in existing saved-plan JSON. Default OFF; explicit
owner opt-in/out,create/edit/cancel/reschedule, IANA/local-time DST gap/fold checks,
validated UTC,20 schedules/100 retained occurrences. Huey's existing UTC minute
scheduler/replay helpers run a bounded rotating due sweep; atomic CAS writes one
in-app delivery per occurrence, labels overdue delivery late and cancels pending
occurrences on opt-out/closed trips. No email/SMS/push/cloud/global activation.
Packing/itinerary/document data survives saves and edits; cloned trips inherit no
reminder consent. No model/migration/dependency or financial change.

56 unique backend/queue cases accepted incrementally (18 reminder,9 packing,
19 editor/organizer,10 durable queue). Includes both real cancel/delivery races,
real Huey crash-after-commit-before-ack and new-process replay, corrupted data,
cursor fairness/outage,private controls,stale edits and cold persistence. Six unique
actual Chrome workflows accepted across repairs;4 global1440/390 light/dark Axe
audits zero violations,captures inspected. Native runtime recheck clean; tests
summary-reviewed,no outside model. JS/migration/dependency and Graphify AST
11455/31904/513 PASS. Counts overlap; failed receipts retained, no unrun pass claims.
Evidence: artifacts/ci-repair-ac05515/travel-reminders-*.json and
artifacts/travel-reminders-20261027/{local-acceptance.json,accessibility.json}.
Verified source **a799b31ec59ace8806460345c6f3de78c7274476** clean source/history
privacy,dependency/migration preflight PASS,zero findings. Final checkpoint changes
only the three trackers; passing runtime evidence is reused. The reminder artifact
directory's source-checkpoint/<HEAD>/release.json,push.json and ci.json bind its final
candidate,normal development push and new exact-head CI. No master/deployment action.

75/143 verified;0/13 extensions. Full TRAVEL2-003 acceptance requires newest-head
CI and remaining mandatory gates; manual screen-reader/incomplete Axe color checks
and production remain unverified. EXECUTION_STATE owns exact source and closure.
NEXT: after matching privacy/push PASS and CI dispatch evidence, READY_FOR_NEXT;
check final-head ci.json once at the next milestone,then reconcile full-story gates
and select tracker-authorized TRAVEL2-004/SCOPE-01 private itinerary export. Missing
closure means CONTINUE_REQUIRED; never attribute another SHA's CI to this source.

### Previous implementation checkpoint — TRAVEL2-003/SCOPE-01

MODE NEXT, recovery sourcec521a6d clean/synchronized. CI40482166662 checked once:
pending at exactc521a6d; organizer remains CI_PENDING. No repeated accepted work.
Implemented bounded private packing per owned saved trip/draft, using existing
plan JSON. Stable UUIDs, editable existing travel/motorcycle suggestions, add/edit/
complete/uncheck/remove,50-item limit, normalized duplicate rejection, CAS/own
revision and natural idempotent retries. Changes auto-save locally; cold-process
reads and reopened sessions retain progress. Both saved-plan write paths preserve
the canonical checklist through itinerary/day/stop changes and undo. No schema,
provider, financial, cloud or browser-storage change. No reminders enabled.

29 unique backend cases accepted across receipts (10 packing,19 affected editor/
organizer);5 unique actual Chrome workflows including keyboard CRUD, offline POST/
reload retry, stale editing at actual390px, private clearing and original editor/
organizer regressions. Final4 global desktop/mobile light/dark Axe audits PASS,
zero violations; captures inspected. Native source review clean after malformed
operation and reload-error repairs; tests summary-reviewed. JS/migration checks
PASS; AST Graphify11384/31653/522. Failed fixtures and first ARIA finding retained,
repaired selectively; reruns overlap and are not additional cases. Source hashes,
counts and limits: artifacts/travel-packing-20261027/local-acceptance.json;
artifacts/ci-repair-ac05515/travel-packing-*.json. Verified source
**6817fa863e95c34e93a9cae121100024f55d8ff7** clean source/history privacy,
dependency/migration preflight PASS,zero findings. This final checkpoint changes
only the three trackers, so local runtime evidence is reused. Exact final HEAD
privacy/push/new CI closure is in that artifact directory's source-checkpoint/
release.json, push.json and ci.json. Require matching final candidate/ref evidence.

**75/143 verified;0/13 extensions.** Scope01 local acceptance does not accept the
whole reminder extension. Manual screen-reader/incomplete Axe color checks and
production remain pending. EXECUTION_STATE owns exact continuation and evidence.
NEXT: reconcile final-head ci.json once at next milestone, then NEXT selects
TRAVEL2-003/SCOPE-02 opt-in durable local reminders; see execution roadmap design.
READY_FOR_NEXT after normal push PASS/CI dispatch recorded; otherwise CONTINUE_REQUIRED.

### Previous implementation checkpoint — editor and organizer

**Current command: recover and execute ALFRED2.0.** Recovery HEAD **4b012a2**, clean
and synchronized at selection. PR16 was OPEN then; GitHub subsequently reports it
MERGED EXTERNALLY by sourabh48 at2026-10-26T23:18:16Z, merge/master **a2274aa**;
PR CI40414777100 at4b012a2 PASS. No master merge, setting change or deployment was
performed by this execution. The external master tree is exactly4b012a2, verified
before normal ancestry merge **9ae82ae** into development. Its tree is identical
to locally verified/pushed editor source **6e816b1**; no source conflict or rerun.
Local masterc47fed9, frozen4aa7ac70 and all worktrees/source branches preserved.
Do not create/reopen a replacement PR automatically; later master integration
still needs full review, newest checks, security/privacy/compatibility/rollback
and publishing authorization. External deployment effects were not validated.

Created [ALFRED2.0 execution](ALFRED_2_0_EXECUTION.md), deduplicating the existing13
extensions and shared coordination work without changing143 baseline IDs or counts.
Mandatory sequence is reconciled there: accepted DOC-02/06/TRAVEL-03 and manual
TRAVEL-04 slices are reused; genuine AI/outcome/currency gates remain open. The
owner-selected deterministic editor is independent of those blocked expansions;
no capability is promoted by this exception. **75/143 verified;0/13 extensions**.

**TRAVEL2-001 LOCAL_VERIFIED / CI_PENDING.** Complete bounded desktop activity CRUD,
native drag/keyboard activity and stop ordering, stable identities,10 undo states,
20 revision/request receipts,512KiB undo cap, CAS/stale checks and idempotent retry.
Existing owned session/plan JSON saves/reopens; unrelated notes, packing, vehicle,
safety checks and source evidence remain. Chat and research mutations now advance
revision; unknown/new activities and reordered stops invalidate old routes/prices.
No monetary arithmetic, provider/model, source upload or schema change.

**180 unique backend tests accepted across receipts**,4 actual Chrome workflows
PASS,2 desktop light/dark global Axe audits PASS (zero violations/skips). The179-test
batch initially had14 synthetic429 failures: isolate new-test cache per reused
account, then12 editor PASS,11 affected legacy PASS and1 legacy identity-contract
case PASS. The latter still checks every original saved field plus unique new IDs.
Counts overlap; never add reruns to totals. Wrong extracted-method rerun labels
executed no real cases and are not evidence. Runtime rate-limit regression remains
enforced. Native source recheck clean after LAN UUID, ID collision, revision,
source/safety renderer and drag repairs; test fixtures summary-reviewed. JS,
migration-drift and generated143/13 checks PASS; Graphify AST11314/31358/523 PASS.

Receipts: artifacts/travel-editor-20261027/local-acceptance.json, browser-final and
accessibility.json; artifacts/ci-repair-ac05515/travel-editor-*.json. Failed receipts
are retained. Exact committed source/history privacy and push are finalized after
this commit in source-preflight/release.json and push.json under the editor artifact
directory; require PASS before remote push. Source commit resolves with
`git log -1 --format=%H -- apps/mobility/services/travel/editor.py`. Baseline75/143
and extensions0/13 unchanged while new exact-head CI/formal acceptance are pending.
Source6e816b1 preflight PASS/zero findings and normal development push succeeded;
post-push verification detected the external master change above. Final checkpoint
and ancestry source preflight is in source-after-master/release.json; actual refs,
publication and CI are recorded in push.json / ci.json. No source tests repeated
for the identical-tree ancestry merge. Receipt external-master-reconciliation.json
preserves the external actor/time/tree evidence.

**2026-10-27 continuation: TRAVEL2-002 bounded organizer LOCAL_VERIFIED.**
Owner-selected existing encrypted PDF/text originals can be listed, linked, opened,
unlinked and reopened with trip JSON. Only IDs/fingerprints persist; expired,
changed, foreign or unavailable copies reveal no original path/name. Originals
remain under Document Center retention; no second copy or booking/permit inference.
CAS revisions, natural idempotence, final-unlink save guards and itinerary undo
preserve unrelated state. Private API responses are no-store; page hiding/auth
loss clears names. Late reads cannot replace a selected trip/newer revision, and
visibility changes retain confirmed chat acknowledgements without duplicate retry.

Organizer evidence:12 unique backend cases accepted across10 passing cases in
travel-organizer-backend-corrected.json and2 repaired original-path cases in
travel-organizer-original-path-repaired.json (real isolated DPAPI-encrypted upload,
exact original-byte stream and unlink preservation). Final5 Chrome workflows PASS,
including editor drag regression;2 light/dark global Axe audits zero violations,
captures inspected. Initial failures retained; reruns overlap. Native read-only
runtime review clean; test evidence summary-reviewed, no outside-model disclosure.
JS/inventory PASS; no schema/dependency change. AST Graphify11345/31512/530 PASS.
Receipts: artifacts/ci-repair-ac05515/travel-organizer-*.json and
artifacts/travel-organizer-20261027/{accessibility.json,local-acceptance.json}.
Manual screen-reader and incomplete Axe checks remain unverified.

PR16 remains externally merged; current GitHub open-PR array is empty. Manual
CI40421447655 PASS at exact editor checkpoint1fa7449, not at the new organizer.
Formal extension acceptance remains0/13; baseline75/143. Organizer source
**61bd9bc35ff3a228fa7e2ddc9b109bb11dcfc1c3** passed exact clean source/history
privacy (zero findings), dependency and migration preflight and was pushed normally
to development. Manual CI dispatch returned204; no pass is claimed for this new
scope. Final checkpoint changes only these two trackers: runtime source is identical,
so passing local tests are reused. The final checkpoint HEAD's source preflight,
normal push and exact-head CI are recorded in the organizer artifact directory's
source-checkpoint/<HEAD>/release.json, push.json and ci.json. No master/deployment action.

**NEXT ACTION:** reconcile ci.json's newest exact-head run at the next milestone;
do not repeat passing local tests. READY_FOR_NEXT: TRAVEL2-003 owner opt-in durable packing/reminder lifecycle,
reusing existing checklist/settings/queue; reconcile its dependencies before edits.
No operator data, master/frozen/release branch or deployment action is authorized.

### Previous Travel batch (accepted bounded source)

**Current command: sprint continuation.** Canonical development resumed clean at
**7d1a44b**, already pushed with all Yahoo, Discovery, Geography and Memory source
refs contained. No consolidation or completed Memory tests are restarted. All PRs
remain owner-closed; masterc47fed9 and frozen4aa7ac70 remain unchanged. Consolidated
remote run40389906654 is still in progress at task selection; it is not green.

- Unit1 COMPLETE: TRAVEL-02 destination history matches case/spacing and catalog
  aliases, includes exact dynamic log/photo locations, combines repeated completed
  trip counts and honors every rejection across source IDs. Another owner's
  records remain isolated; explicit destination requests still take precedence.
  Four regression tests reproduced failures before the fix; **14 focused backend
  PASS, zero skips**, including accepted candidate-pool and existing ranking tests.
  Receipts: artifacts/ci-repair-ac05515/travel-novelty-{red,unit1}.json. No schema,
  provider activation, private disclosure or money change. TRAVEL-02 remains
  IMPLEMENTED_NOT_ACCEPTED for its full scope; **75/143 verified, 0/13 extensions**.
- Unit2 COMPLETE (baseff6e8ea): unsuccessful provider payloads cannot become
  dynamic destination evidence. The original offline candidates and static label
  survive; valid cached guide leads remain explicitly cached, without claiming
  access/availability. The failure was reproduced before the one-line fix;
  **3 focused backend PASS, zero skips**, travel-fallback-{red,unit2}.json under
  artifacts/ci-repair-ac05515. No extra provider calls or dependency changes.
- Unit3 COMPLETE (baseacc5339): existing Travel evidence UI shows discovery guide
  provenance, original check/expiry, recorded novelty, explicit offline catalog
  fallback and stale/unverified states. Saved discovery uses the existing places
  timestamp/source validation; malformed/future/naive clocks abstain, read-time
  aging does not rewrite saved evidence, and unsafe links/markup stay inert.
  **9 focused backend PASS, 1 actual Chrome PASS**, zero skips, JS syntax PASS.
  Receipts travel-evidence-unit3-backend.json and
  travel-evidence-unit3-browser-repaired.json under artifacts/ci-repair-ac05515;
  inspected desktop/narrow captures under artifacts/travel-discovery-20261027.
  Initial browser failure was Windows' minimum window width; the corrected test
  asserts actual390px via existing CDP emulation and retains the overflow check.
- Unit4 COMPLETE (base495ba9d): native review found that successful empty or
  fully filtered discovery could relabel offline suggestions as fresh guide
  evidence. Preserve STATIC_REFERENCE while retaining truthful query metadata;
  remove destinations from verified categories for static suggestions. Regression
  covers empty/filtered results; actual Chrome covers successful offline fallback.
  **123 integration backend PASS, 3 Chrome workflows PASS, zero skips**, including
  accepted pools/places, financial baseline and session-security checks. Receipts
  travel-discovery-batch-{backend,browser}.json under artifacts/ci-repair-ac05515.
  Native repaired-source review found no further supported issue; fixtures were
  summary-reviewed. Optional Claude review could not start (Windows launcher EINVAL)
  and supplies no outside-review coverage. Migration drift PASS/no changes.
- Unit5 COMPLETE (base36636f3): four scoped CSS rules correct light outline-button
  contrast and dark candidate-card/header/fit contrast. Native review caught an
  overbroad fit selector before push; narrowing it preserves existing itinerary
  day labels. **8 global Axe audits PASS, zero violations**, guide/offline ×1440/390px
  ×light/dark, no rule exclusions. Initial4.15:1 and dark1.67:1 failures remain in
  artifacts/travel-discovery-20261027/accessibility-*-failure.json. Final matrix
  accessibility.json and travel-discovery-accessibility-scoped.json (ci-repair
  receipts) bind corrected CSS. Incomplete Axe/manual screen-reader coverage stays
  unverified; these audits do not establish full WCAG acceptance.
- Batch complete: five units on the existing branch/worktree. Final cross-feature
  **123 backend PASS, 3 Chrome workflows PASS**, zero skips; totals overlap focused
  unit checks and are not additive. Migration drift, JS syntax and generated
 143-ID/13-extension checks PASS. Native review has no remaining supported blocker;
  receipt artifacts/ci-repair-ac05515/travel-native-review.json. AST Graphify PASS,
 11264 nodes/31208 edges/486 communities; no model/provider calls. Source/privacy
  preflight and normal development push are finalized after this commit; exact
  HEAD/results belong to artifacts/travel-discovery-20261027/{source-preflight/release,push,ci}.json.
  Require source/privacy PASS before push. GitHub development has no effective
  rules/protection/rulesets and zero open PRs, verified without settings changes.
  Master, frozen candidate and all source branches remain preserved. New exact-head
  CI runs independently after push; pending CI is not acceptance or deployment.
- NEXT TASK: TRAVEL2-001 desktop itinerary editing/undo with revision safety,
  extending the accepted TRAVEL-04 manual multi-stop/reorder foundation. Do not
  repeat its accepted actions or TRAVEL-03 pools, enable providers, claim live
  discovery accuracy, reopen PRs, change master or touch operator data. Full
  TRAVEL-02 acceptance, external-model evidence and FIN-CURRENCY remain gated.
- Resolve this checkpoint's commit with `git log -1 --format=%H -- docs/PROJECT_STATUS.md`.

### Previous consolidation and Memory evidence (completed)

**Current command: MERGE EVERYTHING AND PUSH.** Combined source merges
canonical development **6fc1e54** into the fully reconciled Yahoo/Discovery/Geography
candidate **fc2a4d2**. All original source commits and the five Memory commits are
retained; merge source **81c2876** had no executable conflict. **402 affected backend
tests PASS**, zero skips; **nine unique Chrome workflows accepted** across the
eight passing batch cases and focused Career readiness repair. No assertions or
timeouts were weakened: the fixture now waits for visible evidence, not just DOM
presence. Receipts all-merge-backend.json, all-merge-browser.json and
all-merge-browser-ready.json under artifacts/ci-repair-ac05515.

Accessibility exposed a keyboard-inaccessible mobile Memory score table; its named
region now takes keyboard focus and supports arrow-key scrolling. The extended
Chrome workflow and all four desktop/390px light/dark Memory Axe audits PASS;
the three other affected pages passed12 global Axe audits. An initial transient
sidebar contrast diagnostic and the actual scrollability failure remain preserved;
neutral-pointer sampling keeps global checks intact. Final16 scoped audits report
zero violations; incomplete checks/manual screen-reader remain unverified. Receipt
all-merge-accessibility-memory-final.json; data in
artifacts/consolidation-20261026/all-accessibility-memory/accessibility.json.

Separate-context in-host review of the combined source found no supported defects;
it is not a human GitHub approval or an independent model claim. Authenticated
development protection/rules inspection on2026-10-27 confirms an unprotected branch
with no rulesets/effective required checks. This owner-directed development merge
uses normal fast-forward/push, never a protection bypass. Remote CI is a separate
pending lane, not reported green; full consolidated exact-head CI and all master
review/publication gates remain required before any master merge.

Owner closed PR16/18/19 without merging; do not create or reopen PRs automatically.
All requested development scopes are present in this source, including upstream
policy, INV-02, AMFI/Yahoo, both Career scopes and the latest Memory work. Final
source/branch containment and push SHA are recorded after publication in
artifacts/consolidation-20261026/all-merge-push.json. Source/history privacy must
PASS at that exact HEAD. Original branches/worktrees/receipts remain preserved.
Masterc47fed9 and frozen4aa7ac70 are unchanged; no production/Pages/provider/FX/
private-history/cloud activation. Baseline75/143 and extensions0/13 remain unchanged.
Previous state/pipeline snapshots below are historical; this checkpoint owns current state.

Fast continuous development uses the existing post-audit worktree on
development/alfred-integrated. Requested dfdeac0 is an older ancestor; recovery
HEAD was d5cc181, clean. Earlier multi-case evaluation/held-out work is already
implemented and is not restarted. This checkpoint supersedes older task selection.
Resolve this checkpoint HEAD with `git log -1 --format=%H -- docs/PROJECT_STATUS.md`.

- Unit 1 COMPLETE: edit queued Memory evaluation questions in place, preserve
  unsaved drafts, require explicit review after source changes, prevent duplicate
  submission while editing, and clear editor state on page-hide. Actual Chrome
  regression **1 PASS, zero skips**; JS syntax/whitespace PASS. Receipt:
  artifacts/ci-repair-ac05515/fast-memory-unit1-corrected.json and
  artifacts/fast-memory-20261027/unit1-browser/browser_regression_summary.json.
  The initial runner-option typo ran zero tests and is not acceptance evidence.
- Baseline **75/143 verified**, extensions **0/13 accepted**, unchanged. AI-16
  remains partial; reviewed local workflows are not general accuracy/calibration.
- Unit 2 COMPLETE (base b26cb80): per-question results link every missed expected
  source to its current owner memory/correction controls. Results also explain
  when expected labels exceed the three-reference limit. Source contents are
  rendered as text; source changes invalidate results, and page-hide clears links.
  Actual Chrome **1 PASS, zero skips**, including unchanged vault records and
  correct missed-source IDs. Receipt fast-memory-unit2.json; screenshot/proof in
  artifacts/fast-memory-20261027/unit2-browser. JS syntax/whitespace PASS.
- Unit 3 COMPLETE (base 52997c9): four cosine bands report returned/relevant
  support counts and observed precision, including explicit no-sample values.
  Backend **19 PASS**, Chrome **1 PASS**, zero skips; receipts
  fast-memory-unit3-backend.json and fast-memory-unit3-browser.json. Browser
  demonstrates a high-score false match, corrected labels, unchanged cutoff/vault
  and page-hide clearing. No statistical calibration or policy promotion claimed.
- Unit 4 COMPLETE (base 955594d): whole-report rejection for returned scores below
  the requested cutoff or inconsistent cosine ordering; no partial IDs/diagnostics
  escape the existing session/owner boundary. Reproduced both invalid API reports
  as HTTP200 before the fix (fast-memory-unit4-red-api.json); corrected focused
  API **1 PASS**, actual Chrome **1 PASS**, zero skips. Empty queued edits now
  preserve the original case and require a question. Receipts
  fast-memory-unit4-backend.json and fast-memory-unit4-browser.json.
- Batch source **0c605c0**, units b26cb80 /52997c9 /955594d /0c605c0.
  Affected integration **124 backend PASS, zero skips** (memory learning/evaluation,
  frozen cohort policy, private storage, session/CSRF, financial baseline and
  tracker checks): fast-memory-batch-backend.json. **Six unique Chrome workflows
  accepted across final receipts**, including editing, missed references, score
  diagnostics, existing mobile metrics, stale-source/outage recovery and pending
  cancellation/case limits. The five-case browser batch initially had four passes
  and one obsolete generic button selector; the explicit Remove-question selector
  repair passed its isolated rerun (fast-memory-batch-browser-repaired.json), with
  all privacy/draft assertions retained. Overlapping focused/rerun totals are not
  additive; no backend rerun for this test-selector-only repair.
- JS syntax, whitespace and generated143-ID/13-extension check PASS. AST Graphify
  update PASS (11,172 nodes/30,889 edges/515 communities); no semantic/model call.
  Frozen retrieval policy/holdout, runtime configuration, master and release
  candidate4aa7ac70 are unchanged. Commits are local only; no new PR/branch/worktree.
- NEXT TASK: TRAVEL-02 bounded discovery novelty/source freshness acceptance,
  starting with its existing tracker evidence and scoped graph query; preserve
  accepted TRAVEL-03 pools. Skip completed Memory scopes, independent/chronological
  model-quality evidence blockers, pending feature-branch integration gates and
  FIN-CURRENCY approval. Do not activate providers or claim real-account accuracy.
- No push/master/production, operator database, frozen candidate4aa7ac70, AWS,
  paid OpenAI, cloud sync, private-history or FIN-CURRENCY operation. Resume:
  `Set-Location F:/ALFRED_DEV/post-audit; git status -sb` then read this checkpoint.

## Current execution

Read [EXECUTION_STATE](EXECUTION_STATE.md) for source-bound task state and resume;
[requirements](ALFRED_2_0_REQUIREMENTS.md) own intent and [queue](EXECUTION_QUEUE.md)
owns deterministic selection. Sprint uses one canonical development branch and PR16.

- **PR/CI:** Canonical development d5cc181/master c47fed9 unchanged. PR16/18 green at their existing heads; PR19 Selenium exceeded 30m and retry returned 403. Independent project reviews absent on all three. The local Yahoo/Discovery/Geography candidate passed 309 backend tests, 19 metadata tests, 3 Chrome workflows and 12 overlapping Axe audits, with source/history privacy zero findings; no canonical/GitHub merge, PR closure, Pages or deployment. Authenticated rules/protection inspected; no settings changed. Latest privacy receipt must match the final preparation HEAD.
- **Current task:** Local consolidation preparation is validated on preparation/alfred-consolidation-20261026; required reviews and PR19 CI still block canonical integration. Preserve 143 original IDs/75 verified and 13 extensions/0 accepted. See CONSOLIDATION_STATE for sources, conflict decisions and receipts. Stage7 selection is not reached.
<!-- BEGIN STATUS DASHBOARD -->
**Baseline: 75/143 (52.4%) verified.**

IMPLEMENTED_NOT_ACCEPTED: 24 | PARTIALLY_IMPLEMENTED: 26 | BLOCKED_APPROVAL: 5 | BLOCKED_EXTERNAL: 3 | NOT_IMPLEMENTED: 10 | COMPLETE_VERIFIED: 75

PR/CI: Canonical development d5cc181/master c47fed9 unchanged. PR16/18 green at their existing heads; PR19 Selenium exceeded 30m and retry returned 403. Independent project reviews absent on all three. The local Yahoo/Discovery/Geography candidate passed 309 backend tests, 19 metadata tests, 3 Chrome workflows and 12 overlapping Axe audits, with source/history privacy zero findings; no canonical/GitHub merge, PR closure, Pages or deployment. Authenticated rules/protection inspected; no settings changed. Latest privacy receipt must match the final preparation HEAD.

Extensions: **0/13 accepted**; separate source-bound story ledger.

| Module | Verified | Total | Verified % | Unaccepted | Partial | Missing | Approval | External |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FIN | 11 | 17 | 64.7 | 0 | 4 | 2 | 0 | 0 |
| LOAN | 6 | 8 | 75.0 | 2 | 0 | 0 | 0 | 0 |
| INV | 3 | 8 | 37.5 | 2 | 3 | 0 | 0 | 0 |
| DOC | 7 | 9 | 77.8 | 0 | 2 | 0 | 0 | 0 |
| AI | 11 | 18 | 61.1 | 3 | 2 | 2 | 0 | 0 |
| CAREER | 3 | 8 | 37.5 | 2 | 3 | 0 | 0 | 0 |
| TRAVEL | 10 | 23 | 43.5 | 2 | 5 | 3 | 0 | 3 |
| FAMILY | 4 | 7 | 57.1 | 3 | 0 | 0 | 0 | 0 |
| BIKE | 2 | 6 | 33.3 | 2 | 2 | 0 | 0 | 0 |
| COUNCIL | 0 | 5 | 0.0 | 1 | 3 | 1 | 0 | 0 |
| OPENAI | 5 | 7 | 71.4 | 0 | 1 | 0 | 1 | 0 |
| SYNC | 7 | 11 | 63.6 | 0 | 0 | 2 | 2 | 0 |
| RUNTIME | 6 | 16 | 37.5 | 7 | 1 | 0 | 2 | 0 |
<!-- END STATUS DASHBOARD -->

## Separate 2.0 acceptance ledger

Only these explicit enhancement stories contribute to the separate extension
metric. Definitions/dependencies are in the requirements; shared work counts once.
Change a status to ACCEPTED only with source-bound backend/UI/privacy evidence.

<!-- BEGIN EXTENSION ACCEPTANCE -->
| Extension | Status | Evidence |
| --- | --- | --- |
| CAREER2-001 | UNACCEPTED | No full-story acceptance recorded. |
| CAREER2-002 | UNACCEPTED | No full-story acceptance recorded. |
| TRAVEL2-001 | UNACCEPTED | No full-story acceptance recorded. |
| TRAVEL2-002 | UNACCEPTED | No full-story acceptance recorded. |
| TRAVEL2-003 | UNACCEPTED | No full-story acceptance recorded. |
| TRAVEL2-004 | UNACCEPTED | No full-story acceptance recorded. |
| TRAVEL2-005 | UNACCEPTED | No full-story acceptance recorded. |
| INVEST2-001 | UNACCEPTED | No full-story acceptance recorded. |
| INVEST2-002 | UNACCEPTED | No full-story acceptance recorded. |
| WEALTH2-001 | UNACCEPTED | No full-story acceptance recorded. |
| WEALTH2-002 | UNACCEPTED | No full-story acceptance recorded. |
| WEALTH2-003 | UNACCEPTED | No full-story acceptance recorded. |
| WEALTH2-004 | UNACCEPTED | No full-story acceptance recorded. |
<!-- END EXTENSION ACCEPTANCE -->

## Historical checkpoints (newest first)

- **PR17 OWNER MERGE / RECOVERY — 2026-10-26:** GitHub confirms PR17 merged into development/alfred-integrated asd5cc181, source503b848; master unchangedc47fed9, PR16 open with new exact-head CI40324546766 running. Local development fast-forwarded only; returned to preserved Yahoo branch. Merged target tree equals accepted policy base tree; all8 Yahoo code/test/style blobs and four receipts preserved despite checkout LF/CRLF normalization. Existing Edge fallback restored; prepare scoped Yahoo draft against development, no rebase/reset/history rewrite or redundant business/browser suite rerun. Baseline75/143/extensions0/13 unchanged; integration refs/evidence and recovery in EXECUTION_STATE. No master merge, Pages or production operation performed.

- **INV-05/SCOPE-02 — 2026-10-26:** Existing Yahoo transport now validates symbol/error metadata, aligned finite-positive Decimal daily observations, dates/conflicts/missing latest and actual30-day baseline. Source expiry caps persisted records/scheduler and owner-cache research; no holding or currency/schema changes. Synthetic backend80 PASS, zero skips (`inv05-yahoo-final.json`); final Chrome/theme contrast/Axe in EXECUTION_STATE. Visual inspection exposed unreadable dark evidence/algorithm cards; existing theme surface tokens correct them with >=4.5 contrast regression. Branch based on policy source503b848; PR16→PR17 prerequisites explicit. Full INV-05 NOT_ACCEPTED; no live provider, exchange-close, real-account or packaged acceptance. Source/privacy/commit/push/CI evidence under `artifacts/sprint-8f505a3/yahoo/`; pending CI is not100%. Counts unchanged. Preserve earlier accepted scopes; next independent eligible queue item CAREER-03 subject to candidate capacity.


- **CAREER-03/SCOPE-01 LOCAL — 2026-10-26:** Native normalized-feed discovery now validates evidence dates/source identity, retains explicit unknown/stale cached leads, normalizes/escapes HTTPS posting and source links, prefers fresh evidence for canonical URL duplicates and caps owner-cache verification at source expiry. UI says leads, not verified vacancies, with checked/expiry dates and availability uncertainty; no automatic apply. Synthetic affected backend66 PASS; one Chrome outage/recovery/unsafe-link/owner workflow and four overlapping light/dark desktop/390px Axe audits zero violations, both-theme text/link contrast>=4.5. Final receipts `career-discovery-final.json`, `career-discovery-final-ui.json`; captures/accessibility under artifacts/career-discovery-d5cc181. First fixture-only errors fixed without weakening assertions; prior runs diagnostic/overlapping. Metadata/privacy/commit/CI handoff in EXECUTION_STATE. Full CAREER-03 remains unaccepted; no live source/terms/geography/listing/real-account claims. No money/schema/provider changes; baseline75/143/extensions0/13 unchanged.

- **INV-05/SCOPE-02 CI CLOSURE — 2026-10-26:** Sibling PR18 exact sourcedaed068adef0ce1ea091dc5efe08d52068f1b77f run40325761619 PASS; Linux121581905200, Selenium121581905333, Windows121581905400 all successful. Preserved local80 backend/12 metadata/one Chrome/4 overlapping Axe and source privacy0 revalidated by exact committed blob/receipt identities; no unchanged large local suite rerun. Scope95→100%, full INV-05 still IMPLEMENTED_NOT_ACCEPTED. Source remains on separate PR18 branch until integration; this Career branch does not claim to contain its Yahoo implementation. PR18 already READY/open, reviews0/applicable review/protection gates unresolved; no merge performed. PR16/master/publication gates preserved. Career independent work continued without touching Yahoo branch or cancelling its CI.

- **UPSTREAM / SPRINT POLICY — 2026-10-26:** Owner explicitly added continuous `sprint`, isolated section PRs, maximum three candidates and conditional automatic merges with unchanged review/protection/publication gates. AGENTS and the reference matrix/architecture/pipeline ledger implement that contract; prior manual-only instructions below are historical and superseded. Four default-branch SHAs/licenses and bounded source/tests were inspected, Career Ops identity resolved; no upstream runtime integrated, dependencies installed or product counts changed. Policy branch based on8f505a3; validation/push evidence and exact refs belong in EXECUTION_STATE/CI_PIPELINE_STATE. PR16 remains cumulative and merge-blocked. Next feature is existing eligible INV-05/SCOPE-02; no queue jump.

- **INV-05/SCOPE-01 — CI CLOSURE — 2026-10-26:** `continue` recovered clean, pushed source `79a26aeeeba778201871b04a8c6e89cd9e1a70df`. Run **40292154135 PASS**, actual `head_sha` checked; native Windows **121469494295**, Linux **121469494491**, Selenium **121469494553** all successful. Ten accepted executable/test/style hashes and three receipt hashes match; 56 backend/11 metadata, one unique Chrome and four overlapping Axe receipts retained, not rerun as fresh business acceptance. Source/history privacy proof at accepted source has zero findings. Scope closes **95% → 100%**; full INV-05 remains unaccepted, baseline 75/143 and extensions 0/13 unchanged. This closure edits README/status/state only; metadata/source boundary receipts and refs under `artifacts/inv05-06873da/boundary/ci-close/`. This handoff's own fresh CI remains a separate PR merge gate. Reviews 0, protection access 403, Pages authorization absent; no merge/deployment/settings or real-data operation. NEXT: save/push clean closure, stop READY_FOR_NEXT, wait for `next` before Yahoo SCOPE-02. `continue` must preserve the completed scope.

- **INV-05/SCOPE-01 — LOCAL ACCEPTANCE — 2026-10-26:** Explicit `next` recovered clean, pushed HEAD `06873da3a627189d25e73bc8748fe935ee027ce0`; its run `40286766839` passed all three jobs. Existing AMFI/HTTP/cache/proof paths now reject nonfinite/nonpositive NAVs, stale/future/identity-conflicting observations, duplicate-date inflation and unaligned latest/history NAVs. Decimal source values retain unit-price precision; actual observation dates/baselines prevent invented 60-day returns, and drawdown includes recovered losses. Missing/stale Yahoo summary values no longer become a verified zero; provider expiry suppresses cached owner research without changing holdings. UI shows original NAV/date/coverage; screenshot review found and fixed dark metric contrast using the existing surface token. Fresh final focused backend **56 PASS**, Chrome workflow PASS, **4 Axe audits zero violations**; money/reconciliation/owner/outage/recovery covered with synthetic provider transport. Receipts: `artifacts/ci-repair-ac05515/inv05-backend-final.json`, `inv05-axe-contrast-final.json`; captures/accessibility under `artifacts/inv05-06873da/`. Contrast incomplete/manual screen-reader remains unverified; inspect source-bound receipts before reuse. Earlier red/intermediate runs remain diagnostic, not extra totals. Full INV-05 remains unaccepted; no live terms/quota, Yahoo bar symbol/timestamp alignment, real-account or packaged acceptance established. No BETTER adapter identified. NEXT: finish source boundary/commit/push and check this scope's exact-head CI; then await `next` for INV-05/SCOPE-02. No provider activation, currency/schema/holding write, production, master merge or Pages operation.

- **INV-02/SCOPE-02 — CI CLOSURE — 2026-10-26:** `continue` recovered clean, pushed HEAD `45a91a715577c61eecb8386e7762376cd35bcfc0`. Exact-head run `40241945067` PASS; native-windows `121315486163`, Selenium `121315486280`, Linux `121315486557` all successful. Eight accepted executable/test hashes match the saved proof; 97 backend/3 Chrome/4 Axe receipts were reused without rerunning unchanged acceptance. Fresh source/history privacy PASS with zero findings: `artifacts/inv02-scope02-7807d36/boundary/ci-close/`. Bounded task closes **95% → 100%**, READY_FOR_NEXT YES; full INV-02 remains unaccepted and 75/143 unchanged. This handoff changes README/status/state only; its own fresh PR checks are a separate owner-merge gate. PR #16 is still open, reviews 0, protection access 403, Pages authorization absent; READY_TO_MERGE NO. Remote master c47fed9 and separate local master 3932f39 were preserved; no branch synchronization, merge, deployment, provider/data or runtime change. NEXT: wait for `next` before INV-05; `continue` handles a confirmed manual owner merge without selecting another feature.

- **INV-02 / SCOPE-02 — SYNTHETIC LABELLED LAYOUTS — 2026-10-26:** base `7807d3653e5aad23e235a40294af783ec2de2633`, branch `development/alfred-integrated`. Dated synthetic Groww-style fund and Zerodha-style symbol tables now use labelled money columns, per-row/header account identity, raw decimal inputs and footer reconciliation. Units/prices/metadata/totals are not holdings. Missing/ambiguous money, conflicting rows/accounts, unsupported currency columns/cells and processing bounds abstain without partial writes. Account hints no longer match folio inside portfolio or cross line boundaries. Selected OCR output requires source review even when damaged headers disappear; diagnostic OCR attempts do not override selected digital provenance. Existing account-safe upsert, immutable receipts, owner corrections/retry and deferred upload transactions are reused. UI shows source extraction reasons, distinguishes owner corrections, and makes the overflowing import history a named keyboard-focusable region.
  TESTS: **97 distinct backend PASS**, zero skips: 19 parser/import cases (`artifacts/ci-repair-ac05515/inv02-scope02-layout-final.json`) plus 78 money, evidence, grounding and review/retry cases (`inv02-scope02-related-final.json`). Actual PDFs, exact source-byte download, owner/source/correction denial, reimport identity, original amounts, HALF_UP cents, corrected zero and unsafe-import preservation are covered. **3 unique actual Chrome workflows PASS**, zero skips (`artifacts/inv02-scope02-7807d36/browser-final/browser_regression_summary.json`); **4 Axe audits PASS** at 1440/390, light/dark, zero violations (`accessibility.json`, `inv02-scope02-axe-accepted.json`; final viewport captures in `inv02-scope02-axe-final-proof.json`). Axe overlaps the table Chrome case; do not sum it. Keyboard PageDown focus/scroll is exercised. Contrast incomplete/manual screen-reader is not verified. Earlier red/95-test/intermediate receipts overlap and are not extra totals.
  LIMITS/RECOVERY: synthetic layout acceptance is not broker authentication, generalized positional/scanned layout accuracy, real OCR accuracy, real-account, packaged or production acceptance. The first draft sparse/undated PDF Chrome flow exceeded its unchanged assertion wait; it remains unaccepted. Final representative fixtures include normal statement date/type/reference/prepared-for metadata; OCR safety is tested separately without claiming OCR throughput. A draft click was outside the clear viewport; it now scrolls for a real click. Axe exposed a real scrollable-region keyboard defect, fixed semantically without suppression; the new keyboard assertion waits for actual asynchronous scrolling, preserving its condition. No AI deadline, money/currency policy, schema, security gate or existing Travel assertion changed. Source 41eba07 committed/pushed; clean-source/history privacy PASS, zero findings. Publication refs and exact pushed-head CI are recorded in `artifacts/inv02-scope02-7807d36/boundary/`. Full INV-02 stays IMPLEMENTED_NOT_ACCEPTED, 75/143; extensions 0/13. NEXT: finish checkpoint/push/CI, then wait for explicit `next`; INV-05 is the next Phase A inspection while broad INV-02 evidence is unavailable.

- **INV-02 / ACCOUNT-SAFE PDF ACCEPTANCE — 2026-10-26:** source commit `8907f2840cd8ced230d33e8a405460cedc0a16a1`, base `ec680730d65d65702bc6c4aaa62f38ece1b8f73e`; branch `development/alfred-integrated`. Initial import upsert, line deduplication and immutable receipt matching now include account identity. Explicitly blank institutions remain unknown during correction, preserving the same holding through retry instead of creating a Generic-broker duplicate. The owned positions table displays escaped, masked account suffixes. Existing deferred upload transactions, Decimal rules, source originals, CSRF and owner protection are preserved; no schema/currency/provider/runtime or real-data operation. Eight executable/test file hashes match the accepted backend receipt; clean-source/history privacy PASS, zero findings. Published source CI remains IN_PROGRESS, separate from local bounded acceptance.
  ACCEPTANCE: **84 backend PASS**, zero skips (`artifacts/ci-repair-ac05515/inv02-final-accepted.json`); actual synthetic PDFs exercise extraction, per-account reimport, cross-owner/source denial, CSRF, receipt-write rollback, malformed/missing account abstention and corrections preserving 2.675→2.68 and explicit zero. **3 actual Chrome workflows PASS**, zero skips (`artifacts/inv02-ec68073/browser-accepted/browser_regression_summary.json`): two-account PDF upload/reimport/save-reopen, correction and exact field-source review/revocation/stale handling. Desktop/390px captures inspected. **4 focused Axe audits PASS**, light/dark at 1440/390px, zero violations; color-contrast has incomplete/manual items (`accessibility.json`, pinned official engine, `inv02-axe-accepted.json`). The Axe workflow overlaps one Chrome case; do not sum it. Early fixture/identity failures retained; parallel PDF-heavy local runs timed out while UI processing remained active, then serial runs passed without changing assertions/deadlines. AST/source/history privacy and final refs are pinned in `artifacts/inv02-ec68073/boundary/` after commit.
  LIMIT: a bounded technical scope is accepted, not generalized broker/layout accuracy or real-account acceptance. INV-02 remains IMPLEMENTED_NOT_ACCEPTED and baseline remains 75/143; extensions remain 0/13. Existing unknown-account legacy records remain separate and require owner reconciliation; no automatic history merge/rewrite. Recovery PR CI has a separate Travel failure, missing independent review, protection access 403 and unapproved Pages publishing. NEXT: stop and wait for `next`; inspect remaining INV-02 representative broker/layout evidence without repeating this scope, or explicitly defer genuine corpus blockers before INV-05.

- **BOOTSTRAP-01 / ACCESSIBILITY AND EXECUTION SYSTEM — 2026-10-26:** recovered source `5af834c`; minimal named-region repair committed as `6068100`, validated source `b2528c7`. Exact-source CI `40230734330` SUCCESS on Linux secure-failure, native-Windows and Selenium. Native artifact `12613023936`, browser `12613404250`, Linux `12613186417`; digests and final refs pinned in `artifacts/bootstrap-5af834c/boundary/checkpoint.json`. Local acceptance: 19 backend/documentation tests, two Chrome workflows, 22 native checks and 28 Axe audits PASS; remote native proof independently records the same 22/28 gates. Source/history privacy zero findings. No test/security weakening, migrations, financial/runtime changes, production operation, merge or publication. Later evidence-only documentation commits require their own PR checks; they do not change accepted executable source.
  DONE: requirements, concise README, deterministic phase/module queue, durable command checkpoint and AGENTS protocol; 143 unique original IDs/statuses reconciled unchanged (75 verified), 13 separately defined extension stories all unaccepted. Metadata/reference audit is not whole-product acceptance. Original historical receipts retained. Interrupted TRAVEL-09 hunks are preserved in `docs/recovery/TRAVEL09_DEFERRED.patch`, not executed or marked complete. NEXT: await `next`, then INV-02; PR review/protection/Pages and manual/packaged/real-account/production gates remain separate.

- **INTELLIGENCE HUB / LOCAL ACCEPTANCE — 2026-10-25:** HEAD = this checkpoint commit, base `f1fe646f56e3b8ce6b01a0f8cc14de940b4ebf28`, branch `development/alfred-integrated`. Recovery: clean/pushed source and previous receipt hashes matched. PR #16 READY/unmerged; prior source `f1fe646`, run `40211272570`: Linux/native-Windows/Selenium PASS. Independent reviews absent, protection read 403, Pages publishing unapproved. No merge, permission bypass, deployment or publication. New-head remote CI is recorded separately in `artifacts/intelligence-hub-f1fe646/boundary/checkpoint.json` after push; prior-source green is not new-source CI.
  DONE: Settings/Memory now includes an Intelligence Hub using existing `MemoryLearning`, `MemoryStore`, DPAPI wrapping, protected owner sync keys, retention, transactions and native lifecycle hooks. Existing encrypted candidates retain deduplication, evidence, unverified confidence and expiry; a coalesced encrypted learning revision/checkpoint survives interruption without authorizing uploads. Separately encrypted packs require local opt-in, explicit public source selection, bounded privacy/instruction screening and human confirmation of the exact content digest. Source fingerprints, citations, expiry, version parents and transaction checks reject stale/foreign/changed/conflicting promotions. They are supplementary reviewed data only: no automatic verified-memory import, training, model/registry changes, code execution or financial writes. A no-ORM-write lifecycle regression passes. Account reset clears local packs/consent; generation checks refuse old remote resurrection. Existing document/candidate/memory privacy remains intact.
  DORMANT TRANSPORT: separate Git adapter sends only reviewed encrypted packs in batches, never raw candidates, documents, keys or canonical records. Exact owner refs, fixed HTTPS grammar, bounded fetch/history/body/cache, immutable commit parents and normal fast-forward pushes preserve history; no checkout, force push, repository provisioning or executable remote content. Protected local cache is review-only offline fallback. Explicit digest-bound reconciliation retains local/remote versions; interrupted acknowledgement retries without duplicate commits. Native startup/minute/shutdown ticks checkpoint locally and contact Git only after separate operator authorization, an approved least-privilege credential and owner consent. Examples remain false/blank; credentials would stay in ignored local config/child environment, never URLs/arguments/Git config files/logs. No actual credential was activated, no remote repository was created/contacted for knowledge, and no private upload occurred. Historical encrypted Git commits can retain withdrawn content; portable key/device-loss and real private-Git acceptance remain unverified and approval-gated.
  TESTS: **137 affected backend/native/memory tests PASS**, zero skips (`artifacts/ci-repair-ac05515/hub-backend-accepted.json`). Final **64 backend PASS**, zero skips (`hub-final-accepted.json`): 24 Hub/Git and 40 document-corpus/conversation-history checks; 22 Hub cases overlap the 137. **5 actual Chrome workflows PASS**, zero skips (`artifacts/intelligence-hub-f1fe646/browser-accepted/browser_regression_summary.json`); final **2 affected Chrome rechecks PASS**, overlap the five (`browser-final/`), including consent, citations, escaped text, reopen, invalidation, 503 retry/selection retention, CSRF, cached conflict review, page-hide clearing and restored-page controls. Desktop/390px captures inspected; JS syntax and whitespace checks PASS. AST-only Graphify update PASS. Postcommit source/history privacy evidence is recorded under `boundary/` before normal development push; release acceptance is not claimed.
  FAILED EVIDENCE: `hub-first.json` exposed the public text screen mistakenly scanning random numeric digests; screen now inspects only human text while IDs/digests retain strict validation. `hub-integration.json` exposed the old one-command native tick assertion; it now checks both required bounded commands and startup/shutdown hooks. An earlier combined run (`hub-final-focused.json`) deferred one cached-withdrawal Git sync as unavailable; isolated command timing passed (maximum 0.469s), original cause was not reproduced. Its receipt is retained; final 64 PASS. Added safe operation/type/exit diagnostics, serialized consent/corrections with bounded publication, and preserved queued retries. No deadlines/security assertions were weakened; the 30-second AI deadline is unchanged. This isolated deferral must not be described as proven remote reliability.
  FILES: full merged files, alphabetical: `alfred_ai/native_tasks.py`, `alfred_ai/settings.py`, `alfred_native.py`, `apps/ml_engine/api/memory.py`, `apps/ml_engine/api/urls.py`, `apps/ml_engine/management/commands/checkpoint_knowledge_hub.py`, `apps/ml_engine/services/knowledge_git.py`, `apps/ml_engine/services/knowledge_hub.py`, `apps/ml_engine/services/memory_learning.py`, `apps/ml_engine/services/persistent_memory.py`, `config/local.env.example`, `config/native.local.env.example`, `docs/PROJECT_STATUS.md`, `scripts/release_validation.py`, `static/js/memory.js`, `templates/settings/memory.html`, `tests/test_knowledge_hub.py`, `tests/test_memory_sync_runtime.py`, `tests/test_user_data_browser.py`. No new dependency, Django/financial migration, provider/model activation, key-format change or canonical calculation. Rollback: normal source revert; preserve additive encrypted vault tables and existing keys. Production, backups, frozen candidates and the separate master worktree were not operated on.
  COUNTS/CONTINUATION: new bounded Hub work is separate technical acceptance, not completion of genuine-outcome/training or real-provider requirements. **75 verified / 24 unaccepted / 26 partial / 10 missing / 5 approval / 3 external = 143** unchanged. Weights `[5,10,15,20,15,15,15,5]`; steps 1/3/4/5/6 complete **70%** at source capture. Source/privacy closure, development commit/push and final weighted progress are recorded in `artifacts/intelligence-hub-f1fe646/progress.json` and `boundary/checkpoint.json`; maximum **90% while PR step 2 is blocked**. NEXT: check new-head PR CI without merging; inspect TRAVEL-09's crow-flight corridor ranking and missing road-network detour evidence with synthetic fixtures. Do not rerun accepted Hub/Travel tests without affected changes or activate Git/Pages/providers. RESUME: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content artifacts/intelligence-hub-f1fe646/progress.json; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 16`. Focused Hub regression only if changed: configured SDK `artifacts/ci-repair-ac05515/run.py hub-resume manage.py test tests.test_knowledge_hub --noinput`.

- **TRAVEL-08 LOCAL RESTRICTION REFERENCE ACCEPTANCE / LIVE PROGRESS — 2026-10-25:** HEAD = this checkpoint commit, base `7a0b91201bf884d0ac02ea565e7fe077d5edc602`, branch `development/alfred-integrated`; master remains `c47fed9`, PR #15 merged, PR #16 draft. Recovered a clean, pushed tree and verified the previous checkpoint's receipt hashes (zero mismatches). PR #16 exact source `7a0b912`, run `40208277827`: Linux, Selenium and native-Windows PASS. These are prior-source gates, not CI for this new implementation. Independent reviews are absent; protection read and PR metadata update return integration 403; Pages authorization remains absent. No merge, setting/protection bypass, deployment or Pages operation.
  DONE: reused owned `TravelResearchEvidence` and existing planner-session API/UI for manual public restriction review/withdrawal. A current exact route/profile and trip-context binding, explicit owner attestation, bounded supporting quote, `.gov.in`/`.nic.in` HTTPS reference and current check/expiry within 24 hours are required. Only prohibition/conditional claims are accepted; whole-route permission is rejected. Receipt hashing normalizes times to UTC. Owner/session, revision, timestamp and receipt checks reject unavailable, foreign, corrupt, changed or unsupported evidence. Rows are bounded to 20 per route/context and 100 per session; duplicate identical reviews reuse the row. Withdrawal retains the quote/source and adds a dated conversation event. All reads revalidate state; corrections need a new review. No new model/table/migration, dependency, provider activation, source fetch, monetary arithmetic, encryption, history sharing or runtime change.
  STATUS CONTRACT: **VERIFIED means the owner's reviewed reference only**, never independently authenticated law, route coverage or legal clearance. UNKNOWN covers missing/withdrawn/conflicting/wrong-context evidence; STALE retains expired quotes without a current conclusion; UNAVAILABLE covers missing/expired routing or identity. `motorcycle_legal` remains UNKNOWN in every case. Highway avoidance/car routing never establish bike legality. UI exposes citations, checked/expiry times, escaped supporting quotes, source limits, busy controls, meaningful errors, retained drafts and withdrawal; no cloud/model call. Current canonical finance and saved itinerary/allowances remain unchanged by review.
  TESTS: **160 affected backend integration tests PASS**, zero skips (`artifacts/ci-repair-ac05515/travel08-backend-accepted.json`), including TRAVEL-07 providers/selection, money reconciliation, planner, continuation, refresh, HTTP, pools and multi-stop. Final **21 focused restriction/route tests PASS**, zero skips (`travel08-final-focused.json`), overlap 20 integration cases and add the missing-identity/same-owner-session case; do not sum as independent totals. **13 integrated actual Chrome workflows PASS**, zero skips (`artifacts/travel-restrictions-7a0b912/accepted-browser/browser_regression_summary.json`); final two affected Chrome rechecks PASS, overlap the 13 (`final-browser/`). New workflow covers all four statuses, malicious host rejection with meaningful feedback, 503 retry/draft retention/busy state, citations/XSS escaping, reopen, conflicting reviews, withdrawal, source expiry, route expiry/missing identity, desktop/390px UI and unchanged synthetic financial rows/itinerary. Earlier focused counts overlap. Desktop/narrow captures inspected. Source/JS/AST/privacy closure is recorded under `artifacts/travel-restrictions-7a0b912/boundary/` after commit before push; no new packaged/native/live-provider/production acceptance is claimed.
  FIXES/EVIDENCE: a new local-time regression reproduced a UTC database round-trip receipt mismatch; canonical UTC timestamps fixed it (`travel08-timezone-before.json`). A new API expiry fixture initially advanced Django's shared clock and expired the authenticated session; scoped only the restriction-service clock, preserving session rules (`travel08-api.json`, then passing `travel08-api-accepted.json`). No test deadlines, quality/security assertions, provider quotas, currency rules or financial records were weakened/rewritten. Failed receipts remain available.
  FILES/COUNTS: full merged files, alphabetical: `apps/mobility/planner_views.py`, `apps/mobility/services/travel/restrictions.py`, `docs/PROJECT_STATUS.md`, `docs/TRAVEL_PROVIDERS.md`, `scripts/release_validation.py`, `static/js/travel_planner.js`, `tests/test_travel_planner_browser.py`, `tests/test_travel_restrictions.py`. New regression module is in the required backend profile. TRAVEL-08 remains **PARTIALLY_IMPLEMENTED** for independently authenticated official restrictions, actual road/expressway coverage, current conditions, global sources and real-account/release acceptance. Counts remain **75 verified / 24 unaccepted / 26 partial / 10 missing / 5 approval / 3 external = 143 (52.4% verified)**. Production/private records, backups, frozen releases and the separate master worktree were not operated on. Rollback: normal source revert; no schema/data operation.
  WEIGHTED CONTINUATION: weights `[5,10,10,25,15,20,10,5]`; steps 1/3/4/5 done at source capture (**55%**). Step 2 remains blocked; prior-source green CI does not replace missing independent/protection/publication gates or new-head checks. Acceptance/privacy, push and final verification are completed and recorded in order in the durable `artifacts/travel-restrictions-7a0b912/progress.json` and `boundary/checkpoint.json`; read their exact completion percentage/HEAD before repeating steps. Maximum completion is **90% while step 2 remains blocked**, never 100%. NEXT after closure: inspect TRAVEL-09's sampled crow-flight corridor ranking and bounded road-network detour/provenance gap using synthetic fixtures; do not label straight-line offsets as verified road detours. Preserve DOC-02/DOC-06 verification, DOC-07/TRAVEL-07 bounded acceptance and AI-15/16→AI-12/FIN-07 genuine-outcome gates. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content artifacts/travel-restrictions-7a0b912/progress.json; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 17`. Focused tests only after affected changes: configured SDK `artifacts/ci-repair-ac05515/run.py travel08-resume manage.py test tests.test_travel_restrictions tests.test_travel_route_choices --noinput`.

- **TRAVEL-07 BOUNDED ALTERNATIVES / EXPLICIT ROUTE CHOICE — 2026-10-25:** HEAD = this checkpoint commit, base `90abb2883d507bcfea52fcb54b288637286a1509`, branch `development/alfred-integrated`; master remains merged PR #15 at `c47fed9`. Added a separately cached/quota-accounted ORS alternative request only after a current single-route result of at most 100 km. Requests at most three results, preserves avoidance/profile parameters, deduplicates normalized geometries and retains the single result with an unavailable comparison when alternatives fail. Cache v3 excludes legacy snapshots without deleting evidence. No new provider, credentials, dependency, runtime, schema or currency change; all provider acceptance used synthetic fixtures.
  DONE: destination cards now expose route distance/duration, source/check time, explicit limitations and an owned revision-checked choice. Selection verifies the current geometry identity and source timestamps, rejects expired/changed evidence, updates the selected map geometry and reuses the existing Decimal budget/itinerary builders. The button explicitly rebuilds draft days/allowances; saving remains separate and a previously saved plan is unchanged until Save. Confirmed choices survive matching refreshes; missing choices require review rather than substituting a different route. Home-to-destination choices are refused for multi-stop legs. Existing citations, session/CSRF, owner isolation, worker supersession and retry/busy controls are preserved. Historic research rows and canonical finance records are unchanged.
  TESTS: **147 affected backend tests PASS**, zero skips: 93 route/provider/planner/continuation (`artifacts/ci-repair-ac05515/travel-route-accepted.json`) plus 54 refresh/HTTP/destination-pool/multi-stop (`travel-route-integration.json`). Seven new regressions cover bounded requests/deduplication, unavailable comparisons, long/stale routes, confirmed-choice invalidation, ownership/session/CSRF/revision boundaries, saved-plan isolation, geometry and Decimal category/day reconciliation. **Twelve integrated actual Chrome workflows PASS**, zero skips (`artifacts/travel-routes-90abb28/accepted-browser/browser_regression_summary.json`), including eight planner workflows plus four destination-batch/multi-stop/order-preview/place-evidence workflows (`related-browser/browser_regression_summary.json`), route comparison/503 retry, selection into an itinerary, save/reopen, expiry rejection, unchanged finance rows and existing preferences flows. Final one-case capture recheck PASS, overlaps the twelve (`final-browser/`); desktop and 390px route panels inspected. Initial backend failures were new fixtures incorrectly using save/reopen; original failed receipts retained. First Chrome assertion expected integer display instead of normalized `3.0` hours, with an additional parent-console cp1252 encoding failure; corrected the fixture and used process-local UTF-8, retaining failed evidence. No application/test deadlines or assertions were weakened. JS syntax/whitespace PASS. Graphify AST rebuilt to 10,901 nodes; a scoped query confirms the new symbols (PowerShell warning output gave the update wrapper a nonzero exit despite completed graph output). Source/privacy closure and exact post-push metadata: `artifacts/travel-routes-90abb28/boundary/`.
  FILES/STATUS: full merged files, alphabetical: `apps/mobility/planner_views.py`, `apps/mobility/services/travel/mapping.py`, `apps/mobility/services/travel/providers/routing.py`, `apps/mobility/services/travel/research.py`, `apps/mobility/services/travel_itinerary.py`, `apps/mobility/services/travel_research.py`, `docs/PROJECT_STATUS.md`, `docs/TRAVEL_PROVIDERS.md`, `scripts/release_validation.py`, `static/js/travel_planner.js`, `static/js/travel_research_panels.js`, `tests/test_travel_planner_browser.py`, `tests/test_travel_route_choices.py`. TRAVEL-07 remains **PARTIALLY_IMPLEMENTED**: distinct geometries do not establish different legal roads, scenic quality, actual road overlap, live service availability, long-distance alternatives or independent route quality. No live provider authentication/network acceptance, packaging/native or production acceptance was run. Counts recalculated unchanged **75 verified / 24 unaccepted / 26 partial / 10 missing / 5 approval / 3 external = 143**. Rollback: normal source revert; no data/schema action. Production, Pages, private/live data, backups, frozen releases and the separate dirty master worktree were not operated on.
  NEXT/RESUME: DOC-02/DOC-06 stay verified; preserve DOC-07's accepted bounded whole-extraction scope. AI-12 expansion cannot bypass AI-15 genuine per-model outcomes / AI-16 sustained independent drift gates; FIN-07 predictive acceptance still needs reviewed chronological outcomes, and monetary INV-07 remains currency/valuation-gated. Next independent task: inspect TRAVEL-08's existing restriction evidence/abstention boundary and complete only a separately testable gap; do not certify car routes as motorcycle-legal or activate providers. Review a new scoped draft PR only after exact-source checks; no further master merge/Pages publication is authorized. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 17`. Focused command only after affected changes: configured SDK `artifacts/ci-repair-ac05515/run.py travel-route-resume manage.py test tests.test_travel_route_choices tests.test_travel_providers --noinput`.

- **DOC-07 BOUNDED WHOLE-EXTRACTION ACCEPTANCE — 2026-10-25:** HEAD = this checkpoint commit, base `39ebeb3c293f28b20149e5ad72f63d54fc8c3983`, branch `development/alfred-integrated`; master/merged PR #15 = `c47fed9`. Added optional `context_mode=full_extraction` to the existing encrypted selected-document question API and Documents UI. Supplies every character of the selected retained extraction, including clauses outside keyword hits, or refuses before inference when the existing six-passage/4096-byte request limit cannot hold it. No silent truncation, keyword filtering, partial answer or cloud fallback. Keyword mode remains the default and keeps its existing behavior. The model selects quotation indices only; source hashes/ranges, current ownership, consent, corrections, deletion, expiry/reset and post-inference revision validation remain authoritative. `context_complete` describes supplied retained text, not original extraction authenticity, correctness or arbitrary PDF/OCR comprehension. No financial prose/calculation or canonical-record mutation is introduced.
  TESTS: **159 final affected backend/API/extraction/grounding/privacy/storage tests PASS**, zero skips (`artifacts/ci-repair-ac05515/doc07-full-accepted.json`), including the new PDF original/hash/text-layer provenance case, exact coverage, cross-document coverage, missing/foreign/expired sources, tail corrections and delete/reset during inference, UTF-8/passage limits before inference, invalid mode/extra fields/URL data, session/CSRF and unavailable/late/malformed model outputs. Earlier 45-test run overlaps and is not added. **Five integrated actual Chrome workflows PASS**, zero skips (`artifacts/doc07-full-c47fed9/accepted-browser/browser_regression_summary.json`): new whole-context mode and busy controls, keyword compatibility, no silent fallback for long text, local outage/retry, stale source rejection, original/hash citations, unsafe-text escaping, general PDF/text upload, corpus lifecycle and catalog ordering. Desktop/390px captures inspected; canonical Expense/BankAccount/Investment/Loan rows unchanged. First browser run asserted animated offscreen citation text before scrolling; the failure artifact contains the correct quoted DOM. Moved the existing visibility wait after scroll without weakening assertions/deadlines; original failed receipt remains in `browser/`.
  REAL-LOCAL: **Four new synthetic qwen3.5:4b cases PASS**, zero skips (`artifacts/ci-repair-ac05515/doc07-full-real-local.json`; individual metrics under `artifacts/doc07-full-c47fed9/real-local/`): complete PDF evidence without keywords 9.360s; a late conflicting clause 8.218s; missing penalty amount abstention 7.328s; investment advice abstention 7.015s. All completed with model identity unchanged and `done_reason=stop`; no unchanged legacy cohort was rerun. Observed Ollama `0.40.11`, existing model digest `d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04`. Model/embedding identities, residency settings, schema/quality assertions, 30-second deadline and private/cloud/history policies are unchanged. No driver/runtime/dependency/schema/currency changes, live data, production, Pages, backups or frozen-release operations. Source/JS/AST/privacy closure at `artifacts/doc07-full-c47fed9/boundary/`; exact pushed SHA and scope evidence are recorded there after commit.
  FILES/STATUS: full merged files (alphabetical): `apps/ml_engine/api/document_corpus.py`, `apps/ml_engine/services/document_corpus.py`, `apps/ml_engine/services/document_questions.py`, `docs/PROJECT_STATUS.md`, `scripts/release_validation.py`, `static/js/document_corpus.js`, `templates/documents.html`, `tests/test_document_full_context.py`, `tests/test_document_questions_ollama.py`, `tests/test_user_data_browser.py`. The new deterministic regression module is in the required backend profile; real-local tests remain explicit opt-in. DOC-07 remains **PARTIALLY_IMPLEMENTED** for longer/arbitrary original documents, OCR, independently reviewed broad quality and real-account/release acceptance. Four authored synthetic cases are not independent accuracy or calibrated confidence. Counts remain **75 verified / 24 unaccepted / 26 partial / 10 missing / 5 approval / 3 external = 143**. Rollback: normal source revert; no data or migration action.
  NEXT/RESUME: DOC-02/DOC-06 are already verified; do not rebuild them. Preserve this bounded acceptance and continue the next independent AI-12 owner-scoped evidence gap without bypassing AI-15/16 genuine outcome gates; FIN-07 actual outcome data and monetary INV-07 currency/valuation remain gated. No new master/Pages operation is authorized. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 18`. Focused follow-up only after affected changes: configured SDK `artifacts/ci-repair-ac05515/run.py doc07-full-resume manage.py test tests.test_document_full_context tests.test_document_questions tests.test_document_corpus --noinput`; four explicit real-local cases use `artifacts/doc07-full-c47fed9/run-local.py` inside the isolated runner.
- **POST-MERGE RECOVERY / DEVELOPMENT SYNC — 2026-10-25:** PR #15 is confirmed merged at `c47fed95f919859aa62f1875512e3cb8452f2d48` (2026-10-25 13:28:31 UTC), source `0645e8e2bebf71539ba157e9195c791053654e73`. Recovered a clean development tree, fetched remote refs and fast-forwarded `development/alfred-integrated` to `origin/master` without reset/stash/overwrite. Source and merge have identical tree `7187b464abc3f8ba22beaa3022b0bc1c4e792c48`; no accepted implementation was rebuilt. HEAD = this checkpoint commit, base = `c47fed9`. The separate `F:\ALFRED\alfred_ai` master worktree remains at `3932f39` with pre-existing tracked/untracked edits; it was inspected read-only and left untouched.
  CI/EVIDENCE: exact source `0645e8e`, run `40190071853`, all three jobs PASS: **1,256 backend / zero skips, 102 actual Windows Chrome / zero skips, Linux four secure-failure plus 18 portable Chrome, and 22 native HTTP/recovery/backup/concurrency/worker/accessibility checks PASS**. Native archive `12598625785` SHA-256 `6584dbe55f71971c532ed60f4566b6f3c5b673e655314050a2107429da06b2c9` verified; backend log digest `fe96443fd2eb90b82725aae0521fdb32c6dcea3e0a69cfe6a231056b6c8e33c6` verified. GitHub-tested merge `dc668468c435bbca5f24ffdf6c2cae1068e0f48d` has the same tree. Complete receipts at `artifacts/ci-native-4c661be/passed/ci-evidence.json` and `boundary/pr15.json`. No duplicate full-suite run on unchanged source. The connector returned no workflow run for merge SHA `c47fed9` at recovery; do not turn prior-source evidence into a claim of a new master run.
  SAFETY/STATUS: no production, live database, backup, frozen-release, master-worktree, system/runtime or Pages operation was performed by this continuation. External changes to those systems were not audited through private/live-data access. The user's external merge does not authorize another Pages publication or deployment. Counts unchanged **75 verified / 24 unaccepted / 26 partial / 10 missing / 5 approval / 3 external = 143**. DOC-02/DOC-06 remain verified and must not be restarted. NEXT: DOC-07 explicit bounded whole-extraction context, complete-context-or-abstain handling, exact citations/invalidation, backend/privacy/Chrome and real-local synthetic quality evidence; long/OCR and broader independent quality remain separate until demonstrated. Exact post-push sync metadata at `artifacts/postmerge-c47fed9/sync.json`. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 16`.

- **PR #15 WINDOWS BACKEND QUOTA ISOLATION — 2026-10-25:** HEAD = this checkpoint commit, base `4c661beb99b8f07f80ce6e51363d31654935124f`, branch `development/alfred-integrated`. Run `40187601217` completed: Selenium **102 tests PASS** and Linux PASS; Windows job `121151643966` failed in the backend stage (**1,255 tests, four failures, 998.534s**), so native HTTP/recovery/accessibility did not execute. This was not an installer/native launch failure. Downloaded artifact `12597492720` to `artifacts/ci-native-4c661be/native-windows-proof.zip`; verified SHA-256 `18ae0238e8531f289ac490f5c46635fa37d2f750f0968ae07f9981c58504334e`. GitHub tested merge `1a379ea01ef5e4919585334130dcd1d22c262ced`; its tree equals source `4c661be` (`4941ee717b624e084f0b5a2f60d9f335448862ba`). Preserved original failure evidence; no user work was dirty on recovery.
  ROOT CAUSE/PROOF: loan payoff/retry and cloud sync/reasoning API fixtures shared a persistent request-quota directory across otherwise isolated database tests. The newly included matching module also used that shared store. All four CI-named tests pass alone (`artifacts/ci-repair-ac05515/ci-native-four-before.json`). A synthetic reproduction pre-exhausting the default 120/hour global expensive-request bucket produces exactly the same four failing tests, now with visible 429-versus-202/200/503 assertions (`ci-native-quota-reproduced.json` and log; script `artifacts/ci-native-4c661be/reproduce-quota.py`). The original CI privacy log omits assertion values, so the recorded direct evidence is the named CI failures plus this controlled cross-test contamination reproduction. Database/cache cleanup does not clear persistent diskcache quotas. Including the existing matching module in `63f5ec5` exposed this suite-order dependence; no arithmetic or provider security failure is inferred from the test names alone.
  FIX/TESTS: only test fixtures changed: Career matching, loan money, cloud wire-fixture and reasoning tests now use separate temporary quota directories per case. Production middleware, persistent quotas, thresholds, authentication, CSRF, AWS/provider disables, monetary code and all existing assertions are unchanged. Added a real recruiter 429 regression proving the quota still rejects before parsing or saving and returns Retry-After. With the outer global quota still exhausted, the same four tests now **PASS** (`ci-native-quota-after.json`); **80 focused backend/money/privacy/matching/abuse-limit tests PASS**, zero skips (`ci-native-isolation-focused.json`), including within-test atomic/restart limits, ownership, finite Decimal/zero handling and no external calls. These overlapping runs are not added. System checks/whitespace/AST refresh PASS. No local repeat of unchanged passing Chrome workflows; the required complete backend/native/Linux/Selenium gates run on the pushed source. Exact push/CI result is retained at `artifacts/ci-native-4c661be/boundary/pr15.json`; pending CI is not presumed green.
  FILES/STATUS: full merged files (alphabetical): `docs/PROJECT_STATUS.md`, `tests/test_career_matching_acceptance.py`, `tests/test_loan_related_money_runtime.py`, `tests/test_memory_cloud.py`, `tests/test_memory_reasoning.py`. Counts unchanged **75 verified / 24 unaccepted / 26 partial / 10 missing / 5 approval / 3 external = 143**. No migration, dependency, canonical financial record, live data, runtime, cloud activation, production or master change. Rollback: normal source revert, no data action. PR #15 remains ready/unmerged; independent approval, accessible protection gates (403) and explicit Pages authorization remain missing.
  NEXT/RESUME: inspect exact pushed-head full CI; if another failure appears, inspect its artifact before another change. Do not rerun unchanged failures or relax limits/assertions. After green, continue the bounded DOC-07 full-document evidence contract; AI-15/16 outcome-data gates remain unchanged. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 16`. Focused command only when affected source changes: configured SDK `artifacts/ci-repair-ac05515/run.py ci-native-resume manage.py test tests.test_career_matching_acceptance tests.test_loan_related_money_runtime tests.test_memory_cloud tests.test_memory_reasoning tests.test_global_abuse_limits --noinput`.

- **CAREER-04 MATCHING CONSISTENCY FOLLOW-UP — 2026-10-25:** HEAD = this checkpoint commit, base `63f5ec559182f6b93e366721adfd9bef5b8a164d`, branch `development/alfred-integrated`. The first manual slice was committed/pushed cleanly in `63f5ec5`; its source/history privacy gate passed with zero findings. A further actual Chrome regression showed that the separate job-link button stayed available during a resume-list outage; source inspection confirmed it did not submit the visible resume choice. Both forms now use that owner-checked choice, disable matching when choices are unavailable, and retain busy/error/retry behavior. The helper text explicitly says the choice applies to both forms. No API/security/money/model/timeout change in this follow-up.
  TESTS: **4 final integrated actual Chrome PASS**, zero skips (`artifacts/recruiter-9baf15a/link-accepted/browser_regression_summary.json`): selected older resume for message/attachment and URL, source citations, abstention, unavailable-list recovery, parser retry, correction/reopen, financial invariance and upload-limit recovery. Earlier five/two passes overlap, not additional totals. Before-fix Chrome failure: `link-before/`. Reuse the **81 backend/API/privacy PASS** at the immediately preceding checkpoint: affected Python services are byte-for-byte unchanged. JS syntax, whitespace and AST refresh PASS; final source/privacy evidence at `artifacts/recruiter-9baf15a/link-boundary/source-checks.json`, push/CI details at `artifacts/recruiter-9baf15a/boundary/pr15-latest.json`. Files (alphabetical): `docs/PROJECT_STATUS.md`, `static/js/career.js`, `templates/career/list.html`, `tests/test_user_data_browser.py`. Rollback: normal source revert, no migration.
  STATUS/BLOCKERS/NEXT: counts remain **75 verified / 24 unaccepted / 26 partial / 10 missing / 5 approval / 3 external = 143**; full CAREER-04 remains partial for automatic mailbox/provider acceptance. PR #15 is ready/unmerged; no independent approval, protection visibility returns 403, and Pages publishing is not authorized. Prior source `63f5ec5` run `40187029658`: Linux PASS, Windows/Selenium pending at this checkpoint; latest pushed-head gates must be inspected, not assumed green. DOC-02/DOC-06 remain verified. Inspected DOC-07's existing selector: six retrieved excerpts and a 4096-byte request bound do not implement full-context arbitrary-document Q&A; do not relabel it accepted. AI-15 genuine model outcomes, AI-16 sustained drift/independent cohorts, FIN-07 actual outcomes and monetary INV-07 valuation/currency remain gated or unestablished; no unchanged inference was repeated. Next executable work: design/implement a bounded full-document DOC-07 evidence contract, preserving encrypted explicit selection, source invalidation, abstention and the 30-second deadline; then execute independent quality acceptance. No unfinished source edits remain at this checkpoint. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 18`.

- **CAREER-04 MANUAL RECRUITER ACCEPTANCE — 2026-10-25:** HEAD = this checkpoint commit, base `9baf15aa115670f309ded0bd4cb1da5942cb0e0a`, branch `development/alfred-integrated`. Recovered a clean, pushed tree; preserved both existing worktrees. PR #15 is ready/unmerged at the recovered source, without independent review. Run `40185664852`: Linux secure-failure/portable browser PASS; Windows and Selenium pending at this checkpoint. No master merge: explicit Pages authorization, independent review and accessible protection gates remain missing. Exact final CI/push metadata is retained at `artifacts/recruiter-9baf15a/boundary/pr15.json`; earlier-source checks are not attributed to changed source.
  DONE: manual recruiter intake now lists only the owner's saved resumes and supports an explicit older resume instead of silently choosing the newest. Both text/attachment and job-link APIs validate optional `resume_id` before parsing/provider work, reject foreign/missing records and malformed IDs, and retain the existing latest-resume/manual-profile default when omitted. The comparison captures the selected resume fields and references; later resume edits do not rewrite it. The UI shows the attachment source name, busy/error/retry feedback, retains failed inputs, prevents duplicate active submissions and disables intake while the resume list is unavailable. Reload and successful resume upload refresh the choices. No mail access or new provider is activated.
  FOUND/FIXED: before-fix regressions reproduced both APIs ignoring explicit resume selection and recruiter retry discarding attachment-derived requirements when a message header existed (`artifacts/ci-repair-ac05515/recruiter-before.json`). Retry now reparses the captured combined evidence and preserves accepted corrections. A new owner-isolation test also exposed an uncaught missing-record exception on foreign correction/retry: the shared endpoints now return the same generic 404 for missing/foreign records; authorization remains owner-filtered. Legacy interactive OAuth retirement was already completed in `86947a6`; the old tracker next step was stale and must not be repeated.
  TESTS: **81 focused backend/API/review/retry/privacy tests PASS**, zero skips (`artifacts/ci-repair-ac05515/recruiter-accepted.json`), including selected/legacy resume behavior, abstention, owned citation snapshots, correction/retry ownership, CSRF/authentication, parser failures and unchanged review contracts. Earlier 43-test run exposed the missing-record exception and is retained as failure evidence (`recruiter-focused.json`), not claimed passing. **5 integrated actual Chrome workflows PASS**, zero skips (`artifacts/recruiter-9baf15a/accepted-browser/browser_regression_summary.json`): manual JD attachment/selected older resume, parser failure and retained retry, Document Center retry/correction/reopen, unavailable resume-list recovery, existing matching/abstention/source privacy, opportunity-outcome corrections/stale draft, and upload-limit recovery/valid resume. The earlier two Chrome passes overlap and are not additional tests. Inspected desktop/390px captures; malicious-looking filenames stay text. Expense, bank-account, investment and loan rows are unchanged throughout manual acceptance. JS syntax, Django system checks, whitespace and AST update PASS; no model/schema/migration or money calculation changes.
  STATUS/FILES: CAREER-04 remains **PARTIALLY_IMPLEMENTED**: the local synthetic manual-equivalent scope is accepted, automatic mailbox access/live-provider and independent real-account/release acceptance are not. Counts unchanged **75 verified / 24 unaccepted / 26 partial / 10 missing / 5 approval / 3 external = 143**. Full merged files (alphabetical): `alfred_ai/services/document_review.py`, `alfred_ai/views.py`, `apps/career/views.py`, `docs/PROJECT_STATUS.md`, `scripts/release_validation.py`, `static/js/career.js`, `templates/career/list.html`, `tests/test_career_matching_acceptance.py`, `tests/test_user_data_browser.py`. The matching/ownership regression module is now included in the required backend profile. Rollback is a normal source revert; no migration or canonical financial rewrite is needed.
  NEXT: inspect exact pushed-head PR CI; do not repeat accepted manual matching or retired OAuth. AI-15 per-model outcomes and AI-16 sustained drift remain data-gated; do not claim AI-12 predictive readiness. Inspect the remaining independent DOC-07 full-context/quality gap, preserving verified DOC-02/DOC-06. FIN-07 genuine outcomes and monetary INV-07 currency/valuation gates remain unchanged. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 14`. Relevant focused command, only when affected source changes: configured SDK `artifacts/ci-repair-ac05515/run.py recruiter-resume manage.py test tests.test_career_matching_acceptance tests.test_document_retry_integrity --noinput`.

- **AI-15 BOUNDED READINESS / AI-16 SAFEGUARDS — 2026-10-25:** HEAD = this checkpoint commit, base `a17abbd2688343b268f9c852d6c5aef01966c852`, branch `development/alfred-integrated`. Added lazy, authenticated `/api/ai/runtime-status/?serving_readiness=1` and the AI Assistant's expandable local-readiness panel. Reuses current model specifications, registry maturity and adapter gates; exposes only fixed model labels, eligibility/fallback reasons, fallback descriptions and check time. No artifact paths, private notes/names, sample counts, owner identities, raw confidence/quality scores, model deserialization, inference, training activation or provider changes. Registry eligibility is explicitly **not** artifact execution, predictive accuracy or calibrated confidence; actual adapters revalidate before inference. Refresh clears earlier claims on error; 503 is unknown, not ready. Desktop/390px captures inspected. Corrected expense fallback description to its actual recent-median next-debit fallback, separate from FIN-07 cash flow.
  FOUND/FIXED: regression tests reproduced quality/confidence values above 100 passing registry gates, and future `last_finished_at` metadata remaining fresh. Tightened the shared score range to the existing lower thresholds through 100, and freshness to reject future completion time. Valid thresholds/deadlines, unknown completion-date compatibility, proxy-target blocks and deterministic fallbacks remain intact; no gates weakened. Before-fix failures: `artifacts/ci-repair-ac05515/ai15-score-before.json` (two subcases), `ai15-future-before.json`. No finance arithmetic/schema, model identity/residency, paid/private provider, history, production or system-runtime change.
  TESTS: **45 final readiness/model-registry/orchestration/API tests PASS**, zero skips (`artifacts/ci-repair-ac05515/ai15-readiness-accepted.json`; earlier overlapping runs are not additional tests). **70 retrieval/evaluation/learning/privacy safeguard tests PASS**, zero skips (`ai16-safeguards.json`): frozen thresholds, missing/nonfinite/invalid metrics, incomparable cohorts/models, stale/current-source rejection, owner/index isolation, deadlines, explicit opt-in and no private/cloud use. No unchanged real-Ollama cohort was rerun and no model/protocol was promoted. **4 actual Chrome workflows PASS** (`artifacts/ai15-26bad2e/browser/browser_regression_summary.json`): new readiness view, existing assistant retry, source-policy outage/privacy and investment reminders; **one overlapping final readiness PASS** after the final gates (`accepted-browser/browser_regression_summary.json`). Covers eligible-versus-corrupt artifact separation, deterministic median without prediction, missing/stale/proxy/low-evidence/nonfinite/out-of-range/future metadata, refresh/unavailability, escaping, private-field omission, normal-user controls and narrow-screen overflow. System/migration drift (no changes), JS syntax, whitespace and AST update PASS.
  STATUS: AI-15 remains **IMPLEMENTED_NOT_ACCEPTED** for its full genuine per-model outcome scope; the bounded readiness/UI/fallback acceptance is now recorded, not substituted for real accuracy. AI-16 remains **PARTIALLY_IMPLEMENTED**: safeguards accepted; broader independent cohorts, sustained chronological drift/calibration and promotion remain unestablished. AI-12 expansion must not bypass these prerequisites. Counts unchanged **75 verified / 24 unaccepted / 26 partial / 10 missing / 5 approval / 3 external = 143**. FIN-07 genuine outcomes and monetary INV-07 currency/valuation rules remain blocked; DOC-02/DOC-06/TRAVEL-03 are already verified and must not be restarted. DOC-07 full-context/independent quality remains incomplete.
  FILES (alphabetical): `apps/ml_engine/api/views.py`, `apps/ml_engine/models/training_state.py`, `apps/ml_engine/training/orchestrator.py`, `apps/ml_engine/training/quality.py`, `docs/PROJECT_STATUS.md`, `scripts/release_validation.py`, `static/js/intelligence.js`, `templates/ai_insights.html`, `tests/test_serving_readiness.py`, `tests/test_user_data_browser.py`. Complete merged source saved. Rollback: normal source revert; no schema or canonical financial writes. Exact-source/privacy/push/PR evidence at `artifacts/ai15-26bad2e/boundary/`; fresh pushed-head CI required. PR #15 ready externally, no approving review, Pages authorization or protection access; no merge/deployment. Run `40183764925` at `26bad2e`: Selenium PASS, Linux failed only the duplicate cache-header contract (repaired in preceding `a17abbd`); check Windows completion before treating any broader result as accepted.
  NEXT (superseded by manual recruiter checkpoint above): genuinely reviewed per-model chronological outcomes/unseen evaluation contracts remain necessary before completing AI-15/16 or expanding AI-12. Legacy interactive OAuth was already retired; do not restart it or authenticate providers/access mail. Do not repeat recorded passing suites unless affected source changes.

- **INV-07 CACHE CONTRACT REPAIR — 2026-10-25:** HEAD = this checkpoint commit, base `26bad2e2375b775e5b74e9ae66365f284306aea4`. Run `40183764925` Linux secure-failure exposed GET/POST header mismatch: the reminder endpoint's redundant `never_cache` decorator appended directives to the shared `MemoryAPI` `no-store, private` contract. Removed only the redundant decorator; inherited no-store/private, authentication, CSRF, encryption and fail-closed behavior remain intact. No test/security relaxation. **9 focused reminder/API/privacy tests PASS**, zero skips (`artifacts/ci-repair-ac05515/reminder-cache-contract.json`), with exact header assertions for success and simulated storage failure. Linux's four required real-platform checks must pass on fresh CI; local Windows results do not substitute for them. Files: `apps/investments/alert_views.py`, `docs/PROJECT_STATUS.md`, `tests/test_investment_review_alerts.py`. Counts unchanged 75/143. Continue AI-15 bounded readiness/UI acceptance, then push validated commits and inspect their exact-head three-job CI. PR #15 ready externally, no independent review or Pages/protection authorization; no merge/deployment. Prior run/job metadata in `artifacts/ai15-26bad2e/`; current recovery source is clean before the next implementation.

- **INV-07 LOCAL RECORD-REVIEW REMINDERS — 2026-10-25:** HEAD = this checkpoint commit, base `41e50031ae9aa0bc79e043b0a307d78fb4e59f6c`, branch `development/alfred-integrated`. Recovered clean/pushed source; FIN-07's existing chronological/Decimal fallback is already accepted, while genuine outcome/calibration evidence is still missing, so no duplicate implementation or predictive-quality claim. PR #15 at `41e5003` has exact-source run `40155992396` **ALL PASS** (1,220 backend, 98 Chrome, Windows native/recovery/accessibility and Linux secure-failure); CI merge candidate `ff37f9b` has identical source tree. Evidence/digests: `artifacts/ci-de85bdc/boundary/pr15.json` and `finalization.json`. No independent review, Pages publishing approval or protection-read access; ready-for-review mutation rejected by integration and browser fallback unavailable. Do not merge or deploy.
  DONE: complete nonmonetary reminder workflow at `/api/investments/review-alerts/` and `/investments/`. Explicit owner opt-in, 7/30/90-day record-edit review policy, persistent encrypted local state, on-request evaluation, read/dismiss/resolved lifecycle, correction/deletion invalidation, revision conflicts, future-date abstention, 20-record/reminder bound, 90-day expiry through the existing vault expiry job, opt-out clearing and full owner/account reset. Reuses existing owner-bound vault transactions/state; asset names/amounts are not retained in reminder state and state is excluded from memory-sync export. Records and money calculations are never modified. No migration, financial schema/currency policy, paid provider, private-history, external delivery, runtime or production change. Edit timestamps do **not** verify statement/valuation/market freshness; no monetary thresholds, trade signals or unattended/background notification delivery is claimed.
  TESTS: **129 broader investment/money/projection/vault/history/corpus/sync/reset checks PASS** (`artifacts/ci-repair-ac05515/investment-review-final.json`), plus **8 final focused reminder/API/privacy checks PASS** (`investment-review-final8.json`; overlapping, do not sum). Covers opt-in, owner/session/CSRF, stale revision, encrypted reopen, other-policy preservation, no sync export, maximum batch/quota, future evidence, key loss/corruption, reset, expiry and unchanged amounts. **2 actual Chrome workflows PASS** (`artifacts/investment-review-41e5003/browser/browser_regression_summary.json`), with the final reminder workflow rerun after retention/future-date changes (**1 overlapping PASS**, `final-browser/browser_regression_summary.json`). Desktop and 390px captures inspected, no horizontal overflow; source text escapes markup. Early tests exposed missing full-reset integration (fixed) and a shared-clock/session-expiry fixture error (isolated); an incomplete synthetic mock-provider constructor was corrected. System/migration drift (no changes), JS syntax, whitespace and AST-only update PASS. No unrelated full local suites repeated. New pushed source requires its own CI; record exact-source results at `artifacts/investment-review-41e5003/boundary/pr15.json`, not earlier green receipts.
  FILES (alphabetical): `apps/investments/alert_views.py`, `apps/investments/services/review_alerts.py`, `apps/investments/urls.py`, `apps/ml_engine/services/persistent_memory.py`, `docs/PROJECT_STATUS.md`, `scripts/release_validation.py`, `static/js/investments.js`, `templates/investments/list.html`, `tests/test_investment_review_alerts.py`, `tests/test_memory_platform.py`, `tests/test_user_data_browser.py`. Complete merged source saved; fresh clean-source/privacy/push evidence at `artifacts/investment-review-41e5003/boundary/`. INV-07 remains **PARTIALLY_IMPLEMENTED**. Counts unchanged **75 verified / 24 unaccepted / 26 partial / 10 missing / 5 approval / 3 external = 143**. Monetary alert rules remain currency/valuation-gated; normal real-account/release acceptance remains separate. Rollback: disable/clear reminders through the UI before an authorized older-source rollback; new code has no schema migration or canonical financial writes. Old protected backups have separate retention.
  NEXT: inspect new exact-head PR CI without redoing these focused passes. DOC-02/DOC-06 are already verified; DOC-07 full-context/independent quality remains incomplete. Continue AI-15 serving-readiness acceptance only after inspecting its exact criteria, then AI-16→AI-12; skip genuinely approval/data-blocked work. Master merge still requires independent approval, accessible protection gates and explicit Pages publishing authorization. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 14`. Focused reminder command: configured SDK `artifacts/ci-repair-ac05515/run.py investment-review-resume manage.py test tests.test_investment_review_alerts --noinput` in isolated runtime, only when affected source changes.

- **PR #15 CI REPAIR — 2026-10-25:** HEAD = this checkpoint commit, base `de85bdcb6051cf95450608e14c8e0f3348e6b1e3`, branch `development/alfred-integrated`. Recovered clean/pushed source and preserved both worktrees. Run `40153177576` Linux PASS; Selenium 97 tests / one error; Windows backend 1,220 tests / one failure, downstream native checks not executed. Downloaded browser artifact `12584306768` and native artifact `12584287765`, verified SHA-256 `d6753bc63adfac1cee237ce82a4963dc5d29c16dcf5b1d8942ab94662c066305` / `cac893f2008ace746e483be325922cfbfc553dfc34def2659e8df664cd5a3ccd`, retained at `artifacts/ci-de85bdc/`.
  ROOT CAUSE/FIX: captured `/api/ai/memories/reason/` 503 (`OperationalError`) rejects the all-or-nothing Insights `Promise.all` before financial choices/source initialization. A controlled synthetic API outage reproduces the exact fixture line-1696 timeout; the seven-source expectation is correct. Independent owner-authorized source browsing now initializes when cloud-policy status fails, with visible unavailability and cloud consent/fallback disabled. Authentication/policy permission failures still clear private UI; history failure remains blocking, and all server authorization/source revision checks remain authoritative. No retry, assertion, quota, encryption or timeout relaxation. The originating storage exception is **not independently reproduced**: 30 six-way fresh-vault startups and 24 concurrent existing-transaction probes passed; do not claim a database-lock repair. Unchanged failing browser case also passed locally before the fix, confirming intermittency. Windows backend's named status test separately compares a probe deadline against a clock sampled before client/middleware/database work; a 0.7s synthetic client delay reproduces that assertion failure. It now verifies exactly one second with a scoped fixed clock, preserving production behavior and the 30-second AI deadline.
  FRESH TESTS: **96 affected backend/API/privacy PASS**, zero skips (`artifacts/ci-repair-ac05515/de85-affected-backend.json`); delayed status regression FAIL before / PASS after (`de85-native-status-before.json`, `de85-native-status-after.json`). **7 actual Chrome PASS**, zero skips: failed Document Center + controlled outage/permission regression (2, `artifacts/ci-de85bdc/focused-after/browser_regression_summary.json`); source pagination/exact citations/mobile/privacy, stale selection/loan citation, assistant retry, private-history consent and document-record questions (5, `related-after/browser_regression_summary.json`). Controlled outage regression FAIL before at the original fixture wait (`forced-before/`). System checks, migration drift (no changes), JS syntax, whitespace and AST-only graph refresh PASS. No unrelated local full-suite repeat; required full Windows/backend/native, Selenium and Linux gates run on the pushed source. Read their **exact-head** result at `artifacts/ci-de85bdc/boundary/pr15.json`; CI was pending at source-checkpoint creation, not presumed green.
  FILES (alphabetical): `apps/ml_engine/api/views.py`, `docs/PROJECT_STATUS.md`, `static/js/intelligence.js`, `tests/test_intelligence_ui.py`, `tests/test_user_data_browser.py`. Full merged source saved. Counts unchanged **75 verified / 24 unaccepted / 26 partial / 10 missing / 5 approval / 3 external = 143**. No schema, dependency, money calculation, private-history/provider activation or production change. Rollback: normal revert of this source commit; no data migration or financial-record rewriting required. Clean-source/history privacy closure at `artifacts/ci-de85bdc/boundary/`; normal development push only. PR remains draft/unmerged: no submitted approval at recovery; **Pages/master deployment authorization unresolved**. No self-approval, master merge or deployment.
  NEXT TASK: inspect exact pushed-head three-job CI and review state; fix only demonstrated failures. Once green, keep draft/unmerged until independent approval and Pages/deployment gates are resolved. Resume unblocked roadmap only under the current task scope. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 14`. Do not repeat these focused passes unless affected source changes.

- **GEMINI DEVELOPMENT DIAGNOSTIC — 2026-10-25:** HEAD = this checkpoint commit, base `113ebbddfb28102dfd909d50894405da1aaf55d3`, branch `development/alfred-integrated`. One bounded task only. Added `gemini-development-smoke` to the existing AlfredRouter and a provider using the existing pinned, redirect/proxy-free HTTPS transport and reasoner interface. Fixed `gemini-3.8-flash` via Google's official `v1beta/models/...:generateContent` API; credential in `x-goog-api-key`, never URL/body/logs. Official references: https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash and https://ai.google.dev/api/generate-content (checked today). No SDK/dependency installation. Requires BOTH `ALFRED_GEMINI_DEV_ENABLED=true` and Django `DEBUG=true`; frozen packages blocked. Default opt-in is OFF. Ollama/hybrid routing, financial APIs, document Q&A, memory/history and all existing authorization/quality/deadline gates are unchanged. No automatic cloud fallback. This development diagnostic accepts ONLY a fixed synthetic connectivity prompt and no caller-provided text, records, documents or memories; not a general cloud assistant.
  TESTS: **8 final focused provider/router tests PASS**, zero skips (`artifacts/ci-repair-ac05515/gemini-final.json`; earlier overlapping pass `gemini-focused.json`). Covers disabled/production/packaged gates, missing/invalid key, private/arbitrary payload rejection, bounded transport, timeout/quota/auth sanitization, no retry/fallback, blocked/truncated/malformed responses and command output. Added focused provider module to the existing backend CI profile. No new web/API endpoint or UI: Chrome/full suites not applicable to this command-only integration and were not repeated. Operator command: configure process/local development environment (`ALFRED_LOCAL_RUNTIME=true`, `DEBUG=true`, ignored `config/local.env` or process `GEMINI_API_KEY`, explicit opt-in), then configured SDK `manage.py gemini_smoke`. One request only, total deadline <=15s, response <=16KiB, output <=256 tokens; exact completion sentinel required. Output is sanitized status only.
  REAL API TEST: **SKIPPED**, not PASS — secure local key absent and opt-in false, independently checked through the existing private configuration loader in an isolated process (`artifacts/gemini-113ebbd/smoke.json`). No Google request or billing activation occurred. Chat-pasted credential was not persisted, echoed or used; user asked to rotate it and enter its replacement locally, never paste a replacement into chat. No approval or silent opt-in inferred. `artifacts/gemini-113ebbd/smoke.py` can perform one synthetic isolated smoke after local configuration; it copies only the permitted credential/opt-in into the synthetic runtime, never personal data. Existing local environment loader and ACL checks retained.
  FILES (alphabetical): `alfred_ai/settings.py`, `apps/ml_engine/core/alfred_router.py`, `apps/ml_engine/management/commands/gemini_smoke.py`, `apps/ml_engine/services/gemini_development.py`, `docs/PROJECT_STATUS.md`, `scripts/release_validation.py`, `tests/test_gemini_development.py`. Complete merged source saved. Clean source/history privacy/143-row and push evidence must match this commit: `artifacts/gemini-113ebbd/boundary/`. Counts unchanged **75 verified / 24 unaccepted / 26 partial / 10 missing / 5 approval / 3 external = 143**; development-only provider adds no verified capability.
  CI: prior exact-source `113ebbd` run `40151938289` Linux PASS, Windows/Selenium running at task recovery; inspect fresh status without repeating Travel or CI repairs. Latest pushed Gemini HEAD needs its own CI; record run/head/reviews in boundary `pr15.json`. Keep PR #15 draft unless latest-source gates pass. **No master merge/Pages/production action authorized.** NEXT: stop after this task; await secure local replacement + explicit development opt-in for the one real smoke, and inspect latest PR CI. Do not start DOC-07/Council/other modules in this session. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 14`. Obtain the configured SDK before Python commands; do not print local secret files or credentials.

- **TRAVEL-04 ESTIMATED ORDER COMPARISON — 2026-10-25:** HEAD = this checkpoint commit, base `8c70794e8b0daa80536f695de1c468e90cd25a01`, branch `development/alfred-integrated`. DONE: compare up to five owned stops over at most 120 permutations using the existing town-centre distance allowance. Preview changes no session revision, day edits, saved trip, booking or financial record; equal-distance ties retain the current order. An explicit Apply action uses the existing revision-checked stop builder, recalculates dated days/nights/shared Decimal budget and clears day edits, as disclosed before confirmation. Saved plans change only on an explicit subsequent Save. Ownership, CSRF, stale-revision rejection and bounds remain enforced. No provider, model, dependency, schema, currency or production change; independently implemented, no third-party code copied.
  TESTS: **14 final focused backend/API/privacy PASS**, zero skips (`artifacts/ci-repair-ac05515/travel04-order-security-final.json`, 36.127s); also verifies malformed action objects return 400 without modifying the plan. Earlier overlapping 14-test passes are not added. **11 integrated actual Chrome PASS**, zero skips (`artifacts/travel04-order-8c70794/integration/`); includes the existing seven planner workflows, manual multi-stop, discovery batches, provenance and new preview/confirm/no-change flow. Visual inspection found a garbled arrow from the editing shell; replaced with a JavaScript Unicode escape and clarified that road routing remains unoptimized. **Final affected Chrome workflow PASS** with an explicit arrow assertion, desktop/390px captures and no horizontal overflow (`artifacts/travel04-order-8c70794/final-chrome/`); this overlaps the 11, not an extra capability. Final 14 tests cover the final wording and action dispatch; the malformed-action correction does not change valid browser requests. The preceding manual slice's 104 backend/10 Chrome remain applicable outside this bounded comparison change; no repeat full Memory/Ollama/packaging run. JS syntax/whitespace PASS; final AST update completed with exit 0 (`graph-final.log`). Clean source/privacy/143-row checks and normal push must match this commit at `artifacts/travel04-order-8c70794/boundary/`.
  RECOVERY / CI: `c5cfbbad387c9782b83ad36882fffa63a38c9356` closes the two demonstrated Selenium races: run **40149451366 Windows native + Linux secure-failure + Selenium all PASS**, exact-source artifact IDs/digests and jobs in `artifacts/ci09-09f04c1/boundary/ci-final.json`. Master remains `1e768366fb811decc4a9c1e168ac95c5e201718a`. Manual slice `8c70794` committed/pushed, source/privacy PASS with zero findings (`artifacts/travel04-c5cfbba/boundary/`); its intermediate run `40151245565` was running before this follow-up. The latest pushed comparison commit needs fresh exact-head CI; store its run/reviews/head in the boundary `pr15.json`. PR #15 stays draft until latest-source checks pass; review/merge protections retained. **NO master merge / Pages deployment authorized.**
  STATUS: **75 verified / 24 unaccepted / 26 partial / 10 missing / 5 approval / 3 external = 143**, unchanged. TRAVEL-04 remains PARTIALLY_IMPLEMENTED: manual multi-stop and estimated-order comparison now accepted, but independently verified inter-stop road routing, connection feasibility and broader route acceptance remain open. Estimated optimal distance does not establish fastest/cheapest/legal routes, permits, availability or reserve-aware affordability. NEXT: finish only missing source/push/PR-description closure; inspect latest exact-head Windows/Linux/Selenium CI, preserve any failures, then prepare review without merging. Continue DOC-07 independent full-document/held-out quality, then AI-15→16→12 where unblocked; inter-stop route verification must use existing approved providers without new credentials or false availability claims. Career Ops identity, monetary INV-07/reserve/currency work and master deployment implications remain gated. RESUME: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 18`. Focused comparison regression, only if affected source changes: configured SDK + isolated runner `artifacts/ci-repair-ac05515/run.py <new-receipt> manage.py test tests.test_travel_multistop --noinput`.
  FILES (alphabetical): `apps/mobility/planner_views.py`, `apps/mobility/services/travel_itinerary.py`, `docs/PROJECT_STATUS.md`, `static/js/travel_planner.js`, `templates/mobility/dashboard.html`, `tests/test_travel_multistop.py`, `tests/test_user_data_browser.py`. Full merged source saved.

- **TRAVEL-04 MANUAL MULTI-STOP SLICE — 2026-10-25:** HEAD = this checkpoint commit, base `c5cfbbad387c9782b83ad36882fffa63a38c9356`, branch `development/alfred-integrated`. DONE: owner-only ordered stop actions and desktop UI, up to five previously shown destinations across discovery batches; add/reorder/remove, chronological dated days, evenly shared nights plus a return day, day edits, save and reopen. Reuses the Decimal budget engine once for the whole journey with summed leg estimates and weighted stay allowances; meals/local allowances/buffer are not multiplied per destination. Each stop retains separately labelled destination evidence; single-stop routes, weather, prices, maps or permits never certify the multi-stop journey. Coordinates/mode/duration validation abstains safely; stale revisions return 409; ownership/CSRF/rate limits preserved. Date/price/vehicle changes and explicit single-destination replacement are integrated. Date changes invalidate retained one-stop seeds too, preventing old weather from returning on rebuild. Research publication preserves multi-stop days/route/budget; other-account selection and invalid requests cannot overwrite a plan. No schema, dependency, provider, financial-record, currency or production change.
  TESTS: **104 backend/API/Travel tests PASS**, zero skips, final source (`artifacts/ci-repair-ac05515/travel04-closure.json`, 121.996s); **10 actual Chrome PASS**, zero skips, final source (`artifacts/travel04-c5cfbba/final-chrome/{browser_regression_summary.json,console.log}`). Chrome covers add/reorder/day edit/save/reopen/remove, existing planner, discovery batches and freshness; desktop/390px captures under `final-chrome/user-data/`, visually inspected (no horizontal overflow). Expense records unchanged in the workflow. Earlier 103 backend/10 Chrome and 12 focused checks overlap and are not added. Initial failures were new-test fixture mistakes (ignored save return, duplicate one-to-one session, nonexistent shortcut chip); corrected to the real save/reopen/chat flow. One mistyped test selector also failed; the correctly named module and final 104-test run pass. No assertions or deadlines were relaxed. JS syntax/whitespace and final AST refresh recorded; clean-source/privacy/143-row closure and normal push must match this commit at `artifacts/travel04-c5cfbba/boundary/`.
  STATUS: TRAVEL-04 remains **PARTIALLY_IMPLEMENTED**, because route-order optimization and independently verified inter-stop routing remain incomplete. Counts unchanged: **75 / 24 / 26 / 10 / 5 / 3 = 143**. Only own motorcycle/car modes are supported in this slice; unknown origin/stop coordinates and insufficient nights are rejected. Distances are explicitly town-centre planning allowances, not road measurements, legality, availability, duration or affordability proof. Canonical reserve/goal/currency-aware affordability is still gated.
  PR #15: pushed race repair `c5cfbba`, run `40149451366`: fresh Selenium and Linux PASS; Windows backend step PASS, native HTTP/recovery/accessibility still running at checkpoint preparation. Prior 95 Chrome/122 affected backend evidence remains intact for that repair. Keep draft until exact current pushed HEAD passes all required checks. No master merge or Pages deployment authorized. NEXT TASK: finish missing closure/push only; then implement explicit estimated stop-order comparison with confirmation, retaining unknown legal routing/availability. DOC-07 independent full-document/held-out quality and AI-15→16→12 follow; Career Ops identity, monetary INV-07 and master merge remain gated. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 20`. Do not rerun passing 104/10 suites unless affected source changes.
  FILES (alphabetical): `apps/mobility/planner_views.py`, `apps/mobility/services/travel/costs.py`, `apps/mobility/services/travel_conversation.py`, `apps/mobility/services/travel_itinerary.py`, `apps/mobility/services/travel_research.py`, `apps/mobility/views.py`, `docs/PROJECT_STATUS.md`, `scripts/release_validation.py`, `static/js/travel_planner.js`, `templates/mobility/dashboard.html`, `templates/mobility/planner.html`, `tests/test_travel_multistop.py`, `tests/test_user_data_browser.py`. Full merged source saved.

- **PR #15 SELENIUM REPAIR — 2026-10-25 (LOCAL PASS):** recovered clean/pushed `09f04c122b61632bfbe5bfe41495148d146d0f95`; existing master worktree untouched, no task process was running. Exact-source run `40135104741` native Windows/backend/recovery and Linux secure-failure PASS; Selenium 94 tests / two errors. Artifact `12577016327` downloaded and SHA-256 verified (`fc5e62e216e7f8f553a1cddaec8420c91e1a46c31d6f2d388a06047f30f897a5`), relevant screenshots/HTML/console and raw log saved at `artifacts/ci09-09f04c1/`; remote job/artifact metadata in `remote.json`. Both failures show empty corpus status/list, enabled controls, and no corpus HTTP error. Demonstrated root cause: `initDocumentSources.load()` delivers an initial documents-level response to `knowledge.reset(page)`, which unconditionally calls `corpus.selectionChanged()` even with old/new linked selection both null. This aborts an unrelated pending encrypted list/upload response and discards it by generation. Controlled real-Chrome response ordering reproduced BOTH cancellation paths in 15.002s (`artifacts/ci-repair-ac05515/ci09-race-reproduction.json`, one test/two failing subcases).
  DONE: the shared controller now skips corpus invalidation only for null-to-null source-catalog browsing. Genuine linked-record selection changes still cancel and clear private selections. Auth/CSRF, encryption, quotas, lifecycle guards and all 30-second deadlines are unchanged. No backend/model/schema/dependency/provider/history/financial-write change. FILES (alphabetical): `docs/PROJECT_STATUS.md`, `static/js/documents.js`, `templates/documents.html`, `tests/test_user_data_browser.py`; complete merged source saved.
  FRESH TESTS: each former failing workflow individually PASS (`ci09-corpus-individual.json`, `ci09-upload-individual.json`); both together PASS (`ci09-paired.json`); controlled list/upload response ordering AND genuine linked-selection cancellation PASS (`ci09-race-final.json`). The expanded regression initially used a fixture that navigated away; replaced it with minimal owned synthetic records, without weakening assertions or changing the application fix. **122 backend/privacy PASS**, zero skips (`artifacts/ci-repair-ac05515/ci09-backend-privacy.json`). **Complete CI-equivalent Chrome suite: 95 PASS, zero skips**, driver-backed, source hashes unchanged throughout (`artifacts/ci09-09f04c1/full/{source-run.json,browser_regression_summary.json,console.log}`). Focused runs overlap and are not added to 95. Existing corpus desktop/narrow-screen evidence remains applicable; no layout changed. JS syntax/whitespace and AST refresh PASS. No real Ollama inference repeated because model behavior is unchanged. Source/native/Linux results at 09f04c1 remain historical until fresh remote exact-head CI passes.
  HEAD = this checkpoint commit, base `09f04c122b61632bfbe5bfe41495148d146d0f95`. Closing source/privacy/143-row and normal-push evidence must match this commit: `artifacts/ci09-09f04c1/boundary/{source-checks,privacy-manifest,push,pr15}.json`. Counts remain **75 verified / 24 unaccepted / 26 partial / 10 missing / 5 approval / 3 external = 143**; this regression repair adds no verified feature.
  NEXT: finish any missing/non-PASS source/privacy closure; normal push, inspect fresh PR #15 Windows native + Linux security + Selenium at the exact HEAD, and update review scope for DOC-06, bounded DOC-07, Travel pool/fallback and this race fix. Mark ready only when required gates permit; **DO NOT MERGE MASTER — Pages implications remain unapproved**. Then independently continue TRAVEL-04. Scoped inspection: existing build/edit itinerary is single-destination; ORS accepts start/end only. Integrate bounded ordered stops, per-leg evidence/failure states, day allocation and existing Decimal budgeting; do not simulate verified routing. Connected repository/ALFRED-issue searches found no authoritative Career Ops identity; defer only that conversion until its URL is supplied. No repeated upstream research/code copying or new provider activation. RESUME: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 16`.

- **FINAL DEVELOPMENT CHECKPOINT — 2026-10-25:** HEAD = this checkpoint commit; branch `development/alfred-integrated`, base `f35e3818d961f9c27a24ebc61f8196b0d1785839`. DONE: corrected the existing Travel Advisor preview's unsafe fallback: nonpositive canonical savings capacity now gives zero monthly trip capacity, rather than reusing disposable income already needed for living costs. Positive savings behavior is unchanged. **41 fresh finance/budget/mobility/user-data tests PASS**, zero skips (`artifacts/ci-repair-ac05515/travel-capacity-integrated.json`, 140.604s), including the new deficit/zero/positive regression and Expense/Investment/Loan invariance. Reproduction receipt records two expected failing subcases before the one-line fix. This is backend-only legacy preview behavior: the current chat planner does not call this service, and no frontend changed, so no additional browser run was necessary; the final Travel/DOC-07 Chrome receipts below remain applicable. AST-only refresh PASS. No canonical arithmetic, schema, FX policy, reserves/goals, records, provider/history activation or production changes. Counts remain **75 / 24 / 26 / 10 / 5 / 3 = 143**.
  FILES (alphabetical): `apps/mobility/services/travel_advisor.py`, `docs/PROJECT_STATUS.md`, `tests/test_financial_baseline_alignment.py`. Full merged files saved. This checkpoint also repairs the previous tracker substitution, which updated TRAVEL-03 inventory/counts at f35e381 but left its stale active paragraph. Earlier source closures: DOC-07 `711225f3d91d8fed9937061db1c0f46a289696eb`, Travel `f35e3818d961f9c27a24ebc61f8196b0d1785839`, both privacy PASS with zero findings. Final source/history/143-row checks and ordinary push must match this commit: `artifacts/travel-pool-711225f/boundary-final/{source-checks,privacy-manifest,push,pr15}.json`. Verify these receipts first on resume; finish only a missing/non-PASS closure, not completed implementation/tests.
  NEXT TASK: inspect PR #15 exact remote HEAD and CI/reviews, update description to the document Q&A + independent Travel pool/fallback scope; prepare for review only after required exact-head checks pass. Do not merge: Pages deployment implications still need explicit approval. Then continue TRAVEL-04 ordered multi-stop/day-wise itinerary foundation using existing Travel services, after inspecting current source and route constraints. DOC-07 arbitrary full-context/OCR comprehension and independent quality evidence remain partial; no fresh disclosed-case inference repeats. Career Ops conversion needs its actual repository URL; monetary INV-07/shared reserve/goal contracts remain currency/goal-gated; TradingAgents selective adaptation needs component/dependency clearance, no bulk install. Latest public upstream/license map is in the canonical dashboard and `artifacts/doc07-6fc5266/upstream-research.json`. Packaging/native-runtime/normal-account/production were not reaccepted. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 18`. Relevant focused next-task tests: isolated runner `manage.py test tests.test_travel_candidate_pool tests.test_travel_planner tests.test_travel_continuation --noinput`; get the configured SDK first, use a fresh synthetic runtime, and do not rerun this already passing set just for recovery.

- **TRAVEL-03 ACCEPTED — 2026-10-25:** source `f35e3818d961f9c27a24ebc61f8196b0d1785839`, base `711225f3d91d8fed9937061db1c0f46a289696eb`. Persist up to 20 distinct ranked candidates in existing owned session JSON; research/display three per batch. Next/Previous, pending/exhaustion, current-batch comparison and same-session reopen preserve explicit choice. Context edits invalidate the pool; rejection/history rules are reapplied. Lease/revision checks prevent superseded workers replacing current requests. Private pool internals are omitted from API/browser provenance. No schema/provider/financial/history change or upstream code copying.
  TESTS: **169 focused integration backend PASS**, zero skips (`artifacts/ci-repair-ac05515/travel-pool-integrated.json`), covering pool/planner/continuation/providers/refresh/places/HTTP, Travel Decimal money and release validation; **six overlapping exact-final pool tests PASS** (`travel-pool-final-core.json`) after an equivalent exhaustion-expression rewrite. **One final actual Chrome PASS**, driver-backed, zero skips (`travel-pool-chrome-accepted.json`, 26.028s): batch uniqueness, pending job, compare, reload, Previous, explicit selection and actual 390px viewport. Desktop/390px screenshots inspected at `artifacts/travel-pool-711225f/browser-accepted/user-data/`; no overflow. Earlier Chrome exposed a queued-job readiness race in the test and paging controls remaining after selection; both corrected, failed receipts preserved. Existing TRAVEL-10 flow passed individually in the preceding two-test run, which remains FAILED overall. JS syntax/whitespace/AST PASS. No new migration, live inventory, package, native or production acceptance. Closing privacy/source receipt PASS: `artifacts/travel-pool-711225f/boundary/`; zero findings.
  FEATURES: **75 verified / 24 unaccepted / 26 partial / 10 missing / 5 approval / 3 external = 143**. TRAVEL-03 is newly verified for available source candidates (may be fewer than 20), persisted batches and current-batch comparison; DOC-07 remains partial for full-context/OCR comprehension. FILES (alphabetical): `apps/mobility/planner_views.py`, `apps/mobility/services/travel_conversation.py`, `apps/mobility/services/travel_research.py`, `docs/PROJECT_STATUS.md`, `scripts/release_validation.py`, `static/js/travel_planner.js`, `templates/mobility/dashboard.html`, `templates/mobility/planner.html`, `tests/test_travel_candidate_pool.py`, `tests/test_user_data_browser.py`. Full merged files saved.
  PR / NEXT: #15 remains draft/no reviews/no merge. Source `711225f` run `40133205142`: Linux PASS, Windows backend/recovery PASS with extended native and Selenium still running at last observation. No result is inherited by a later HEAD. Pushing Travel expands review scope by one independently tested slice; update PR description and require fresh exact-head CI. Pages deployment approval remains mandatory before master merge. Career Ops URL is missing; reserve/goal/currency-dependent contracts and monetary INV-07 remain gated. Next dependency: TRAVEL-04 ordered multi-stop itinerary foundation, plus independent DOC-07 full-context and AI holdout quality work. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 16`.

- **DOC-07 / PR #15 REPAIR CHECKPOINT — 2026-10-25:** HEAD = this checkpoint commit, base `6fc52661f7fefde98e12a21eecb89bf66601d0e6`. Recovered all interrupted edits; completed the bounded encrypted-corpus local extractive Q&A slice. Explicitly selected owned documents and keywords provide exact quoted evidence, character offsets, original fingerprints/private citations and source revalidation after inference. The fixed local model selects passage indices only; authored figures/prose/citations, malformed/incomplete output, missing evidence, conflicts and stale sources cannot become financial facts. Session/CSRF, 30-second deadline, fixed model/digest, encryption, quotas, no-store, retention/reset and no-cloud/history/financial-write rules are preserved. Documents UI includes question, loading/error/abstention states and clears private content on lifecycle changes. **DOC-07 remains PARTIALLY_IMPLEMENTED**: keyword-bounded extractive questions are accepted locally; arbitrary full-document/OCR comprehension and independent unseen quality evaluation remain open. Counts remain **74 verified / 24 unaccepted / 27 partial / 10 missing / 5 approval / 3 external = 143**.
  TESTS: **176 focused integration backend PASS**, zero skips (`artifacts/ci-repair-ac05515/doc07-pr15-integration.json`); **four actual Chrome CI-repair workflows PASS** (`pr15-browser-final.json`). The final Q&A/general-upload pair also passed **two actual Chrome tests**, zero skips (`doc07-final-ui.json`, driver-backed 77.968s); six final distinct Chrome workflows passed across the two receipts. Six real-local synthetic Q&A cases PASS in **80.343s aggregate**, individual question latency **9.297–15.828s**: positive exit-load and statement-period evidence, missing rate/penalty, conflicting policies and advice abstention. Receipts `artifacts/doc07-6fc5266/ollama/b9b4046184/`, runner `doc07-real-schema.json`. These are disclosed development cases, not independent holdout or broad accuracy claims. Initial fixture/viewport/assertion failures and real-model over-abstention/malformed outputs are retained; defining states/cardinality and supplying the output schema in the prompt fixed the demonstrated local selection defects without weakening validation. [Official Ollama structured-output guidance](https://docs.ollama.com/capabilities/structured-outputs) informed the prompt correction. Actual desktop/390px Q&A screenshots inspected: exact untrusted text is escaped and wraps; conflict sources retain separate citations. Django system, both JavaScript syntax checks, whitespace and AST-only graph refresh PASS; final source/privacy closure must PASS before push; no schema/dependency changes require a new migration rehearsal. Existing DOC-06/reviewed-field evidence remains applicable.
  PR / CI: #15 remains draft/no reviews, source `6fc5266` at recovery. Exact-source run `40130144937`: **Linux and native Windows PASS; Selenium FAILED (90 tests, two errors)**. Failure artifact SHA-256 `5261e926eeabecbeabed063d66f74370499e2da04015a6e03db312f078ef9092`, extracted logs/screenshots under `artifacts/pr15-6fc5266/`. Repaired document-hub background polling (seven endpoints every second exhausted unchanged quotas) and initial controller readiness; actual Chrome verifies an idle page preserves request budget and the full corpus lifecycle. The other error correctly enforced the frozen holdout's source hash. Production policy/hash/thresholds remain unchanged: synthetic report/metric tests now use explicit test-only labels; new actual Chrome proves changed-source holdout rejection before model invocation. Fresh independent holdout acceptance is still required. No dependency changes were made for nonfatal pip resolver warnings. Master CI `40111115989` remains PASS; no master merge or deployment. Push triggers fresh PR exact-head CI; do not mark ready until it passes. **Master merge remains held for explicit Pages deployment approval**.
  FILES (alphabetical): `apps/ml_engine/api/document_corpus.py`, `apps/ml_engine/api/urls.py`, `apps/ml_engine/services/document_questions.py`, `docs/PROJECT_STATUS.md`, `scripts/release_validation.py`, `static/js/document_corpus.js`, `static/js/documents.js`, `templates/documents.html`, `tests/test_document_questions.py`, `tests/test_document_questions_ollama.py`, `tests/test_global_abuse_limits.py`, `tests/test_memory_platform.py`, `tests/test_retrieval_quality.py`, `tests/test_user_data_browser.py`. Full merged files saved. Boundary/push evidence: `artifacts/doc07-6fc5266/boundary/`. NEXT TASK: finish non-PASS/missing final UI/system/AST/privacy/normal-push receipts, inspect fresh PR #15 CI, then continue independent shared-contract/domain work below. Do not rerun real inference without a relevant source change. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 16`.
- **DOC-06 GENERAL CORPUS ACCEPTANCE — 2026-10-25:** HEAD = this checkpoint commit, base `61f5e88f039f39c8fd3ceaa2701dc8dfc012e144` (pushed with clean source/privacy closure, zero findings). DONE: general owner-directed PDF text-layer / UTF-8 `.txt` ingestion alongside the three existing financial-document types. Explicit session/CSRF-protected consent retains the original bytes, full supported text and keyword index together inside the same encrypted per-document record; owner-only original attachment citations include original SHA-256, exact extracted-character offsets, `no-store, private`, `nosniff`, controlled content type and forced attachment. No new financial model/migration, encryption/key-recovery policy, OCR/model/provider/history activation or financial writes. Originals are limited to 512 KiB; text to 256 KiB; combined original/text/index record to 1 MiB, plus the existing owner/global/index/document/retention quotas. Oversized, unsupported, binary/invalid UTF-8, no-text/scanned PDF and malformed/duplicate form inputs abstain or reject without partial storage. Common save/reset/expiry/key-loss/corruption/ownership controls are reused; uploaded originals are immutable and deletion/expiry/reset removes both original and index. File change clears consent; uploads require explicit document selection before search; long untrusted excerpts wrap without clipping.
  TESTS: **167 integration backend PASS**, zero skips (`artifacts/ci-repair-ac05515/corpus-general-integration.json`), including corpus, old one-off/bank retrieval, private vault/history/account-reset, upload limits/retention, auth/CSRF/abuse and tracker. **30 overlapping final backend PASS** after two additional input-type guards and their malformed-file/field tests (`corpus-general-guards.json`); use this receipt for final corpus/API Python hashes. **Two actual Chrome PASS** (`corpus-general-chrome-final.json`, 68.693s raw test run), including new general TXT/PDF upload/private-original/multi-selection/deletion workflow and the full earlier financial-corpus lifecycle. Desktop and genuine 390px light/dark screenshots actually inspected, no text clipping/overflow; search-button contrast at least 4.5:1 in both themes; `artifacts/doc06-general-61f5e88/browser-final/`. Final browser receipt predates only the two backend input-type guards; valid UI behavior is unchanged and the final 30 tests exercise those guards. Initial 49-test run had an oversized uncompressed scan fixture and global future-clock session expiry; corrected with a genuinely rasterized compressed PDF within the cap and service-level expiry followed by actual HTTP absence. Failed receipts preserved; earlier 64 core/two-browser passes overlap. System and AST refresh PASS; prior migration-drift applies because this slice changes no Django model/migration. Final source binding, privacy closure and commit/push follow immediately. Fresh real-Linux CI, full-project/native/package, normal-account and production acceptance are not claimed.
  FILES (alphabetical): `apps/ml_engine/api/document_corpus.py`, `apps/ml_engine/api/urls.py`, `apps/ml_engine/services/document_corpus.py`, `docs/PROJECT_STATUS.md`, `static/js/document_corpus.js`, `templates/documents.html`, `tests/test_document_corpus.py`, `tests/test_global_abuse_limits.py`, `tests/test_memory_platform.py`, `tests/test_user_data_browser.py`. Full merged source saved. **DOC-06 becomes COMPLETE_VERIFIED for bounded local Windows PDF/text keyword knowledge ingestion/retrieval**, not semantic understanding, arbitrary Q&A, OCR, every document format or release readiness. Counts **74 verified / 24 unaccepted / 27 partial / 10 missing / 5 approval / 3 external = 143**; delta +1 verified, -1 partial. NEXT TASK: clean source/privacy closure and normal push, then scoped draft PR/CI for this corpus increment if no equivalent PR exists; no master merge because Pages authorization is unresolved. Next implementation dependency is **DOC-07 grounded arbitrary-document Q&A** using this corpus with unchanged quality/deadline/source isolation, not more DOC-06 infrastructure. Before coding, inspect only current document-question/reasoning adapters and evidence validation. Focused regression: configured SDK / isolated runtime `manage.py test tests.test_document_corpus tests.test_document_knowledge tests.test_memory_platform --noinput`. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 14`.

- **DOC-06 ENCRYPTED CORPUS SLICE — 2026-10-25:** HEAD = this checkpoint commit, base `5f7754ca4118351497dd855bd5c709321daf7201` (pushed). DONE: explicitly consented local encrypted text/index copies of owned bank text-layer PDFs and retained loan/investment extractions; one to three explicitly selected copies per keyword search, exact extracted-character offsets/private originals/fingerprints, no inferred answers or financial authority. Existing Windows DPAPI master and per-document wrapped Fernet keys are reused; plaintext text/index/filenames never enter the SQLite journal, verified facts, conversation records or sync events. Ownership, original bytes, extraction, links and linked-record corrections are revalidated before/after retrieval; stale copies are removed, mixed stale/foreign selections return no excerpts. Expiry (1–30 days or shorter Memory policy), policy shortening, source deletion, full Memory reset, owner deletion and account-data reset clear copies/keys. Owner/global document, ciphertext, text, token and linked-record quotas bound processing/storage. Missing/corrupt keys or authenticated-record/index corruption preserve existing data and fail closed. Metadata listing is owner-directed, queries use POST bodies, session/CSRF/no-store and existing expensive-work quotas remain enforced. No provider, private-history, currency, production or financial-write change.
  TESTS: **167 focused integration backend PASS**, zero skips, including 20 corpus cases, existing 19 selected-document cases, vault/privacy/history/sync/account-reset/upload-retention/abuse/platform/release-runner coverage (`artifacts/ci-repair-ac05515/corpus-integration.json`). **One exact-final actual Windows Chrome lifecycle PASS**, plus two individually passing unchanged selected-document/bank workflows from the initial three-case run (that run overall FAILED its new case; do not label it all green). Final corpus flow covers explicit consent, persisted reopen, exact citations/private no-store media, foreign-owner rejection, XSS-safe text, genuine 390px layout, missing-key preservation, correction invalidation, private removal and full reset; `corpus-chrome-final.json`, screenshots/driver summary `artifacts/doc06-corpus-5f7754c/browser-accepted/`. Desktop/390px results actually inspected. Initial 34/57-backend and new-browser failures were test-fixture/contract mismatches (Decimal fixture refresh, invalid signature error, existing origin label, malformed DELETE body, Django public test-media handler and reselecting the source after reload); corrected without weakening assertions/security. Failed evidence remains retained. System and migration-drift PASS (`corpus-system.json`, `corpus-drift.json`); JS syntax/whitespace PASS. New Linux refusal paths are registered in the existing real-Linux CI job and passed locally using the established Windows unsupported-platform simulation; **fresh real-Linux execution is pending**, not claimed. No full 1,142-backend/106-browser, packaged/native, normal-account or production rerun. AST/privacy/source closure and normal commit/push are the immediate next operations; preserve receipt/source hashes.
  FILES (alphabetical): `alfred_ai/services/abuse_protection.py`, `apps/ml_engine/api/document_corpus.py`, `apps/ml_engine/api/urls.py`, `apps/ml_engine/memory_signals.py`, `apps/ml_engine/services/document_corpus.py`, `apps/ml_engine/services/document_knowledge.py`, `apps/ml_engine/services/persistent_memory.py`, `docs/PROJECT_STATUS.md`, `scripts/release_validation.py`, `static/js/document_corpus.js`, `static/js/documents.js`, `templates/documents.html`, `tests/test_document_corpus.py`, `tests/test_global_abuse_limits.py`, `tests/test_memory_platform.py`, `tests/test_user_data_browser.py`. Full merged source saved. Final AST refresh, five tracker checks and exact-source binding PASS (`graph-update.log`, `source-binding.json`; latter binds backend Python and final Chrome/UI hashes). Postcommit privacy closure remains required before push. LIMITATIONS: corpus currently ingests these three existing financial-document types only; arbitrary uploads/OCR/general semantic knowledge and arbitrary Q&A remain unfinished. Before older-binary rollback, remove retained copies using the current app; protected backups retain their own lifecycle. **73 verified / 24 unaccepted / 28 partial / 10 missing / 5 approval / 3 external = 143**, unchanged; DOC-06 remains PARTIALLY_IMPLEMENTED, not relabeled as general full-document acceptance. BLOCKERS: Pages deployment authorization still prevents any new agent master merge; FIN-CURRENCY/provider/history/native latency gates unchanged. NEXT TASK: finish clean source/privacy closure and push this bounded corpus slice, then extend DOC-06 general ingestion using the same encrypted lifecycle; do not restart selection/bank search or master CI. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 13`. Focused command: configured SDK / isolated runner `manage.py test tests.test_document_corpus tests.test_document_knowledge tests.test_memory_platform --noinput`.

- **MASTER CI CLOSED / DOC-06 RESUME — 2026-10-25:** HEAD = this checkpoint commit, base `480f3866ffac02124c4d8e8a3b51c6ac83515535`. Master run **`40111115989` is now PASS**, retaining native/backend and Linux passes and retrying only the failed Selenium job. Retry job `120946807462` ran **88 Chrome tests PASS**, zero skips; `master-selenium-retry-pass.log`. Native/Linux artifact IDs and digests are unchanged; no passing backend/native/Linux suite was requested again. Initial Selenium failure was one Chrome inspector stale-node error while reading the throttle page body across navigation; the checksummed `master-login-failure.zip` HTML contains the expected throttling feedback. The development regression now reads/checks body text in one synchronous browser script, preserving invalid-password, lockout and 601-second recovery assertions, without ignoring WebDriver failures or changing production authentication/quotas. **One focused actual Chrome PASS**, `master-login-atomic.json`; source hash matches the committed test. This fix is development-only: green master retry used unchanged `1e76836`, not the later test edit. Graph AST refresh PASS. FILES (alphabetical): `docs/PROJECT_STATUS.md`, `tests/test_user_data_browser.py`. Closure/normal push follows; **73/143 verified unchanged**. PR #14 remains externally merged; no agent master merge or deployment. Pages deployment implications remain unresolved, so **no further agent master merge** is authorized. NEXT: proceed directly to DOC-06 owner-consented encrypted corpus; preserve existing selected-document/bank PDF search and its receipts. Resume command remains the command below; master CI no longer needs polling or rerunning.

- **FINAL PR CI / EXTERNAL MERGE CHECKPOINT — 2026-10-24:** HEAD = this documentation checkpoint, base `1e768366fb811decc4a9c1e168ac95c5e201718a`. PR #14 was marked ready and merged **externally** by the repository owner at **16:20:35 UTC**; the agent did not perform the master merge. Only `development/alfred-integrated` was fast-forwarded to `origin/master`; local master remains `3932f391aa4eed7b3200ad3b034f7991435e01e4`, and the frozen candidate is unchanged. Validated PR source `fa9536718f0b0ecb34b00d1de3e135841b0d1f9a`, tested merge `842adbe643f1bad470d0f454d9fa02ba158c42a9` and remote master `1e76836` share exact tree `f0fbb031af933046f27b29569fff57faebd3ce1a`; this checkpoint changes only this tracker, so the application/test evidence remains applicable.
  **FINAL TESTS: all three PR jobs in run `40109122829` PASS — 1,142 Windows backend; 88 Windows Chrome; 18 Linux Chrome; three actual Linux secure-failure tests; zero skips.** All **22 native checks, 28 responsive layouts and 28 light/dark axe audits PASS**, zero serious/critical findings; explicit Expense heading/label contrast is covered by the new full-suite browser regression. Native restart honored one real **429 / 23-second Retry-After** without changing quotas or deadlines, then passed account/queue persistence and backup/restore. Raw job logs, GitHub-digest-verified `{windows,native,linux}-expense-pass.zip`, parsed summaries and `expense-contrast-closure/source-checks.json` are in `artifacts/ci-repair-ac05515/`. Privacy closure has zero findings; failed reproductions and interrupted receipts remain preserved. Fresh local two-Chrome/six-axe evidence and all earlier source boundaries remain below; counts overlap, not additive. No source/native proof is represented as packaged AI, real-account or production acceptance.
  **MASTER / DEPLOYMENT:** master Browser Regression **run `40111115989` is IN PROGRESS**, Windows native/backend job `120922852816`, Windows Chrome `120922852986`; Linux job `120922853029` PASS. Check this run directly: the commit-workflow connector returned an empty list while the Actions UI and run-jobs endpoint showed it running; no duplicate workflow was dispatched. The Actions page also revealed GitHub-managed **Pages build/deploy run `40111115142` completed externally**, including successful deploy job `120922896529`. No application production deployment is established, and the agent initiated no deployment or repository-settings change. No independent reviews are recorded on PR #14; this external merge does not prove review/protection compliance. Future agent master merges require the existing review/security/CI/rollback gates **and an explicit decision about the Pages deployment trigger**; do not silently repeat a master merge or change that setting.
  **CURRENT / NEXT:** **73 verified / 24 unaccepted / 28 partial / 10 missing / 5 approval / 3 external = 143**, unchanged. CI source repair is accepted on the exact PR tree; finish recording master run `40111115989` without rerunning the already-passing PR suite. Then resume **DOC-06 encrypted ingestion/index/ownership/invalidation/retention**. Selected retained extraction and bank text-layer search are already implemented/accepted in their bounded scope; do not rebuild them. Next implementation unit: owner-consented encrypted document knowledge using the existing vault primitives, distinct from verified facts, conversations and sync events; integrate source invalidation, expiry and account reset before exposing the API/UI. Inspect only `apps/ml_engine/services/document_knowledge.py`, `persistent_memory.py`, the existing conversation-vault lifecycle pattern and relevant document tests. Focused tests after relevant changes: configured SDK / isolated runtime `manage.py test tests.test_document_knowledge tests.test_persistent_memory tests.test_memory_privacy tests.test_user_data_reset --noinput`, then actual document Chrome flows. No encrypted corpus code was started in this checkpoint. FILES (alphabetical): `docs/PROJECT_STATUS.md`. Normal development commit/push follows closure; no new PR is needed for this tracker-only receipt. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -4 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 16`.

- **CI GREEN / CONTRAST FOLLOW-UP CHECKPOINT — 2026-10-24:** HEAD = this checkpoint commit, base `d84a81e0eb84cae034838e0f5fb81591af829c89` (pushed). All three jobs in run `40107292475` PASS: **1,142 Windows backend, 87 Windows Chrome, three actual Linux secure-failure and 18 Linux portable Chrome tests**, zero skips; **22 native checks**, responsive layouts and both-theme axe gates PASS. Tested merge `0c6f6d4ebabb190f9996d12c7a5d4703b1bf9eef` and source `d84a81e` have identical tree `7bd8c39ea37662b8e18ef77fc4b0cb314e69a690`. Checksummed `{native,windows,linux}-career-pass.zip`, summaries and logs are in `artifacts/ci-repair-ac05515/`. Native CI exercised one real **429 / 21-second Retry-After** before passing restart and backup/restore; production quotas and the AI deadline remain unchanged. This confirms the bounded retry path, not the exact unrecorded response in the older failed run. Master remains `9736a554c8d19c0134d295102560306bcc3addc6`; its failed workflow is not retroactively green.
  VISUAL GAP / FIX: manual inspection found pale Expense card headings on white in dark mode despite axe reporting contrast as incomplete. A new real-browser regression reproduces **1.18:1** for all four headings, then **1.63:1** for the light warning label. Fix the header surface and scope readable summary-label colors to Expenses; bump the stylesheet cache version. Assert all four headings and five labels at **4.5:1 or better**, light/dark and actual **390/1440-pixel viewports**. **Two final Chrome workflows PASS**, zero skips, including unchanged owner-only CSV amounts, formula neutralization and foreign-owner exclusion; `expense-contrast-accepted.json` / `expense-accepted/`. An intervening run passed the contrast assertions but failed CSV fixture cleanup on a Chrome-held `downloads.htm`; retain that failed receipt. The temporary download directory now lives until the class-owned browser quits, without ignored cleanup errors or weakened assertions. **Six focused axe scans PASS**, zero serious/critical violations, `expense-axe-final.json`; only the later fixture-lifetime change followed that CSS proof. Desktop/narrow screenshots inspected; earlier header-only narrow screenshots used Chrome's minimum window width and are superseded by the asserted viewport proof.
  FILES (alphabetical): `docs/PROJECT_STATUS.md`, `static/css/workspace.css`, `templates/base.html`, `tests/test_user_data_browser.py`. Full merged source saved. Graph/source/privacy closure is required before push. **73 verified / 24 unaccepted / 28 partial / 10 missing / 5 approval / 3 external = 143**, unchanged. The new contrast test joins the existing full Windows browser lane; new-head CI is still required for this follow-up. PR #14 remains draft/unmerged with independent review and the required protected workflow unresolved; no settings, master, deployment, schema, money, crypto, provider or history changes. NEXT EXACT ACTION: push this validated checkpoint, inspect all three latest-head CI jobs and save their proof. Resolve review/protected-workflow requirements before readiness/merge. Continue DOC-06 encrypted ingestion/index/ownership/invalidation/retention independently after CI repair; preserve its existing selected-text acceptance. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -4 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 14`.

- **CAREER SUBMIT SYNCHRONIZATION CHECKPOINT — 2026-10-24:** HEAD = this local checkpoint commit, base `f73146d3708d0e261bbd558f5679b975ed0e244a` (pushed). Hold the next push until native job `120906895555` in run `40105724473` finishes, so its new HTTP diagnostics are not canceled. Linux secure-failure checks PASS; portable Chrome failed intermittently before Career analysis creation. Checksummed `linux-submit.zip` and extracted `linux-submit/` show the draft intact, feedback untouched/hidden and no console errors. The test waited only for the static page title; it now waits for initial dashboard completion and rendered summary cards before typing/clicking, retaining the record-count, source, uncertainty, ownership and financial-preservation assertions. **Three actual Career Chrome PASS**, zero skips, `career-loaded-final.json` / `career-loaded/browser_regression_summary.career-loaded.json`. This synchronization correction still needs Linux CI on the next pushed head.
  FILES (alphabetical): `docs/PROJECT_STATUS.md`, `tests/test_user_data_browser.py`. No server, money, crypto, quota or deadline changes. **73/143 verified remains unchanged.** NEXT EXACT ACTION: inspect both remaining Windows jobs at run `40105724473`, especially native restart dashboard status. Repair any actual HTTP error; if it passes, push this verified synchronization checkpoint and inspect all three new-head jobs. Preserve all review/protected-workflow gates. The tracker below records the completed source/native proofs and all incomplete scopes. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -4 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 12`.

- **CI COVERAGE / NATIVE RESPONSE CHECKPOINT — 2026-10-24:** HEAD = this checkpoint commit, base `5ae88c79b07ed365aae9a2416a29fa523ed0d51c` (pushed). Run `40103676300` at that base: **Windows backend PASS**, **87 Windows Chrome PASS**, zero skips; **three Linux secure-failure + 18 portable Chrome PASS**, zero skips. Native CI now passes all responsive layouts and both-theme accessibility, then fails after restart with `KeyError: summary` because that checker parsed a response without first checking its HTTP status. Raw log `native-followup.log`, checksummed `native-followup.zip`, extracted release/native JSON, and `windows-followup.zip`/summary are in `artifacts/ci-repair-ac05515/`. Do not call the whole CI run green or master repaired.
  DONE / TESTS: register PR #14's previously omitted `tests.test_document_knowledge` in the explicit backend profile; **19 focused retrieval tests PASS**, `document-ci-coverage-final.json`. A deterministic changed-test-module check confirms every changed PR test module has a selected backend/browser lane, `pr-test-coverage.json`. The synthetic native dashboard reader now validates HTTP/summary responses at all three call sites and honors at most one explicit 429 Retry-After within the existing 90-second HTTP budget. Invalid/excessive waits, exhausted deadlines, persistent throttling, auth/server errors and malformed success bodies still fail. **23 focused native/runner tests PASS**, `native-request-accepted.json`; production quotas, auth/CSRF, financial assertions and the 30-second AI deadline are unchanged. A real CI 429 is a hypothesis until its status is observed; unrelated HTTP failures are not retried or hidden.
  ACCEPTED SOURCE EVIDENCE: local full native source run `38d43f44aa` **PASS: 22 checks, 28 responsive layouts, 28 light/dark axe audits, zero serious/critical violations**, plus worker crash/restart, canonical financial totals, account/upload isolation and backup/restore including pending jobs. `native-final-report.json`, `native-final-source-match.json`, `artifacts/native-tests/38d43f44aa/mobile-accessibility.json`. Implementation hashes match `5ae88c7` except the later checkpoint text; this predates the new dashboard-reader helper, which still requires new-head CI execution. The 15 Career/live-HTTP, three Career Chrome, navigation Chrome and six focused axe receipts remain recorded below. Incomplete interrupted backend run remains explicitly INCOMPLETE.
  FEATURES / MERGE: **73 verified / 24 unaccepted / 28 partial / 10 missing / 5 approval / 3 external = 143**, unchanged. PR #14 remains draft/unmerged; no reviews, no classic branch protection rules and no rulesets visible; no repository security settings changed. Existing workflow has no deployment step; no configured webhook entries visible. Reviewer username requested from user, no approval inferred. Master `9736a554c8d19c0134d295102560306bcc3addc6`, local master and frozen candidate remain unchanged. Normal protected/reviewed merge requirements are not satisfied.
  FILES (alphabetical): `docs/PROJECT_STATUS.md`, `scripts/release_validation.py`, `scripts/verify_native_runtime.py`, `tests/test_native_runtime.py`. Full merged files saved. NEXT EXACT ACTION: finish AST/source/privacy closure, commit/push this checkpoint, then inspect all three new-head CI jobs. If native fails, inspect the now-explicit HTTP status/response-contract error; never relax a security or financial assertion. If CI passes, resolve review/protected-workflow gates before readiness/merge; continue DOC-06 encrypted ingestion/index/retention independently when safe. Packaging, independent-PC, live accounts, private-history and real cloud/currency work remain separate/gated. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 13`.

- **CI FOLLOW-UP CHECKPOINT — 2026-10-24:** HEAD = this checkpoint commit, base `b737acdb16876225fdae12dd00fe27f7b3dc5274` (pushed). Follow-up source/tests are saved with this checkpoint; normal push follows source/privacy checks. Run `40087837378`: **1,119 Windows backend PASS**, zero skips; native continued to actual accessibility, failing export-button contrast and unlabeled-region semantics. Full Windows Chrome: 87 run, one navigation timeout (86 pass); private memory now executes on Windows. Linux: three real secure-failure checks PASS; 18 portable Chrome run, 17 pass, Career expanded-source read failed. PDF reimport and investment review passed on Linux; historical timeout is not reproduced there. Full job logs and checksummed artifacts: `artifacts/ci-repair-ac05515/{native-first,linux-first,windows-browser-first}/` and corresponding archives/logs. No master merge, deployment or capability promotion.
  IMPLEMENTATION: Career had a real pending-refresh race: `careerRoot` covered only the hero, so open sources/editors were outside the interaction guard; dashboard responses also failed to recheck it. Controlled pre-fix Chrome reproduces DOM replacement. Expand the root to the whole Career page, recheck the existing guard on live response, bump the JS query version, and assert the same open source-details element survives a held response. **Three integrated Career Chrome PASS**, zero skips (matching/source uncertainty/privacy, Decimal salary/experience reload, owner outcome correction/stale draft). Receipt `career-integrated-final.json`, artifacts `career-integrated/`. The separate API/session/Career run ended during session interruption without a summary: `career-backend-final.json` is explicitly INCOMPLETE; original receipt preserved. No passing claim for it. Initial guard-only diagnostic failed because the root was still too small; a subsequent diagnostic also had an initial submit timeout. Preserve failed receipts.
  ACCESSIBILITY: expense export now uses filled secondary; comparison results have `role="region"`. Local full native run `e6de39f111` passed 18 stages, all 28 layouts and fixed ARIA, then exposed dark-theme contrast on export/credit refresh; it remains FAIL (`native-first-local-report.json`). Correct the shared dark button styles, bump the stylesheet query version, and audit settled light/dark themes explicitly without weakening axe thresholds. **Six focused actual Chrome axe scans PASS**, zero serious/critical violations: expenses/settings/credit-score in both themes, `a11y-settled-final.json` and `a11y-focus-results.json`. Pinned axe 4.13.0 hash matches CI. A first theme-switch scan caught transitional colors; settled-state wait now matches the existing native audit's requirement.
  CURRENT RUN: full synthetic native/HTTP/worker/concurrency/backup/accessibility validation on isolated port 8147: `native-final.json` / `.log`; unique runtime under `artifacts/native-tests/`, final report `artifacts/ops/native_huey_extended_verification.json`. Require `passed: true`; native memory/Ollama and packaging are not part of this run. Navigation timeout did not reproduce locally; **one focused Chrome PASS** after waiting for rendered Travel preferences (asynchronous initialization), `navigation-ready-final.json`. All ownership/filter/navigation assertions remain. **15 fresh backend/live-HTTP checks PASS**, zero skips: Career matching acceptance and authenticated pages/assets, `career-http-final.json`. AST/JS syntax/whitespace and workflow routing checks PASS. Final CI still must execute the updated source.
  FILES (alphabetical): `docs/PROJECT_STATUS.md`, `scripts/verify_native_extended.py`, `static/css/workspace.css`, `static/js/career.js`, `templates/base.html`, `templates/career/list.html`, `templates/expenses/list.html`, `templates/settings/memory.html`, `tests/test_user_data_browser.py`. NEXT EXACT ACTION: finish `native-final`; inspect any actual failures. Check source/privacy closure, push status and all three CI jobs at this pushed SHA; require reviews/protection before PR #14 can leave draft/merge. Reviewer username requested asynchronously; no response is approval. Preserve 73/143 and all encryption/quality gates. Resume DOC-06 only after CI repair. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 12`.

- **CI RECOVERY / PR #14 — 2026-10-24:** HEAD = this repair checkpoint commit, base `ac055154ad8a09feb5b4344ddd112f587d39d2ab`; branch `development/alfred-integrated`. Recovered clean/pushed source and downloaded/checksummed master run `40080906887` plus PR run `40084929452` failure artifacts. Master `9736a554c8d19c0134d295102560306bcc3addc6` ran 1,114 backend tests; PR base source ran 1,116. Both have the same six failures across four methods. All six reproduced locally with an 8.3 short TEMP alias; ordinary TEMP passes. Canonicalize synthetic fixture/comparison paths so ACL-at-creation observations and strict target/environment checks measure the same directory. No product storage, key protection or recovery policy changed.
  DONE: retain the complete required, zero-skip Chrome suite on compatible Windows; add explicit Linux directory/key/store/API refusal, preserved-data, no-plaintext/no-model-fallback, authentication and CSRF checks, plus portable browser coverage. Linux failures classified separately: 11 direct unsupported-vault errors, 26 memory-dependent UI timeouts, one investment live-render stale-element error, one incomplete animated Career snapshot and one statement-upload timeout. Preserve all assertions; retry stale elements only inside bounded waits and validate a complete Career snapshot. Add pre-navigation failure artifacts for user-data browser workflows. The unresolved Linux statement case remains explicitly selected in Linux CI; do not claim it fixed from a Windows pass.
  TESTS: **64 focused backend PASS**, zero skips, including all four formerly failing methods under a real 8.3 short TEMP alias and three new unsupported-platform tests; **one final workflow contract PASS**. Three focused actual Windows Chrome workflows PASS, zero skips (Career, investment review/revocation, PDF reimport); this preceded the additional failure-artifact hook, whose full-suite CI remains required. Windows simulates only the unsupported platform capability; real Linux refusal remains a separate required CI execution. Evidence: `artifacts/ci-repair-ac05515/{diagnosis,windows-repro,windows-short-repro,platform-final,regression-final,workflow-contract-final,focused-chrome}.json`, full logs, master/PR native artifacts, checksummed master browser archive and `chrome-focused/browser_regression_summary.ci-repair-focus.json`. The first platform-test draft used a wrong public error field and an unconfirmed reset; corrected fixtures preserve API validation. Workflow YAML/routing self-check and AST update PASS. Broader live-HTTP UI contracts are running (`ui-contract.json`); finish/inspect that receipt. No whole-project/browser/native/package passing claim.
  FEATURES / BLOCKERS: **73 verified / 24 unaccepted / 28 partial / 10 missing / 5 approval / 3 external = 143**, unchanged. PR #14 is scoped, draft and unmerged; no reviews/approvals at recovery. Final-head CI, protection/review/compatibility/rollback gates remain required. Only browser validation runs on master push; no deployment wiring found. Master/local master/frozen candidate, private data and backups unchanged. All financial, privacy/provider/runtime approval gates remain in force.
  FILES (alphabetical): `.github/workflows/browser-regression.yml`, `docs/DEVELOPMENT.md`, `docs/PROJECT_STATUS.md`, `scripts/release_validation.py`, `tests/test_browser_regression_runner.py`, `tests/test_document_review_browser.py`, `tests/test_live_ui_contracts.py`, `tests/test_memory_platform.py`, `tests/test_release_gate.py`, `tests/test_source_storage.py`, `tests/test_user_data_browser.py`. Full merged source files saved. NEXT TASK: finish source checks, commit/push this repair and inspect all three CI jobs/artifacts at the exact pushed SHA. Fix actual remaining failures before marking CI repaired. Mark PR ready only when appropriate; never self-approve or bypass missing reviews/protection. Resume DOC-06 encrypted owner-directed ingestion/indexing/retention after CI repair; accepted metadata/keyword retrieval remains reusable. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 12`.

- **CLEAN CONTINUATION / PR #14 — 2026-10-24:** HEAD = this tracker-only checkpoint commit, base **`03358f66dd3078ad59b24d3caa857e98f3f1865a`**. DONE: recovered/preserved clean pushed source; TRAVEL-10/FIN-05/CAREER-02 VERIFIED_INTACT in their recorded bounded scopes; unified Alfred 2.0 roadmap added below. Implemented/tested/pushed two end-to-end DOC-06 slices: selected retained loan/investment keyword excerpts (**`e1bf76e6bda1dde34ec0f9dce4620830782d50b1`**), then protected bank text-layer retrieval, overlap correction and unchanged heavy-work quota enforcement (**`e099b54215b7531b1f5524be4ff66d15232a667c`**). Development-only ancestry reconciliation **`03358f6`** incorporated externally merged master `9736a55` with **identical before/after tested tree**; no local master push or production action. All merged source is saved; file lists below are alphabetic. Latest source/privacy/normal-push receipts PASS, zero findings: `artifacts/doc06-bank-e1bf76e/boundary-merged/` (preceded by both slice boundaries). Closing tracker-only source/privacy/push receipts: `artifacts/doc06-bank-e1bf76e/closure/`; require matching PASS before new edits.
  TESTS / PR: final application source **165 backend PASS**, zero skips; 33 overlapping final security/retrieval PASS; two strengthened raster-PDF backend PASS; two actual Chrome PASS plus one overlapping raster-PDF Chrome PASS. Receipts `artifacts/doc06-bank-e1bf76e/{integration-accepted,security-final,scanned-final,chrome-security-final,chrome-scanned}.json`; corresponding browser summaries prove driver-backed, zero skips. Prior slice 72 backend/two Chrome, system/drift and final overlapping Chrome remain separately recorded, not summed. Static independent adversarial finding fixed and reread; no external-provider review claimed. AST-only graph and JS syntax PASS. Bounded local structured Ollama probe PASS in 13.438s with original settings and no remaining resident model; not general quality/package acceptance or claimed token savings. [PR #14](https://github.com/sourabh48/alfred_ai/pull/14) is **OPEN / DRAFT**, source `development/alfred-integrated`, base `master`, 11 changed files and three commits at creation. The connector denied creation (403 integration permission); existing signed-in Edge successfully created it, then UI and connected read API verified exact source/head. No new credentials/permissions. Evidence `pr14.json`, `pr14-proof.png`. CI run **40084675765 was in progress**, reviews empty; neither is a passing landing gate. The final documentation commit changes the PR head; recheck exact-head CI next time rather than reusing this observation. No auto-merge or promotion.
  FEATURES / BLOCKERS: **73 verified / 24 unaccepted / 28 partial / 10 missing / 5 approval / 3 external = 143**, unchanged by these bounded DOC-06 slices. General encrypted corpus/index/relevance/retention and arbitrary DOC-07 Q&A remain incomplete; do not relabel keyword search as full-document understanding. FIN-07 genuine outcome calibration and INV-07 canonical currency/valuation evidence remain open/gated. Native loan-document latency, independent-PC, normal-account and production/recovery acceptance remain separate. Local master/frozen candidate/private data/backups preserved. AWS, paid providers, private-history activation OFF. No release/version promotion, driver/runtime/residency/deadline, schema/FX or encryption/key-recovery changes.
  **NEXT TASK: DOC-06 owner-directed encrypted corpus ingestion/indexing and retention/relevance acceptance.** First inspect existing `apps/ml_engine/services/persistent_memory.py` protected ingestion/deletion/retention and document deletion hooks using a scoped graph query; reuse crypto/consent patterns and complete selected-document provenance, revocation and owner isolation. Do not restart accepted metadata, reviewed fields, passage search or the three recovery milestones. Do not activate history/sharing or change keys/recovery. Before landing PR #14, inspect current source/head, checks/reviews/protection/compatibility and rollback; missing gates continue to block master merge. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -4 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 14`. Obtain the configured PyCharm SDK before Python/Graphify; create a new sanitized runtime through `scripts.release_validation.environment`, then focused command `manage.py test tests.test_document_knowledge tests.test_global_abuse_limits --noinput` only when affected. No running test or unfinished source edit remains at this checkpoint.

- **DOC-06 BANK TEXT-LAYER RETRIEVAL — 2026-10-24:** HEAD = this checkpoint commit (base `e1bf76e6bda1dde34ec0f9dce4620830782d50b1`, first selected-extraction/roadmap slice committed/pushed with pinned privacy PASS). Completed the next bounded retrieval slice: the existing protected parser worker can extract only a selected bank PDF's text layer. Search verifies original bytes before processing and source/owner/account/link revisions afterward; time/memory/file/output protections are preserved. No OCR/model fallback, persistent extraction/index, transaction/balance update, currency assumption or source-authenticity claim. Results distinguish original PDF text from retained loan/investment text. Worker failure/limit, missing/changed source and image-only content abstain. Native independent adversarial review found the JSON route missed heavy-work quotas; fixed with POST-only classification into the existing account/global expensive buckets, unchanged thresholds, ordinary metadata discovery unaffected. Parent review also fixed a real overlap omission for a keyword crossing the previous passage end, with regression.
  TESTS: **165 integration backend PASS**, zero skips (`integration-accepted.json`), including retrieval/selection/session/security, actual bounded-worker limits/timeout/Windows memory enforcement, upload privacy/retention, bank grounding and tracker checks. Final **33 security/retrieval PASS** overlap; **two actual Chrome PASS** after the quota fix (`chrome-security-final.json`), driver-backed, zero skips. Two additional backend cases and **one overlapping Chrome PASS** after strengthening the image-only fixture to a genuinely rasterized PDF (`scanned-final.json`, `chrome-scanned.json`). Desktop/narrow-screen results actually inspected, no overflow. Early 150 integration/18 focused and Chrome repeats are retained overlapping receipts, not added totals. Historical system/drift PASS from the immediately preceding slice remain applicable: no model/schema/settings/dependency changes. JavaScript syntax/whitespace PASS. Review receipt `adversarial-review.json`: independent static review, not independently executed tests; the P2 was reread and confirmed fixed. All evidence/source hashes under `artifacts/doc06-bank-e1bf76e/`; full code saved.
  FILES alphabetically: `alfred_ai/services/abuse_protection.py`, `alfred_ai/services/bounded_parser.py`, `apps/ml_engine/services/document_knowledge.py`, `docs/PROJECT_STATUS.md`, `static/js/documents.js`, `templates/documents.html`, `tests/test_document_knowledge.py`, `tests/test_global_abuse_limits.py`, `tests/test_user_data_browser.py`. Counts stay **73 verified / 24 unaccepted / 28 partial / 10 missing / 5 approval / 3 external = 143**. DOC-06 remains PARTIALLY_IMPLEMENTED: bounded selected-document passages do not implement a general encrypted knowledge corpus or arbitrary Q&A. FIN-07 real calibration, INV-07 currency/valuation evidence and packaged loan-document 30-second latency remain open. No package/independent-PC/normal-account/production acceptance. Hardware configuration read-only receipt `artifacts/resume-4789784/hardware.json`; no driver/runtime/model/residency/quality changes. New PR assessment is scoped to this document increment against externally merged master `9736a55`; no whole-history merge or production deployment.
  NEXT: finish/push this clean exact-source boundary (`artifacts/doc06-bank-e1bf76e/boundary/`), reconcile only the already merged master ancestry without changing the tested tree, and create a scoped draft source PR if remote HEAD still matches. No automatic master merge with missing CI/protection/rollback gates. Then continue DOC-06 owner-directed encrypted corpus ingestion/indexing, relevance and deletion/retention acceptance using existing encryption/consent patterns; preserve completed metadata/selected-field/passage workflows. Do not activate private history, change key recovery or add a private external provider. Exact continuation command: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -4 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 13`. Focused tests: configured SDK `manage.py test tests.test_document_knowledge tests.test_global_abuse_limits --noinput` in a new sanitized runtime. Canonical 2.0 queue/dashboard below stays unchanged; no new audit IDs.

- **DOC-06 SELECTED EXTRACTION RETRIEVAL — 2026-10-24:** HEAD = this checkpoint commit (base `4789784`). Implemented POST-only keyword search of one explicitly selected owned loan/investment retained extraction in the existing Documents UI. Reuses signed discovery catalogs, source-file fingerprints and before/after revision/ownership/link revalidation. Whole-keyword matching has bounded input/text/passages/results and no fabricated relevance/confidence, regex execution, inference, new retained plaintext/index, memory/history/provider call or financial write. Results carry exact retained-text character offsets and a private original-file link; missing/failed/oversized/changed sources abstain. Old extraction is explicitly unverified and cannot override corrected records. UI clears results on selection/refresh/session/page lifecycle, aborts superseded fetches and preserves retry keywords. DOC-06 remains **PARTIALLY_IMPLEMENTED**: no general encrypted searchable corpus or arbitrary Q&A is claimed.
  TESTS: final **72 integration backend PASS** (`integration-final.json`), including 13 new retrieval checks, existing selection/session/privacy and tracker-inventory checks. Earlier 66 backend and 13 focused PASS overlap. Two actual Chrome flows PASS, then one overlapping exact-final Chrome PASS after lookup/UI wording refinements; zero skips. Fresh isolated Django system/migration-drift PASS (`system.json`, `drift.json`). Receipts/source hashes: `artifacts/doc06-4789784/`. Both desktop/narrow-screen screenshots inspected. Initial Windows streaming-file fixture cleanup failure was fixed by closing the response; an integration command's nonexistent audit-test label was corrected to `tests.test_audit_project`, preserving the failed receipt. New tests cover whole-word/Unicode/boundary search, all-keyword/no-match behavior, bounds, missing/stale/deleted/tampered/expired sources, source races, foreign/mixed owners, cross-document tokens, session/CSRF/no-store, no memory and financial invariance. `node --check static/js/documents.js` PASS; Graphify AST-only refresh PASS, no semantic API.
  FILES alphabetically: `apps/ml_engine/api/financial_evidence.py`, `apps/ml_engine/api/urls.py`, `apps/ml_engine/services/document_knowledge.py`, `docs/PROJECT_STATUS.md`, `static/js/documents.js`, `templates/documents.html`, `tests/test_document_knowledge.py`, `tests/test_user_data_browser.py`. Full merged source saved. Counts stay **73 verified / 24 unaccepted / 28 partial / 10 missing / 5 approval / 3 external = 143**. Local runtime probe `artifacts/resume-4789784/ollama-probe.json`: synthetic structured JSON **PASS**, 13.438s total, 10.225s loading, 1.103s prompt/28 tokens, 2.073s generation/10 tokens (~4.82 tokens/s), complete stop. Uses existing qwen3.5:4b/think=false/keep_alive=0/30-second settings, no post-run residency or policy change. This demonstrates a bounded structured delegation path, not document-quality/package acceptance or measured token savings.
  NEXT: extend the same retrieval unit to selected bank PDFs using existing time/memory-bounded text-layer extraction and no OCR/model/persistent copies; verify original bytes, parent/account ownership, selection races and real PDF/browser acceptance. Then continue DOC-06 corpus retention/relevance acceptance before broad DOC-07. FIN-07 calibration, INV-07 currency metadata and native loan-document latency remain open. No production/native/full-suite acceptance claimed. PR #13 is externally merged; assess a new small current-master-compatible PR only against this new slice and all applicable gates. Boundary evidence: `artifacts/doc06-4789784/boundary/`. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 12`.

- **RECOVERY / ALFRED 2.0 ROADMAP — 2026-10-24:** recovered clean, fully pushed `478978433f405d15ad4ec51ecabab75a8eec1c84`; no interrupted edits or unpushed commits. Fetch found **PR #13 already merged externally** at `9736a554c8d19c0134d295102560306bcc3addc6` (source `4789784`, target master); master and development have identical source trees at recovery. No open PR. This records the external merge, not a new CI, privacy, rollback, deployment or release acceptance claim. No local master operation, reset, stash or merge performed. Prior no-PR/master-3932f39 notes below are historical. TRAVEL-10, FIN-05 and CAREER-02 are **VERIFIED_INTACT** in their bounded acceptance scopes: accepted source commits `42106cb`, `7ede529`, `a0a954d` are pushed ancestors; final ignored receipts exist. TRAVEL-10 source is unchanged; FIN-05's subsequent forecast changes have the recorded FIN-07 49-backend/three-Chrome integration evidence; Career source is unchanged. Earlier failed reproduction receipts remain retained and are superseded only by their recorded final passing runs. No full acceptance rerun was needed for recovery. Counts remain **73 / 24 / 28 / 10 / 5 / 3 = 143**.
  CURRENT: FIN-07 local chronological planning is complete, genuine predictive calibration still lacks authorized real outcomes. INV-07 monetary thresholds still require the unapproved FIN-CURRENCY contract and currency/valuation-as-of evidence. DOC-02 bounded extraction is accepted. Next executable unit is DOC-06 selected retained-extraction retrieval, with exact source/owner checks and no new persistent private-text copies, history activation or providers. This unit does not by itself deliver the general encrypted full-document knowledge index or arbitrary Q&A. Recovery/runtime receipts: `artifacts/resume-4789784/`. Local Ollama API is available with `all-minilm:latest`, `alfred-routine:latest`, `qwen3.5:4b`; no model was resident when checked. No model load, residency change, download or delegation/token-saving claim is made. Existing CPU/30-second runtime evidence remains applicable; configuration inspection is not a fresh throughput benchmark.

### Canonical Alfred 2.0 execution dashboard

The existing **143 capability denominator stays unchanged**. New workstream IDs below are separate requirements, not additional verified audit items. All are queued unless an exact accepted slice is recorded here. Reuse existing domain models, canonical Decimal baseline/projection services, evidence/citation adapters, local model routing and Django desktop UI. The strict foundation queue is **FIN-07 → INV-07 → DOC-02 → DOC-06 → DOC-07 → AI-15 → AI-16 → AI-12 → TRAVEL-03 → TRAVEL-04 → TRAVEL-07 → TRAVEL-08 → TRAVEL-09 → TRAVEL-15 → CAREER-04 → CAREER-07 → CAREER-08 → INV-04 → INV-06 → COUNCIL-01 → COUNCIL-02 → COUNCIL-04 → COUNCIL-05 → COUNCIL-03**. Skip only documented blocked operations and continue independent units; never infer approval or reopen accepted bounded work.

| Workstream | State / existing foundation | Missing 2.0 scope and dependency |
| --- | --- | --- |
| 2.0-FIN shared financial contracts | QUEUED; FIN-05 accepted, FIN-07 planning available | Reuse canonical cash flow/net worth/disposable income/fixed obligations; add explicit reserve/goal/scenario/affordability contracts after FIN-06/FIN-15 decisions. No duplicate arithmetic, inferred INR, historical currency backfill or unapproved FX. |
| 2.0-EVIDENCE shared intelligence | QUEUED; existing reviewed-source adapters and model registry | Source dates, evidence registry/proposal provenance, structured tools, explicit confirmation; depends on DOC-06/07 and AI-15/16/12 acceptance. Distinguish source facts, estimates, assumptions and unknowns. |
| 2.0-CAREER | QUEUED; CAREER-02 accepted | Advanced resume/JD analysis and recommendations, local mock interviews/evaluation/improvement plans, salary/growth scenarios and opportunity/application tracking. Reuse Career infrastructure; CAREER-04 → 07 → 08 and evidence-ready local routing first. No unconfirmed offer recorded as income. |
| 2.0-TRAVEL | IN_PROGRESS; TRAVEL-03/10 accepted | Desktop drag/drop day revisions, optimization/exploration, private booking/document organizer, packing/reminders, personal budgets, PDF/GPX/ICS, history/photo journals. Foundations TRAVEL-03/04/07/08/09/15; reserve/obligation/goal-aware affordability uses shared finance contracts. Confirmed expenses alone enter reconciliation. |
| 2.0-INVESTMENT | QUEUED; portfolio/projections already exist | Fundamental/technical/news/valuation research, exposure/risk analysis, bounded analyst/challenger agents, sourced suggestions and long-term scenarios. Depends on INV-07, INV-04/06, source freshness/currency and Council routing/governance. No automatic trading. |
| 2.0-WEALTH | QUEUED; existing canonical net worth/expense/loan/investment calculations | Dated wealth snapshots/reconciliation, ETF/fund look-through, dividends, goals/reserve-aware sizing, financial provenance and proposal/confirmation cards with independent risk challenge. Approved Indian instrument sources and currency policy required; scenario returns never booked as cash. |
| 2.0-INTEGRATION / DESKTOP | QUEUED after shared contracts and relevant domain foundations | Career scenarios → projections; itinerary revisions → affordability; contributions → reserves; portfolio exposure → goals. Preserve Django; usable desktop dashboards/charts/editors/explanations without frontend rewrite. |
| 2.0-RELEASE | QUEUED after scoped source acceptance | Cross-module regression/reconciliation, real Chrome/privacy/security, migration/rollback, exact-source Windows package and separately approved real-account/production acceptance. Source-only verification is not release readiness. |

**Upstream strategy checked 2026-10-25:** read-only public source/license receipts in `artifacts/doc07-6fc5266/upstream-research.json`, including inspected blob IDs. No code/assets copied, dependencies installed or providers activated. Latest execution order: PR #15/DOC-07 → repository/license/gap mapping → reuse shared finance/evidence/local-AI contracts → Career Python conversion → independent Travel → selective Investment adaptation → reference-only Wealth → cross-module acceptance. Existing verified capabilities are reused; the foundation queue above still applies to their unmet dependencies.

- **Career Ops:** actual repository URL is still missing (requested asynchronously); do not guess a similarly named project or claim licensing review. Port selected useful behavior into existing Django Career after inspection; no permanent Node backend. Existing CAREER-02 remains accepted.
- **[TREK](https://github.com/liketrek/TREK): AGPL-3.0.** Independently implement desktop itinerary ordering/revisions, private organizers/exports and journal improvements using existing Django Travel services. No upstream code/assets reuse. Existing route legality, source freshness and canonical affordability safeguards remain prerequisites; no inferred booking/permit availability.
- **[TradingAgents](https://github.com/TauricResearch/TradingAgents): Apache-2.0; inspected version 0.7.0.** Selective Python adaptation needs component-level license/attribution and dependency review before copying. Python >=3.11 is compatible, but upstream pandas >=3.0.6 / yfinance >=1.7.0 conflict with ALFRED's tested pandas 2.2.3 / yfinance 0.2.36; LangGraph/provider packages are not adopted. Bulk import also loads `.env.enterprise`; do not introduce that configuration path. Reuse current portfolio evidence/Ollama; bounded analyst/challenger/risk suggestions only, no execution/trading, AWS or paid activation. Missing `NOTICE` at the checked path is not repository-wide clearance.
- **[Aurelio Finance](https://github.com/LosaLosSantos/aurelio-finance): MIT; reference only.** Independently implement dated wealth/provenance, reserves/goals, reconciliation and proposal/confirmation behavior against canonical calculations. No direct integration or provider/private-data upload. Currency, goal and source approvals still govern Indian instrument/INR claims.

Explicit exclusions: mobile development, collaborative editing, friend invitations, shared permissions, group settlements and public sharing. Production/live migrations, destructive financial changes, private-history/disclosure, paid/new authenticated providers, privileged/system-wide runtime changes, model residency/deadline/quality weakening and unsafe Git operations remain gated. Preserve AWS OFF, paid OpenAI OFF and private-history activation OFF. No competing roadmap file is created.

- **DOC-02 EXTRACTION / PROVENANCE ACCEPTANCE — 2026-10-24:** HEAD = this checkpoint commit (base `ed9e333`, PR assessment committed/pushed there). DONE: accepted the existing bounded bank/loan/investment extraction, source-kind/type, review and provenance workflows without rebuilding parsers. Fresh **70 backend PASS** = 55 extraction/document-center/statement/investment evidence checks plus 15 loan-evidence checks; zero skips. Fresh **four actual Chrome PASS**, driver-backed, zero skips: generated real loan PDF import/reimport with sanitized failure handling, real statement PDF reimport/deduplication and balance/fingerprint preservation, investment field correction/confirmation/revocation/stale-source behavior, and investment review Decimal normalization with original source retention. Desktop/narrow-screen screenshots actually inspected; the private field table scrolls horizontally at narrow widths. Fresh Django system and migration-drift checks PASS (`No changes detected`). Receipts: `artifacts/doc02-ed9e333/{backend,chrome,checks,checkpoint}.json`, `browser/browser_regression_summary.json`; screenshots in that browser directory. Existing unchanged document review/retry evidence from `artifacts/career-7ede529/backend-complete.json` is historical supporting evidence, not added to fresh totals.
  SCOPE: known generated text-layer PDF layouts, bounded malformed/partial recovery and disclosed OCR-stub unit fixtures, owner/session/CSRF/source-pair isolation, immutable originals, reviewed-current-value precedence, generation/confirmation invalidation, duplicate replay and financial-record reconciliation. Owner attestation is not broker/lender authentication or a live quote. Unknown currency remains unknown. No new business code, parser threshold, schema, provider/private-history activation or production operation; complete merged source remains committed. General arbitrary scanned/PDF accuracy, full-document knowledge, native/package/normal-account/independent-PC acceptance are not claimed. Files alphabetically: `docs/PROJECT_STATUS.md` only. FEATURES: **73 verified / 24 unaccepted / 28 partial / 10 missing / five approval / three external = 143**, newly verified DOC-02 in this bounded source-level scope.
  PR / BLOCKERS / NEXT: no open PR; #12 already merged. Master remains `3932f39`; the assessed development source `d6921cb` was 149 commits ahead with 308 changed files and missing master-side Decimal prerequisites. No new scoped candidate has master-based compatibility, review/CI/protection/rollback acceptance; no PR or master merge created. Evidence `artifacts/pr-assessment-d6921cb.json`; this assessment is not a waiver. FIN-07 local planning is complete, predictive calibration remains open. INV-07 monetary rules remain gated by the unapproved FIN-CURRENCY schema and missing position currency/valuation-as-of evidence. Continue **DOC-06 private document knowledge**, then DOC-07: scoped graph query and inspect existing selected-document discovery/projections/text evidence before changing code; preserve source selection, citations, owner consent/encryption and abstention. Do not count metadata search as full-document understanding or activate private-history storage/sharing. Exact-source checkpoint/privacy/push receipts: `artifacts/doc02-boundary-ed9e333/{source-checks,privacy-manifest,push}.json`; finish non-PASS/mismatched receipts before editing. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -4 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 12`. Fresh tests need a new sanitized runtime/artifact directory; do not reuse executed runner directories. No fresh full-suite/package/release gate was requested or inferred.

- **PR / RESUME ASSESSMENT — 2026-10-24:** HEAD = this checkpoint commit (base `d6921cb`). Recovered clean development; finished FIN-07 AST/privacy/normal push, remote verified at `d6921cbc4b3cf803097feb2961da5749bb543283`. Its 49 backend, three Chrome integration and final one overlapping Chrome receipts remain applicable; no rerun for this read-only assessment. Fresh `git fetch origin` and connected GitHub inspection found **zero open PRs**. Latest PR [#12](https://github.com/sourabh48/alfred_ai/pull/12) is already merged (head `b4e8974`, merge `da745706`, 2026-09-30). Master remains `3932f391aa4eed7b3200ad3b034f7991435e01e4`. At assessed source `d6921cb`, development was **149 ahead / zero behind**, 308 changed files / 92724 additions / 2055 deletions. Recent finance changes need `apps/budgets/money.py`, absent on master, and a newer baseline resolver. Focused development receipts do not validate a newly assembled master-based candidate. No whole-branch PR or merge created. Exact-head classic statuses and PR-triggered workflow queries returned empty; other check-runs/protection/review/rollback gates remain unverified, not passing by inference. Master's sole tracked workflow is browser regression; no AWS workflow was found in that tree, but remote deployment hooks/settings were not verified. Durable evidence: `artifacts/pr-assessment-d6921cb.json`. A prerequisite slice must be constructed and independently validated before any new scoped PR; no bypass or production operation is proposed.
  BLOCKERS / NEXT: FIN-07 planning unit is done; genuine forecast calibration remains open. INV-07 monetary alert thresholds cannot infer compatible units or quote freshness: Investment stores amounts and `updated_at`, with no canonical currency/valuation-as-of fields. The **FIN-CURRENCY reviewed contract below explicitly says SCHEMA BLOCKED / NOT APPROVED** and proposes position cost/valuation and source quote denominations; no currency metadata migration or rule activation is attempted. Do not confuse InvestmentCurrencySerializerField's amount validation with currency evidence. Continue the next independent queued item, **DOC-02 extraction/classification/provenance acceptance**, with owned reviewed fixtures and actual statement/loan/investment browser flows. Preserve private records and existing reviewed-field gates. Counts unchanged: **72 verified / 25 unaccepted / 28 partial / 10 missing / five approval / three external = 143**. Modified file alphabetically: `docs/PROJECT_STATUS.md`; all merged source from prior modules is saved. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -4 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 12`.

- **FIN-07 CHRONOLOGICAL PLANNING CHECKPOINT — 2026-10-24:** HEAD = this checkpoint commit (base `a0a954d`). DONE: completed the safe local planning-estimate unit after TRAVEL-10 `42106cb`, FIN-05 `7ede529` and CAREER-02 `a0a954d` were accepted, privacy-checked and pushed. Forecast training now excludes future transactions and the current partial month; missing months remain unknown, not zero. The latest up to three completed recorded living-spend months drive Decimal/HALF_UP monthly and cumulative estimates. Canonical income/fixed-bill rules remain unchanged. Explicit dated baseline inputs bypass, and cannot overwrite, the ordinary cache. Forecasts expose owned dated aggregates, held assumptions, unavailable income/history states, bounded calendar horizons and genuine break-even/deficit labels. At least three observations permit a historical range, explicitly not a prediction interval; four permit walk-forward observed spending errors using only earlier observations, capped to twelve recorded months. There is no fabricated confidence, bank-balance forecast, model training/promotion, currency/FX change or financial-record write. The existing Budget chart displays source months, uncertainty, error and assumptions, preserves expanded details across refresh and hides an unavailable chart. Existing theme cards restore history-note readability.
  TESTS: **49 focused backend PASS**, zero skips: twelve new forecast checks plus existing budget/money/baseline/user-data acceptance; `artifacts/forecast-a0a954d/backend-accepted.json`. **Three actual Chrome integration PASS** (Budget/Career/forecast), followed by **one final overlapping forecast Chrome PASS** after narrow-screen capture/history styling, zero skips; `chrome-final.json`, `chrome-ui.json`, driver-backed `browser-{final,ui}/browser_regression_summary.json`. Final desktop/narrow-screen evidence inspected, no horizontal overflow, ordinary account switch shows unknown state and synthetic financial records remain identical. Coverage includes HALF_UP/cumulative reconciliation, future/current-month leakage, sparse months, Dec/Jan rollover, no-lookahead holdouts, observed error response to changed targets, owner/direction/debt/housing exclusions, cached-baseline preservation, unknown versus known-zero income, horizon validation and break-even. Initial ten-test reproduction (eight failures/six errors), missing dated-resolver integration errors and four corrected income-fixture expectations retained; the fixture now declares monthly 100 rather than assuming the existing income interpretation of 1200. Existing seed acceptance intentionally expects 8000/42000 from completed months while its canonical baseline remains 8666.67/41333.33 including current data. No assertions or financial policies weakened.
  FEATURES: **72 verified / 25 unaccepted / 28 partial / 10 missing / five approval / three external = 143**, unchanged by this unit. FIN-07 remains PARTIALLY_IMPLEMENTED: genuine outcome calibration and sustained forecast quality are unverified; synthetic holdouts cannot establish those. This continuation newly verified three capabilities (69 -> 72), with a fourth tested implementation unit completed. Files alphabetically: `apps/budgets/services/budget_intelligence.py`, `apps/budgets/views.py`, `apps/expenses/services/financial_intelligence.py`, `docs/PROJECT_STATUS.md`, `static/js/budgets.js`, `templates/budgets/list.html`, `tests/test_cashflow_forecast_acceptance.py`, `tests/test_user_data_acceptance.py`, `tests/test_user_data_browser.py`. Boundary receipts: `artifacts/forecast-boundary-a0a954d/{graph,privacy-manifest,source-checks,push}.json`; complete non-PASS/mismatched receipts before editing. Master/frozen/package unchanged; no gated operation attempted, new approval requested or production/private-history/provider activation. Full suites/native/package/independent-PC/production were not rerun. Packaged loan-document inference still has its separate 30-second acceptance blocker.
  NEXT TASK: INV-07 persistent portfolio alerts: use a scoped graph query, inspect existing Investment/alert storage, service methods, URLs and UI, then implement the owner opt-in workflow, deterministic freshness rejection, persisted lifecycle and local delivery acceptance using existing patterns. Abstain for unavailable currency/evidence; do not activate providers, infer FX policy or disclose personal data. This independent work need not wait for genuine FIN-07 calibration. Then DOC-02 -> DOC-06 -> DOC-07, followed by the user's recorded dependency queue. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -4 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 14`. Focused completed-module test command: `& F:\ALFRED\alfred_ai\.venv\Scripts\python.exe manage.py test tests.test_cashflow_forecast_acceptance tests.test_budget_acceptance tests.test_budget_money tests.test_financial_baseline_alignment tests.test_user_data_acceptance --noinput` (first obtain the PyCharm SDK and use the sanitized isolated environment runner `artifacts/forecast-a0a954d/run-accepted.py`; its existing runtime directory must not be reused).

- **CAREER-02 MATCHING ACCEPTANCE — 2026-10-24:** HEAD = this checkpoint commit (base `7ede529`, FIN-05 committed/pushed there). DONE: accepted bounded local resume/profile versus JD skill-gap matching. Both parsers now share catalog word-boundary extraction; JavaScript/PostgreSQL and ordinary prose no longer manufacture Java/SQL/Excel matches. Whitespace/case/duplicate skills normalize consistently. Existing 60/25/15 fit weights, cap and decision thresholds remain unchanged. Overall fit abstains for incomplete/nonfinite/failed-resume, optional/negated or conflicting experience evidence. Missing listed terms are not asserted to be absent abilities or mandatory requirements. Results persist numbered source snapshots, owned resume/profile identity, parsed fields, JD excerpt and explicit catalog/uncertainty limits; they are not hiring probabilities or verified employer claims. JD corrections/retries preserve the captured resume instead of silently switching uploads. Non-null legacy storage is retained; the metadata availability marker drives nullable API/UI/admin and conservative Career/Risk behavior without a schema/history rewrite. Salary extraction skips unrelated experience/version/deadline numbers and requires existing pay cues; no currency/FX policy changed. Existing theme cards restore comparison/fit-signal readability.
  TESTS: **93 integration backend + 14 final focused backend (overlapping) + three actual Chrome PASS**, zero skips. `artifacts/career-7ede529/{backend-complete,backend-last}.json`, `chrome-verified.json`, driver-backed `browser-verified/browser_regression_summary.json`; desktop/mobile screenshots inspected. Fourteen new matching checks plus existing recruiter/resume/adaptive, financial-baseline/risk freshness, document review/retry, public-HTTP and sanitized-error regressions. Chrome runs ordinary recruiter text submission/reload, numbered owned source references, escaped malicious filename, absent salary evidence and incomplete-input abstention; financial records remain identical and contrast >=4.5. Source details stay open across live refresh. The bounded browser click helper retries stale/intercepted elements; final Chrome integration also reruns FIN-05 and TRAVEL-10. Six-test initial reproduction (11 failed subtests), one invalid test-module label and incomplete macro fixture failures retained; overlapping 40/92-test and earlier Chrome passes are not added to final totals. Public providers are stubbed; no personal upload or provider activation. No calibrated real recruiter/hiring outcomes, full arbitrary JD semantics or release/native acceptance claimed.
  FEATURES: **72 verified / 25 unaccepted / 28 partial / 10 missing / five approval / three external = 143**. Newly verified CAREER-02, bounded to reviewed deterministic matching/source/abstention workflows. Files alphabetically: `alfred_ai/services/document_review.py`, `apps/career/admin.py`, `apps/career/models.py`, `apps/career/serializers.py`, `apps/career/services/job_intelligence.py`, `apps/career/services/resume_intelligence.py`, `apps/career/views.py`, `apps/risk/services/risk_intelligence.py`, `docs/PROJECT_STATUS.md`, `static/js/career.js`, `tests/test_career_matching_acceptance.py`, `tests/test_user_data_browser.py`. Exact-source boundary receipts: `artifacts/career-boundary-7ede529/{graph,privacy-manifest,source-checks,push}.json`; finish non-PASS/mismatched receipts before editing. Master/frozen/package and approval gates unchanged. NEXT TASK: FIN-07 chronological cash-flow forecasting: exclude future/partial observation leakage, retain canonical income/fixed-bill assumptions, expose honest empirical uncertainty and chronological holdout evidence. Genuine calibrated forecast accuracy remains unverified; do not claim it from synthetic tests. Then INV-07 per the dependency queue. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 12`.

- **FIN-05 BUDGET ACCEPTANCE — 2026-10-24:** HEAD = this checkpoint commit (base `42106cb`, TRAVEL-10 committed/pushed there). DONE: accepted owner budget CRUD, current-month selection, canonical living spend, utilization and daily plan guidance. Daily arithmetic and category allocation now use Decimal/HALF_UP; deterministic cent remainders reconcile category limits to the available plan. Zero limits leave utilization undefined. Unknown income abstains; an explicit plan is labeled PLAN_ONLY and an oversized plan warns that funding is unconfirmed. City/category rules are disclosed assumptions. Saved historical-spend notes cannot replace canonical transactions. Forecast errors no longer erase valid budget guidance or fixed obligations; unavailable sections are explicit. Live refresh preserves drafts, form amounts remain decimal strings and repeat submission is disabled. Existing theme cards restore recommendation contrast.
  TESTS: **29 focused backend + one final actual Chrome PASS**, zero skips. `artifacts/budget-42106cb/backend-final.json`, `chrome-contrast.json`, driver-backed `browser-contrast/browser_regression_summary.json`; desktop/mobile screenshots inspected. Eleven acceptance tests plus existing money/baseline tests cover cent ties/HALF_UP, canonical spending boundaries, zero/unknown/oversized budgets, date boundaries, owner/session/CSRF, cache invalidation, isolated forecast failure and unknown-income fixed bills. Chrome executes ordinary plan saves/reload, draft refresh, exact category reconciliation, zero-plan and separate-account unknown states, financial-record nonmutation and recommendation contrast >=4.5. Reproduction failures and corrected fixture/login-selector failures remain in the same artifact directory; earlier overlapping passes are not added to final totals. FIN-14 schema/rollback receipts reused: no schema or money-policy change. Full suites, native/package and real-account acceptance were not repeated.
  FEATURES: **71 verified / 26 unaccepted / 28 partial / 10 missing / five approval / three external = 143**. Newly verified FIN-05 in bounded synthetic source-level acceptance. Files alphabetically: `apps/budgets/money.py`, `apps/budgets/services/budget_intelligence.py`, `apps/budgets/views.py`, `docs/PROJECT_STATUS.md`, `static/js/budgets.js`, `templates/budgets/list.html`, `tests/test_budget_acceptance.py`, `tests/test_user_data_browser.py`. Exact-source boundary receipts: `artifacts/budget-boundary-42106cb/{graph,privacy-manifest,source-checks,push}.json`; complete non-PASS/mismatched receipts before editing. Master/frozen/package and all approval gates unchanged. NEXT TASK: CAREER-02 reviewed skill-gap/JD matching, source references, uncertainty, ownership and Chrome acceptance; inspect stored resume/JD fit paths, fix demonstrated defects without claiming calibrated hiring probability. FIN-07 follows CAREER-02. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 12`.

- **TRAVEL-10 PROVENANCE ACCEPTANCE — 2026-10-24:** HEAD = this checkpoint commit (base `5c88944`). DONE: accepted local camping/attraction evidence freshness, provenance and stale/offline states. Reproduced malformed-date API errors and unsupported verification claims for missing/naive/future clocks or unsafe source links. Read-time ageing now abstains for unusable place evidence and removes it from verified categories without rewriting stored research. Expired place evidence is explicitly stale; original source/check/expiry times survive offline cache fallback. UI exposes mapped hours/access as leads, direct source citations, incomplete coverage and explicit UNKNOWN booking/opening and unverified permits. Screenshot review fixed low-contrast unavailable text using existing theme colors. No provider authentication/activation, private upload, pricing, currency or production change.
  TESTS: **47 focused backend + one final actual Chrome PASS**, zero skips; `artifacts/places-5c88944/{backend-integrated,chrome-accepted}.json`, driver-backed `browser-accepted/browser_regression_summary.json`; desktop/narrow-screen results inspected. Six new acceptance tests plus existing provider/continuation regressions cover cache reuse, offline/partial/unconfigured behavior, unknown availability, invalid clocks/source links, original receipts, no read mutation and foreign ownership. Chrome uses disclosed synthetic places through the actual session API/UI, checks escaped names/citations, fresh-to-stale-to-unavailable transitions and responsive states. Pre-fix six-test reproduction (six failures/one error) and overlapping initial Chrome pass retained. No live POI accuracy, bookable camping or live permit acceptance claimed.
  FEATURES: **70 verified / 26 unaccepted / 29 partial / 10 missing / five approval / three external = 143**. Newly verified TRAVEL-10, bounded to the requirement's freshness/provenance workflow. Files alphabetically: `apps/mobility/services/travel/presentation.py`, `docs/PROJECT_STATUS.md`, `static/css/travel_planner.css`, `static/js/travel_research_panels.js`, `tests/test_travel_places_acceptance.py`, `tests/test_user_data_browser.py`. Exact-source boundary receipts: `artifacts/places-boundary-5c88944/{graph,privacy-manifest,source-checks,push}.json`; finish non-PASS/mismatched receipts before editing. Master/frozen/package unchanged; all approval gates remain in force. NEXT TASK: FIN-05 budget/utilization/affordability acceptance; reuse completed Decimal fields/migration receipts and canonical baseline, test rounding/reconciliation, unknown income, owner/cache/UI behavior, then CAREER-02. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 12`.

- **REGISTRY RECOVERY / THREE-MODULE CHECKPOINT — 2026-10-24:** HEAD = this checkpoint commit (base `de7a498`). DONE: invoice replay/atomic posting `0dc9e66` and private media acceptance `de7a498` are committed, privacy-checked and pushed. Third module fixes reproduced registry receipt loss: serialize finite JSON before writes, load the latest snapshot for each update, coordinate threads/instances in one process, flush/fsync a same-directory temporary file and atomically replace the receipt. Publish in-memory metadata only after replacement succeeds. Corrupt/non-object input is unavailable to new readers and is preserved for operator review; updates cannot overwrite it. Exclusive initial creation avoids truncating existing receipts. This file records training metadata; it is not a planning/coding/review agent router or proof of model accuracy.
  TESTS: **28 focused backend PASS**, zero skips (`tests.test_model_registry_recovery`, `tests.test_ml_readiness`, `tests.test_ml_training_orchestrator`); `artifacts/registry-de7a498/backend-integrated.json`. Six registry checks cover failed serialization/nonfinite metrics, failed replacement/cleanup, stale-instance merge, corrupt input preservation, complete snapshots and concurrent threaded updates. Readiness/consent/revoked/stale/proxy-evidence fallbacks remain passing; no real training activation/model promotion. Pre-fix five-test reproduction retained (seven failed subtests/three errors). No UI/API contract changed in this module; the invoice and media Chrome evidence remains applicable. Prior module final receipts: invoice 24 backend + one Chrome; media 56 integration backend + ten final focused (eight overlap) + one final Chrome, all zero skips. Full suites/packages/native/independent-PC were not repeated.
  FEATURES: **69 verified / 27 unaccepted / 29 partial / 10 missing / five approval / three external = 143**. Newly verified this continuation: TRAVEL-19 only. BIKE-04 real layouts and COUNCIL-01 role/held-out acceptance remain open. Registry coordination is process-local; separate writer coordination is required before multi-process training. No schema/dependency/financial-record/production/provider/currency/history activation. Files alphabetically: `apps/ml_engine/core/alfred_registry.py`, `docs/PROJECT_STATUS.md`, `tests/test_model_registry_recovery.py`.
  BOUNDARY / NEXT: exact-source AST/privacy/push receipts `artifacts/registry-boundary-de7a498/{graph,privacy-manifest,source-checks,push}.json`; finish non-PASS/mismatched receipts before editing. Master/frozen/package remain unchanged; accepted package is `3bc75ac`, and packaged loan-document AI latency remains a separate unresolved gate. NEXT TASK: TRAVEL-10 camping/attraction freshness and provenance acceptance: inspect existing stored/public-evidence paths and tests, validate expiry/partial/offline/owner/UI states with disclosed synthetic fixtures, leave bookable availability/permits unknown, and do not activate a provider. Do not repeat completed photo, invoice replay or registry persistence work. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; git log -3 --oneline; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 14`.

- **TRAVEL-19 PRIVATE MEDIA ACCEPTANCE — 2026-10-24:** HEAD = this checkpoint commit (base `0dc9e66`, invoice replay committed/pushed there). DONE: accepted generated local JPEG/PNG upload, EXIF timestamp/GPS inference and private trip galleries. Fixed first-day UTC/local-date mismatch; invalid timestamps no longer discard valid GPS, and malformed/nonfinite/out-of-range/invalid-hemisphere DMS evidence abstains without losing valid dates. User metadata wins. Image decoding and finite coordinate validation precede storage. Trip associations require owner confirmation; ignored/stale/foreign matches are rejected. The form leaves unknown capture time blank, retains upload feedback and prevents repeat submit while busy. Screenshot review found unreadable dark gallery cards; existing theme variables restore caption/metadata contrast. No schema, dependency, provider activation or financial writes.
  TESTS: **56 integration backend + 10 final focused backend PASS** (eight overlap), zero skips. Final actual Chrome **one PASS**, driver-backed, zero skips; ordinary upload, EXIF suggestion/preview, explicit Add, cached gallery/reopen, escaped captions, protected media no-store and both theme/mobile layouts. Caption/metadata contrast >=4.5 verified in Chrome; desktop and both narrow-screen theme screenshots inspected. Privacy: foreign media/API/association denied; anonymous media redirects to login; CSRF enforced; media learning needs both opt-ins, favourite and explicit tags. Existing middleware cache invalidation passed; no cache rewrite. Receipts: `artifacts/media-0dc9e66/{backend-integrated,backend-accepted,chrome-gallery}.json`, `browser-gallery/browser_regression_summary.json`; earlier failures and overlapping Chrome checks retained. Test-only Django public media serving is bypassed so Chrome exercises ALFRED's actual protected endpoint.
  FEATURES: **69 verified / 27 unaccepted / 29 partial / 10 missing / five approval / three external = 143**. Newly verified TRAVEL-19 is local/source acceptance; no HEIC/unreviewed camera-layout universality, real location authenticity, public sharing, live provider or packaged acceptance claimed. BIKE-04 stays unaccepted pending approved real invoice/insurance layouts. Files alphabetically: `apps/mobility/planner_views.py`, `apps/mobility/serializers.py`, `apps/mobility/services/travel_media.py`, `docs/PROJECT_STATUS.md`, `static/css/style.css`, `static/js/mobility.js`, `templates/mobility/dashboard.html`, `tests/test_travel_media_acceptance.py`, `tests/test_user_data_browser.py`.
  BOUNDARY: exact source AST/privacy/push receipts `artifacts/media-boundary-0dc9e66/{graph,privacy-manifest,source-checks,push}.json`; finish non-PASS/mismatched receipts before editing. Master/frozen/package unchanged; accepted package stays `3bc75ac`. NEXT TASK: COUNCIL-01 scoped registry persistence/recovery inspection after media boundary, without claiming planning/coding agents or enabling training; inspect current callers and reproduce any defect before changes. Registry routing/held-out model acceptance remains separate. If no defect is established, continue TRAVEL-10 freshness/provenance acceptance with booking availability explicitly unavailable. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 14`.

- **BIKE-04 INVOICE REPLAY CHECKPOINT — 2026-10-24:** HEAD = this checkpoint commit (base `3c09291`). DONE: recovered interrupted work and fixed duplicate service posting. Validated costs/chronology precede atomic document/log writes. Renamed byte replay returns the existing owned log, preserving reviewed cents/source; complete identity conflicts, stale vehicle edits, legacy identities and missing/ambiguous logs return 409 for review. Concurrent SQLite uploads post one log; failed posting rolls back rows/new raw files. Imported source/profile links are immutable. UI identifies replays. Actual PDF regression restores missing next-service checkpoints to unknown/None. No schema/dependencies/history or canonical expense writes changed.
  TESTS: **24 focused backend + one actual Chrome PASS**, zero skips; `artifacts/invoice-3c09291/{backend-integrated,chrome-accepted}.json`, driver-backed `browser-accepted/browser_regression_summary.json`; desktop/narrow-screen screenshots inspected. Covers cents, rollback, identity/replay, owner isolation, concurrency/retry, source immutability, review/delete compatibility and actual synthetic PDF parsing. Earlier reproduction, multipart file-copy, missing fixture dependency and zero-checkpoint failures retained; final checks pass with existing PyMuPDF. Prior service/refill Chrome also passed in `chrome-final.log` (not summed). Files alphabetically: `apps/mobility/serializers.py`, `apps/mobility/views.py`, `docs/PROJECT_STATUS.md`, `static/js/bike_service.js`, `tests/test_service_import_receipts.py`, `tests/test_user_data_browser.py`.
  FEATURES: **68 verified / 28 unaccepted / 29 partial / 10 missing / five approval / three external = 143**, unchanged. BIKE-04 remains IMPLEMENTED_NOT_ACCEPTED: approved real invoice/insurance layouts have not been accepted. Incomplete identifiers support byte replay only; legacy rows are not backfilled. Exact-source boundary receipts: `artifacts/invoice-boundary-3c09291/{graph,privacy-manifest,source-checks,push}.json`; finish any non-PASS/mismatched receipt before new edits. Package stays `3bc75ac`; native/runtime/independent-PC/production and approval gates unchanged. NEXT TASK: TRAVEL-19 local photo/EXIF/date/GPS and gallery acceptance, with explicit association confirmation and private media. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 12`.

- **BIKE-02 / FIVE-MILESTONE CHECKPOINT — 2026-10-24:** HEAD = this checkpoint commit (base `95f30bc`). DONE: accepted owner service/fuel/cost records using the existing Decimal-backed registers; the former float/migration limitation in BIKE-02 was stale. Fixed reproduced nonfinite/boolean/overflowing refill measurements before writes and inconsistent sub-0.01 L mileage/price denominators. Measurements retain their entered precision; stored money retains HALF_UP cents. Malformed bodies return 400. Actual Chrome uncovered a valid default refill being rejected when the browser calendar was ahead of the server: the dashboard now supplies its validation date outside the cached payload, the form uses it for defaults and preserves manually edited dates during refresh. No host/server timezone setting or future-date rule was changed. Long escaped notes also clipped cost/Delete controls in narrow desktop cards; text now wraps, with controls visible on desktop/mobile. Existing immediate correction/cache behavior passed and was left unchanged.
  TESTS: **35 focused backend + one actual Chrome PASS**, zero skips; final `artifacts/vehicle-95f30bc/checkpoint-accepted.json`. Coverage: owner CRUD/profile isolation/CSRF, exact cents and independent 0.2 km / 0.005 L = 40 kmpl, unit price, zero/nonfinite/overflow/future-date/malformed rejection, read-only predictions, accounting invariants, cached corrections and server-date rollover. Browser exercises ordinary forms, escaped notes, visible costs/controls, server-date save, refresh/reopen, draft preservation and confirmed deletion while preserving foreign rows and financial history; desktop/390px screenshots inspected. Pre-fix/import-setup, API/date and layout failures retained. A new test initially expected fixed `40.0` formatting; corrected to the existing `40 kmpl` contract. Backend evidence reused after only UI/assertion changes. Prior money migration/rollback receipts remain applicable; schema/dependencies unchanged.
  FEATURES: **68 verified / 28 unaccepted / 29 partial / 10 missing / five approval / three external = 143**. Five session modules: direction `ec9c161`, Career outcomes `81f88b8`, investment projections `76c1522`, financial-health acceptance `95f30bc`, and this service/fuel acceptance. **252 focused backend / eight actual Chrome** final passing checks across those modules, plus one overlapping direction screenshot flow. Newly verified CAREER-05, INV-03, FIN-04 and BIKE-02; DOC-07 remains partial. No employer/invoice authenticity, physical mileage accuracy, calibrated maintenance prediction or product-wide AI accuracy is claimed. Modified files alphabetically: `apps/mobility/serializers.py`, `apps/mobility/services/bike_service_intelligence.py`, `apps/mobility/views.py`, `docs/PROJECT_STATUS.md`, `static/js/bike_service.js`, `templates/mobility/bike_service_dashboard.html`, `tests/test_mobility_record_acceptance.py`, `tests/test_user_data_browser.py`.
  BOUNDARY / BLOCKERS: first four modules at `95f30bc` passed AST refresh (exit 0), JavaScript/143-row/protected-ref guards and pinned privacy (**901 paths / 876 blobs / four commits, zero findings**) and were pushed; remote ref was independently verified. Evidence: `artifacts/source-boundary-76c1522/{graph,privacy-manifest,source-checks,push}.json`. Final module boundary receipts are `artifacts/vehicle-boundary-95f30bc/{graph,privacy-manifest,source-checks,push}.json`: if PASS and their candidate equals current HEAD with the matching remote ref, this boundary is complete and must not be repeated; otherwise finish it before new edits. No master/frozen-candidate change. Full release/CI/native/package/independent-PC gates were not rerun; accepted package is still source `3bc75ac`, so these new features remain source-only. Currency/history/provider/production approvals and packaged AI runtime blocker remain unchanged. NEXT TASK: BIKE-04 invoice/document review acceptance: inspect existing upload/extract/review lineage and owner/cost boundaries, use synthetic local evidence, and leave real private/provider authentication claims unaccepted. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 12`.

- **FIN-04 HEALTH ACCEPTANCE CHECKPOINT — 2026-10-24:** HEAD = this checkpoint commit (base `76c1522`; INV-03 accepted there). DONE: accepted existing financial-health and historical-spending indicators without changing application behavior. Independent stable-history and loss-making cases verify bounded heuristic scores, exact income/outflow/net cents, recorded reference month, all-history rates, zero/no-history distinction and read-only financial invariance. Transfers and large uncategorized debits remain excluded from confirmed cash flow; foreign history cannot change owned cached or fresh indicators. Ordinary reviewed-owner Chrome acceptance shows the expected score, estimated-risk and rule-based/not-credit-score labels, actual reporting month and all-history rate explanation; no owner financial writes. Prior unchanged review-required/empty/older-history Chrome receipts remain applicable.
  TESTS: **13 focused backend + one actual Chrome PASS**, zero skips. Initial two failed backend receipts retained: the new fixture first used an explicit expense and then an amount below the existing 50,000 review threshold; it now uses uncategorized 52,345.67. No product policy changed to fit the test. Final receipt `artifacts/health-76c1522/checkpoint-verified.json`, backend-verified/Chrome logs, inspected desktop/390px screenshots. Passing Chrome was reused while correcting only the backend fixture. Graph update/source privacy/development push are the next integration boundary.
  FEATURES: **67 verified / 29 unaccepted / 29 partial / 10 missing / five approval / three external = 143**. FIN-04 technical verification covers recorded-history heuristics, not creditworthiness, future health/returns, private-account accuracy or product-wide AI reliability. Session milestones: direction `ec9c161`, Career outcomes `81f88b8`, projections `76c1522`, and this health acceptance. Modified files alphabetically: `docs/PROJECT_STATUS.md`, `tests/test_financial_health_acceptance.py`, `tests/test_user_data_browser.py`. BLOCKERS: accepted package remains `3bc75ac`; session features are source-only; currency/history/provider/runtime/independent-PC and production gates unchanged. NEXT TASK: finish exact-source AST/privacy checks and push the development branch; then BIKE-02 service/fuel/cost acceptance, inspecting the existing Decimal migration evidence before deciding its remaining scope. Do not repeat completed nominal projections or health acceptance. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 12`.

- **INV-03 PROJECTION ACCEPTANCE CHECKPOINT — 2026-10-24:** HEAD = this checkpoint commit (base `81f88b8`; owner Career outcomes committed there). DONE: accepted the existing deterministic 13-point investment projection with independent beginning-of-month annuity results, recorded month zero, owner-only aggregation, zero/negative returns, SIP/no-SIP, month rollover and disclosed nominal rate assumptions. Fixed reproduced nonfinite/boolean return inputs before any mutation. Extreme finite assumptions preserve summary precision and recorded values; forecasts outside JSON's finite range are withheld in full, never rendered as partial/zero estimates. The UI destroys a stale chart, shows an accessible unavailable explanation, and restores a valid chart after correcting the assumption. Growth cache schema bumped; no record repair, provider access, model, schema, currency/FX default or production change.
  TESTS: **32 focused investment backend + two actual Chrome PASS**, zero skips. Backend includes invalid create/update atomicity, Decimal cents/aggregate rounding, extreme/nonfinite forecasts, previous-cache rejection, foreign mutations/unauthenticated denial and existing money/import rollback regressions. Chrome checks actual chart data against independent expected values, invalid-rate rejection, unavailable desktop/390px state, foreign exclusion, correction/recovery and unchanged financial amounts. Desktop/mobile screenshots inspected. Pre-fix two-test reproduction failed as expected (nonfinite storage/JSON rendering); retained unchanged. Evidence: `artifacts/investment-81f88b8/{backend,chrome,checkpoint,reproduction}.json`, logs and screenshots. JavaScript syntax PASS. Existing source-wide/backend/native/package receipts reused outside affected code; final AST/privacy/push boundary is next.
  FEATURES: **66 verified / 30 unaccepted / 29 partial / 10 missing / five approval / three external = 143**. Newly verified INV-03 covers nominal planning using entered rates/contributions, not guaranteed/live returns, inflation forecasting, suitability or approved currency conversion. Modified files alphabetically: `apps/investments/money.py`, `apps/investments/serializers.py`, `apps/investments/views.py`, `docs/PROJECT_STATUS.md`, `static/js/investments.js`, `templates/investments/list.html`, `tests/test_investment_projection.py`, `tests/test_user_data_browser.py`. BLOCKERS: new features remain source-only; accepted package `3bc75ac` and independent-PC/runtime/production/provider/history/currency gates unchanged. NEXT TASK: complete one scoped source/privacy/development-push boundary for the three session modules; then FIN-04 financial-health indicator acceptance using existing local dashboard architecture, without external delivery or goal/currency schema changes. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 12`.

- **CAREER-05 OWNER-OUTCOME CHECKPOINT — 2026-10-24:** HEAD = this checkpoint commit (base `ec9c161`; transaction-direction Q&A committed there). DONE: ordinary owners can browse paginated opportunity history, choose an analysis, record accepted/rejected salary-bearing decisions, correct them and reopen saved reports in Career. Projection omits raw documents; ownership/CSRF checks remain. UI states that decisions are owner reports, discloses annualization assumptions, requires an explicit recorded currency code, escapes notes/links, preserves unsaved drafts during dashboard refresh and rejects stale saves without losing edits. PATCH preserves omitted report fields and retained job evidence. Compare-and-swap protects current source metadata, including SQLite; it does not replace a concurrent source edit. Invalid/nonfinite/negative/overscale/overprecision salary inputs no longer silently fall back to source values; Decimal scaling, annualization and HALF_UP midpoints preserve cents. No profile-income posting, new model/schema/FX/currency defaults, provider contact or private-history activation.
  TESTS: preimplementation stale-save/provenance reproductions FAIL as expected; final **45 focused Career backend + one actual Chrome PASS**, zero skips. Coverage includes source/owner boundaries, 20-item pagination, raw-data exclusion, CSRF, salary units/precision, invalid amounts/dates/links, safe partial corrections, concurrent source preservation, source/report lineage, admin-form compatibility and salary-profile invariance. Browser exercises save/reload/correction, separate owner opportunities, escaped markup/unsafe links, dashboard refresh, stale draft and desktop/390px forms; screenshots inspected. Initial browser assertion compared a just-created string value against a reloaded Decimal; it was corrected by loading the baseline from the DB, with the failed receipt retained. Evidence: `artifacts/career-outcome-ec9c161/{backend,chrome-final,checkpoint-final}.json`, logs and screenshots. Only the affected Chrome flow was rerun; passing backend evidence reused. JavaScript syntax PASS; graph refresh is due at the session integration boundary.
  FEATURES: **65 verified / 31 unaccepted / 29 partial / 10 missing / five approval / three external = 143**. CAREER-05 is verified for this bounded local owner-report workflow, not employer authentication, a universal ATS or learned salary accuracy/maturity. Savings-goal/currency/private-history/provider and external runtime/recovery gates remain closed; accepted package is still `3bc75ac`, and subsequent features are source-only. Modified files alphabetically: `apps/career/serializers.py`, `apps/career/services/job_intelligence.py`, `apps/career/urls.py`, `apps/career/views.py`, `docs/PROJECT_STATUS.md`, `static/js/career.js`, `templates/career/list.html`, `tests/test_career_outcome_workflow.py`, `tests/test_user_data_browser.py`. NEXT TASK: INV-03 investment planning/projection acceptance: verify disclosed deterministic assumptions, independent expected results, empty/zero/invalid inputs, owner isolation and actual UI; keep provider calls and guaranteed-return claims OFF. Then run the source/privacy/development push boundary once. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 12`.

- **TRANSACTION-DIRECTION CHECKPOINT — 2026-10-24:** HEAD = this checkpoint commit (base `1257eb5`). DONE: exact singular/plural debit/credit questions and reviewed Transfer-label questions in bank, canonical-record and explicitly selected document scopes. Current reviewed direction must match a valid retained import direction. Each selected record keeps its own account flow and private citation; credits do not become income/refunds, debits do not become expenses, and a Transfer label does not establish a paired account/transfer. No reviewed reversal linkage exists in this schema: reversal/refund/ambiguous/compound requests explicitly abstain. No description/sign inference, model/retrieval/cloud/history, financial writes or new schema/currency behavior. Owner, retained-source, selection, revocation and final revision checks are preserved. UI guidance and feedback distinguish these answers and preserve unsupported drafts.
  TESTS: **127 focused backend + three actual Chrome PASS**, zero skips; one overlapping direction flow rerun only to capture its visible 390px answer also PASS. Backend covers debit/credit with misleading descriptions, transfer labels in both directions, missing/invalid/conflicting retained directions after review, source races, foreign-owner citations, cross-document rejection and financial/original invariance. Browser covers review, two separate accounts, citations, explicit reversal abstention, draft behavior and no model/cloud. Desktop/mobile screenshots inspected. Initial two new test expectations were corrected to the existing fail-closed response/404 contract; failed receipts retained. Evidence: `artifacts/direction-1257eb5/` (`backend-final.json`, `chrome-final.json`, `chrome-visual.json`, logs and screenshots). AST graph refresh completed with unsupported-file warnings; no semantic API used. Full unchanged backend/native/package gates were not rerun. The accepted package remains source `3bc75ac` and does not include this new feature.
  BLOCKERS: savings-goal persistence still depends on the existing unapproved currency/money decisions; reversal linkage/paired transfer authenticity is not invented. Existing independent-PC/operator/runtime/provider/history/production restrictions remain. All **143** rows recalculated unchanged **64 verified / 32 unaccepted / 29 partial / 10 missing / five approval / three external**; this bounded extension does not complete arbitrary DOC-07. Modified files alphabetically: `apps/ml_engine/services/canonical_evidence.py`, `apps/ml_engine/services/hybrid_intelligence.py`, `docs/PROJECT_STATUS.md`, `static/js/intelligence.js`, `templates/ai_insights.html`, `tests/test_bank_statement_grounding.py`, `tests/test_user_data_browser.py`. NEXT TASK: CAREER-05 owner-reported application/outcome tracking acceptance: inspect existing outcome normalization/API/UI, fill missing end-to-end behavior and test ownership/lineage without contacting employers/providers. Commit/push only validated development changes; no master merge while its gates remain unaccepted. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 12`.

- **COMPILED/OFFLINE FOLLOW-UP CHECKPOINT — 2026-10-23:** HEAD = this checkpoint commit (base `c9cd0cc`); application/package source remains **`3bc75acf5db85e2e361987c42228bdf4c7333704`**. DONE: six existing routing regressions executed against bytecode extracted directly from the hash-verified packaged executable: malformed request/response coordinates, unsupported shapes/elevations, unavailable/cache/map exclusion, explicit-zero compatibility, uncertainty and preserved version-one caches. Shared source services are unchanged; these are compiled-code fixture tests, not live-provider or native Travel HTTP acceptance. A separate real-bundle distribution attempt correctly rejected the newer tracker-only checkout before creating output; original embedded metadata remains unchanged. Evidence: `artifacts/compiled-travel-c9cd0cc/{loaded-bytecode,checkpoint,guards,provenance}.json`.
  TESTS: **six compiled routing + one real stale-bundle rejection PASS**; **five further compiled HTTP/mobile checks PASS with Ollama fully stopped**: correct cited statement period, usable 390px answer/draft clearing, the exact owned transaction citation opens, financial rows/retained originals unchanged, and no model server started. Offline mobile answer screenshot inspected; current/retained dates and the selected source are visible. Initial harness initialization/class/viewport/selector failures are retained; final checks pass without application changes. Evidence: `artifacts/compiled-travel-c9cd0cc/{offline-period-report,cleanup}.json`, `guards-verified.log`, `offline-period-verified.log` and mobile screenshots. No additional model inference, provider contact, dependency or schema change. The earlier **1,108 backend / 74 Chrome / 35 native / six installer / ten packaged document** PASS receipts remain applicable and were not rerun. All test application/Ollama processes stopped and ports closed.
  BLOCKERS: independent-PC/reboot/normal-account/device-loss/manual accessibility acceptance and operator adoption of the staged Vulkan runtime remain separate; currency/private-history/external-provider approvals remain closed. Master/frozen/production/operator data/backups untouched; no merge/push/promotion. Counts recalculated unchanged **64 verified / 32 unaccepted / 29 partial / 10 missing / five approval / three external = 143**. Modified file alphabetically: `docs/PROJECT_STATUS.md`. NEXT TASK: bounded DOC-07 reviewed transaction-direction Q&A (recorded debit/credit): inspect current/retained direction proofs in `apps/expenses/services/statement_evidence.py`, `canonical_evidence.py` and `hybrid_intelligence.py`; reuse existing exact-question, selected-citation, stale/owner/cross-document abstention and browser patterns. Do not infer direction from amount signs, alter financial records/currency, repeat completed period/classification work or relabel the accepted package. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 12`.

- **FRESH WINDOWS ACCEPTANCE CHECKPOINT — 2026-10-23:** HEAD = this checkpoint commit; exact tested/packaged source **`3bc75acf5db85e2e361987c42228bdf4c7333704`**, tree `5b7e0d83162ae189b28e0bbc6dbb56002c043392`. DONE: isolated official Vulkan remediation (`1b54f28`), reviewed statement-period Q&A (`98c913b`), embedded build-source enforcement (`c5665ef`), and fresh PyInstaller/ZIP/Inno packaging of classification, period and Travel changes. Gate-start commit `3bc75ac` remains the package identity; a later tracker-only HEAD does not relabel it. Modified file at this closing checkpoint: `docs/PROJECT_STATUS.md`.
  TESTS: **1,108 full backend + 74 actual Chrome PASS**, zero skips; pinned privacy **900 paths / 1,185 blobs / 87 commits, zero findings**, system/migration drift PASS. Fresh distribution: **10,393 files**, zero private runtime paths, matching embedded/ZIP/manifest commit/tree and all four executable/distribution hashes verified before/after acceptance. Fresh compiled package: **35 native + six installer lifecycle + ten statement-period/classification HTTP/Chrome checks PASS**. Real local embeddings/reasoning, loan-document abstention/injection exclusion, owner isolation, outages, restart, encrypted-vault/queue backup restore and unchanged financial rows/originals PASS. Desktop/390px screenshots inspected; period/classification checks made zero model-generation calls. Earlier interrupted full runs and the runner's reused-directory failure are retained; only unfinished gates/distribution were resumed, without rerunning passing suites or rebuilding the successful bundle. Evidence: `artifacts/windows-integrated-20261023/{pipeline,backend,chrome,build,acceptance,native-fresh-report,installer-report,packaged-period-report}.json`; release artifacts/independent-PC kit in its `release/` directory.
  BLOCKERS: same-host synthetic acceptance does not establish independent-PC/reboot/normal-account/device-loss/manual accessibility acceptance. The installed CPU runtime is unchanged; adopting the qualified staged Vulkan runtime is a separate operator decision. Driver/model/residency/deadline changes and currency/private-history/external-provider activation remain closed. Owned Vulkan server/children stopped, test ports closed, installed executable unchanged/no backend added, original desktop/startup state restored; staged binaries, failed evidence and backups retained (`artifacts/vulkan-33003bc/rollback-final.json`). Master/frozen refs untouched; no release promotion/merge/push. All **143** statuses recalculated unchanged: **64 verified / 32 unaccepted / 29 partial / 10 missing / five approval / three external**. NEXT TASK: accept the freshly compiled Travel coordinate guards against bounded synthetic cache/provider failure fixtures without contacting external providers; preserve existing receipts and source identity. Then select the next safe bounded DOC-07 grounding unit. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 12`.

- **PINNED WINDOWS GATE START — 2026-10-23:** HEAD = this checkpoint commit; application/build-tool source through `c5665ef`. DONE: isolated Vulkan four benchmarks + unchanged-package 35 native PASS; statement-period/classification/Travel integration 225 backend + five Chrome PASS; provenance four direct/67 related release PASS. Full backend/Chrome/privacy/configuration and fresh bundle/ZIP/installer are **PENDING**, not acceptance. Their durable receipts/logs will be under `artifacts/windows-integrated-20261023/` with the full candidate SHA; inspect `pipeline.json`, `backend.json`, `chrome.json`, `build.json` before restarting anything. Running PIDs are recorded; only final PASS receipts count. All future package metadata must match this exact clean source. Owned isolated Vulkan server is still active (`artifacts/vulkan-33003bc/server.json`), with unchanged installed runtime/model/driver/configuration. NEXT TASK: finish those source/build gates, then fresh native/installer/packaged statement-period/classification HTTP/browser checks, preserve failures and stop only owned processes. No release/master acceptance yet; counts **64/32/29/10/8 = 143**. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 10`.

- **EMBEDDED BUILD-SOURCE CHECKPOINT — 2026-10-23:** HEAD = this checkpoint commit (base `98c913b`). DONE: PyInstaller captures a clean exact Git commit/tree before analysis, checks it again after collection, and embeds `build-provenance.json` in the bundle. Distribution validates that record against the current clean checkout before assembly and again before its manifest; manifest source fields come from the frozen record and bind its SHA-256. Dirty/untracked source, source movement, malformed/forged metadata and attempts to relabel an older bundle fail closed. Existing packages are not modified. Updated native build instructions use the guarded package helper; new regression module joins the established backend gate. Modified files alphabetically: `docs/NATIVE_WINDOWS.md`, `docs/PROJECT_STATUS.md`, `packaging/ALFRED.spec`, `scripts/package_windows_release.py`, `scripts/release_validation.py`, `tests/test_windows_build_provenance.py`.
  TESTS: **four direct provenance tests / 67 related release tests PASS**, zero skips, using disposable synthetic Git repositories and preserving old metadata on rejection. Graphify AST refresh is running; inspect `artifacts/build-provenance-98c913b/graph-update.log` before claiming completion. Evidence: `artifacts/build-provenance-98c913b/`. Counts unchanged **64/32/29/10/8 = 143**. BLOCKERS: no fresh build/installer acceptance yet; legacy bundles have their historical source receipts and are not retroactively marked as embedded-provenance builds. NEXT TASK: keep this exact clean commit unchanged for full backend/Chrome/privacy/configuration checks, a fresh PyInstaller/ZIP/Inno build and native/installer/packaged period/classification acceptance using the owned isolated Vulkan server. Its identity remains in `artifacts/vulkan-33003bc/server.json`; installed runtime/model/driver/host config remain untouched. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 12`.

- **STATEMENT-PERIOD CHECKPOINT — 2026-10-23:** HEAD = this checkpoint commit (base `1b54f28`). DONE: explicit period/date-range questions return inclusive ISO start/end dates from one selected owner-reviewed statement, with individual selected-record citations. Current boundaries must be complete, ordered and match the retained import snapshot; the selected transaction must fall inside them. Missing/invalid/conflicting ranges, mixed statements, unsupported/ambiguous requests and foreign documents abstain without retrieval, inference, cloud or saved history. Current metadata is revalidated before returning; record/account/file/catalog privacy and stale-source guards remain intact. Multiple owned accounts/statements require explicit selection and never combine periods. Ordinary date/classification answers are preserved. UI guidance/feedback, bank and document selectors, private citations and desktop/390px flows are complete. No inferred period, schema, currency, parser-learning or provider change. Modified files alphabetically: `apps/ml_engine/services/canonical_evidence.py`, `apps/ml_engine/services/hybrid_intelligence.py`, `docs/PROJECT_STATUS.md`, `static/js/intelligence.js`, `templates/ai_insights.html`, `tests/test_bank_statement_grounding.py`, `tests/test_user_data_browser.py`.
  TESTS: expected one-case preimplementation FAIL; **28 focused backend PASS**, **225 combined grounding/Travel backend PASS**, **five actual Chrome PASS**, zero skips; inclusive start/end, leap-day/same-day, originals/current mismatch, absent dates, explicit multi-record citations, cross-account/owner isolation, ambiguous unselected requests, stale catalogs/races, readonly financial state and no-history-save assertions included. The first Chrome probe had one new-fixture `Select` attribute error, retained and corrected with the existing Selenium API. JavaScript syntax, diff and desktop/mobile visual review PASS; AST-only graph refresh complete. Evidence: `artifacts/statement-period-1b54f28/` (`integration.json`, `chrome-final.json`, logs/browser captures). BLOCKERS: arbitrary PDF/OCR Q&A and independent document authenticity remain unaccepted; period correction cannot override conflicting retained boundaries. Counts recalculated unchanged **64/32/29/10/8 = 143**. NEXT TASK: use this clean commit for one integrated backend/Chrome/privacy/configuration gate and a fresh PyInstaller/ZIP/Inno build; verify exact embedded source, installer lifecycle, native AI and packaged period/classification HTTP/browser acceptance. Keep the owned isolated Vulkan server for those tests and stop it afterwards. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 12`.

- **VULKAN RUNTIME CHECKPOINT — 2026-10-23:** HEAD = this checkpoint commit (base `33003bc`). DONE: user authorized isolated unprivileged evaluation. Official Ollama **v0.40.9** base/AMD archives downloaded from the vendor GitHub release, matched published SHA-256 digests, checked safe extraction paths, and staged under `artifacts/vulkan-33003bc/runtime/`. Executable Authenticode **Valid / Ollama Inc.**, SHA-256 identical to the installed executable. The complete copy supplies the missing Vulkan backend: **RX6700XT / 12 GiB / 33 of 33 layers offloaded**, without driver changes. Four unchanged-adapter benchmarks PASS: cold short **11.985s** (load **9.841s**, prompt **1.947s**, generation **0.094s**); filesystem-warm short **6.532s**; memory **8.281/7.390s**, prompt **0.205/0.205s**, generation **0.780/0.763s**, **76.900/78.669 tokens/s**, versus CPU **25.079/25.500s**. Warm residency was not enabled; model digest/options, `keep_alive=0`, 30-second deadline and quality assertions unchanged. GPU memory wording differs from CPU; unchanged adapter checks and actual financial safety assertions, rather than exact prose equality, establish the tested scope.
  TESTS: unchanged exact-source **`0bb6930` package / 35 native checks PASS**, including the previously failing loan-document explicit abstention, injection/identifier exclusion, owner isolation, real embeddings, Chrome, offline-model outage/no-cloud behavior, restarts and synthetic restore. Application executable checksum/source unchanged; prior CPU failures preserved. Evidence: `artifacts/vulkan-33003bc/` (`base-provenance.json`, `rocm-provenance.json`, `runtime-provenance.json`, `benchmark.json`, native receipt/report/log, `rollback-readiness.json`). BLOCKERS: the deadline issue is resolved in this isolated vendor-runtime environment; the installed runtime remains unchanged/incomplete and no production adoption or independent-PC readiness is claimed. Owned Vulkan server remains running for the upcoming fresh-package gate; identity/path/start are in `server.json`; stop only that owned process tree at completion. No host PATH/startup, driver, model, residency, deadline, provider/history or master changes. Counts remain **64/32/29/10/8 = 143**. NEXT TASK: complete explicit reviewed statement-period Q&A end-to-end, then integrated focused/privacy checks and a fresh exact-source Windows package/installer/native acceptance. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 12`.

- **FINAL CONTINUOUS CHECKPOINT — 2026-10-23:** HEAD = commit containing this checkpoint; verified source **`8d8e3733be26873ec148845c2354210af6a28916`**. DONE: three milestones committed: `49311cc` (bounded CPU benchmarks/native blocker evidence and remediation), `08ecce4` (reviewed category/classification Q&A across owner-selected bank records/documents, existing UI/citations), `8d8e373` (request/response route-coordinate guards and legacy-cache isolation). Modified files alphabetically are recorded in the corresponding checkpoints below. TESTS: **133 grounding/backend PASS**, **86 Travel backend PASS**, **four actual Chrome PASS**, separate final **one no-history-save PASS**; earlier 22 focused tests overlap. Four real synthetic Ollama benchmarks PASS; packaged acceptance remains **FAIL after 12 passing checks**, at the subsequent loan-document inference deadline. No full suite was repeated; the prior 1,094 backend/72 Chrome evidence remains historical for its pinned source. Exact-source privacy at `8d8e373` PASS: **899 paths / 1,169 blobs / 82 commits / 52,773,551 bytes / one batch / zero findings** (`artifacts/route-shapes-08ecce4/privacy-source.json`). JavaScript syntax, diff/143-row counts, desktop/mobile review and final AST-only Graphify refresh PASS. No inference API cost for Graphify. Diagnostic failures remain separately retained.
  BLOCKERS/APPROVALS: local CPU-only loan-document generation still hits the unchanged 30-second deadline. A user decision was requested for a separate official Vulkan-capable runtime test; no approval has arrived and nothing was staged/installed. Driver/model/residency/timeout/cloud changes remain unauthorized. Independent-PC/normal-account/reboot/recovery acceptance remains unexecuted; currency/private-history/provider gates remain closed. All owned native/Ollama test processes stopped, ports released. Production/master/frozen candidates/private operator data/backups untouched. Counts recalculated unchanged **64 verified / 32 unaccepted / 29 partial / 10 missing / 5 approval / 3 external = 143**. The old package is still exactly `0bb6930`; new source features are **not packaged**. NEXT TASK: safe DOC-07 statement-period questions: inspect retained original statement start/end and current owner-review projections in `statement_evidence.py`/`hybrid_intelligence.py`, then implement only an exact, cited, fail-closed period answer with UI/regressions. Do not infer unknown periods from uploads or repeat completed label/date work. If runtime approval arrives, prioritize isolated GPU discovery/benchmarks and failed memory acceptance against the unchanged bundle. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 14`.

- **TRAVEL ROUTE VALIDATION CHECKPOINT — 2026-10-23:** HEAD = this checkpoint commit (base `08ecce4`). DONE: one coordinate guard now validates request and provider-response point shape, geographic bounds and finite optional elevation; malformed strings/dictionaries/oversized points cannot become plausible map coordinates. Routing cache schema advances to v2 so old accepted entries cannot bypass validation; historical snapshots stay preserved. Existing provider failure handling returns unavailable evidence without a LIVE route/cache write. Valid 3D input and explicit zero distance/time remain supported; motorcycle legality/closures stay UNKNOWN. Modified files alphabetically: `apps/mobility/services/travel/providers/routing.py`, `docs/PROJECT_STATUS.md`, `tests/test_travel_providers.py`.
  TESTS: preimplementation malformed-string reproduction FAIL as expected; final **86 Travel provider/planner/continuation backend PASS**, zero skips, including failed-response map/cache exclusion and legacy-cache preservation. The earlier 85-case run had one new-test exception-type expectation error (TypeError for null elevation), retained and corrected; no application bypass was added. Evidence: `artifacts/route-shapes-08ecce4/` (`reproduction.json`, `final.json`, diagnostic logs). No UI, currency arithmetic, provider settings or live calls changed. BLOCKERS: alternative-route generation/selection/scenic quality, endpoint/road-access verification and live provider quota/terms acceptance remain partial; native-AI runtime approval remains pending. Counts recalculated **64 verified / 32 unaccepted / 29 partial / 10 missing / 8 blocked = 143**. NEXT TASK: exact-source privacy check at this clean commit and final Graphify AST refresh; then continue the next safe DOC-07 reviewed statement-period question unit. Retain the unchanged `0bb6930` package for any approved GPU-runtime retry. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 20`.

- **DOC-07 CLASSIFICATION CHECKPOINT — 2026-10-23:** HEAD = this checkpoint commit (base `49311cc`). DONE: the existing assistant answers explicit category/classification questions for owner-reviewed bank transactions, canonical bank-record selections and up to three explicitly selected records from one statement. Current validated application labels and individual private citations come directly from revalidated evidence; no memory retrieval, model/cloud call, money calculation or conversation turn is used. Corrections require fresh review, original extraction stays unchanged, stale/foreign/missing/invalid/ambiguous sources fail closed. Existing date behavior remains covered; assistant guidance/feedback and desktop/mobile flows are complete. Modified files alphabetically: `apps/ml_engine/services/canonical_evidence.py`, `apps/ml_engine/services/hybrid_intelligence.py`, `docs/PROJECT_STATUS.md`, `static/js/intelligence.js`, `templates/ai_insights.html`, `tests/test_bank_statement_grounding.py`, `tests/test_user_data_browser.py`.
  TESTS: expected one-case preimplementation FAIL; **22 focused / 133 related backend PASS**, final **four actual Chrome PASS**, separate **one history/no-save PASS**, zero skips; overlapping counts are not summed. JavaScript syntax/diff checks and desktop/390px screenshot review PASS. The first Chrome attempt had three passing cases and one new-fixture wrong-ID error, retained separately and corrected. Evidence: `artifacts/transaction-labels-49311cc/` (`integration.json`, `chrome-final.json`, `history-final.json`, browser summaries/captures); Graphify AST-only refresh, no API cost. BLOCKERS: native CPU inference deadline/remediation approval above remains; arbitrary PDF/OCR knowledge, independent authenticity and real-account acceptance are not established. Counts recalculated unchanged **64/32/29/10/8 = 143**. Existing package stays pinned to `0bb6930` and does not contain this new source feature. NEXT TASK: inspect the safe TRAVEL-07 provider-backed alternative-route request/selection unit; preserve provenance, explicit route choices and unknown motorcycle legality, without live-provider activation. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 17`.

- **AI RUNTIME CHECKPOINT — 2026-10-23:** HEAD = this checkpoint commit (base `29255e2`). DONE: inspected Ollama **0.40.9**, Ryzen 5 3500X six cores, Radeon RX 6700 XT/Windows driver **32.0.21045.16010** (2026-10-16). Runtime still logs CPU-only/AMD-driver warning; installed CPU/CUDA backends, no Vulkan/ROCm backend. Four actual-adapter synthetic benchmarks PASS: cold short **13.851s** = **8.937s load + 4.675s prompt + 0.220s generation**; repeated short **12.908s**; memory **24.988/25.409s**, load **7.899/7.930s**, prompt **4.935/4.801s**, generation **12.145/12.668s**, **63 tokens / 5.187 and 4.973 tokens/s**. Warm means filesystem cache only; unchanged `keep_alive=0` unloads every call. Model/digest, `think=false`, context 8192, output cap 256, temperature zero, deadline and quality assertions unchanged. TESTS: unchanged `0bb6930` package retried, **FAIL after 12 passing native checks**: embeddings, owner isolation and packaged memory conversation PASS; later loan-document `/api/chat` HTTP500 at **29.97s** (prompt **5.88s**, completion censored). No package-specific defect proven. Evidence: `artifacts/ai-runtime-8e8af9355b/` benchmark/hardware/native/server/cleanup receipts. Owned server/children stopped and test ports released; operator settings/data/models untouched.
  BLOCKERS/APPROVAL: sustained packaged AI latency. [Official Windows guidance](https://docs.ollama.com/windows) recommends Vulkan fallback for RX6000; the [hardware list](https://docs.ollama.com/gpu) omits RX6700XT for Windows ROCm and enables Vulkan when installed. Inference: test a vendor Vulkan-capable runtime first; a driver-only fix and GPU performance remain unproven. Approval required to stage/test that official runtime/backend separately, preserving the existing installation/model/residency/deadline. Then verify GPU offload, repeat bounded benchmarks and failed packaged-memory acceptance. No driver/model/cloud/timeout/residency change authorized. Counts recalculated unchanged **64/32/29/10/8 = 143**. NEXT TASK: continue safe DOC-07 reviewed transaction-field questions while runtime approval is pending. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 14`.

- **WINDOWS INTEGRATION CHECKPOINT — 2026-10-23:** HEAD = commit containing this checkpoint (base `1caafbb`); session commits `0bb6930` (build tools), `d1d7ef6` (Windows acceptance/policy readiness), `1caafbb` (serialized browser composer). Modified files alphabetically: `docs/PROJECT_STATUS.md`, `tests/test_user_data_browser.py`. DONE: PyInstaller 6.22.3/Inno Setup 6.7.3 restored; fresh bundle/ZIP/installer under `artifacts/packaging-0bb6930/`; **20 packaged native**, **six installer lifecycle**, **six packaged CSV/correction HTTP** checks PASS. Four checksums and **10,392 bundle paths / zero private runtime paths** PASS (`integrity-final.json`); installer startup/shortcut state restored. Application bytes remain pinned to clean `0bb693022f1f4c1332a21885de5a5cab0b00ffec`; later changes are tests/tracker only and excluded by the package spec. No package relabeling or runtime behavior change.
  TESTS: Django 6.0.9 complete **1,094 backend PASS** at `0bb6930`; complete actual **72 Chrome PASS** at clean `1caafbb7b58487f3003ef7bab83bd1e105379023`, zero failures/errors/skips and source unchanged (`artifacts/packaging-0bb6930-chrome-composer-final/results.json` and labeled browser summary). Isolated system/drift PASS; exact-source privacy **899 paths / 1,157 blobs / 78 commits / 50,450,619 bytes / zero findings** (`privacy-composer-source.json`). Five tracker tests PASS (`tracker-final-checkpoint.log`). Five affected caller tests and one controlled three-second delayed-policy hybrid PASS separately; counts overlap. Earlier three complete Chrome FAIL runs and diagnostic harness failures remain preserved. Fixtures await terminal policy/composer completion and reuse the existing question helper; the erroneous disclosure experiment was removed before `1caafbb`. Graphify AST-only refresh completed, no API cost.
  BLOCKERS: full real-model packaged native attempts FAIL twice after 11 checks at the unchanged 30-second reasoning deadline; real embeddings/owner isolation passed, CPU-only/old AMD driver reported. Owned Ollama server/children stopped and test ports released. Counts remain **64 verified / 32 implemented-not-accepted / 29 partial / 10 missing / 8 blocked = 143**; independent-PC/normal-account/reboot/recovery acceptance unexecuted. Operator data, production/master/frozen candidates/backups untouched; AWS/paid OpenAI/cloud sync/private-history activation OFF; currency approval-gated. NEXT TASK: resolve the native-AI host/runtime decision with the operator, then rerun only failed packaged memory acceptance against the existing exact-source bundle; do not silently change deadline/model/driver. Independent-PC/normal-account/recovery acceptance needs the corresponding operator environment/approval. Skip approval-blocked work for the next safe roadmap unit; do not repeat passing gates unless affected code changes. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content docs/PROJECT_STATUS.md -Encoding UTF8 -TotalCount 11`.

- **Build-tool checkpoint — 2026-10-23:** HEAD = this checkpoint commit (base `6fe05b3`). DONE: installed the existing `requirements-build.txt` pins in the configured Python 3.12 environment: Django **6.0.9**, PyInstaller **6.22.3** and its build helpers; other application dependencies were already satisfied. Inno Setup **6.7.3** restored to `F:/ALFRED-tools/InnoSetup/ISCC.exe` in a fresh directory. Official release SHA-256 `9c73c3bae7ed48d44112a0f48e66742c00090bdb5bef71d9d3c056c66e97b732` and valid Pyrsys B.V. signature verified against the [vendor verification guidance](https://jrsoftware.org/isdl-verify.php) before execution; per-user silent installation exited zero. The initial combined command was policy-rejected; separated verification and installation succeeded without a bypass. Receipts: `artifacts/packaging-6fe05b3/`.
  TESTS: dependency installation/pip check PASS; five tracker tests PASS, zero skips. Existing source evidence remains 1,094 backend/72 Chrome at `8c18a5b`, not newly claimed for the changed Django environment. BLOCKERS: no build-tool blocker; fresh bundle/native/installer acceptance pending. NEXT TASK: build a new exact-source PyInstaller bundle using isolated environment/storage and fresh output directories, revalidate backend/security/migrations for Django 6.0.9, then execute synthetic packaged/native acceptance. Counts **64/143** unchanged; production/master/frozen candidates/private data/backups and provider/history approvals remain untouched. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status -sb; Get-Content docs/PROJECT_STATUS.md -TotalCount 10`.

- **FINAL SESSION CHECKPOINT — 2026-10-23:** HEAD = commit containing this checkpoint; tested source **`8c18a5bb5385352b67a5f14c772fa02b96d9b38a`**. DONE: five milestones in `6c60887` (owner corrections/import identity), `3a289a6` (import parent/source guards), `4414b26` (bank-snapshot correction safety), `1e868cd` (private exact-value CSV/UI/download), `8c18a5b` (preserved source-scan batching completed). Memory multi-case evaluation was already complete and was not restarted. TESTS: complete existing house backend **1,094 PASS**, complete actual Chrome **72 PASS**, zero failures/errors/skips; both receipts confirm source unchanged. Exact-source privacy **899 paths / 1,151 blobs / 74 commits / 48,142,537 bytes / one batch / zero findings**. Isolated system/migration-drift PASS; earlier focused/tracker checks overlap and are not summed. Receipts: `artifacts/consolidation-20261017/continuous-8c18a5b-backend/` and `continuous-8c18a5b-chrome/`; feature details/focused regressions below. This is source acceptance, not fresh packaged/installer/normal-account/independent-PC acceptance.
  BLOCKERS: PyInstaller is absent from the configured Python environment, and Inno Setup was not found on PATH or its standard installation paths; no new package was built and old/frozen packages were not relabeled. Currency/provider/private-history approvals and independent recovery/product acceptance remain outstanding. Latest user forbids master/production/frozen changes, live-data access and backup deletion; AWS/paid OpenAI/cloud sync/history activation remain OFF. NEXT TASK: restore the established isolated Windows build prerequisites, build a fresh package from the pinned clean source into a new output folder, then run its synthetic packaged/native acceptance; preserve all existing packages/backups. If build tooling requires operator setup, continue another safe partial roadmap unit without changing currency or provider approvals. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status --short; git log -6 --oneline; Get-Content docs/PROJECT_STATUS.md -TotalCount 10`. FEATURES: **64 completed / 143**; these bounded FIN-13 additions do not complete general financial portability. Graphify AST-only updates completed after each code milestone; no model/API cost. This closing tracker-only commit does not replace the tested source SHA.

- **Checkpoint 5 — 2026-10-23:** HEAD = this checkpoint commit (base `1e868cd`). DONE: reviewed and verified the two preserved source-privacy files, retaining their bounded deterministic Git-blob batches, 128 MiB total/64 MiB response bounds, one shared body-scan deadline, exact framing checks and fail-closed reset of prior evidence. All historical aliases/removed secrets remain scanned; fixture exemptions are unchanged. TESTS: `source-scan-focused` **89 PASS**, zero skips (privacy, release gates/promotion/rehearsal and browser runner); includes later-batch secrets/errors/timeouts, malformed/truncated/trailing frames, exact boundaries, alias exemptions, work caps and expired scans. Actual read-only pinned history scan at `1e868cd`: **899 paths / 1,148 blobs / 73 commits / 47,628,999 bytes / one batch / zero findings**; multiple batches were exercised with synthetic bounds, not claimed for this measured repository. Earlier current-source unit evidence remains **186 backend + two Chrome PASS**, plus **five tracker PASS**, zero skips; counts overlap. BLOCKERS: fresh broad/backend Chrome and exact-source package acceptance still pending; latest user forbids master/production/frozen changes, live-data access and provider/history activation. NEXT TASK: freeze this clean checkpoint, run the existing complete local backend/Chrome scopes once with durable receipts, fix only reproduced failures, and retain all nonlocal acceptance limits. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status --short; git log -5 --oneline`. Five milestones complete; **64/143** unchanged.

- **Checkpoint 4 — 2026-10-23:** HEAD = this checkpoint commit (base `4414b26`; prior session commits `6c60887`, `3a289a6`, `4414b26`). DONE: four verified units — preserve owner corrections/import identity; protect imported account/source linkage; guard current bank snapshots; owner-only streaming expense CSV at `/api/expenses/export/` and **Export all (CSV)** in the existing UI. CSV retains exact Decimal cents/null/zero, escapes spreadsheet formula prefixes, omits account numbers/raw text/document paths and uses private/no-store responses. No currency is inferred. New regressions join the existing house backend scope; only that one-line runner change is committed, preserving its pre-existing privacy edits and uncommitted tests.
  TESTS: `artifacts/consolidation-20261017/corrections-20261023/`: `export-focused` **28 PASS**; final `integration-backend` **186 PASS**, final `integration-browser` **two actual Chrome PASS**, all zero skips; isolated system/migration-drift and diff checks PASS. Focused counts overlap and are not summed. The actual CSV download and note edit/account-snapshot flow passed; desktop screenshot inspected. BLOCKERS: broad backend/Chrome, fresh exact-source package, normal-account/independent recovery acceptance remain pending; pre-existing release-validation edits remain uncommitted. Latest user forbids master/production/frozen changes; all provider/history flags remain OFF. NEXT TASK: finish/review the preserved release-validation privacy-scan work and its targeted tests, then freeze a clean source for the pending full integration gate; skip approval-blocked currency, provider and production work. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status --short; git log -4 --oneline`. Counts remain **64/143**; FIN-13 is partial because this is an expense register export, not comprehensive financial portability.

- **Checkpoint 3 — 2026-10-23:** HEAD = this checkpoint commit (base `3a289a6`). DONE: expense PATCH updates the bank snapshot only for a changed, explicit closing balance on the latest balance-bearing transaction (date, then ID). Ordinary corrections, resubmitted unchanged balances, nulls and historical rows preserve the account snapshot; exact cents/zero and atomic rollback retained. TESTS: `balance-reproduction` reproduced six failing assertions; `balance-final` **46 backend PASS**, zero skips, including synthetic financial/UI-API invariance. BLOCKERS: broad/package acceptance remains pending; existing release-validation edits preserved. NEXT TASK: owner-only exact-value expense CSV download in the existing Expense UI, then focused integration/browser checks. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status --short; git log -1 --oneline`. Counts **64/143**; no ledger reconstruction or currency change.

- **Checkpoint 2 — 2026-10-23:** HEAD = this checkpoint commit (base `6c60887`). DONE: imported expense corrections reject account reassignment/removal and source relabeling before mutation; same-parent edits and owner-scoped manual moves remain supported. TESTS: `parent-reproduction` FAIL as expected; `parent-final` **65 backend PASS**, zero skips, including statement/canonical evidence and bank grounding. BLOCKERS: unchanged release/provider/currency acceptance; pre-existing release-validation edits excluded. NEXT TASK: prevent unrelated/historical expense corrections from overwriting the current bank balance. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status --short; git log -1 --oneline`. Counts **64/143**.

- **Current session checkpoint — 2026-10-23:** HEAD = commit containing this checkpoint (base `366488b`). DONE: FIN-13 partial corrections preserve omitted owner classifications/labels, raw import text and transaction identity; explicit label clearing works. TESTS: `corrections-20261023/omitted-reproduction` reproduced three failures; `omitted-final` **44 backend PASS**, zero skips (correction, money/identity, baseline and statement evidence). BLOCKERS: existing broad/package acceptance remains pending; two pre-existing release-validation edits preserved; latest user forbids master/production changes. NEXT TASK: reject imported-transaction parent/source relinking, then prevent unrelated corrections from overwriting bank balances. RESUME COMMAND: `Set-Location F:\ALFRED_DEV\post-audit; git status --short; git log -1 --oneline`. Memory multi-case/cohort UI work was already complete and was not restarted. Counts remain **64/143**; no currency/provider/history activation.

- Prior consolidation checkpoint: **8d1a77e3d6b1ca215351fef0e43601292cfa3af8** before the 2026-10-23 repairs below; current development is recorded in the checkpoints above. Functional packaged runtime remains **8fdd0fc62494a3e8ccabb35248d78c4bbf0850e7**. COUNCIL-04, source-pinned CI, operator reconciliation, cache metadata, HTTP permission status and migration-fixture repairs are committed. Source-native **34 PASS** and packaged **35 PASS**. Complete backend and Chrome runs finished with failures; no new full gate/package acceptance is claimed. Do not repeat completed repairs or label focused/running/interrupted gates a complete PASS.
- Development: `F:/ALFRED_DEV/post-audit`, branch `development/alfred-integrated`.
- Consolidation base: `fb28846552122da2d0014f802eaf7c5dc5267179`. Latest verified runtime **`98a3c89bdbdd516a48a55b213a61a473c91811ee`** (reviewed bank transaction-date answers), retaining exact question forms d18d1d1 and all completed provenance, source-selection, Memory and Council work below. Final exact-source gate: **133 backend + 1 Chrome PASS**, separate **one real local Ollama compatibility PASS**, zero final failures/skips. Source/privacy, system/drift, synthetic financial invariance and desktop/mobile screenshots PASS. Normal Graphify AST-only refresh now PASS; earlier policy blocks remain historical evidence. No new native/package/release acceptance. Counts overlap and are not added. Discover actual HEAD with `git rev-parse HEAD`; closing tracker-only commits do not replace tested source SHAs.
- Completed commits: `8a76870` (one active matrix/checkpoint), `305b81a` (integrated gate/native fixture), `4173191` (investment originals/review), `57621f2` (assistant citations/races), `77e8162` (bounded upload/error/UI correction), `bd2232a` (loan originals/owner field review), `845cc32` (canonical loan-field citations/races), `449a19c` (applied-payment references), `0a72660` (signed source catalog/selection), `1116cad` (paged picker/exact citations/backward cursor), `d04a7cc` (domain-bound questions/real-local selection), `f03ee6d` (multi-case evaluation), `07b207c` (Memory UI/cohort citations), `c56a063` (shared deadlines/real-local cohort), `cd64443` (failed-evaluation session expiry), `9356ad9` (owner-indexed model context), `1de0143` (reviewed quality/model comparisons), `2a0aae7` (Council core), `bbb03dd` (verified Council UI task), `5e365d0` (blocked-advice reporting/budgets), `33b00d4` (combined-gate checkpoint), `00aca63` (structured local advice/safe diagnostics). No other development checkout remains active.
- All 23 local branch tips are ancestors of development, including M20 0052410 and every named M14/M15, audit, FIN-MONEY, history and grounding branch; no duplicate merge/cherry-pick is needed. The only unique remote commit, 357360e on `origin/agent/browser-regression-maturity-gate`, adds obsolete AWS-only AGENTS instructions, not browser implementation. It is deliberately excluded; its history is preserved.
- Primary/master and fetched `origin/master` remain `3932f391aa4eed7b3200ad3b034f7991435e01e4`. Latest user forbids master/production changes, production restart, live-data access and frozen-candidate modifications; earlier conditional master authorization is superseded. Seven operator changes remain preserved. This session uses only the existing development worktree and isolated synthetic data; primary tracked source/private runtime remain unchanged.
- Frozen tested candidate `release/post-audit-runtime-20261016` = `4aa7ac70fa27c1410e695470af5c3987235244b1` remains unchanged. The integrated branch is newer development, not a replacement frozen package or deployment approval.
- AWS retired permanently; paid OpenAI, real cloud synchronization and private conversation-history activation OFF. No cancelled key dialogs or key export. M15's device-loss waiver is not inherited.
- FIN-CURRENCY C1–C10 below remain the unapproved design contract; no schema/backfill/FX/inferred INR. Preserve exact Decimal values, raw import evidence, fingerprints, owner/parent linkage and guarded rollback.
- Document/filter/question Councils 696c858d48945a8f / 194ba73f8aeeddfe / faf7449750df0154 / d4aea2d0484afc58 / 1f7f380994e26e91 / 3461f90aeab752ca / e0405cf5a302cee6 and bank-date Council **74ed3d42f57b6d0c COMPLETE**. All retain actual independent Reviewer/Security and exact source/test/commit evidence. Bounded metadata, field and date questions are complete; full DOC-06/07 remain partial. COUNCIL-04 retention is complete at 97ed191; finish current consolidation/release validation and operator reconciliation before the scoped financial-correction regression. Do not rebuild Council or repeat completed grounding.
- Council extension **f649da661dcf60a04bfcd188300e8c841423ab1a COMPLETE locally**: bootstrap **686c7d593e9bda26 COMPLETE**, actual independent review/security and **75 backend PASS**, source/privacy PASS. New v3 tasks have seven operator roles, source-bound Architect and durable M20-backed Release Guardian; **faf7449750df0154** actually exercised all seven for b0bc54a. Historical evidence remains unchanged. No full product/release/usage-accuracy claim. Continue the existing assistant UI under this workflow; do not rebuild Council again.

Safe resume:

```powershell
Set-Location F:\ALFRED_DEV\post-audit
git status --short
git branch --show-current
git rev-parse HEAD
Get-Content docs/PROJECT_STATUS.md -TotalCount 145
```

### Consolidation gate repair — 2026-10-23

Resumed clean **8d1a77e3d6b1ca215351fef0e43601292cfa3af8**. The durable complete backend run at 8fdd0fc finished **1,599 tests / two failures / two errors / 81 skips**; the loan-bound full Chrome rerun finished **71 tests / three errors / zero skips**. Both remain FAIL evidence, not release acceptance. No primary master integration or push occurred.

Confirmed repairs reuse existing infrastructure. The combined expense/investment rehearsal fixture now also rewinds Mobility to 0012, because its 0013 conversion requires expenses/0005. The actual rehearsal then reproduced the private-storage guard: it created retained database copies before securing their fresh output directory. `scripts/rehearse_money_migrations.py` now protects the newly created output, shadow, runtime and backup before use, retaining source-byte invariance, no-overwrite, exact reconciliation and guarded rollback. It never repairs existing source/production permissions. The Windows setup lock fixture protects its empty disposable directory before writing retained sentinels. The audit test now validates all 143 unique IDs, current statuses and local links in this authoritative tracker against the preserved historical ID inventory, rather than requiring deleted duplicate Markdown trackers or current paths in immutable historical JSON.

`consolidation-rehearsal-storage-final-20261023`: **19 backend PASS**, zero failures/errors/skips, Django 6.0.9; includes actual synthetic forward/repeat/reverse migration, independent local restoration and owner-private output checks, Windows locks/no-overwrite and storage guards. Python AST **592 PASS**. Earlier eight-test PASS overlaps; the 35-test follow-up retained its pre-runtime-fix rehearsal failure while the other 34 tests passed, including Expense/User migration and storage scopes. One User migration mixed-plan error from the complete run did not reproduce in either focused migration run; no speculative production or migration change is claimed. Keep it visible and inspect the complete rerun's retained sequence evidence if it recurs.

The three-case browser diagnosis passed hybrid insights and loan fields but reproduced a mobile navigation `ElementClickInterceptedException`. The helper now retries only intercepted real WebDriver clicks within its existing 20-second wait, stopping after the first successful click. No forced JavaScript click, application timeout, assertion, financial value or security guard is changed. A separate one-case mobile run passed before this repair. The final repaired three-case run completed with mobile navigation and loan provenance PASS, but one hybrid-insights timeout waiting for verified-memory save (two PASS / one error / no skips). This independent timeout remains a release blocker under diagnosis, not a green browser gate. Actual independent `quality_review` inspected all five changed source/test files: no blocking correctness/security findings; static review only, not independently executed tests.

The changes since packaged runtime 8fdd0fc affect the rehearsal CLI, tests and this tracker; packaging/ALFRED.spec excludes the rehearsal CLI and tests. No new application implementation, dependency or migration is introduced. The earlier package SHA and its exact source remain separately identified; no substitute packaged SHA or fresh-PC/installer acceptance is claimed. Counts remain **64 complete / 32 unaccepted / 29 partial / 10 missing / five approval / three external = 143**. Primary/master, private data, backups, frozen4aa7ac70 and provider/history activation are unchanged.

Rehearsal/fixture repair committed **aa5f9590600dae8a6e499dcaad1847daf9a6b0d1**. Next: diagnose the remaining verified-memory browser save timeout, run the final complete backend/Chrome gates and exact-source privacy/system/drift checks, then perform the already authorized ordinary master reconciliation/fast-forward/push only if critical gates pass. No app start, live migration, key/ACL repair or production deployment is authorized. Safe resume uses the commands above and receipts under `artifacts/consolidation-20261017`; never restart the audit or completed feature milestones.

Polling closure: **2231921f4555eca15efe0f981e0e1765ce21aa1c** commits the bounded real-click helper. The separate memory-save diagnosis retained a screenshot showing actual safe **429** responses with verified checkbox and unsent memory intact. Cause: `ai_insights.js` used the shared one-second default to poll the expensive personal-insights GET, consuming its unchanged 30/hour quota while the owner used the conversation. The narrow runtime correction uses the existing per-caller `intervalMs: 300000`; other polling and all server limits/auth/consent remain unchanged. Manual questions, source revalidation and explicit memory writes stay independent. Passive financial-pattern cards may be five minutes stale; multiple tabs/reloads still share quotas.

`consolidation-insights-polling-backend-20261023`: **33 backend PASS**, no failures/errors/skips, Django 6.0.9, including served frontend contracts, actual quota rejection/atomicity and owner memory/privacy controls. The deterministic contract budgets twelve polls plus two initial requests per hour, at most half the default expensive allowance. `consolidation-insights-polling-browser-20261023`: **three actual Chrome PASS**, no skips, including verified-memory save, mobile outage/retry and loan provenance. Actual independent `council_release_review` inspected the real callers, quota code, screenshot and two-file diff: no blocking correctness/security findings; review did not independently execute tests. Earlier failing receipts remain FAIL. The 2231921 broad run was stopped only in its verified disposable test process tree because source changed during validation; retained receipt is **BLOCKED/source_changed_during_validation**, never PASS. No production process was stopped.

Freeze the ordinary closing commit and re-run complete backend/Chrome and exact-source privacy/system/drift checks. Unlike the preceding test-only repairs, this static runtime change requires a new exact-source package and packaged acceptance; 8fdd0fc remains historical package evidence, not the updated candidate. Do not change source during these runs. All production/master/private data/frozen refs, backups, provider/history flags and 143-feature counts remain unchanged. The authorized master source merge/push remains pending passing critical gates; it does not authorize service startup or live schema application.

### Consolidation repair continuation — 2026-10-22

Current committed development is **a7c0a0f7f8a9c929d76806a8e5b2d570be812bf8**, retaining COUNCIL-04 97ed191, reviewed-source CI c3614eb and privacy-reviewed operator reconciliation 78c2058. Primary/master remains 3932f391 with its seven original operator files unchanged; no merge/push/deployment has occurred. The durable broad backend run timed out at 1,184 recorded tests, 10 errors / five failures / 18 skips; its progress is incomplete, not a final suite count or PASS. Chrome completed **71 tests / one error / zero skips**. All failure evidence remains under `artifacts/consolidation-20261017/`.

Confirmed repairs in progress:

- Cache registry and traffic exercise still used `financial-baseline` after the canonical display cache was versioned. Three references now use `financial-baseline-display-v1`; the existing source/telemetry tests reproduced the failure, and an added assertion rejects an old-name proof. `consolidation-cache-registry-final-20261022`: **36 backend PASS**, zero errors/failures/skips, Django 6.0.9, including retention and canonical financial invariance.
- The bank-outage browser fixture sent an arbitrary unsupported question; the completed intent guard correctly abstained before inference. Use the already supported statement-record explanation to exercise outage/draft/revocation, retaining all assertions. `consolidation-bank-outage-browser-20261022`: **one actual Chrome PASS**, zero skips. This repairs a fixture, not private inference permissions or arbitrary-PDF support.
- Expense migration tests requested expenses/0004 and mobility/0013, although mobility/0013 depends on expenses/0005. Rewind the synthetic test frontier to mobility/0012 as well, preserving current leaves for upgrade/cleanup and the same targets for alias rollback. No migration file, snapshot or historical monetary value is changed. Actual independent `quality_review` confirmed this dependency conflict and narrow repair.
- Multipart middleware converted Django PermissionDenied into a generic 500, reproducing actual HTTP 500 versus required 403 on the superuser-only career outcome route. The repair preserves a generic safe 403 without returning exception contents. Existing endpoint plus a sensitive-message regression cover it. Legacy job-HTTP tests are updated to the centralized safe transport and generic redacted API contract; no public-network safeguards are relaxed.
- Two upload assertions failed only in the broad run and pass in the isolated reproduction. Their fixtures now use fresh owner-protected persistent throttle directories per test, following the existing global-abuse fixture; limits and independent abuse tests remain enabled. Django locmem clearing does not reset disk-backed quotas and was removed before acceptance. An exact historical 429 cause is not asserted without response evidence.

Actual independent `quality_review` accepted the cache, historical migration frontier and supported browser question repairs with no remaining actionable correctness/security issue. The cache and browser scopes are verified above; final HTTP/security/privacy/alias-migration execution and separate middleware review remain pending. The a7c0a0f build was explicitly stopped after confirmed source regressions; its incomplete artifacts are preserved with BLOCKED receipt, never accepted as a package. No new package, final broad PASS, real-account acceptance or release readiness is claimed. Feature counts stay **64 complete / 79 not fully verified (143 total)**; no feature-count increase for test repairs.

## Current execution and validation

1. COMPLETE: all completed source was already integrated by ancestry. Eight obsolete checkouts removed with ordinary non-force Git operations after preserving and SHA-256 verifying 15,144 ignored/untracked payloads. Preservation manifests and owner/SYSTEM/admin-protected payloads are under `artifacts/consolidation-20261017/preserved-worktrees/`. The only registered worktrees are production (untouched) and this development checkout; all branches/frozen refs remain.
2. COMPLETE: integrated house gate **911 backend / 53 Chrome PASS**, zero failures/skips; system/migration drift and source privacy PASS (869 paths/826 blobs, zero findings). Actual **34 source-native/Ollama checks PASS**, zero failed checks, after the synthetic fixture correction below. Evidence: `combined-before-provenance`, `chrome-before-provenance`, `integrated-source-checks`, `native-corrected-fixture` under the consolidation evidence root. These certify integrated runtime source fb288465 plus the stated test-harness correction, not future implementation or a new packaged release.
3. COMPLETE locally in bounded scopes: financial/document provenance, source selection, multi-case evaluation, reviewed development/held-out quality gates and source-bound host-mediated Development Council cycles. Legacy installed embedding reference remains **REJECT** on development; experimental protocol is eligible for review on measured development and independent held-out partitions only. All six roles passed the completed scoped cycles; exact v2 actor attribution and source/commit/test evidence are recorded below. Initial BLOCKED advice remains evidence; later local signals/proposals are advisory only, never role approval, private training or activation.
4. Commit each verified unit and update this file. No new status/audit/roadmap/checkpoint/prompt Markdown files. Historical continuation/audit/release reports remain evidence, not alternate active instructions.

Current consolidation evidence: `artifacts/consolidation-20261017/` (ignored local machine-readable receipts, not source or private-provider uploads).

### COUNCIL-04 retained review decisions — 2026-10-20

Existing v3 Council **7d16cda585ffafc1**, base **76326fad46a60398f76c38d78f6fe7922953cf29**, pins only `scripts/development_council.py`, its existing contract tests and this tracker. Reuse all seven roles, isolated test runner, local optional advisor, source/commit Guardian and host-only implementation/Git boundary. No competing service or scheduler. Planner selects this recorded safe task; actual Codex-host tools implement it.

Two new synthetic regressions first reproduced lost host review history and an identical PASS resetting a passed task (`council-review-history-reproduction`: one error/one failure). Decisions now append safe source/role/provider/actor/status/reason-code/time metadata to the existing task JSON, surviving source repairs and restarts without satisfying current approvals. Exact current duplicate verdicts preserve stage, Tester evidence, attempts and model reservations; the ordinary transactional revision may still advance. Maximum 64 accepted decisions; attempted distinct overflow permanently blocks this task, its tests and commit verification while retaining all prior evidence. No silent trimming or history/approval reconstruction. Legacy absence displays NOT_RECORDED. Existing local HTML exposes escaped history; CLI `--reason-code` uses the existing bounded code contract, and FAIL/BLOCKED exits are nonzero. No raw review prose, model payloads or private content are retained.

Initial focused **41 backend PASS**, but actual independent `doc_discovery_review` found a P2: duplicate/overflow paths preceded same-source Reviewer independence validation after the Coder actor changed. Existing final approval checks still blocked acceptance; the API could falsely accept a duplicate verdict or consume the cap on an invalid request. The real FAIL/reason/source is retained in this task's new history, not relabeled. `council-review-independence-reproduction` preserved the failing regression. Independence validation now precedes both shortcuts and deliberately ignores stale prior-source actors after a source change. Repaired **42 tests PASS** on the configured SDK's Django 6.0.8; this is compatibility evidence, not the pinned dependency gate.

Final independent `council_release_review` found a second P2: cap overflow persisted BLOCKED then raised before CLI HTML refresh, leaving an old ready-to-commit page. `council-overflow-html-reproduction`: **one expected failing regression**, Django **6.0.9**. The CLI now refreshes the existing guarded status output only for that durable cap error, then re-raises with nonzero exit. `council-overflow-html-repaired`: **43 backend PASS**, zero failures/errors/skips, Django **6.0.9**; no thresholds or security checks weakened. Actual independent repaired-code correctness/security review found no remaining actionable issue; final three-file binding, Council Tester/Guardian and ordinary commit are still pending. `council-history-status-chrome`: **one actual Chrome PASS**, retained real FAIL/reason/source and current pending roles shown, desktop/390px layout; the browser does not invent approval. No paid/advisory call. Tests overlap the earlier runs and are not summed.

No application, finance, schema/dependency, provider/history activation or private data changes. Host account cost/usage remains unobservable; optional local advisory usage is zero for this unit. Counts remain **64 verified / 79 remaining**, Council overall partial. Latest user order is now consolidation/release validation before resuming the scoped expense correction below.

Master-consolidation preparation: `artifacts/consolidation-20261017/master-consolidation-20261020/` retains owner/SYSTEM-protected, SHA-256-verified copies of seven primary operator files and three development WIP files plus their patches. All 29 local/remote refs are inventoried; only the AWS-only remote commit is not contained. `cleanup.json` records **469 untracked bytecode files removed / 5,378,455 bytes**, no links followed, no tracked files or backup/data/media/key/package/history deletion. `retention-inventory.json` retains 80 other root entries; uncertain/protected deletions require review/approval. Both registered worktrees and frozen 4aa7ac70 remain intact. The console size-summary command initially failed after writing the deletion manifest; re-reading that manifest independently established the totals above.

Manual test-setup diagnosis: raw pytest has no configured Django plugin/settings; an unisolated manage.py invocation falls back to source/private storage and is correctly refused by the ACL guard. Use the existing sanitized `scripts.release_validation.environment()` with a fresh disposable runtime, explicit SQLite/media/registry and temporary signing key. No ACL bypass or live permission repair. Development `.venv` is not a junction; its documented `read_only_baseline.pth` shares installed libraries from the main SDK, while local Django is pinned 6.0.9. Configured PyCharm SDK has Django 6.0.8 and no pytest; no production package was installed/changed. Focused final validation explicitly prepends development site-packages for child tests and asserts 6.0.9. This shared-library setup is not clean-machine acceptance.

`master-consolidation-full-backend` was interrupted without a completion/count receipt and no matching worker remains: **BLOCKED/incomplete**, never PASS. Its runtime used SDK Django 6.0.8, so final broad validation must use the pinned development package path. Initial isolated system/drift passed on that SDK; rerun on 6.0.9. Final complete backend/Chrome/native/package/privacy gates and seven operator-file reconciliation remain pending; master merge/push has not occurred. Keep all failure/interruption evidence. No new source migration in this Council unit; integration since M15 includes seven already implemented Decimal/provenance migrations plus reviewed dependency changes, so do not claim the entire release has no migrations. Next: finish this Council checkpoint, then pinned comprehensive checks and operator reconciliation; if any critical gate fails, stop master promotion and record the exact blocker here.

Postcommit COUNCIL-04 closure: **97ed191c82620f067c8f31c8b908144c652ebc69**, task **7d16cda585ffafc1 COMPLETE**, all seven roles PASS. Actual independent `council_release_review` accepted the repaired final three-file fingerprint **75459e91f25f020c02614e8f116262314253f34025d3749031d8c7baf96f0e48**. Existing Council Tester **82 PASS**, zero failures/skips, on SDK Django 6.0.8 (compatibility); the separate final repair run above used pinned 6.0.9. Release Guardian source/privacy PASS: 892 paths / 849 blobs / one commit, six reviewed synthetic identifiers, zero findings. This is a development checkpoint, not operational deployment approval. No Council rebuild is pending.

Cache repair committed **81c6446d0efe1e9a32155134d98addef6630cac8**, with actual independent review and the recorded 36-test PASS. Browser outage fixture is verified by its one-case Chrome PASS and independent review; it preserves the current source allowlist and all failure/draft/revocation assertions.

HTTP repair closure: `consolidation-quota-isolation-final-20261022` **39 backend PASS**, zero errors/failures/skips, pinned Django 6.0.9. Includes actual 201→429/count-one enforcement, safe PermissionDenied403, non-superuser no-write behavior, upload retention/cleanup and global-abuse isolation. Actual independent `council_release_review` reviewed the final four-file hashes and shared guards: correctness/security PASS, no remaining scoped finding. The old public-job parser fixture now uses the centralized transport; its current unsafe URL/redirect/TLS contracts remain exercised by existing tests. Broader HTTP/alias-migration gate is still running with no recorded failures. Browser fixture committed **378f8ac43d3a4251e946411051ad276953c68f12**; in-memory Python compilation **592 PASS**, JavaScript syntax **28 PASS**.

Historical migration fixture closure: `consolidation-http-migration-repaired-20261022` **84 backend PASS**, zero errors/failures/skips, Django 6.0.9. Covers all seven Expense Decimal migration tests (original-value reconciliation, unchanged ownership/fingerprints/transfers, invalid-value atomic abort, repeat/guarded rollback and separate database alias), safe HTTP transport, multipart resource limits, privacy retention, session/CSRF and abuse limits. Actual independent `quality_review` accepted the historical frontier repair; no migration or canonical-money code changed. This overlaps the 39-test final quota run and is not summed. HTTP repair committed **993a5b19a11d6345db7ea67c2c246b28a0e930da**. The earlier nine-test diagnosis intentionally retains two pre-repair HTTP failures while its seven migration cases passed; it is not relabeled as a green suite.

Final-source evidence: runtime frozen at **8fdd0fc62494a3e8ccabb35248d78c4bbf0850e7** after the test-frontier commit. Fresh system/migration drift PASS. Source/ancestry/dependency/migration/privacy preflight PASS: **907 paths / 1,553 blobs / 113 commits**, ten reviewed synthetic identifiers and zero findings. Native **8ce4322a8d: 34 checks PASS**. Fresh portable build inspected **10,408 files** with Django 6.0.9 / PyInstaller 6.22.3 and installed no packages; executable SHA-256 **9f35cb5c2b439d6c646a7b65c26e8787936585e1ebbf6f6f06322e844d4686b7**. Actual packaged **2b824e7632: 35 checks PASS**, including launcher, seven embedded Chrome flows, real local Ollama, disabled providers/history, ownership/encryption, worker/scheduler, restart and synthetic SQLite/vault/queue restore. Distinct source/executable reports are copied into their dated evidence folders; an initially selected source report was retained as `source-native-reference.json`, and the packaged proof is the actual `native_exe_verification.json` copy. Frozen 4aa7ac70 and its dated proof remain unchanged. Packaged desktop assistant/dashboard and 390px screenshots reviewed PASS; no fresh-PC, installer, real-account or device-loss claim.

Full Chrome rerun completed **71 / two errors / zero skips**: inferred-loan confirmation and real PDF reimport. Inferred-loan passed in isolation. PDF diagnosis reproduced a 20-second UI wait expiring while a real import request remained active; the application parser contract permits 90 seconds. The test now waits for upload completion within the existing configured parser bound plus ten seconds, then asserts the exact parsed-record count; teardown drains actual live-server requests within that same bound before database flush. Application budgets, raw exception filtering, exact amounts and deduplication assertions remain unchanged. `consolidation-loan-processing-bound-20261022`: **two actual Chrome PASS**, zero errors/skips; actual independent `quality_review` accepted the test-only diff. Complete Chrome rerun remains required. Diagnostic failures, including secondary cleanup errors, remain preserved and are not relabeled as application successes.

Final complete backend is running under `consolidation-all-final-8fdd0fc-20261022`, with an explicit 3,600-second local harness cap and durable per-test progress; only COMPLETE plus a final receipt is acceptance. Ordinary focused runs retain their original bounds. No final count is claimed until completion. The source/package runtime remains 8fdd0fc; this follow-up changes only browser acceptance and this tracker, so it is not a silently substituted packaged SHA. All original primary operator hashes and three private DB/WAL/SHM metadata records still match preservation (no private DB content read). Fetched remote master and primary remain3932f391; no production server/worker process or port8000 listener was observed. No restart, migration, master merge or push occurred. Branch metadata reports master unprotected; detailed protection API returned403 for the integration, and ordinary Git must still honor server enforcement.

### Master consolidation release gates — 2026-10-21

The previous `master-consolidation-pinned-backend` and `master-consolidation-pinned-chrome` sessions also ended without completion receipts; no matching test process remained on resumption. Mark both **BLOCKED/interrupted**, with no invented test counts. `master-consolidation-pinned-schema` system/drift PASS and `candidate-source-privacy.json` remain valid for 97ed191: 903 paths / 1,526 blobs / 106 commits, ten reviewed synthetic identifiers and zero findings. Existing operator originals and merge previews remain preserved outside tracked source.

CI's real preflight was reproduced against 3932f391 → 97ed191: **FAIL** for undeclared dependencies/migrations. The integration has seven reviewed Decimal/provenance migrations and two dependency files; no migration is applied by source validation. The scoped repair extends the existing release gate with an explicit full `--reviewed-source` SHA. It derives only baseline-to-reviewed dependency/migration expectations, compares literal paths and complete Git diff contents against the candidate, persists the pin across later checks, and grants no inherited allowance when a later baseline already contains the review. New paths, modified approved contents, mixed policies and divergent/short pins fail closed. CI uses the pinned declaration; deployment/recovery approval remains independent.

Actual independent review found quoted-path/pathspec and rename-detection gaps in the comparison; NUL-delimited literal paths and `--no-renames` classification repair them with synthetic regressions. Focused release/Council/promotion/acceptance suite **110 PASS**; literal-path follow-up **33 PASS**; final rename and persisted-policy CLI follow-up **2 PASS**, all Django 6.0.9 with zero failures/skips. These overlapping scopes are not summed. Native run **04a33d9b5b: 34 checks PASS**, including actual local Ollama, seven embedded Chrome flows, owner isolation, worker/scheduler, restart, encrypted-vault and synthetic SQLite/upload/queue recovery; proof copied to `consolidation-native-20261021/native-proof.json`. Test names containing packaged are shared assertions, not evidence of a new executable build. The broad backend/Chrome processes were interrupted again without final receipts; retain them as incomplete. Resumed runs use hidden bounded processes with persistent diagnostic progress at `consolidation-backend-durable-20261021` and `consolidation-chrome-durable-20261021`, plus launch receipts in `master-consolidation-20261020`. Only COMPLETE receipts count as final acceptance. Actual independent `council_release_review` rechecked the final four-file diff and test receipts: correctness/security PASS, no remaining actionable findings. Source commit and final broad results, fresh package, operator reconciliation and master merge/push remain pending. This scoped review is not deployment authorization.

Consolidation follow-up: source-gate repair committed **c3614eb9d4c7a49b9e7c91d9fb42fe23adc40c3c**; the actual repaired CI preflight PASS is saved at `consolidation-ci-repaired-20261021`. Its promotion decision remains BLOCKED, not deployment approval. Graphify AST refresh PASS (10,144 nodes / 27,495 edges); no paid semantic extraction. Independent operator-note privacy review requested removal of real record-inventory details from three public previews; the host generalized those details and `doc_discovery_review` independently re-reviewed the actual bytes: PASS. All seven historical/operator additions are now reconciled into development, with only public status/invariance assertions and historical-only banners. Byte-identical originals remain protected locally; primary files remain untouched. `operator-public-reviewed.json` pins the reviewed publication copies. No new active tracker is created. Native desktop assistant/dashboard and 390px screenshots were inspected: PASS for the captured synthetic states; current account/device-loss/installer acceptance remains unverified.

Operator reconciliation committed **78c2058f4e3f37e9ded393eff31551a3bb77a3a5**. CI now pins that reviewed source so the preserved public `skills-lock.json` additions are explicitly accounted for alongside the two dependency inputs and seven migrations. No package installation, schema execution or operational waiver follows from that source declaration. Final runtime source remains c3614eb; these later changes are historical documentation, public skill metadata and the CI pin only.

### DOC-07 reviewed bank transaction-date questions — 2026-10-20

Resumed clean **9a4e561451c85302a29b60a4dc36e28549091d44** on the existing development branch/worktree. Existing v3 Council **74ed3d42f57b6d0c** pins eight service/UI/test/tracker paths and the existing bounded browser gate. No Council replacement, additional repository or provider activation. This unit answers explicit transaction-date questions from current owner-reviewed bank receipts, including canonical bank records and up to three explicit records selected from one statement. Each selected record gets its own ISO date/reference and authorized citation, including equal dates on distinct records; no implicit search or first-match choice.

The shared field grammar now includes expense-only transaction dates; plural “what are” is confined to dates, preserving the monetary grammar. Original import dates must be retained and valid ISO dates; manual records, missing/malformed originals, incomplete/conflicting/unreviewed sources and ambiguous/free-text requests abstain. Corrected current dates take precedence while safe original-date metadata and the unchanged private evidence view preserve provenance. Source equality/ownership is rechecked immediately before deterministic return, reusing the existing post-inference safeguard. Dates are not LLM-generated and require no model, embeddings or saved-memory retrieval. Legacy bank/canonical APIs may initialize their existing protected MemoryStore; selected-document questions avoid it entirely. No conversation turn or trusted memory is created by a date answer. No money, fingerprint, currency, ownership or parsing changes.

Initial `doc07-bank-dates-reproduction` preserved one expected failing date-answer test. Actual independent `doc_discovery_review` found a P2 in the first implementation's temporal keyword guard: “Which record was from September?” and “What is the transaction time?” still reached inference. `doc07-bank-dates-temporal-reproduction` preserved the failing no-retrieval regression. The repair removes the denylist and applies the bounded expense intent allowlist to **all** bank-statement requests before retrieval/inference. Evaluated legacy source-transaction/statement-record explanations remain supported; arbitrary questions now fail closed. A browser fixture's artificial “synthetic” adjective was removed from its question rather than hardcoded into production grammar. The same reviewer actually reinspected the repair and found no remaining actionable runtime/security issue; final source binding is pending.

`doc07-bank-dates-focused`: 34 tests with five error/subcase reports caused by the new fixture trying SQL NULL in the existing non-null original JSON field. Replaced with its actual empty-dict historical representation; `doc07-bank-dates-focused-corrected`: **34 backend PASS**. After the allowlist repair, `doc07-bank-dates-allowlist-repaired`: **97 backend PASS**, zero failures/skips, including Bank/Loan/Investment compatibility, original/current dates, retained evidence, multiple explicit records, duplicates/transfers, owner/citation access, in-read date/revocation/owner/deletion races and financial/fingerprint invariance. Later history assertions also ensure a synthetic opted-in history never saves deterministic dates as model turns; they remain subject to the final gate. Preliminary counts overlap and are not added.

The new browser flow first hit a stale-element wait during evidence-page reload, then a visible-text assertion during the existing page fade. A diagnostic screenshot confirmed the correct current/original dates; the test now waits for current status and actual visible text using Selenium's existing stale-safe condition, without sleeps or relaxed financial assertions. `doc07-bank-dates-browser-review-diagnostic` and `doc07-bank-dates-browser-visible-review`: **one actual Chrome PASS each**, same overlapping flow. Corrected-date desktop/390px screenshots inspected; final gate recaptures the mobile answer after viewport reflow. In the earlier two-flow run only the new wait/assertion failed; the legacy bank explanation/correction/citation flow passed. Failed receipts are preserved.

Separate `doc07-bank-dates-local-compat`: **one actual bounded local Ollama PASS**, existing reviewed investment-value path, not date generation or general accuracy. Date answers use zero model/cloud calls. `doc07-bank-dates-schema`: system/migration drift PASS; JavaScript syntax PASS. Graph query now executes through the normal installed CLI; AST-only refresh is in progress, not yet claimed PASS, with no policy bypass or paid extraction. Final independent fingerprint binding, Architect/Coder, Council Tester/Guardian, ordinary commit and postcommit closure are **PENDING**. No new schema/dependency, production/private financial data/runtime/config/backup/GitHub/frozen changes; approval-gated history/currency/cloud/OpenAI remain OFF. Counts stay **64 verified / 79 remaining**, full DOC-07 partial. Next independently safe Council unit: preserve bounded structured host review decisions/reason codes across source repairs and retries; existing current-role overwrite currently loses them. Reuse this Council and its host-only code/commit boundary.

Postcommit closure: **98a3c89bdbdd516a48a55b213a61a473c91811ee**, Council **74ed3d42f57b6d0c COMPLETE** with all seven roles PASS. Actual independent Reviewer/Security `doc_discovery_review` approved exact fingerprint **f058001f05cd07153be595b48cb8851237ee669930df9ea31e24c9cb325cbe6b**. The first final attempt was interrupted without a result; after read-only confirmation that its development workers had stopped, the normal explicit resume retained it as BLOCKED. Second/final allowed attempt: **133 backend + 1 Chrome PASS**, **115.678 seconds** test time / **137.000 seconds** bounded duration, zero failures/skips. Evidence: `artifacts/council/74ed3d42f57b6d0c-2/`. Desktop and 390px corrected-date/source screenshots reviewed PASS. Final history regression included: deterministic dates do not become saved model turns. Synthetic money/fingerprint comparisons: zero mismatches.

Release Guardian verified the exact ordinary host commit, source/ancestry, no dependency/migration changes and privacy: **892 paths / 849 blobs / one commit**, zero findings. Its scope is development checkpoint only; production authorization and full release readiness remain false. Normal installed `graphify update .` completed AST-only, **10122 nodes / 27429 edges**, no model/API cost or policy bypass; old semantic labels remain unrefreshed. Documentation validation: 143 feature rows, valid local links, unchanged C1?C10. No production, private DB, backup, master/frozen or provider/history activation changes. Counts remain **64 verified / 79 not fully verified**. Next is the bounded COUNCIL-04 decision-history gap; independent design review found no blocker but implementation approval is still pending. A synthetic date-correction screenshot also showed an unrelated category changing; inspect/reproduce that existing hydration path after Council completion before making a financial fix.

### DOC-07 exact question-form aliases — 2026-10-20

Continued the next safe master-queue item from clean **f7c6aa4576e688aafb7517dd9be3240150fd4633** using existing seven-role Council **e0405cf5a302cee6**, seven scoped service/template/test/tracker paths, browser profile and the existing 600-second/two-attempt budget. `doc07-question-forms-reproduction` preserved **one expected failing API test**: “What is my current value?” previously abstained despite a current reviewed selected field. The minimal shared grammar repair adds only the exact **“what is”** prefix to the existing field-specific command forms. It does not broaden generic record intents, introduce a language/model classifier, infer missing facts/currency or bypass domain/selection/field-availability checks. Other unsupported questions still abstain.

`doc07-question-forms-focused`: **three backend PASS**, zero failures/skips. Deterministic fixtures cover all eight existing monetary fields across expense/loan/investment versus wrong/unspecified/budget/baseline domains; canonical/selected current values and exact citations; revoked/missing EMI and investment fields; historical, arithmetic, currency, arbitrary-record and injected/free-form request rejection. These test intent/evidence contracts, not general language or model accuracy. Existing Chrome correction/stale-selection/draft/retry flow and bounded two-record real-local acceptance are updated to the exact question form; legacy command compatibility stays covered by unchanged backend cases.

Final actual independent Reviewer/scoped Security, source-bound host Architect/Coder, Council backend/Chrome Tester, exact committed Guardian/Coordinator closure, real-local receipt and ordinary commit are **PENDING** at this precommit checkpoint. Resume this task/current diff, not a new Council, audit or document system. No new models, migrations, dependency, money calculation, full-text retention, provider/history activation or production/private-data/frozen/GitHub change. DOC-07 and the same **64 verified / 79 remaining** feature counts stay partial/unchanged. Broader arbitrary financial-document Q&A, sustained model accuracy, normal-account/native/package/provider and portable recovery acceptance are not established by aliases.

Postcommit closure: **e0405cf5a302cee6 COMPLETE** at ordinary host commit **d18d1d1ffbbb05fe7e82b75986cb13316b5d548c**, fingerprint **93b56a156098e57fa2aeb5201d32b5c99ceb206d3deeb84f699497450681af10**, all seven v3 roles PASS. Actual independent `doc_discovery_review` Reviewer/scoped Security found no actionable issue; host Architect/Coder are not independent. First final Council gate **79 tests = 78 backend + 1 actual Chrome PASS**, **83.859s** bounded / **62.117s** suite, zero failures/skips, covering old commands plus exact field questions, selected current/corrected evidence, stale/revoked/missing fields, owner/citation/privacy, baseline/fingerprint invariance and unsupported-intent rejection. `doc07-question-forms-real-local`: **one bounded real local PASS**, **13.625s**, two fictional reviewed investment values; no model promotion/general accuracy claim. Current exact answer/citation/narrative-withholding screenshot reviewed PASS under `artifacts/council/e0405cf5a302cee6-1/browser/user-data/`.

Guardian exact source/dependency/migration/privacy PASS, **892 paths / 849 blobs / one commit**, six reviewed synthetic identifiers and zero findings; development checkpoint only, `release_ready=false / production_authorized=false`. Zero optional advice calls/reservations; host usage/cost totals unavailable. `doc07-question-forms-schema` system/migration drift PASS; document validator confirms **143 rows, zero broken local links, unchanged C1–C10**. Counts remain **64 verified / 32 unaccepted / 29 partial / 10 missing / 5 approval / 3 external**, 79 not fully verified. Graph refresh is still Windows-policy-blocked; no new package/native/real-account/provider/recovery acceptance. Read-only Git verification confirms production/master **3932f391** and frozen **4aa7ac70** unchanged; production availability/private financial data were not probed. No source/runtime/config/database/backup/GitHub mutation outside this development branch.

Next bounded local unit: reuse the bank receipt/current canonical `Expense.transaction_date` provenance for explicit transaction-date questions on currently selected owner-reviewed bank records. Keep financial transaction dates distinct from UTC document-upload dates and unrelated record-update/valuation/payment dates; reject unsupported domains, stale/revoked/missing evidence and free-form questions. Add original/corrected date, owner/race/citation, API/Chrome and financial invariance tests before broadening the shared grammar. Do not create another document system or infer currency/authenticity. Broader PDF/OCR knowledge and approval-gated items stay partial/disabled. Resume this master queue from actual clean HEAD; do not rerun the completed alias/field/filter Councils.

### DOC-07 explicit reviewed monetary-field questions — 2026-10-20

Continued from clean tracker closure **934431561bb1441433cac98564f5c521cd5e6062**, retaining DOC-06 runtime c022fad. Existing v3 Council **3461f90aeab752ca** pins that base, eight existing service/template/test/tracker paths and a bounded 600-second/two-attempt browser gate. The current runtime diff extends the shared fail-closed question grammar to stored expense amount/closing balance, loan principal/EMI/remaining balance and investment invested amount/monthly SIP/current value. The existing canonical/source tools remain authoritative; every explicitly selected document record must project the requested current reviewed value. Missing/unreviewed/wrong-domain fields abstain before inference; **0.00 remains a recorded value**. Generic record explanations retain their existing limitations. No new extraction/index/memory system, totals/FX/inferred currency, data writes, dependencies or migrations.

`doc07-fields-reproduction` preserved the initial failing current-value query. An independent `doc_discovery_review` Reviewer/scoped Security inspection then found a P2 legacy grammar gap: EMI “details/values/status” was accepted but not recognized as a specific amount request, bypassing the availability check. `doc07-field-suffix-reproduction` ran one test with **four failed subcase/assertions** against a loan with reviewed principal but revoked EMI. The minimal repair shares the existing accepted suffix set; a direct API regression now checks all four variants, local abstention and no model/cloud call. The reviewer actually reinspected the repair and reported no remaining actionable runtime issues; final source binding is pending below. No reviewer edits, tests or provider calls are implied.

`doc07-fields-first` ran 60 tests with eight failing subcase assertions in the newly written tests: construction-time string attributes were compared to persisted Decimal output, and one backend expected value accidentally used the separate browser fixture. Both fixtures/assertions were corrected without changing monetary logic or thresholds. `doc07-fields-fixtures-corrected`: **four backend PASS**. After the independently identified suffix repair, `doc07-fields-suffix-repaired`: **61 backend PASS**, zero failures/skips, covering current selected/canonical values, zero, revocation/missing-field abstention, owner/citation/race/original-evidence safeguards and unchanged financial values. Failed receipts remain preserved and overlapping counts are not added.

Separate `doc07-fields-chrome`: **one actual Chrome PASS**, zero failures/skips, covering all-selected-field abstention, draft/retry, narrower selection, correction/stale refresh, exact private citations, unknown currency and suppression of invented INR figures. Final Council run will recapture the latest answer rather than the first conversation turn. `doc07-fields-real-local`: **one bounded real local Ollama PASS** using two fictional reviewed current-value records; no general accuracy/model-promotion claim. `doc07-fields-schema`: system checks and migration drift PASS. Graph refresh remains blocked by Windows Application Control from the preceding unit; no policy bypass. No new native/package, normal-account/provider/device-loss acceptance.

Architect/Coder source attestations, final independent source binding, Council Tester, Guardian, ordinary commit and postcommit closure are **PENDING** at this checkpoint. Continue this same task/diff; do not recreate the Council or repeat DOC-06. Source/runtime, finite Decimal values, raw evidence, fingerprints, owner permissions, frozen 4aa7ac70, production/master/private data/backups and disabled provider/history flags remain preserved. DOC-07 remains PARTIALLY_IMPLEMENTED; counts remain **64 verified / 32 unaccepted / 29 partial / 10 missing / 5 approval / 3 external = 143**, 79 not fully verified. Full arbitrary PDF/OCR Q&A and retention/recovery/provider/currency decisions remain separate and gated.

Postcommit closure: **3461f90aeab752ca COMPLETE** at ordinary host commit **9d2fd789d0691122477602e982d25b3e8b48a107**, fingerprint **547f79d478daf2957b9d8a39fafe71703731e24babb8aa9fbad4cef33b389dfb**, all seven v3 roles PASS. Actual independent `doc_discovery_review` Reviewer/Security approved the repair and final source; host Architect/Coder are not independent. First Council attempt **100 tests = 97 backend + 3 actual Chrome PASS**, **150.250s** bounded duration / **132.711s** suite, zero failures/skips. Guardian source/dependency/migration/privacy PASS, **892 paths / 849 blobs / one commit**, six reviewed synthetic identifiers, zero findings; explicitly development checkpoint only, `release_ready=false / production_authorized=false`. Zero optional advisory calls/reservations; host token/cost totals unavailable. Current exact-value/currency-withholding screenshot reviewed PASS under `artifacts/council/3461f90aeab752ca-1/browser/user-data/`.

Additional `doc07-fields-legacy-compatibility`: **32 backend PASS**, zero failures/skips, sharing existing canonical evidence and hybrid contracts. A final Ollama invocation initially used a nonexistent test-class label (`doc07-fields-final-real-local`, one loader error, no inference); corrected exact label in `doc07-fields-final-real-local-correct-label`: **one real local synthetic PASS**, zero failures/skips. Preliminary/overlapping counts are not added; no broader accuracy or currency claim. Source-bound gate includes session/CSRF/history, financial baseline/fingerprints with zero mismatches, source revocation/corrections and stale-inference safeguards. System/drift and documentation validation PASS (143 rows, zero broken local links, C1–C10 unchanged). All earlier failed/precommit evidence is preserved and superseded only for its stated scope. No migration/dependency, provider/history/currency activation or production/private-data/backup/frozen/GitHub change. Next safe task is evaluated exact question-form aliases over the same existing field adapter; general PDF/OCR Q&A remains partial.

### DOC-06 owned metadata filters — 2026-10-20

Resumed clean **342c0bad24e352dc0ccc4078d3d33710fd71b1d3** on the sole existing development branch/worktree. Existing seven-role Council **1f7f380994e26e91** pins that base, seven scoped source/UI/test/tracker paths and a 600-second/two-attempt browser gate. No Council rebuild, optional advisory/model-role calls, new dependency, schema or production action.

The existing document discovery service now accepts a bounded displayed-basename substring (Unicode casefold, literal characters) and inclusive **UTC upload-date** bounds. The owner and date window are applied before the existing 4096-candidate metadata cap, and displayed-name filtering occurs before five-item keyset pagination/counting. Oversized catalogs fail completely and request a narrower date window; filename search never silently searches only the first 4096 or five records. Duplicate names keep distinct IDs. Signed catalogs contain filter/metadata hashes, not raw search terms, and recheck all matching names/timestamps/membership before returning. Filter/cursor changes, concurrent edits, deletion or ownership changes require refresh. Linked-record catalogs and reviewed selections retain their separate current revisions, originals/corrections, revocation, owner citations, exact Decimal values and unknown-currency rules.

Filtered reads use CSRF-protected JSON **POST on the existing list endpoint** so private search terms do not enter URLs/access logs; GET remains cursor-only and linked-record POST remains 405. Search fields are validated, never stored in memory/history/indexes or sent to a model/cloud. The existing Documents UI provides explicit Apply/Clear, current counts/empty/error states, preserved applied filters on return from linked records, draft preservation, request cancellation and page-hide clearing. Filters lock while viewing linked records, without changing the separate assistant picker. No arbitrary PDF/OCR extraction/search/Q&A, financial writes, currency inference or activation.

`doc06-filter-first`: **56 backend PASS**, zero failures/skips, covering bank/loan/investment metadata, owner-before-limit/pagination, duplicate and Unicode/literal/basename search, inclusive UTC boundaries/year extremes, malformed dates/ranges/types, CSRF/session/foreign cursors, signed filter/metadata binding, concurrent edits, unchanged selected evidence/originals and synthetic financial baseline/fingerprints. `doc06-filter-chrome-first`: **2 actual Chrome PASS**, **54.431s**, zero failures/skips, including paging/back, empty/invalid results, draft preservation, POST-only private filters, stale refresh, page-hide/cache return, safe hostile-name rendering, exact document-to-assistant citations and revocation rejection. Actual desktop/390px filter screenshots reviewed PASS. Separate `doc06-local-ollama`: **one real local synthetic PASS**, **21.322s**, existing two-reviewed-record acceptance; this is not general accuracy or a new model promotion. System/migration-drift and JavaScript syntax PASS. Overlapping counts are not added.

Actual independent `doc_discovery_review` initial Reviewer/scoped Security inspection found no actionable issues; final source-bound approval, host Architect/Coder attestations, Council Tester, Guardian and ordinary commit are **PENDING** at this checkpoint. Graphify AST refresh was attempted but **BLOCKED by Windows Application Control (ApplicationFailedException)**; no policy bypass or paid fallback. Existing graph/source navigation remains read-only; graph freshness is not claimed. No fresh native/package, real-account/provider or device-loss acceptance. Counts stay **64 verified / 32 unaccepted / 29 partial / 10 missing / 5 approval / 3 external = 143**, 79 not fully verified. DOC-06 stays PARTIALLY_IMPLEMENTED because metadata filtering is not general full-document knowledge. After this task closes, the next independent DOC-07 unit is evaluated, allowlisted financial-field questions (for example current value) over the existing selected current reviewed projections; full arbitrary PDF/OCR work and retention/provider/currency decisions remain gated.

Postcommit closure: **1f7f380994e26e91 COMPLETE** at exact runtime **c022fad0a9ab2a06f2c6f55656a6a53e34245f62**, fingerprint **7454d42f915c987fa37b8e7e527a4377885e720a09c2a255a0e738b6ec5cc7a1**, all seven v3 roles PASS. Genuine separate `doc_discovery_review` Reviewer/Security found no actionable issues; host Architect/Coder are not independent. Final first-attempt **96 tests = 92 backend + 4 actual Chrome PASS**, **163.922s**, zero failures/skips, including metadata filtering, current/legacy grounding, session/CSRF/history, baseline/fingerprint equality with zero mismatches. Guardian source/dependency/migration/privacy **PASS**, **892 paths / 849 blobs / one commit**, six reviewed synthetic identifiers, zero findings; `release_ready=false / production_authorized=false`, development checkpoint only. Zero optional Council advisory calls/reservations; host usage/cost totals unavailable. Prior 56/two/one runs overlap. Current receipts/screenshots under `artifacts/council/1f7f380994e26e91-1/`; system/drift, JavaScript and local-doc links PASS, C1–C10 unchanged. Graph refresh remains policy-blocked and no native/package/real-account/provider/device-loss acceptance is newly claimed. No production/private data, backups, GitHub/master, frozen 4aa7ac70, currency schema, history activation or provider flags changed. Continue DOC-07 field questions below; no general accuracy or arbitrary-PDF completion claim.

### Seven-role Development Council continuation — 2026-10-19

Recovered clean a65c1cd and inspected both completed Council cycles **696c858d48945a8f / 194ba73f8aeeddfe** from actual task state: exact commits, source-bound roles, retained tests and zero advisory reservations match their evidence below. Bootstrap **686c7d593e9bda26** is intentionally the existing v2 contract; it does not retroactively invent Architect/Guardian approvals. New tasks use v3: Coordinator selects the reviewed master queue and verifies the checkpoint; Architect performs source-bound design/reuse review; Coder uses the existing developer role/CLI alias; actual independent Reviewer, scoped Security and isolated Tester retain existing requirements. No extra model is needed for a deterministic role. Separate reviewer attribution remains mandatory, whereas the host Architect may also be Coder and is never labeled independent.

Release Guardian reuses M20 exact clean source, dependency/migration policy and pinned privacy scans for the tested ordinary host commit. Its result is explicitly **development_checkpoint_only**, **release_ready=false / production_authorized=false**; operational/recovery/full-release gates and approvals remain separate. Attempts are reserved durably before scanning, bounded by the existing two-attempt policy, retained across timeouts/OS errors and interruptions, and final source/review state is rechecked. Interrupted workers require expiry plus explicit stopped-worker confirmation; late results cannot replace an interrupted/newer attempt. CLI/escaped HTML show role results, source/commit, tests, failures/retries, conservative advisory reservations and unavailable host usage/cost measurements. Local Ollama advice is optional and never approves roles or bypasses quota. No automatic source edits, commits, migrations, financial writes, deployment or GitHub push.

`council-seven-roles-first`: **73 backend PASS**, zero failures/skips, before independent review. Actual `doc_discovery_review` requested two repairs: operational Guardian exceptions could roll back attempt evidence; and postcommit routing hid valid Guardian retries/exhausted budgets behind a generic base-change blocker. Both are repaired with durable running leases/failure history, redacted classification, explicit resume and exact-parent/source-bound v3 routing. New regressions cover seven-role completion without release approval, Architect/independence enforcement, Coder alias, forged Guardian rejection, retry/exhaustion, TimeoutExpired/OSError, crash/restart and legacy v2 behavior. Repaired tests, final independent re-review, bootstrap Council gate and ordinary commit are **PENDING** at this source-bound checkpoint. No source/system/privacy or fresh browser/native acceptance is claimed yet. 143-feature counts and all production/provider/history/currency restrictions remain unchanged.

Postcommit closure: bootstrap **686c7d593e9bda26 COMPLETE** at **f649da661dcf60a04bfcd188300e8c841423ab1a**, source **7e16af1f4ba6a94bf73be9e786cd1e8f6898d8c5f751cab08d4d959983b71f27**, all its historical v2 roles PASS. Actual independent `doc_discovery_review` re-reviewed both repairs with no remaining actionable findings. Repaired standalone **75 backend PASS**; final source-bound Council first attempt **75 backend PASS**, **204.871s** suite / **207.343s** bounded duration, zero failures/skips. Counts overlap, not 150 distinct tests. `council-seven-role-clean-source.json` pins this one commit to e6df491: source/dependency/migration/privacy **PASS**, **892 paths / 849 blobs**, six reviewed synthetic patterns, zero findings. No schema/dependency or application behavior changes in this unit; fresh app/browser/native/model/release gates were not rerun. AST-only graph update exit 0. The next actual DOC-07 task will exercise v3 Architect and Guardian; synthetic contract tests alone are not reported as that production task's acceptance. All 143-feature counts stay unchanged.

Operator CLI is the existing `scripts/development_council.py`. Resolve the configured SDK to `$taskPython`, then use `plan --feature DOC-07 --path ... --label ...`, `handoff --task ID`, `inspect --task ID`, source-bound `record --task ID --role architect|coder|reviewer|security --actor ACTOR --status PASS|FAIL|BLOCKED --source FINGERPRINT`, `test --task ID`, `status --task ID` and `complete --task ID --commit EXACT_SHA --authorization-reference DEVELOPMENT_APPROVAL`. The legitimate host makes the ordinary tested Git commit; Council never stages/commits source. `resume --task ID --confirm-worker-stopped` only releases an expired, actually stopped worker. Reviewers must be genuinely separate actors; role aliases are attestations, not identity/quota proof. Existing local `artifacts/council/status.html` is a safe evidence view, not a second project tracker or application/production agent.

### DOC-07 bounded document questions — 2026-10-19

Council **faf7449750df0154**, contract v3, pins clean base **cfffd0c332db86ceae3451427ab3e2b26e8e9017** and seven existing backend/test/tracker paths. The existing Insights API accepts `financial_document` plus one owned bank, investment or loan import and **one to three explicitly selected reviewed canonical record revisions**. Signed owner/document catalogs bind the whole current membership; deterministic record ordering, bounded field projection, duplicate/conflicting/foreign/changed/missing evidence rejection and repeated before/after inference checks prevent partial or stale answers. Exact private review citations preserve corrected-value precedence and original evidence. Each authoritative Decimal amount stays separate with currency `not_recorded`; no totals, FX, inferred currency, independent authenticity or arbitrary OCR/PDF comprehension is claimed.

Local reasoning reuses the existing intent gate, 4096-byte evidence context, 256-token/30-second inference budget and unsupported numeric/currency narrative suppression. Only selected reviewed fields reach the model; unreviewed fields are labeled without their values. This mode creates no memory vault, retrieves no unrelated memories, writes no conversation history or financial records, and rejects cloud consent. Session freshness is rechecked on success and error so expired sessions cannot be renewed by SAVE_EVERY_REQUEST. Existing canonical, bank and conversation callers retain their behavior. No migration, dependency, configuration or provider/history activation change.

`document-questions-projection`: **68 backend PASS**, zero failures/skips, **32.405s**. Cases cover bank/investment/loan selection, original/corrected fields, unknown currency, exact owner-only citations, strict malformed/foreign/duplicate/over-budget selections, unsupported totals/questions, numeric narrative suppression, pre/during-inference correction/revocation/relink/deletion/owner/file races, session/CSRF/expiry, outages, no vault/cloud/history, unchanged canonical financial baseline and statement/transaction fingerprints. Earlier 47-test execution overlaps and is not added. `document-questions-real-local`: **one bounded actual Ollama PASS**, **17.072s**, two fictional reviewed holdings with exact values/citations and unknown currency. This validates the installed local path, not general model accuracy, arbitrary document Q&A or promotion of the rejected embedding model.

Actual independent `doc_discovery_review` initially found no actionable correctness/security issues; final source-bound Reviewer/Security approval, host Architect/Coder attestations, Council Tester, Guardian and ordinary commit are **PENDING** at this checkpoint. No new browser/native/package acceptance is claimed for this backend. DOC-07 moves from NOT_IMPLEMENTED to **PARTIALLY_IMPLEMENTED** because bounded document-level questions now execute; full arbitrary-document acceptance and UI wiring remain incomplete. Counts: **64 verified / 32 unaccepted / 29 partial / 10 missing / 5 approval / 3 external = 143**, still **79 not fully verified / 44.8% technical**. Next isolated unit after this Council closes: expose explicit document-record selection in the existing assistant UI. All production, frozen-candidate, money/currency/history/provider and recovery restrictions remain unchanged.

Postcommit closure: **faf7449750df0154 COMPLETE**, exact source commit **b0bc54a5e61ebe171b6b71245eb3ca0a0452cbf5**, fingerprint **e24164aa0d36c47375777d802d02179a9d81ce06826af828d287f1c24123d51b**. All seven actual v3 roles PASS: deterministic Coordinator; host Architect/Coder `codex_developer` (not independent); genuine separate `doc_discovery_review` Reviewer/Security with no actionable findings; isolated Tester; M20-backed Guardian. Final first-attempt **85 backend PASS**, **72.157s** bounded duration, zero failures/skips, includes financial baseline/fingerprint checks with zero mismatches. Guardian exact clean source, unchanged dependencies/migrations and pinned privacy **PASS**, **892 paths / 849 blobs / one commit**, six reviewed synthetic identifiers, zero findings. `release_ready=false`, `production_authorized=false`, scope development checkpoint only; zero advisory calls/reservations and no claim to observable host token/cost totals. Repeated counts overlap. AST-only graph update exit 0; local links, 143 rows and unchanged C1–C10 verified. Evidence is under `artifacts/council/faf7449750df0154-1/` and the separate real-local receipt above. No new Chrome/native/package or normal-account claim. Next task is existing assistant/document-center UI selection, bounded to three current reviewed records and page-only answers; full arbitrary-document acceptance stays partial.

### DOC-07 document-question UI — 2026-10-19

Council **d4aea2d0484afc58**, contract v3, pins clean base **04231ce804d9882277b2cc59b0c173e4f07daf58** and six existing UI/test/tracker paths. Documents now links to the existing assistant's `financial_document` mode, not another chat. Its shared source picker pages every linked record, requires explicit selection of **one to three** current reviewed records from that one document, preserves selections across pages, labels eligible/unreviewed fields and unknown currency, and displays exact private citations. No automatic record selection, totals/FX, extraction, raw OCR/PDF Q&A, new memory system or financial/schema/dependency changes. Question drafts survive 409/503; current correction/revocation checks stay in the backend. Page-hide clears private names/selections/answers, and document questions remain page-only even for a synthetically opted-in history owner. OpenAI/cloud/history activation remains OFF outside disposable tests.

Actual independent `doc_discovery_review` requested two P2 repairs: scope changes while generating could strand a never-loaded picker; an unrelated saved-history conflict could block page-only questions. Scope/record selectors now lock while requests run, picker creation is deferred until pending operations finish (including history callbacks), and saved-history conflict state does not guard document-only questions. The first repair missed internal history callbacks; independent re-review caught that path and the additional stay-in-document-mode regression now covers it. Reviewer/Security re-review found no remaining actionable issues; final fingerprint binding and Council acceptance remain **PENDING**.

Focused browser evidence is deliberately separate: `document-questions-ui-first` ran two tests with one failure from an incorrect expected field count (renamed source invalidated old attestations; only three current-value fields were re-reviewed). Corrected picker flow **one Chrome PASS**. `document-questions-ui-repaired` picker passed but the new history fixture timed out on a button inside closed details; opening the details explicitly corrected that fixture. `document-questions-ui-history-repaired`: **one Chrome PASS**, zero failures/skips, covers actual stale saved-history revision, document retry without reopening history, selected-source revocation/correction, safe local-model outage, held pending answer/disabled controls, no extra saved turns and no verified memory promotion. Receipts remain preserved; these overlapping runs are not a final combined gate. Actual desktop/390px picker, hostile-name text rendering, private citation and stale-source screenshots were inspected; the pre-existing evidence table uses horizontal scrolling on mobile. System/migration drift and JavaScript syntax PASS. No fresh native/package, normal-account, provider or device-loss acceptance claimed. Final source-bound Council backend/Chrome gate and ordinary commit follow; 143-feature counts stay **64/32/29/10/5/3**, 79 not fully verified.

Postcommit closure: **d4aea2d0484afc58 COMPLETE**, exact runtime **7cccbc1aa9e704f5273ebbe57131a0beacc3d5de**, fingerprint **a572d90653cfad464a0ef8f07368eccbc0ef4d90650b4071ee647857051b9ed6**. All seven v3 roles PASS, with actual independent `doc_discovery_review` Reviewer/Security after repairs; host Architect/Coder are not labeled independent. First/final Council attempt **84 tests = 80 backend + 4 actual Chrome PASS**, **100.657s**, zero failures/skips. Includes both new document flows, legacy multi-document picker and document-center discovery, owned canonical tools, session/CSRF and synthetic financial baseline/fingerprint reconciliation with zero mismatches. Guardian exact clean source/dependency/migration/privacy **PASS**, **892 paths / 849 blobs / one commit**, six reviewed synthetic identifiers, zero findings; development checkpoint only, `release_ready=false / production_authorized=false`. Zero advisory calls/reservations; host token/cost totals are not observable. Final Council desktop/390px picker screenshots were actually reviewed PASS; long source lists scroll vertically and the existing evidence table horizontally. Evidence: `artifacts/council/d4aea2d0484afc58-1/`; system/drift evidence `document-questions-ui-schema`, AST-only final graph exit 0, JavaScript syntax PASS. No frozen/native rebuild or release approval. DOC-07 remains PARTIALLY_IMPLEMENTED: bounded reviewed-field Q&A is available, arbitrary financial PDF/OCR comprehension is not. Next safe unit is DOC-06 metadata filtering below, not another Council setup, audit or automatic provider/history activation.

### DOC-07 bounded eligibility continuation — 2026-10-19

Recovered clean integrated HEAD **f17fcd753ba03a563517979521ea9eb607eeb166**, newer than the supplied dfdeac09 checkpoint (verified ancestor); no interrupted tracked/untracked source changes found. Retrieval/held-out and Council setup are already complete within the scopes above and are not repeated. One development checkout/branch is retained; production and frozen 4aa7ac70 remain untouched.

Council task **58b9233eda5d91b4**, pinned base **f17fcd7**, extends the existing canonical document adapter, source-page API and Insights picker rather than adding a new extraction/index/model path. Source entries explain current eligible reviewed fields, pending owner/document/loan-contract review, missing files and source conflicts. Partial attestation exposes only confirmed fields as eligible; estimated loans are not selectable even if imported fields are attested. Existing signed selection/revision checks and owner-only citations remain authoritative. Full-text Q&A is explicitly unsupported; no raw OCR/payload is added to responses/prompts, no memory retention, inferred currency, financial mutation, schema/dependency or provider/history activation. This is a bounded prerequisite, not completion of arbitrary-document Q&A: **64/143 verified / 79 remaining**, DOC-07 remains NOT_IMPLEMENTED for its full acceptance scope.

Focused synthetic `doc07-focused-f277c0fb`: **34 backend PASS**, zero failures/skips, including field/revocation/partial/missing/deletion/injection/estimated-loan eligibility and prior canonical/closure/selection races. Independent review caught an encoding mistake in the browser fixture (restored original Unicode) and a loan-conflict preflight mismatch (shared the existing canonical conflict check and added regression coverage). Exact backend/Chrome Council gate, final independent review, visual acceptance, source/privacy and committed completion are pending at this precommit source-bound checkpoint. Fresh native/package, real-account/provider and independent recovery acceptance remain pending; no historical counts are presented as new runs. Next milestone after this adapter: owner-directed document-center discovery/routing to supported exact field citations, with unsupported documents abstaining; broader extraction/Q&A needs its own bounded implementation and acceptance.

Postcommit closure: **58b9233eda5d91b4 COMPLETE** at exact authorized host commit **f057d85f78ee9725ff24fe6bafc8ebb1c51c1a4b**, all six v2 roles PASS; source fingerprint **da09ef247756ed22a69224ca918b9c831ff46cb9a23a83510772bfa114b119bc**. Actual independent reviewer `doc07_independent_reviewer` identified two issues, both fixed and re-reviewed with no remaining actionable findings. Security review and tests are separate evidence, not model-advisory approval. Council first/final attempt: **37 tests = 35 backend + 2 real Chrome PASS**, **35.079s** suite / **48.547s** bounded operational duration, zero failures/skips. No advisory model calls or token reservations. Focused 34 plus the separate new conflict regression overlap and are not added. Existing stale/deletion/foreign-source rejection, exact Decimal/currency assertions, selected older citations, draft preservation and pagehide clearing passed.

Actual desktop, 390px mobile, stale-draft and exact older-loan citation screenshots reviewed in `artifacts/council/58b9233eda5d91b4-1/browser/user-data/`: PASS for this bounded synthetic flow. Long source lists require vertical scrolling; normal-account, full accessibility certification and fresh packaged/native acceptance were not executed. System/migration drift and JavaScript syntax PASS, no schema/dependency changes. `doc07-clean-source.json`: exact clean source/ancestry and pinned privacy PASS against f17fcd7 (**892 paths / 849 blobs / 1 commit**, six reviewed synthetic patterns, zero findings). AST-only Graphify completed at exit 0 (10020 nodes/27082 edges); stale community labels were not regenerated with a paid model. The precommit pending language above is retained as source-bound historical evidence; this paragraph closes it. Final checkpoint changes only this tracker.

Next bounded DOC-07 milestone: owner-directed document-center discovery/routing to the existing supported exact-field review/citations; do not create an alternate extraction/index/model pipeline or claim arbitrary PDF Q&A. Full feature counts remain **64 verified / 79 remaining**. Broader retrieval accuracy, default/private activation, FIN-CURRENCY approval, cloud/OpenAI/history consent, fresh native/package/normal-account/separate-PC and independently recoverable backups/keys remain explicit blockers. AWS stays OFF. Production/master 3932f391, frozen 4aa7ac70, private data/configuration and backups are untouched; no GitHub push or passphrase dialog.

### DOC-07 document-center discovery — 2026-10-19

Resumed clean **c9c7d8b3f01ce11694386e5965535c51cb6b8296**, already containing the prior f057d85 adapter and its closure. Council **696c858d48945a8f**, contract v2, pins that base and eight files: existing canonical evidence/API routes, document-center JavaScript/template, source-selection/browser regressions and this tracker. Planner selected the next recorded DOC-07 prerequisite; no model advisory calls or token reservations were needed. Only legitimate host actions edit source. One independent review attempt hit a usage limit and produced no review; the same reviewer resumed after its indicated reset, without account/model switching. Its actual request for changes is preserved here, not relabeled PASS.

Implemented owner-only, signed keyset pages of five bank/loan/investment documents and five linked canonical records per page, with deterministic primary-key order and a fail-closed 4096-member discovery bound. Lists are metadata-only; exact review pages remain the correction/confirmation authority. Record pages reuse retained-original status, current corrected-field eligibility, freshness/revocation/loan-conflict checks and exact owner-protected citations. New document-center controls route to those pages and the existing assistant picker; they do not select evidence or invoke inference automatically. Unsupported sources/full-document Q&A explicitly abstain. No raw OCR, extracted financial values, paths or source text enter discovery responses/model prompts, caches, memory or cloud. Currency remains unrecorded; no financial, schema, dependency, provider or history activation changes.

`doc07-discovery-first`: 25 executed, one cursor error (tuple/list JSON mismatch); fixed by serializing the file stamp consistently. The original `doc07-discovery-focused` process was interrupted before a receipt, so **NOT_RUN/incomplete**, never PASS. `doc07-discovery-resumed`: **53 backend PASS**, zero failures/skips, including pagination/backward/foreign/tampered cursors, membership/file changes, correction/revocation/deletion races, bank review/citation routing, no inference/cloud/history and synthetic baseline/fingerprint equality (**zero mismatches**). `doc07-discovery-browser-first`: **1 real Chrome PASS**, **19.877 seconds**, synthetic eight-document/seven-linked-record discovery, stale-list rejection, original-status separation, exact citation/revocation, injection-as-text, draft preservation and pagehide clearing. Its desktop and exact-review screenshots were inspected; the first mobile capture showed the page header rather than the new controls, so the final flow must capture the actual discovery panel. Counts overlap other gates and are not added. System/migration drift and JavaScript syntax PASS for the initial implementation.

Independent Reviewer/Security `doc_discovery_review` found one P2 race: bank duplicate/conflicting peer rows and loan payment/closure conflicts can change eligibility without changing the original evidence revision. The repair recomputes the complete current document item on the second pass; two new deterministic bank/loan mutation-between-passes regressions cover those related records. Final repaired-source tests, independent re-review, Council gate, visual/source/privacy closure and ordinary commit are **PENDING** at this precommit checkpoint. Resume from the task handoff and current diff; do not rerun the completed f057d85 unit or claim arbitrary document Q&A. This remains a bounded prerequisite: DOC-07 NOT_IMPLEMENTED, **64/143 verified / 79 remaining**.

Postcommit closure: **696c858d48945a8f COMPLETE** at exact ordinary host commit **43fd6eabdcfbb3b94654bb011997da95324a7398**, all six v2 roles PASS, source fingerprint **fed325cedbbf94936d5aa13bcf0a664f9b2b4908893fe4c4af69d9346c412014**. Actual independent `doc_discovery_review` re-reviewed the repair and both bank/loan regressions with no remaining actionable findings. `doc07-discovery-conflict-revalidation`: **2 PASS**, four related-conflict subcases. Final Council gate: **45 tests = 44 backend + 1 real Chrome PASS**, **39.450s** suite / **53.063s** bounded duration, first attempt, zero failures/skips. Separate repaired-source `doc07-discovery-privacy-compatibility`: **56 backend PASS**, **20.899s**, including canonical, bank, investment/loan grounding, history and session/CSRF. Preliminary counts overlap and are not added. No advisory model call/token reservation, private inference/training or runtime activation.

Final desktop/390px discovery-panel and exact revoked-record citation screenshots reviewed PASS in `artifacts/council/696c858d48945a8f-1/browser/user-data/`. Discovery controls wrap without horizontal overflow; larger lists require vertical scrolling. This is synthetic local browser acceptance, not a normal-account, packaged, separate-PC or full accessibility claim. `doc07-discovery-clean-source` pins 43fd6ea against consolidation fb288465: system/migration drift, exact clean ancestry/declared migrations and privacy **PASS**, **893 paths / 1033 blobs / 39 commits**, six reviewed synthetic patterns, zero findings. No new migration/dependency; only the previously declared investment0005/loan0016 relative to consolidation. JavaScript syntax and documentation validation PASS (143 rows, unchanged C1–C10, zero broken local links); AST-only Graphify exit **0**, 10043 nodes/27154 edges, no paid labeling. The earlier pending text is historical precommit evidence closed by this paragraph.

Next independent safety unit: prove and close inverse document-to-record cursor invalidation when a loan/investment link is removed and re-added with the same final record IDs. Existing record-to-document selection already tracks through-row generations; reuse that pattern, preserve originals/attestations/money and test before/after/during-read plus owner scope. No additional feature-count completion or general accuracy claim. Production/master, frozen candidate, financial data/configuration and recovery assets remain untouched; deployment, FIN-CURRENCY/history/cloud/OpenAI and real acceptance remain gated.

Relink continuation: Council **194ba73f8aeeddfe**, v2 backend profile, pins clean tracker closure **0303ab5ee115db9627e786aafd678d0deb36982f** and exactly three paths: canonical evidence, its existing source-selection tests and this tracker. `doc07-relink-reproduction` executed **1 test with 4 failing subcases**, zero errors/skips: both loan/investment same-ID unlink/relink passed an old cursor or final same-read membership stamp. The repair adds current through-row count/max-generation to the signed discovery stamp, reusing record-to-document catalog semantics. Existing 15-minute cursors without that field fail closed and require refresh; originals, correction/confirmation receipts, record IDs, amounts, fingerprints and currency remain unchanged. No migration, dependency, UI/inference/model or provider activation. This does not add a general bank foreign-key history/audit model or retroactively establish document authenticity.

One synthetic regression checks unchanged retained/current field evidence, fresh-page eligibility, foreign-owner citation denial and all four before/during-read relation changes. Focused repaired execution, actual independent review, Council Tester and exact commit are **PENDING** at this source-bound checkpoint. Final release/package/normal-account/device-loss acceptance remains unexecuted. Counts stay **64 COMPLETE_VERIFIED / 32 IMPLEMENTED_NOT_ACCEPTED / 28 PARTIAL / 11 NOT_IMPLEMENTED / 5 BLOCKED_APPROVAL / 3 BLOCKED_EXTERNAL = 143**, 79 not fully verified (44.8% technical); DOC-07 still lacks arbitrary-document Q&A. Resume the existing Council task/diff rather than creating another copy, audit or checkpoint file.

Postcommit relink closure: **194ba73f8aeeddfe COMPLETE** at exact ordinary host commit **a4d9f013c37d85cabdf11aaedeefa9fe122dcbfd**, all six v2 roles PASS, source fingerprint **8e3868cab026648d492ae6b13947ce2bcb4480d469d4feaa5ca675e94301b19e**. Actual independent `doc_discovery_review` reviewed the final three-path diff and extra foreign-citation assertion: no actionable findings. `doc07-relink-focused`: **1 PASS** (four repaired subcases); final Council first attempt: **45 backend PASS**, **22.770s** suite / **35.047s** bounded duration, zero failures/skips, no advisory model calls/reservations. The pre-fix failure remains preserved. Source/context revision and full evidence equality plus existing baseline/fingerprint checks show **zero mismatches**; a refreshed list remains usable. No browser rerun was needed for this backend-only generation change; the actual prior discovery Chrome receipt is attributed to 43fd6ea, not relabeled as a new run.

`doc07-relink-clean-source` pins a4d9f01 against fb288465: exact clean ancestry/declared migrations, system/drift and pinned privacy **PASS**, **893 paths / 1037 blobs / 41 commits**, six reviewed synthetic patterns, zero findings. No new migration/dependency/configuration. AST-only Graphify native exit **0**, 10046 nodes/27160 edges; no paid semantic labeling. Production/master 3932f391, frozen 4aa7ac70, private records/configuration/keys and all recovery assets remain untouched. No fresh native/package, real-model accuracy, normal-account or independent-recovery acceptance is claimed.

Next bounded DOC-07 backend unit: explicitly select at most three current owned canonical records linked to one supported financial import, reuse their existing reviewed-field/current-source context and exact citations, and revalidate the entire selection before/after local reasoning. Keep each amount/currency status separate, forbid totals/FX/inferred currency and unsupported text/questions, and reject partial/stale/foreign/conflicting selections without model fallback. No raw OCR/full-text indexing or retention, private-history activation, provider contact, model promotion or financial mutation. Start with focused backend/privacy/race/reconciliation tests and an existing Council plan from the clean current HEAD; do not reopen the completed discovery or audit. Full arbitrary-document search/Q&A remains future work and feature counts are unchanged.

### Reviewed AI-quality cohorts and Council execution — 2026-10-19

Retrieval continuation from **57898c96ccd96eb62e41d0ed7d258ca7c4757162**: an independent Codex reviewer committed a new fictional held-out fixture before tuning, SHA-256 **ee0401374fb7c15a4cec65d4a4b5ab3c1199ee3b7d6ac9e27421bc856813208e**, **1587 bytes** compact UTF-8 JSON, no BOM/newline, 12 cases (six positive/six abstention). Contents/expected answers were withheld until candidate policy commit **0651e7a**. Only the existing 24 development cases informed changes. Extra above-cutoff tail matches and one conflicting-source miss were then measured below; the independently authored holdout was disclosed only after source freeze. No private-data tuning, cutoff reduction or runtime activation.

Development-only follow-up: JSON-versus-plain input experiment reproduced original precision **0.50/0.5454545**, recall **1.00/0.75**. Plain statement text alone changed this to precision **0.50/0.50**, recall **1.00/0.875**; it is not a sufficient fix. Full synthetic score traces confirmed extra partial-topic tail matches. The experimental **owner-statement-specificity-top3-v1** protocol now embeds only singleton string statements as text, preserves general structured JSON/content/provenance/deduplication, and prefers complete discriminating word matches only when present among live cosine-eligible sources; otherwise dense fallback remains. No names, fixture IDs or expected answers enter the ranker. Original cosine cutoff **0.45**, result bound three and all quality/drift floors remain unchanged. Raw scores stay cosine, not invented probabilities. Default app protocol remains **owner-cosine-top3-v1**. New encrypted indexes carry a representation marker; legacy/mixed indexes fail closed for the experimental protocol until explicit owner reembedding. No private rewrite or activation.

`retrieval-policy-final-contracts`: **76 backend PASS**; `retrieval-policy-revocation-final`: **55 backend PASS**, including an independently strengthened above-cutoff deletion fallback, encrypted sync/privacy, canonical financial baseline and fingerprint invariance (**zero mismatches**). Counts overlap, not summed. Independent scoped review caught the initial specificity-before-revocation/cutoff ordering bug; fixed and covered. `retrieval-policy-final-real-development`: **1 actual local PASS**, **64.273 seconds**, unchanged 24 development cases, same installed all-minilm model, comparison-local digest-checked embedding reuse. Candidate precision **1.00/1.00**, recall **1.00/0.875**, abstention/citation identity **1.00/1.00**, zero owner violations, stale/foreign guards PASS. Recommendation **ELIGIBLE_FOR_REVIEW on development only**, never promotion/general accuracy. Positive-case fixed-denominator precision@3 **0.444444/0.388889**, recall@3 **1.00/0.916667**; the former is bounded by the number of reviewed relevant labels, distinct from conditional returned-reference precision. Explicit missed/unexpected/false-abstention errors are reported.

**Candidate policy frozen BEFORE held-out reveal at 0651e7a:** LF-normalized SHA-256 of `apps/ml_engine/services/persistent_memory.py` is **1d339250ceddeaf924f7e895e0ad58bfa264dc7b6ef4ce818f297caf8e19afb4**. [Independent fixture](../apps/ml_engine/services/retrieval_holdout.py) enforces exact committed labels and frozen source; changed/missing policy blocks held-out execution without breaking the disabled/default Memory page. A policy change after disclosure requires a new independent holdout, not retuning from these answers. Existing 143-feature counts and production/provider/history restrictions are unchanged.

`heldout-contracts-first`: **14 backend PASS**, zero failures/skips, including immutable fixture/partition binding, correction/conflict/deletion/foreign guards, blocked policy/label tampering before model use, API session/CSRF/no-store, no private-vault reads and unchanged thresholds. Expected-label fake vectors test metric/control contracts only, not accuracy. `independent-heldout-real`: **1 actual local test PASS**, **30.802 seconds**, same installed all-minilm, legacy versus frozen experimental protocol, **12 independent cases**, no policy changes after reveal. Legacy precision **0.80**, recall **1.00**, two unexpected references; candidate precision/recall **1.00**, zero unexpected/missed references and zero false abstentions/matches. Both citation identity/abstention **1.00**, zero owner violations, stale and foreign guards PASS. Positive-case candidate precision@1/2/3 **1.00 / 0.666667 / 0.444444**, recall@1/2/3 **0.833333 / 1.00 / 1.00**. Precision divides by k; recall divides by expected labels. Sparse labels limit precision@3, so it is not compared to the conditional precision floor. **ELIGIBLE_FOR_REVIEW for this partition only**, not general accuracy, sustained drift, distinct-model acceptance or automatic/private activation. Original rejected reference and all failed/incomplete receipts remain preserved.

Council task **00e191d98cb1a5d8**, pinned base **0651e7a**, uses the legitimate host for exactly eight planned source/tracker files. Existing Memory UI now offers explicit development/held-out selection and candidate protocol comparison, exact partition/policy binding, honest same-model protocol-versus-new-model labeling, positive-case ranking/error metrics and per-case fictional aliases. No synthetic citations are presented as private owner records. Independent reviews verified fixture/source hashes and label isolation; a recall-denominator wording finding was corrected. Required host reviews, Council Tester/Chrome, screenshot and exact committed completion remain pending at this source-bound checkpoint; postcommit closure must record actual results. No schema, dependency, financial, cloud/OpenAI/history activation changes.

First Council Tester attempt executed **15 tests**, with **one failed contract assertion** and no skips. The synthetic embedder gives two relevant conflicting records exactly equal cosine scores; production retrieval correctly breaks ties by opaque record UUID, so their alias order is not predetermined. The test now checks both returned aliases without asserting a false tie order. No ranker, labels, quality floors or actual held-out scores changed. Failed receipt retained under `artifacts/council/00e191d98cb1a5d8-1/`; the second bounded attempt must revalidate the changed source and tracker.

Postcommit closure: Council task **00e191d98cb1a5d8 COMPLETE** at exact authorized host commit **238eb730f3c0ceaff3bf88f2df29eaf340635a2b**, all six roles PASS. Second/final allowed Tester attempt: **14 backend + 1 Chrome PASS**, **33.742 seconds**, zero failures/skips; fingerprint **12c160de3cbefdb0792b4459926b3fa0bfc3026f2e43fbc582ab121cb9de4ce3**. Actual desktop and 390px held-out screenshots reviewed PASS under `artifacts/council/00e191d98cb1a5d8-2/browser/user-data/`. Completion independently verifies clean exact Git parent/source; earlier pending language describes the immutable precommit checkpoint. No advisory model was called unnecessarily on this task. Next bounded unit is the explicit COUNCIL-04 continuation below; source/system/privacy and relevant combined closure follow that source unit, without repeating unrelated M16–M21/package gates.

Council efficiency/recovery continuation: task **0e5ebb24f1faf604**, pinned base **b47ebd04a85b08b8f8f2936de1240cf662a9b40e**, changes only the existing Council script/tests and this tracker. Optional advice is keyed to supplied public objective/base/scope/test labels and declared adapter/model, reused without another call or reservation; this is explicitly **not fresh source review**. Failed calls retry only on an explicit request, under two-attempt and conservative token limits; unknown/interrupted spend is never refunded. New tasks reserve at most **8192 tokens total**, existing tasks retain their original **4096** cap; each context/response stays **4096 bytes**, output **256 tokens**, local call **30 seconds**, tests **600 seconds/two attempts**. Developer proposals contain at most four allowlisted planned path/action pairs, no generated commands/code or required-role approvals. Only the legitimate host edits and commits.

New task contract v2 requires explicit safe host aliases and different developer/reviewer identities, rechecked before tests and commit completion; these are host attestations, not cryptographic identity. Historical receipts retain their original contract. Test attempts retain source, status/counts/timing/log references; older failure summaries survive both a direct retry and a source fix/fresh review, with unrecorded timing labeled honestly. Independent review found late-advice/interrupted-status and legacy-summary-loss races; fixed using precise leases, guarded finalization, durable expired outcomes even when retry budget is exhausted, and preservation before review resets. Deterministic interleaving/legacy regressions cover them.

`council-context-proposals-final`: **26 backend PASS**, **40.600 seconds**, zero failures/skips (overlaps earlier 22/25-case iterations). One actual local qwen3.5:4b developer advisory on this public development task returned **ADVISORY_ONLY**, approximately **9.8 seconds**, three bounded path/action suggestions, **3146/4096** conservatively reserved tokens. All required implementation/review/test roles remained NOT_RUN then. A repeated request was demonstrably reused with the provider method forbidden, **zero additional model calls/tokens**, cache hits one. The initial receipt's precommit code says validated_signals_only and explicitly includes validated steps; current code names new such outcomes validated_scoped_proposal, without rewriting historical evidence. Actual host reviews, Council Tester, exact source commit and refreshed status-browser/combined gates remain pending at this precommit checkpoint. No code is executed from model advice, no quota/provider fallback or paid/cloud call, no schema/configuration/financial change.

Postcommit closure: Council task **0e5ebb24f1faf604 COMPLETE** at **cc3e53eb9d90d858105ac022cb185313512eb9c0**, all six roles PASS, actual distinct host developer/reviewer aliases retained. This task was planned under its original v1 contract; new v2 attribution enforcement is demonstrated by deterministic contracts, not retroactively asserted for historical tasks. Council Tester **40 backend PASS**, **60.861 seconds** test time / **72.859 seconds** bounded operational duration, zero failures/skips; fingerprint **1bf7ab5f448f99ea2285ccf219f19685f1d628c5fc1dc47e15d2c30fc6c2ef8c**. Fresh-process exact committed completion passed. `council-proposals-status-browser`: **1 standalone Chrome flow PASS**, persisted completion/commit/proposals/attempt history/cache/aliases displayed, 390px scroll width **390**; actual desktop/phone screenshots reviewed PASS.

Combined closure `quality-council-heldout-final-backend`: **299 backend PASS**, zero errors/failures/skips, against application/Council source **cc3e53e**. Covers quality/ranking, encrypted retrieval/recovery/checkpoints/mock sync, owner/session/CSRF, disabled private history/public-only reasoning, canonical/bank grounding, user reset, Decimal baseline and statement/transfer identity. Synthetic financial comparisons **zero mismatches**; no new migration/dependency. `quality-council-heldout-final-chrome-corrected`: **4 Chrome PASS**, **52.466 seconds**, no failures/skips. Initial four-flow run had three intercepted login clicks because the earlier comparison fixture did not clear mobile emulation. Added its missing cleanup; application/authentication behavior unchanged. Failed receipt retained. Source/system/drift/privacy at cc3e53e PASS (**893 paths / 1013 blobs / 33 commits**, zero findings), comparison baseline fb288465. AST-only graph update exit **0**, no semantic API calls; community labels are partly stale after graph restructuring and remain unrefreshed rather than enabling an LLM. No fresh native/package or normal-account/provider/device-loss acceptance is claimed. These gates overlap focused runs and are not summed.

Automatic next unit: Council task **545cbf8e08f20704**, pinned base **4b6fbdeed6bf24dd9ca86c3fa33c67afe3b7f1cb**, original **v2** contract, only script/tests/tracker. Existing handoff and local status now expose deterministic next-host-action recommendations: implementation, current-source independent/security review, scoped tests, active-worker wait, explicitly confirmed interrupted-worker recovery, exhausted budget and authorized-host commit verification. Missing planned source files are handed to the host without creating them. Invalid source/scope/base blocks; stale reviews are never reused. Incomplete test receipts route to repair, current PASS/incorrect stage to explicit receipt review, not automatic repeat. Completed receipts are expressly historical. Routing never calls a model, runs a command, mutates roles or grants approval. Independent review: no remaining findings. Initial focused **29 backend PASS**; expanded final contracts and exact source-bound Council Tester/commit/HTML acceptance remain pending at this precommit checkpoint. Application/financial/schema/frontend code is unchanged after the 299-backend/four-Chrome gate; only relevant Council checks need repeating.

Final closure — **2026-10-19**: task **545cbf8e08f20704 COMPLETE** at **d5078b97d9089dcf8b855e9d5beb39acb600c5c8**, all six v2 roles PASS, source fingerprint **23513fa2855a6e0be6057c79adee933580c788d1c8d36de4f2d8295e812c5cbe**. Actual handoff progressed from host_implementation_review to run_scoped_isolated_tests, then authorized_host_commit_then_verify; the host made the ordinary exact commit and Coordinator independently verified it. Actual Tester **30 backend PASS**, **53.249 seconds** test time / **55.953 seconds** bounded duration, zero failures/skips; **zero model calls/reservations**. `council-routing-status-browser`: **1 separate Chrome flow PASS**, persisted completion/attribution/current recommendation/history, desktop/390px screenshots reviewed PASS; width and scroll both **390**. Together with the earlier proposal-status flow these are two independent status-browser checks, not six Django Chrome tests.

`heldout-council-routing-clean-source`: system/drift, exact clean source/ancestry/declared migrations and pinned privacy **PASS**, **893 paths / 1018 blobs / 35 commits**, zero findings, candidate d5078b9 / consolidation baseline fb288465. No new migrations/dependencies; no application/frontend changes after the 299-backend/four-Chrome gate. AST-only graph exit **0**, no API cost; old community labels may be stale and were not regenerated through a model. Documentation validation: **143 feature rows**, exact unchanged C1–C10, valid local links and unchanged counts **64 verified / 32 unaccepted / 28 partial / 11 missing / 5 approval / 3 external**. Technical completion **44.8%**, 79 not fully verified; retrieval/Council progress does not certify whole-product accuracy or acceptance.

Current runtime/source is fully committed at d5078b9; the closing tracker commit only records these receipts. Production/master **3932f391**, frozen **4aa7ac70**, private databases, backups and runtime/provider/history flags untouched. Production DOWN remains the last historical operational finding, not a fresh service probe. Remaining blockers: broad/chronological/distinct-model quality and explicit experimental-private migration approval; FIN-CURRENCY contract, private-history activation/recovery/retention, real provider/cloud/OpenAI authorization; normal-account, fresh native/package/installer/separate-PC and independent device-loss acceptance. No M15 waiver is inherited. Next independently safe implementation is the DOC-07 bounded owner-reviewed document eligibility/provenance adapter below; inspect existing extraction/review/citation paths, not a new project audit. Do not retune the disclosed holdout or repeat completed Council setup.

[Synthetic comparison service](../apps/ml_engine/services/retrieval_quality.py) reuses MemoryLearning/MemoryStore in disposable encrypted vaults. Two source-reviewed fictional contracts contain **24 questions per model** (12 positive/12 negative), corrected/superseded/deleted/foreign records and explicitly conflicting relevant statements. The versioned manifest binds the exact cohort labels. Each cohort requires precision **≥0.90**, recall **≥0.85**, negative-case abstention **≥0.95**, citation identity **1.0**, zero owner violations and successful foreign-reference/stale-deletion probes. Maximum allowed precision/recall/abstention drop versus baseline: **0.05**; citation/privacy/stale regressions have zero tolerance. Missing/invalid/incomparable evidence blocks; failures reject. A passing new-model comparison is only **ELIGIBLE_FOR_REVIEW**, never runtime promotion, general accuracy or sustained drift proof.

The existing Memory UI displays floors, per-cohort baseline/candidate/deltas, per-case counts, safety guards and explicit incomplete/outage states. Comparisons only accept two approved installed local embedding tags, never download a model, share a **120-second budget** across preparation and inference, and revalidate sessions on errors too. Identical model selections use one measured reference with `baseline_reference_reused`, never independent new-model evidence; otherwise both models are measured separately. Cross-cohort model identity changes fail closed. Operator setting `ALFRED_SYNTHETIC_QUALITY_ENABLED` defaults **OFF**, like cloud/OpenAI/history activation; tests enable it only in disposable settings. Comparison reads no private user vault and returns no synthetic memory UUIDs or false owner citations.

`quality-cohorts-final`: **66 backend PASS**, zero failures/skips, including thresholds, real cosine/label regression, incomplete/invalid results, ownership, shared deadlines, current private evaluation, history/session/CSRF compatibility and synthetic financial invariance. `quality-cohorts-final-chrome`: **2 Chrome PASS**, including original Memory evaluation compatibility, comparison/mobile/outage/page-hide and refresh cancellation on successful/failed refresh. A login-animation timing failure was a fixture hit-target race; the fixture now waits for the auth-panel animation before clicking. Scope review found the refresh cancellation gap, which is fixed and covered. Early failing fixtures/receipts remain preserved.

Actual Ollama `quality-reviewed-cohorts-real-reference`: **1 integration test PASS**, **52.770 seconds**, all-minilm:latest, cutoff 0.45, one reused same-model reference, **quality decision REJECT**. Preferences cohort: precision **0.50**, recall **1.00**; correction/conflict cohort: precision **0.5454545**, recall **0.75**. Both: abstention/citation identity **1.00**, zero owner violations and both foreign/stale probes rejected correctly. This is broader fictional evidence than the previous three cases, not general/real-account accuracy. The first redundant same-model double run hit the 120-second budget; it returned no verdict, is preserved, and is not counted as quality success. No threshold was lowered to hide the measured failure. Distinct real-model acceptance remains unperformed; no model/runtime/provider/configuration was changed.

Quality unit committed as **1de014398257dfa5c188f78e06cce754fdf33b41**. Council core reuses [release helpers](../scripts/release_gate.py), [isolated/redacted test adapters](../scripts/release_validation.py), tracked skills and the existing local Ollama transport through [development_council.py](../scripts/development_council.py). The deterministic planner selects only noncomplete feature rows explicitly marked COUNCIL_SAFE_LOCAL below. Six roles are tracked; Developer is a legitimate Codex-host/human handoff, Reviewer/Security require explicit current-source host attestations, Tester executes real isolated house suites, and Coordinator verifies the host's expressly authorized exact Git commit. The Council itself never edits/stages/commits source, changes Git refs, runs generated commands or deploys. Ollama is a provider-neutral bounded advisory and cannot approve required roles or cause a provider/quota fallback.

State is owner-protected SQLite plus an escaped local HTML interface under ignored `artifacts/council/`; this is operational evidence, not another status/roadmap document. Tasks deduplicate by reviewed objective, pin base/branch/scope/full source including this tracker, preserve interrupted tests, reject changed reviews, cap retries at two and reserve advisory input/output budgets. Native profiles share the same execution deadline and require a fresh passed nonempty report, an identical retained artifact/hash and final source revalidation. State/report symlinks/hardlinks fail closed. `council-core-corrected`: **16 backend PASS**, zero failures/skips (nine Council contracts plus seven quality contracts; overlaps earlier gates). Disposable Git acceptance includes exact host commit completion/reopening, duplicate tasks, blocked approvals, source/tracker invalidation, no-test evidence, model failures/budgets, interruption, native report/budget/source contracts and safe HTML. These are not actual fresh native or production acceptance. Scoped Codex review findings on refresh, source binding, automatic commit races and evidence are addressed by regression tests and the host-only commit design. The first core run's mock-result alias produced circular test data; corrected fixture passes. Core commit: **2a0aae72e23cb4e4f3d1e1c9bbfeea9d6843027e**.

Council task **8b90e347fe099efa**, pinned base **2a0aae72e23cb4e4f3d1e1c9bbfeea9d6843027e**, completed at **bbb03ddca95eb325ae441fdab6f11c84a97f5482**. Legitimate Codex-host handoff implemented public fictional expected/returned/unexpected/missing source aliases, expandable case explanations, cohort/policy identity and independent-versus-reused model context in the existing Memory comparison UI. Exactly five planned source/tracker files changed; no private IDs/citations, model tuning, schema or financial/provider/history changes. Required Planner/Developer/Reviewer/Security/Tester/Coordinator all **PASS**. Actual isolated Tester: **8 backend + 1 Chrome PASS**, zero failures/skips, one of two allowed attempts; source fingerprint `dec5321b9ce85c7edafba6ddbf8909a33e95fb81d4c71a120b09a017efb991f9`. Scoped review caught and fixed a missing-measurement label that incorrectly implied independent execution. Mobile screenshot reviewed: PASS. Exact immutable host commit verified after clean ordinary Git commit, then reloaded through a fresh Council process with stage COMPLETE. A separate optional real-local planner advice attempt returned **BLOCKED**/needs_review, retained no raw output and approved no role; no retry or provider/quota fallback. Conservative advisory reservation: 2734/4096 tokens, not measured usage. The task's precommit source-bound tracker said pending; this postcommit receipt is the closure. Run `scripts/development_council.py status --task 8b90e347fe099efa`; state/HTML holds role/test evidence without replacing this master tracker.

Reporting correction follows the observed optional-advice failure: `advise` now exits **2** when advice is blocked, rejects late/oversized replies, and the local HTML explicitly shows optional-advice results, required-role blockers and reserved budgets. It never converts a blocked model into a failed or successful host review. `council-advisory-failure-status`: **19 backend PASS**, zero failures/skips (11 Council + 8 quality contracts, overlapping earlier tests). Independent scoped code/privacy review: no additional actionable findings. Actual standalone Chrome status flow **PASS**, persisted COMPLETE/host commit, optional BLOCKED and reservations visible after restart; desktop and emulated **390px** screenshots reviewed PASS. The first phone check exposed table overflow (438px); fixed wrapping and the retained final receipt confirms 390px viewport/scroll width. Evidence: `artifacts/council/8b90e347fe099efa-1/status-browser-final.json` and `council-status-final-*.png`. This separate local-file flow is not a Django or real-account test. Final combined/source closure follows below.

Closing source **5e365d0e4f7220e5785b2ddc30a530f06ceee09a**: `quality-council-final-backend` **214 backend PASS**, zero failures/errors/skips. This single combined run covers Council/quality, existing memory learning/evaluation/encryption/privacy/checkpoints/mock sync/retries, public-only reasoning and hybrid/UI contracts, private history kept disabled, session/CSRF, canonical finance and expense/fingerprint invariance. Synthetic financial comparisons: **zero mismatches**; no production data read or changed. Earlier overlapping test counts are not added. `quality-council-clean-source`: exact clean ancestry/source, system, migration drift and privacy **PASS**, **892 paths / 987 blobs / 25 commits**, zero findings, pinned to 5e365d0 and consolidation baseline fb288465. No new migration/dependency; the two existing investment/loan receipt migrations remain the only declared changes relative to that baseline. JavaScript syntax PASS. AST-only graph refresh completed with native exit **0**; extraction warnings concern symbol-free modules, not failed code validation. No semantic/paid graph update. Documentation: **143 rows**, category totals consistent, no broken local links and C1–C10 unchanged. Production/master still 3932f391; frozen 4aa7ac70 preserved; only production and this one development worktree registered. No fresh native/package, real-account or independent-device recovery acceptance claimed.

The original structured-advice, held-out, recovery and deterministic-routing units above are completed. Next independently safe unit is DOC-07 below. The first advisory's cause remains unclassified; later success does not retroactively relabel it. Legacy embedding rejection remains; experimental held-out review eligibility is not runtime promotion.

Council task **e4e15415160cbf97**, pinned base **33b00d456fc9a7b4081582ce2a6811146bf0e224**, implements only safe advisory failure categories and a development-specific structured signal contract. It reuses the existing fixed-loopback Ollama HTTP/digest transport, installed **qwen3.5:4b**, 30-second deadline, 4096-byte context/response bounds, 256 output-token cap and conservative reservation policy. The local adapter no longer imports/configures Django or reuses the financial-answer prompt. Local schema support was checked against [official Ollama structured-output documentation](https://docs.ollama.com/capabilities/structured-outputs); no dependency, key, runtime-model setting or private-data access changed. Invalid JSON/schema, duplicate/unsupported signals, late/oversized responses, transport failures, model changes and tool calls fail closed with allowlisted categories, never raw exception/model text. Historic unclassified advice is displayed as legacy_unclassified rather than retroactively guessing its cause.

One actual bounded local planner advisory on this public development objective returned **ADVISORY_ONLY / validated_signals_only**, signal clear, approximately **9.8 seconds**, 2753/4096 conservatively reserved tokens. Developer/Reviewer/Security remained NOT_RUN at that point, proving model advice does not satisfy those gates. Independent Codex review then found a test indentation error, corrected before execution; final source/privacy review had no remaining findings. Actual Council Tester: **14 backend PASS**, **19.026 seconds**, zero failures/skips, one of two allowed attempts. Required roles all PASS after legitimate host review/test evidence and exact ordinary commit verification at **00aca63a8e2f584ffa8c0be1c9bc98955810d2dd**; source fingerprint `e70d9ad995511b26c95931d1df4cc1bbb4cd3f4b93101653f4b4cc6afcfe0cd0`. The precommit tracker said pending because its content is source-bound; this is the postcommit closure. No paid/cloud calls, quota fallback, model-generated code/command execution or general review-accuracy claim. Earlier blocked advice and embedding-quality REJECT remain preserved.

Follow-up `council-signals-source`: exact clean source/ancestry/privacy **PASS**, **892 paths / 991 blobs / 27 commits**, zero findings, pinned to 00aca63 and consolidation baseline. Fresh-process state reopened COMPLETE; actual standalone Chrome status flow **PASS**, including both tasks, legacy BLOCKED versus validated ADVISORY_ONLY, current commit and budgets. Desktop/390px phone screenshots reviewed PASS in that evidence directory. AST-only graph native exit **0**. No migration/dependency/application change in this follow-up; system/drift and the broader 214-test evidence above remain scoped to their actual source. No fresh native/package or real-account claim. The two missing Council capabilities now have bounded prototypes (PARTIALLY_IMPLEMENTED); totals remain **64/143 verified, 79 remaining**. Approval-gated FIN-CURRENCY/history/cloud/OpenAI and operational recovery/acceptance blockers are unchanged.

Exact resume commands after reading this tracker; define the next bounded Council scope only after inspecting these existing document paths:

```powershell
git status --short
git rev-parse HEAD
Get-Content docs/PROJECT_STATUS.md -TotalCount 145
& 'C:\Users\soura\.local\bin\graphify.exe' query 'document_extraction document_review canonical_evidence owner-scoped document grounding' --budget 1800
```

Consult the configured Python SDK as required before executing Python. The SDK above is used read-only with bytecode disabled; all source, task state, runtime fixtures and databases stay in this development checkout/disposable directories. The planner emits a pinned scope and task ID, not permission to change models, production or paid providers.

### Multi-case private memory retrieval evaluation — 2026-10-17

Backend unit reuses [MemoryLearning.evaluate](../apps/ml_engine/services/memory_learning.py) and the existing session/CSRF/no-store API. It accepts legacy single expected_id or an owner-reviewed expected_ids set per question, capped at 20 cases/8192 total UTF-8 query bytes/three returned references per case. Reports include per-case IDs, ranked owner citations, relevance/miss counts, precision/recall and abstention, plus aggregate precision, recall, ranking, exact match and negative-case false-positive/abstention metrics. Empty denominators remain not applicable. Citation correctness means current owner/record identity, not semantic truth or bank authenticity. Conflicting owner-confirmed statements can both be relevant and are never resolved or promoted by evaluation.

The whole report is rejected on invalid/foreign/duplicate references, nonfinite scores, corrections, deletion, expiry, changed owner snapshots or a session revoked during evaluation. Queries, source contents, provenance and results are not persisted by evaluation or sent to reasoning/cloud/training. Only local embeddings run. No schema, financial writes or approval-sensitive activation. Backend committed as **f03ee6d4855ac4e3248204cf29c76b8c1d713e4c**. `memory-multi-case-backend-one`: **96 backend PASS**, zero failures/skips, including new multi-case/privacy/revocation tests and existing memory/history/session/UI contracts. Deterministic five-case fixture: precision/recall/negative-case abstention **1.0**, three correct current-owner citations; a deliberately imperfect fixture measures **0.5 precision / 2⁄3 recall / 1.0 negative false-positive rate**, proving mismatches are represented. These are synthetic fixture metrics, not personalized model quality.

UI unit extends the existing Memory settings form with queued cases, multiple relevant labels, a finite relevance cutoff, understandable per-case results and current-owner memory links. No-match cases remain explicit; source corrections/deletions never silently relabel expected results. Failed runs preserve question drafts; refresh clears stale results, and page-hide clears cases, source-label cache and result details while aborting the client request. Model outages are safe/retryable, and model text is never rendered as HTML. `memory-multi-case-chrome-one`: **4 Chrome PASS** (new cohort metrics/citations/mobile/privacy and stale-source/outage retry plus existing candidate correction/stale draft compatibility). `memory-multi-case-chrome-labels`: **2 Chrome PASS**, overlapping targeted reruns after readable source labels and error-control cleanup. Zero failures/skips. Desktop/mobile and retry screenshots reviewed under those directories: PASS. JavaScript syntax PASS. Next independently safe unit: shared batch deadlines through the existing local embedding adapter, then bounded real-local synthetic retrieval measurement. No activation or production claims; AI-16 stays partial and counts remain 64/143.

Continued with that independent execution-safety unit: all cases share a **60-second monotonic processing deadline**, passed through existing MemoryStore retrieval, local model-digest checks, embedding HTTP and final source revalidation. Late results are discarded; later queries do not start after expiry. Each socket wait remains bounded to 30 seconds, with a 75-second client transport grace/cancellation timer. Normal callers without deadlines retain their existing behavior. No source locks are held across inference. `memory-evaluation-budget-backend`: **183 backend PASS**. Final broader `memory-evaluation-final-backend`: **254 backend PASS**, including cloud/mock-sync/runtime/checkpoint compatibility, financial grounding, history, owner/session/CSRF, release-validation and resource cases. Synthetic financial/family rows, transfer/statement fingerprints and canonical Decimal baseline: **zero mismatches**. No migrations or dependencies added.

`memory-evaluation-budget-chrome-corrected`: **3 Chrome PASS**, including actual delayed-request cancellation/page-hide, cache restoration, a refused 21st question with all 20 existing cases/draft preserved, current source citations and safe outage retries. The first budget browser gate exposed an empty restored selector; default no-match initialization and busy-state cleanup are fixed without silently relabeling stale source IDs. Its failed receipt remains preserved. `memory-evaluation-citation-metrics-chrome`: **1 Chrome PASS**, an overlapping final display check for per-case and aggregate citation correctness. All final gates have zero failures/skips; counts overlap and are not added. Actual current desktop/mobile screenshots reviewed; same-host synthetic browser acceptance only.

Separate `memory-evaluation-real-local`: **1 actual Ollama embedding/index-reopen PASS**, fictional data only, test duration **17.434 seconds**. Installed all-minilm:latest, cutoff **0.45**, three cases (two positive including two conflicting relevant statements, one negative): measured precision/recall/recall@3/MRR/top-1/exact-match/negative-case abstention/citation-record correctness **1.0**, negative false-positive rate **0.0**, three owner-correct references. Superseded/deleted/foreign IDs remain excluded and encrypted index reopening preserves owned records. Machine-readable metrics: `memory-evaluation-real-local/quality.json`. No model download, reasoning generation, private/cloud upload or training. This is a bounded integration fixture, not statistical accuracy, semantic truth, contradiction resolution, sustained drift or real-account acceptance. Exact-source/system/drift/privacy closure follows the committed unit; frozen/native packages are not rebuilt.

Follow-up error-path regression reproduced expiry during a failed evaluation: success-only session revalidation could let Django SAVE_EVERY_REQUEST renew an expired session on a conflict response. Evaluation now finalizes with the existing fresh-session check on both success and failure, flushes expired sessions, and exposes no partial report. `memory-evaluation-session-final`: **56 backend PASS**, zero failures/skips, including the new expiry/conflict regression, memory learning/evaluation, private history and session/CSRF security. The failing reproduction and a separate mistyped test-label loader error remain preserved; the corrected final gate passes. No unrelated session behavior or activation changed.

Closing runtime source **cd64443426fd0cda8c31045404107dc61824beb7** is committed. `memory-evaluation-session-clean-source`: Django system/migration drift, exact source/declared migrations and pinned privacy PASS, **887 paths / 956 blobs / 18 commits**, zero findings. The comparison baseline is development consolidation fb288465, not production M15. No new migration/dependency from evaluation. Documentation checks still require 143 original feature rows, intact C1–C10 and valid local links. Feature counts remain **64 verified / 79 remaining**, AI-16 partial; broader quality, chronological/drift and normal-account acceptance remain unproven. Continuing only the independently safe model-context prerequisite in this same worktree; no private cohort persistence or approval-sensitive activation.

Continued model-context unit — **2026-10-19**: the existing MemoryStore now describes only the owner's indexed embedding identity (SHA-256 of the stored model identity), vector dimensions and eligible record count. Evaluation binds this profile before/after the run, rejects mixed or changed profiles, and includes a versioned cosine/top-three protocol plus explicit no-cohort-persistence/comparability limits. It never returns vectors, raw model strings, query hashes, source content or another owner's profile. Empty vaults have no indexed model; no fictitious model run is claimed. UI displays a short model fingerprint and readable context, while requiring the same full model identity, cutoff, reviewed cases and source revisions for meaningful comparison. Matching these alone is not sustained drift evidence. No financial/schema/configuration changes or automatic model training.

`memory-evaluation-model-context-corrected`: **102 backend PASS**, zero failures/skips, including model/profile isolation, mixed-model rejection before inference, concurrent profile changes, financial baseline/fingerprint invariance, encrypted restore/sync, history and session/CSRF compatibility. An earlier runner used a nonexistent test label; its loader-only error receipt is preserved. `memory-evaluation-model-context-chrome`: **3 Chrome PASS**, zero failures/skips, covering current metrics/context/citations, mobile rendering, stale-source and outage retry, page-hide cancellation, cache return and case limits. Desktop/mobile screenshots reviewed: PASS. `memory-evaluation-model-context-real-local`: **1 actual local PASS**, fictional cohort, **5.087 seconds**; all-minilm:latest, **384 dimensions**, three current owned records, cutoff **0.45**, the same three positive/negative cases and **1.0 precision/recall/abstention/citation-record correctness**. This bounded result is not statistical accuracy or real-account acceptance. These gates overlap preceding gates and are not summed. Source/privacy/system/drift closure follows this committed unit; no frozen/native rebuild is required by these changes.

Latest verified runtime **9356ad963ddc811c382b8dde4578e31d15ff1616**: `memory-evaluation-context-clean-source` system/migration drift, exact clean fast-forward/declared-migration checks and pinned privacy PASS, **887 paths / 965 blobs / 20 commits**, zero findings. AST-only graph update and JavaScript syntax PASS. Master-document validation PASS: **143 feature rows, zero broken local links, C1–C10 unchanged**. No new migrations/dependencies, no financial mismatches, no fresh native/package or real-account acceptance. Resume the reviewed-synthetic comparison unit below; all implementation and evidence are saved in this single development worktree and tracker. Frozen 4aa7ac70, production/master 3932f391, private data, recovery assets and GitHub remain untouched; OpenAI/cloud/private history remain OFF.

### Explicit financial source selection — 2026-10-17

First backend unit adds owner-only keyset pages of five linked sources and explicit selection of one to five current reviewed document revisions. Signed, owner/record-bound catalog cursors expire after 15 minutes and reject record or membership changes; each chosen source is revalidated before and after inference. No silent truncation or replacement: distinct files with identical contents conflict, revoked/missing/changed sources fail closed, and all unselected linked documents remain explicitly unreviewed. This selects evidence for one supported canonical record, not arbitrary PDF Q&A or mixed-currency totals. Existing bank, investment, loan and canonical financial services/calculations remain authoritative. No schema, dependencies, source text transmission, history activation or financial writes.

`source-selection-unit-one`: **57 backend PASS**. `source-selection-backend-corrected`: **119 backend PASS**, including Banking, field review and history compatibility. `source-selection-history-ui-backend`: **62 backend PASS**, including exact amount-free history references, replay/selection binding, existing session/CSRF, UI contracts and release validation. Each run has zero failures/skips; overlapping counts are not added. Synthetic financial/register/fingerprint and baseline reconciliation: **zero mismatches**. The initial wider command had one misspelled test-module import; its failed receipt is preserved and the corrected label passed. UI/source certification/browser acceptance remain pending for this backend checkpoint. Exact current commit is obtained by the resume command above; this is not a new frozen release or production remediation.

UI/cursor unit: assistant selection persists across keyset pages, exposes linked-file count/type/upload date/current or partial review status, supports explicit single/multiple selection and removal, prevents a sixth selection and shows each chosen source's private citation. Revoked/stale selections block and preserve the question draft; manual refresh requires current revisions. Page-hide clears names/tokens/choices and stale asynchronous responses cannot repopulate them. Existing small-history automatic behavior remains; larger histories require explicit selection. Model inputs exclude file names, source URLs, tokens and raw extraction. Saved history (synthetic opt-in tests only) retains reference allowlists, not copied financial facts; activation remains OFF.

`source-selection-final-backend`: **204 backend PASS**, zero failures/skips, including processing-limit visibility/413, partial field confirmation, financial baseline/fingerprint invariance, Banking, loan/investment proofs, history, session/CSRF and M14 resource/diagnostic compatibility. `source-selection-chrome-corrected`: **6 Chrome PASS**; `source-picker-mobile-bank`: **2 Chrome PASS** (one repeated picker flow and bank compatibility; not eight unique workflows). Actual desktop/mobile picker, stale-draft and exact older-source screenshots reviewed under those evidence directories: PASS. The first browser gate exposed a backward-page token replacement bug; signed first-page cursors now preserve the catalog, with a time-separated backend regression (`source-selection-back-cursor`: **25 PASS**) and successful browser reruns. Earlier failed receipts remain preserved. The first separate real-Ollama attempt hit its 180-second outer harness timeout; `source-selection-real-local-retry` **1 real-local synthetic PASS**, zero failures/skips, test duration 19.349 seconds with a bounded 300-second outer startup/test allowance. Actual installed local model selects one owner-confirmed source from seven linked documents, returns the exact citation/canonical EMI and records no currency. Application inference remains capped at 30 seconds. No model installation/configuration, provider activation, migrations/dependencies or production changes; final clean-source/system/drift/privacy certification follows committed source.

### Financial question-domain accuracy — 2026-10-17

Next independent AI-GROUND/AI-QUALITY unit: [intent gate](../apps/ml_engine/services/canonical_evidence.py) now binds domain-specific supported questions to the selected canonical record. Shared record/evidence/provenance questions remain supported; loan/EMI/repayment, investment, expense/transaction, budget and reported income/rent questions only match their corresponding source. Incompatible questions abstain before memory retrieval or model inference; owner checks, exact Decimal/source cards, no FX/unknown-currency totals, local-only restrictions and draft preservation remain intact. No new calculator, model, schema or approval-sensitive activation.

Reproduction: `scoped-question-reproduction` failed five domain-mismatch subcases inside one test; no production data involved. Corrected `scoped-record-question-backend`: **106 backend PASS**, zero failures/skips, including the cross-domain positive/negative intent matrix and existing bank/history/selection/payment/baseline compatibility. `scoped-record-question-chrome`: **2 Chrome PASS**, zero failures/skips, including wrong-domain abstention, preserved draft, supported multi-domain questions, stale-source rejection and owner citations. Actual abstention screenshot reviewed: PASS. These counts overlap earlier gates and are not added. Broader natural-language/document understanding and sustained retrieval/drift quality remain partial; this correction does not claim general financial Q&A or completed product acceptance.

Closing runtime **d04a7cc** is committed and clean. `source-selection-final-checks`: Django system/migration drift, exact clean source/ancestry/declared migrations and pinned privacy PASS; **885 paths / 930 blobs / 13 commits**, zero findings against consolidation baseline fb288465 (not a newly claimed production baseline). No new migrations or dependencies in these units; only the pre-existing two receipt migrations are declared relative to consolidation. `source-selection-native-smoke`: **19 source-native checks PASS**, including actual isolated HTTP/Chrome/offline assets, worker/scheduler crash/retry, restart persistence, private upload ownership and independent synthetic backup/restore. Its original report is copied with matching SHA-256 to `source-selection-native-smoke/native_report.json`. This is same-host source evidence, not a fresh packaged/installer/separate-PC acceptance. AST-only graph update and JavaScript syntax PASS. Master-document check: **143 features, no broken local links, unchanged C1–C10**. Final documentation-only closure receives a separate pinned source/privacy scan under `source-selection-closing-source`; no runtime tests are represented as newly rerun for that documentation commit.

Integration failure fixed: the first source-native run passed 28 checks but exhausted its synthetic expensive-account quota of 64 at post-restart retrieval (HTTP 429; persisted counter confirmed exactly 64 reservations). The drill now allows 128 only under its existing `--memory` synthetic mode; application/default production quotas are unchanged. A fresh complete source-native run passed, including actual local Ollama, encrypted-vault retrieval, outage recovery, worker crash/retry, scheduler, restart, local backup/restore, deletion and owner isolation. Failed receipts/partial report are retained; reruns are not summed. Fresh packaged candidate, independent PC, normal account and device-loss acceptance remain unclaimed.

### Investment field provenance — 2026-10-17

Source: [receipt service](../apps/investments/services/document_evidence.py), [owner API](../apps/ml_engine/api/investment_evidence.py), [private review](../templates/document_field_evidence.html). Three supported fields: invested_amount, monthly_sip and current_value. Parser values retain original decimal text; current corrected Decimal cents remain authoritative. No raw OCR/account/note contents enter the evidence API or memory. Legacy originals are explicitly not_retained; missing files/partial parses block confirmation. Revocation and record/file changes invalidate confirmations. Renamed/deleted holdings preserve original receipts under their source document; document/account deletion cascades receipts. Existing historical backups may retain older evidence.

Additive migration `investments.0005_investment_document_evidence`, dependent only on existing investments.0004. No backfill, money rewrite, dependency or currency schema. An empty receipt table reverses normally; reverse with receipts refuses to discard original evidence. Use the verified pre-migration source/data recovery path, preserving subsequent writes; never blindly drop the table. Synthetic alias rehearsal verifies exact forward plan, independent SQLite backup/restore, integrity/FK checks, original database hash, unchanged financial/family/fingerprint rows, empty reversal and guarded nonempty reversal.

`investment-unit-one`: **96 backend PASS**, zero failures/skips, including receipt/migration, existing Investment money, document correction/retry, bank and canonical sources. `investment-upload-final`: **18 backend PASS**, zero failures/skips, including extended upload precision/atomic ownership and migration rehearsal; overlaps the 96 and is not added to it. `investment-field-chrome-corrected`: **2 Chrome PASS**, zero failures/skips (new field selection/confirmation/revocation, correction/stale-file error with preserved choices, mobile/privacy clearing, existing bank confirmation compatibility). Desktop/mobile screenshots reviewed in its browser/user-data directory. Initial fixture/expectation failures and first browser failure are preserved. The existing upload middleware returns a safe HTTP 500/error reference on synthetic operational failure; tests must not expect an unhandled raw exception. The browser work also restores display of validated safe reference IDs in the shared review error UI. JavaScript syntax PASS. System/drift subprocesses PASS; source certification correctly refused the uncommitted worktree and will be rerun after commit.

Unit 2 connects per-field attestation and exact source IDs to the existing canonical financial tool and citations. Fields are only labeled owner_confirmed_document_field when their confirmed value exactly matches the canonical snapshot being presented. All three fields confirmed against one document link directly to its private review; partial/multiple evidence remains explicit on the canonical page. At most five document files are read per holding; larger histories abstain pending explicit source selection. Revocation/file removal drops the document-verification label, while current register facts remain honestly user recorded rather than disappearing. In-flight source changes reject the answer. No originals, account hints, names, file URLs or OCR enter local model prompts; explicit cloud consent is refused.

Race regressions bind the confirmation revision to the actual displayed record snapshot, and prevent a newly confirmed value from certifying an older concurrent canonical read. No financial/calculation/fingerprint mutation. An existing history privacy test was timing-dependent: `2.68` can occur in an allowed timestamp. It now fixes the timestamp to contain that text and verifies the exact source-reference allowlist and amount-free narrative, rather than searching the entire timestamp-bearing JSON. This is test-only; private history remains OFF.

`investment-grounding-final-focused`: **106 backend PASS**, zero failures/skips (current investment receipts/races/migration, canonical tools, bank/history, document/currency, financial baseline, reset and session/CSRF). `investment-grounding-chrome`: **4 Chrome PASS**, zero failures/skips (assistant → exact field citation, per-field review/stale/mobile, existing canonical and bank workflows). `investment-real-ollama`: **1 separate real-local PASS**, bounded installed-model inference with synthetic confirmed holding fields; no model download, paid call or live configuration change. Earlier failed focused runs are retained; counts overlap and must not be added. These are local acceptance results, not broker accuracy, real-account or packaged-release acceptance.

Final boundary correction: preserve the existing lazy `begin_upload_writes` scope after bounded extraction; the investment upload view must not wrap heavy parsing in an extra SQLite write transaction. Regression fixtures now exercise the real parse/persist boundary and verify no extra transaction during extraction plus whole-import rollback on failed receipt capture. HTML citations return safe HTTP 413 on resource limits and reference-bearing 503 on unexpected investment-source failures; ownership 404 remains intact. Assistant evidence no longer dumps the internal document-source array; owner citation links remain functional. FileResponse fixtures explicitly close downloads before Windows disposable-directory cleanup.

`investment-final-upload-resource`: **97 backend PASS**, zero failures/skips (current import/receipt/migration, M14 upload limits/loan diagnostics, retry and release validation). `investment-safe-errors-corrected`: **41 backend PASS**, zero failures/skips (final source/error/ownership/race/timestamp conditions). `investment-final-browser`: **2 Chrome PASS**, zero failures/skips, after the source-display correction. These overlap other focused runs. `final-native-schema` at 57621f2: **19 source-native checks PASS**, including fresh schema startup, server/worker/scheduler, queue/restart persistence, source/private media and independent synthetic backup/restore. Earlier full native/Ollama 34 and dedicated investment real-local 1 remain separate evidence.

`final-source-checks` at clean 57621f2: system/drift/source/declared migration/privacy PASS, 876 paths/861 blobs/four new commits scanned, zero findings. `final-boundary-source-checks` at clean **77e8162** repeats system/drift/source/declared-migration/privacy PASS: **876 paths/868 blobs/five new commits**, zero findings; no dependency changes. Only the explicit new investment receipt migration is declared relative to the consolidation base. AST-only graph updated; JavaScript syntax and master-document links/count/unchanged currency-contract checks PASS. The 911/53/34 consolidation gate predates the investment feature; it is not represented as a new full-suite run for later source. Latest source uses the explicit focused gates above; a new complete release/package gate remains required before promotion.

Closing state: one active development checkout, clean committed source; frozen `4aa7ac70`, production/master `3932f391`, private databases, recovery assets and GitHub untouched. All final executed runs above PASS with zero failures/skips; early failed fixtures/rehearsals remain evidence. Financial table/baseline/fingerprint and migration comparisons have zero mismatches. Full-product technical count remains **64 verified / 79 remaining** because investment field provenance strengthens an existing unaccepted broker-import capability rather than claiming real-document acceptance. No new packaged executable or real-account/provider/device-loss acceptance is claimed. No permissions or recovery waivers were inherited.

### Loan-import field provenance — 2026-10-17

Unit 1 source: [receipt service](../apps/loans/services/document_evidence.py), [owner API](../apps/ml_engine/api/loan_evidence.py), shared [private field review](../templates/document_field_evidence.html). Supported fields are principal, EMI and remaining balance, with exact current Decimal cents and first unambiguous parser output retained separately. Historical/ambiguous originals stay not_retained; missing remaining balance stays null. No inferred currency. Parser output may contain estimated/defaulted values and is explicitly labeled accordingly. Per-field owner confirmation/revocation does not confirm an estimated loan, authenticate a bank document, verify closure, change any financial value or save long-term memory.

The existing upload, correction and retry workflows retain first originals. Field revisions bind the actual displayed record, file hash, document payload and review generation. Record/file/parser/owner/link changes invalidate confirmations; generation CAS prevents replay/ABA. Original receipts survive loan deletion while the parent document exists; deleting the source/account cascades them. Owner-only HTML/download/API access, session/CSRF, safe 413/503 errors and private no-store/pagehide behavior reuse the bank/investment boundary. Both field-review pages share one template, preserving the investment route and behavior.

Additive `loans.0016_loan_document_evidence` depends on existing loans.0015 only. No historical backfill, financial rewrite, dependency or currency change. Empty reversal is supported; nonempty reversal refuses to destroy receipts and requires the verified pre-migration recovery path, preserving subsequent writes. The synthetic rehearsal checks independent SQLite backup/restore, integrity/foreign keys, source hash and all original financial/family/fingerprint rows. Production and the frozen candidate have not been migrated.

`loan-fields-resumed-final`: **130 backend PASS**, zero failures/skips (loan receipts/forward-reverse-recovery rehearsal, existing investment receipts, document correction/retry, Loan Decimal runtime, M14 diagnostics, release validation, financial baseline and reset). The prior `loan-fields-final` run was interrupted and has no result; it is not counted. `loan-field-browser`: **3 Chrome PASS**, zero failures/skips (new loan field confirmation/revocation/correction/stale mobile flow plus existing investment and bank review). Actual desktop/mobile screenshots reviewed in that run's browser/user-data directory. Early failed runs are retained: missing local deepcopy import fixed; incorrect test label fixed; retry fixture date changed to the parser's actual ISO-text contract. The earlier 117/118 run is not reported as a passing gate. Financial comparisons have zero mismatches. Continued with canonical assistant integration below, preserving the existing loan-contract and closure checks.

Unit 1 committed as `bd2232aba024435e32f3dcaeee0b7523a6d0d35b`. `loan-fields-schema`: isolated Django system and migration drift checks PASS. Unit 2 reuses the same bounded document lookup/value-join logic for loan and investment canonical tools. Three supported imported loan fields may carry owner_confirmed_document_field; total_paid never inherits that attestation. Contract verification remains separate; an estimated or conflicting loan still abstains. Unknown remaining balance stays unavailable. Confirmed fields against a sole document link to `/documents/loans/<document_id>/records/<loan_id>/`; partial/multiple evidence retains canonical-page source links. File/revocation/ownership/link changes during inference reject the answer; newly confirmed values cannot certify older concurrent snapshots. No raw originals, document names, accounts or private URLs enter local model instructions; explicit cloud consent is refused.

`loan-grounding-initial`: **63 backend PASS**, zero failures/skips (new loan integration and existing canonical, investment, bank, closure and currency safeguards). `loan-grounding-browser`: **5 Chrome PASS**, zero failures/skips (assistant to exact loan citation, loan review/stale/mobile, existing investment/canonical/bank flows); actual source-card screenshot reviewed. `loan-real-ollama`: **1 separate real-local PASS**, bounded installed-model inference on synthetic loan fields, no downloads/external calls/live config changes. Final `loan-grounding-final`: **115 backend PASS**, zero failures/skips, including latest source-failure regressions, receipt migration/restore, canonical sources, bank/investment/closure compatibility, fingerprint identity, private history, auth/session/CSRF and financial baseline. Financial comparisons have zero mismatches. Source certification follows a clean committed tree. Canonical HTML preserves ownership 404/403 and source-size 413, returning safe reference-bearing 503 for unexpected source failures instead of a debug traceback. Original failed/interrupted receipts are retained and overlapping runs are not added together.

`loan-clean-source` at clean **845cc32**: Django system/drift, exact source/declared migrations and pinned privacy PASS, **883 paths / 895 blobs / 8 commits**, zero findings, no dependency changes. The declared additions relative to consolidation base fb288465 are investment.0005 and loan.0016 only; this is not the full production migration plan. `loan-native-schema`: **19 same-host source-native checks PASS**, no failed checks, covering fresh schema/server/worker/scheduler, restart/queue persistence, private media, browser and independent synthetic backup/restore. This run used the implementation subsequently committed as 845cc32; it is not a new frozen package or separate-PC acceptance.

### Applied-payment transaction references — 2026-10-17

Source: [existing canonical tool](../apps/ml_engine/services/canonical_evidence.py), [focused regressions](../tests/test_loan_payment_sources.py), [shared owner citation page](../templates/canonical_evidence.html).

Next safe unit: existing canonical loan retrieval now resolves the latest matched/applied payment's recorded Expense reference through the existing owner-scoped canonical/bank evidence tools. It adds an authorized transaction citation and separate reference-verification status, without copying the bank statement or recalculating/matching amounts, dates, allocations, totals or balances. Manual entries are owner-recorded references; statement references require the existing bank owner review. Owner confirmation never becomes independent bank authentication. Missing/deleted sources are explicitly unavailable; current canonical loan facts remain recorded facts. Rejected/unapplied payments do not acquire source references.

The loan revision includes the child transaction/statement receipt revision, so revocation, file replacement/removal, deletion, correction and reparenting during local inference reject stale answers. A second owner-scoped lookup closes the race after the initial loan-parent permission check. Private nested references are excluded from local model instructions and the generic assistant metadata renderer; the canonical page provides the real authorized link. OpenAI/cloud/private history remain OFF. No new schema, money/currency change or write endpoint.

`loan-payment-source-initial`: **86 backend PASS**, zero failures/skips. `loan-payment-source-browser`: **3 Chrome PASS**, zero failures/skips (new loan-to-bank review/revocation flow, exact loan-import citation and existing bank assistant); actual associated-source screenshot reviewed. Final `loan-payment-source-final`: **172 backend PASS**, zero failures/skips, including final owner-lookup race, current loan import/payment evidence, canonical/investment/bank/closure compatibility, loan lifecycle/verification/money, migration/independent restore, fingerprint identity, session/CSRF, financial baseline and private-history regressions. Financial comparisons have zero mismatches. Counts overlap earlier runs and are not summed. These are synthetic local acceptances; normal accounts, real bank layouts, fresh packaging, independent recovery and production remain unaccepted/unmodified. The 143-feature totals remain **64 verified / 79 remaining**; these bounded provenance units do not complete general financial-document knowledge or real-provider acceptance.

Closing source **449a19ce76678196823e3a3ca076cda648955b8e** is committed and clean. `loan-payment-clean-source`: system/migration drift, exact source/declared migration and pinned privacy PASS, **884 paths / 903 blobs / 9 commits**, zero findings. The machine-readable manifest pins the exact candidate and consolidation baseline. No dependency change; only the two declared receipt migrations relative to fb288465. AST-only graph and JavaScript syntax PASS. Master-document validation: **143 features, zero broken local links, C1–C10 unchanged**. Native evidence is preserved at `loan-native-schema/native_report.json` beneath the existing consolidation root; 19 same-host checks at the preceding loan-field implementation, not a new package. The separate real-local loan inference passed at 845cc32; payment-reference inference uses mocks and explicitly excludes nested private data from model input.

Source selection, question-domain accuracy, multi-case/held-out memory evaluation, reviewed comparisons and source-bound Council cycles are complete locally in their bounded scopes above. Reviewed bank transaction dates are closed at 98a3c89. Next safe work is COUNCIL-04 durable review-decision history, then the observed financial-correction path, using existing services. Keep full PDF/OCR knowledge partial and the disclosed retrieval holdout frozen. General/sustained model quality remains partial; no private activation or model promotion. Resume from this file and actual HEAD, without repeating completed FIN-MONEY, M16?M21 or frozen gates. Fresh release/package, normal-account, separate-PC and portable recovery acceptance remain outstanding; production and frozen 4aa7ac70 are preserved.

## Counts and interpretation

The denominator remains the original 143 audited capabilities, not new commit/subfeature counts. COMPLETE_VERIFIED is bounded technical evidence, **not** real-account/provider/clean-PC/device-loss acceptance. Partial capabilities are not fractionally counted. The JSON audit inventory remains a dated immutable snapshot; the live rows below supersede its statuses.

- BLOCKED_APPROVAL: **5**
- BLOCKED_EXTERNAL: **3**
- COMPLETE_VERIFIED: **75**
- IMPLEMENTED_NOT_ACCEPTED: **24**
- NOT_IMPLEMENTED: **10**
- PARTIALLY_IMPLEMENTED: **26**

Technical completion: **74/143 = 51.7%**. Remaining: **69**, including implemented but unaccepted and approval/external blockers. This is not a product acceptance percentage.

## Prioritized remaining roadmap and approval boundaries

| Order | Existing unit | Current scope / next action | Gate |
| --- | --- | --- | --- |
| 1 | AI-GROUND | Investment/loan/bank/canonical proofs, applied-payment references, paginated explicit source selection and question-domain accuracy complete locally. Broader verified-document tools remain partial | Synthetic local tests and financial invariance; no financial writes by AI |
| 2 | FIN-CURRENCY | C1–C10 explicit ownership, unknown history, incompatible totals, ISO scale, FX policy and reversible migration contract below | Explicit contract approval before schema work |
| 3 | AI-HISTORY | Implemented private encrypted conversations; owner opt-in/retention/recovery acceptance | Operator activation remains OFF |
| 4 | Non-AWS sync | Reuse encrypted journal/checkpoint/queue; evaluate/implement approved compatible R2 or other non-AWS adapter | No live provider contact/private uploads; independent key recovery and provider approval first |
| 5 | AI-QUALITY / OpenAI | Development/independent held-out comparisons, ranking/error metrics and unchanged thresholds measured locally. Legacy reference REJECT; experimental policy review-eligible on 12 unseen cases, not general accuracy, distinct-model or sustained-drift acceptance. Council has five verified host-mediated cycles, bounded proposals/reuse/recovery/routing, no model approval authority. Broader tools/public-query-only provider acceptance remain partial | No automatic model promotion, private query persistence, training, paid calls/private export or hypotheses promoted to facts |
| 6 | Travel | Larger novel destination pools, true scenic/alternate/bike-legal routes, detours, permits/freshness, authorized inventory, galleries | Reuse providers/cache; contracts/credentials/terms before real availability claims |
| 7 | Finance/product | Savings goals/export, investment alerts/planning, tax policy years, career/vehicle/relationship inference and safe AI Council | Canonical models/Decimal; no invented eligibility/accuracy or autonomous financial/code writes |
| 8 | Operational acceptance | Production availability/ACL repair, normal-account UI, clean-PC installer lifecycle, portable independent recovery, remote CI/branch governance | Separate authorization; synthetic and real acceptance remain distinct |

M16 retention/invalidation and M17 experimental retirement are implemented locally; M18 dependency security and M19 same-host packaging evidence exist. M20 local gate engine and M21 disposable same-host rehearsal passed at frozen 4aa7ac70. Their remote/real-environment acceptance remains open. Do not repeat completed development or redefine milestone numbers.

Release workflow: **Develop → Test → Integrate → Package → Backup → Approve → Promote → Verify → Push**. One active dev checkout; archive unique ignored artifacts before removing redundant worktrees, retain all branch/frozen refs. Never delete recovery backups or overwrite uncertain/operator work.

Known release blockers: fresh exact-source integrated gate/package; normal real-account/separate-PC/installer acceptance; independent portable-key/device-loss restore; production repair/promotion authorization; remote CI/branch protections. Provider activation, currency schema and private history have their own approvals. Checksum verification does not establish decryptability.

## All 143 capabilities — current implementation inventory

For unchanged rows the dated code/test scope is retained from the completed audit; no new acceptance is invented. Cross-cutting global gates and explicit updates above supersede obsolete per-feature baseline advice. References below point to code/tests, not live private data.

### FIN-01 — Dashboard, income, expenses and fixed obligations

**COMPLETE_VERIFIED** · Personal finance · P2.

- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py).
- APIs/UI/models: /expenses/; /api/expenses/ (see urls.py); User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Canonical baseline distinguishes measured, entered, inferred and unavailable values; complete transaction history is not assumed. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Retain reconciliation and complete real-account visual acceptance.

### FIN-02 — Disposable cash flow and savings capacity

**COMPLETE_VERIFIED** · Personal finance · P2.

- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py).
- APIs/UI/models: /expenses/; /api/expenses/ (see urls.py); User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Capacity is an estimate based on recorded history/obligations, not an automatic future income guarantee. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Keep canonical baseline as the single calculation path.

### FIN-03 — Net worth, liquid cash and account snapshots

**COMPLETE_VERIFIED** · Personal finance · P2.

- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py).
- APIs/UI/models: /expenses/; /api/expenses/ (see urls.py); User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Entered account values are snapshots; partial imports do not establish an audited ledger. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Accept with the owner's actual account and snapshots.

### FIN-04 — Financial health and historical spending indicators

**COMPLETE_VERIFIED** · Personal finance · P2.

- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py).
- APIs/UI/models: /expenses/; /api/expenses/ (see urls.py); User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py), [tests/test_financial_health_acceptance.py](../tests/test_financial_health_acceptance.py), [tests/test_user_data_browser.py](../tests/test_user_data_browser.py). **13 backend / one actual Chrome PASS**, zero skips; independent normal/loss/no-data values, owned cache/fresh isolation, transfer/review exclusions and financial invariance. Evidence: `artifacts/health-76c1522/checkpoint-verified.json` and inspected desktop/mobile screenshots.
- Acceptance: local recorded-history heuristic workflow verified on ordinary synthetic-owner dashboard; existing unavailable/review-required/old-period UI receipts reused because application code is unchanged. Explicit estimated-risk and not-credit-score labels visible.
- Limitations/dependencies: Bounded heuristic summaries, not predictive accuracy, creditworthiness, private-account or external-provider validation. Currency/history/provider and release acceptance remain separate.
- Next: Evaluate calibration against an approved reviewed-outcome corpus; do not repeat this bounded dashboard acceptance.

### FIN-05 — Budget management, utilization and affordability

**COMPLETE_VERIFIED** · Personal finance · P2.

- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py), [apps/budgets/models.py](../apps/budgets/models.py), [apps/budgets/serializers.py](../apps/budgets/serializers.py), [apps/budgets/services/budget_intelligence.py](../apps/budgets/services/budget_intelligence.py).
- APIs/UI/models: /expenses/; /api/expenses/ (see urls.py); User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: `tests.test_budget_acceptance`, `tests.test_budget_money`, `tests.test_financial_baseline_alignment`: 29 backend PASS; actual Chrome budget acceptance one PASS, zero skips; receipts in `artifacts/budget-42106cb/` above.
- Acceptance: Owned session/API and ordinary Chrome plan workflow, Decimal/category reconciliation, canonical transaction boundaries, cache/CSRF/isolation, unavailable income, explicit plan warnings and desktop/mobile evidence accepted locally with disclosed synthetic data. Financial records unchanged.
- Limitations/dependencies: FIN-14 Decimal schema/rollback receipts remain applicable. Category/city weights and daily guides are planning rules, not verified local prices or funding confirmation. Unknown income/zero utilization abstain; saved plans can exceed available income only with an explicit warning. No currency/FX, schema, provider, packaging or production changes.
- Next: Preserve these invariants during FIN-07 chronological forecasting; real-account and release acceptance remain separate.

### FIN-06 — Persisted savings goals and progress workflow

**NOT_IMPLEMENTED** · Personal finance · P2.

- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py).
- APIs/UI/models: /expenses/; /api/expenses/ (see urls.py); User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: No dedicated goal model or end-to-end goal management route found; savings capacity is not goal persistence. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Confirm goal requirements; add owner goals only after currency/money decisions.

### FIN-07 — Cash-flow forecasting

**PARTIALLY_IMPLEMENTED** · Personal finance · P2.

- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py), [apps/budgets/services/budget_intelligence.py](../apps/budgets/services/budget_intelligence.py), [apps/ml_engine/models/expense_forecaster.py](../apps/ml_engine/models/expense_forecaster.py).
- APIs/UI/models: /expenses/; /api/expenses/ (see urls.py); User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: Twelve forecast checks plus budget/money/baseline/user-data acceptance: 49 backend PASS; three Chrome integration PASS plus one final overlapping forecast Chrome PASS, zero skips. Receipts: `artifacts/forecast-a0a954d/` above. ML training/readiness receipts remain historical, not a fresh model promotion.
- Acceptance: Local chronological planning fallback, Decimal/calendar/owner/cache invariants, dated source aggregates, no future/partial-month training, honest observed ranges and walk-forward errors, unavailable evidence and desktop/narrow-screen UI accepted with synthetic fixtures. Genuine predictive accuracy remains PENDING.
- Limitations/dependencies: Three completed recorded months drive an uncalibrated constant-cost estimate; missing months are unknown and recorded months may be incomplete. Historical ranges are not prediction intervals. Walk-forward spending MAE does not validate future income/fixed bills or bank balances. Sufficient genuine outcomes and calibrated sustained forecast quality remain unverified; no model training/activation or currency-policy change.
- Next: Obtain an authorized genuinely reviewed chronological outcome dataset and evaluate calibration before any predictive-quality/COMPLETE_VERIFIED claim. Continue independent INV-07 development meanwhile.

### FIN-08 — Expense categorization and merchant correction learning

**COMPLETE_VERIFIED** · Personal finance · P2.

- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py), [apps/expenses/services/transaction_intelligence.py](../apps/expenses/services/transaction_intelligence.py).
- APIs/UI/models: /expenses/; /api/expenses/ (see urls.py); User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py), [tests/test_parser_adaptive_learning.py](../tests/test_parser_adaptive_learning.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Parser/history heuristics require review on new layouts; corrections do not prove classifier accuracy. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Continue reviewed synthetic and authorized document-family acceptance.

### FIN-09 — Bank accounts and statement imports

**COMPLETE_VERIFIED** · Personal finance · P2.

- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py), [apps/expenses/services/statement_import.py](../apps/expenses/services/statement_import.py), [apps/expenses/services/statement_lifecycle.py](../apps/expenses/services/statement_lifecycle.py).
- APIs/UI/models: /expenses/; /api/expenses/ (see urls.py); User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py), [tests/test_statement_columns.py](../tests/test_statement_columns.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Actual balances must be reconciled against full bank evidence; OCR availability can require review. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Complete real-document and real-account acceptance.

### FIN-10 — Account-scoped duplicate detection and fingerprints

**COMPLETE_VERIFIED** · Personal finance · P2.

- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py), [apps/expenses/services/transaction_intelligence.py](../apps/expenses/services/transaction_intelligence.py).
- APIs/UI/models: /expenses/; /api/expenses/ (see urls.py); User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py), [tests/test_expense_money_identity.py](../tests/test_expense_money_identity.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Fingerprint schema and cross-account distinctions are preserved by money migrations. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Reject any unexplained fingerprint changes.

### FIN-11 — Transfer legs and cross-account financial relationships

**COMPLETE_VERIFIED** · Personal finance · P2.

- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py), [apps/expenses/services/financial_relationships.py](../apps/expenses/services/financial_relationships.py).
- APIs/UI/models: /expenses/; /api/expenses/ (see urls.py); User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py), [tests/test_financial_relationships.py](../tests/test_financial_relationships.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Detected relationships are evidence/confidence driven; unresolved transfers need owner review. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Keep transfers separate from income/living spend.

### FIN-12 — Financial reconciliation

**COMPLETE_VERIFIED** · Personal finance · P2.

- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py).
- APIs/UI/models: /expenses/; /api/expenses/ (see urls.py); User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Historical synthetic/deployment reconciliation passed; current private rows were not reread in this audit. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Use approved private-copy reconciliation during the next release.

### FIN-13 — Financial export and correction

**PARTIALLY_IMPLEMENTED** · Personal finance · P2.

- Source: [expense API/export](../apps/expenses/views.py), [correction boundary](../apps/expenses/serializers.py), [shared hydration](../apps/expenses/services/transaction_intelligence.py), [Expense UI](../templates/expenses/list.html), [existing reports](../apps/reports/services.py).
- APIs/UI/models: `/expenses/`, `/api/expenses/`, owner-authenticated `/api/expenses/export/`; existing Expense/BankAccount/StatementUpload records, no duplicate register or schema change.
- Tests: [correction regressions](../tests/test_expense_corrections.py), [CSV/privacy regressions](../tests/test_expense_export.py), [actual UI/download](../tests/test_user_data_browser.py), [financial invariance](../tests/test_financial_baseline_alignment.py). Final **186 backend + two Chrome PASS**, zero skips, at the checkpoint above.
- Acceptance: synthetic local correction/export flow PASS; normal-account, broader financial portability and fresh package acceptance PENDING.
- Limitations/dependencies: CSV exports all owner expenses, independent of timeline display filters; retains exact recorded cents without asserting currency, blanks null balances, escapes formula-leading text and omits raw source/account details. Current-value export, not a backup or a reimport contract. Corrections preserve omitted owner values, import linkage/identity and unrelated bank snapshots.
- Next: Broader multi-domain structured portability requires an agreed format; reuse existing owner registers/reports and the unapproved currency contract without inferring currency.

### FIN-14 — Money storage across every domain

**COMPLETE_VERIFIED** · Personal finance · P1.

- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py), [apps/users/models.py](../apps/users/models.py), [apps/users/serializers.py](../apps/users/serializers.py), [apps/budgets/models.py](../apps/budgets/models.py), [apps/career/models.py](../apps/career/models.py), [apps/mobility/models.py](../apps/mobility/models.py).
- APIs/UI/models: /expenses/; /api/expenses/ (see urls.py); User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Core Expense/BankAccount/Investment/Loan amounts are Decimal; User, Budget, Career and Mobility money tail remains float. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Budget/User/Career/Mobility Decimal tail, original snapshots and guarded rollback complete; tests/test_budget_money_migration.py, tests/test_user_money.py, tests/test_career_money.py, tests/test_mobility_money.py. No currency inferred.

### FIN-15 — Canonical currency persistence and multi-currency aggregation

**NOT_IMPLEMENTED** · Personal finance · P1.

- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py).
- APIs/UI/models: /expenses/; /api/expenses/ (see urls.py); User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Legacy INR convention exists; finance models generally lack currency codes. AI correctly labels currency unrecorded; no proven FX ledger. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Decide currency ownership, migration/backfill and historical rate policy separately.

### FIN-16 — Tax calculations and source-backed eligibility

**PARTIALLY_IMPLEMENTED** · Personal finance · P2.

- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py), [apps/ml_engine/services/tax_policy.py](../apps/ml_engine/services/tax_policy.py), [apps/ml_engine/services/tax_optimizer.py](../apps/ml_engine/services/tax_optimizer.py).
- APIs/UI/models: /expenses/; /api/expenses/ (see urls.py); User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py), [tests/test_tax_policy.py](../tests/test_tax_policy.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Dated tax policy supports deterministic arithmetic; effective dates, deduction eligibility and reviewed actual tax cases remain acceptance dependencies. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Confirm current-year authoritative policy and conditional eligibility; do not infer deductions.

### FIN-17 — Credit bureau reports and official score access

**PARTIALLY_IMPLEMENTED** · Personal finance · P2.

- Source: [apps/expenses/services/financial_intelligence.py](../apps/expenses/services/financial_intelligence.py), [apps/expenses/urls.py](../apps/expenses/urls.py), [apps/expenses/models.py](../apps/expenses/models.py), [apps/integrations/services/credit_report_parser.py](../apps/integrations/services/credit_report_parser.py), [apps/integrations/services/credit_score_tracker.py](../apps/integrations/services/credit_score_tracker.py).
- APIs/UI/models: /expenses/; /api/expenses/ (see urls.py); User, Expense, BankAccount, Loan, Investment; canonical baseline.
- Tests: [tests/test_financial_baseline_alignment.py](../tests/test_financial_baseline_alignment.py), [tests/test_credit_report_upload.py](../tests/test_credit_report_upload.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. Official bureau integration BLOCKED_EXTERNAL; uploaded reports synthetic/dated acceptance only.
- Limitations/dependencies: Uploaded bureau evidence and clearly labelled estimates exist; authenticated bureau pulls/contracts are not accepted. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Keep estimates distinct; obtain approved bureau access before live pulls.

### LOAN-01 — EMI, schedules, outstanding and repayment metrics

**COMPLETE_VERIFIED** · Loans and liabilities · P2.

- Source: [apps/loans/services/loan_intelligence.py](../apps/loans/services/loan_intelligence.py), [apps/loans/models.py](../apps/loans/models.py), [apps/loans/urls.py](../apps/loans/urls.py).
- APIs/UI/models: /loans/; /api/loans/ (see urls.py); Loan, LoanPaymentHistory, LoanImportDocument, LoanClosureDocument, LoanForeclosureSnapshot.
- Tests: [tests/test_loan_money_runtime.py](../tests/test_loan_money_runtime.py), [tests/test_loan_lifecycle_and_reports.py](../tests/test_loan_lifecycle_and_reports.py), [tests/test_loan_foreclosure_money.py](../tests/test_loan_foreclosure_money.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Rates/tenure assumptions and missing history remain explicit; monetary persistence uses Decimal. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Keep lender reconciliation and real-statement acceptance.

### LOAN-02 — Loan PDF import and repayment statement parsing

**COMPLETE_VERIFIED** · Loans and liabilities · P2.

- Source: [apps/loans/services/loan_intelligence.py](../apps/loans/services/loan_intelligence.py), [apps/loans/models.py](../apps/loans/models.py), [apps/loans/urls.py](../apps/loans/urls.py), [apps/loans/services/loan_pdf_parser.py](../apps/loans/services/loan_pdf_parser.py).
- APIs/UI/models: /loans/; /api/loans/ (see urls.py); Loan, LoanPaymentHistory, LoanImportDocument, LoanClosureDocument, LoanForeclosureSnapshot.
- Tests: [tests/test_loan_money_runtime.py](../tests/test_loan_money_runtime.py), [tests/test_loan_lifecycle_and_reports.py](../tests/test_loan_lifecycle_and_reports.py), [tests/test_loan_diagnostics.py](../tests/test_loan_diagnostics.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Layout-specific parsing can require review; safe diagnostics hide historical/current parser internals. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Expand authorized real layouts without weakening M14 resource budgets.

### LOAN-03 — Loan payment detection and review

**COMPLETE_VERIFIED** · Loans and liabilities · P2.

- Source: [apps/loans/services/loan_intelligence.py](../apps/loans/services/loan_intelligence.py), [apps/loans/models.py](../apps/loans/models.py), [apps/loans/urls.py](../apps/loans/urls.py), [apps/loans/services/payment_review.py](../apps/loans/services/payment_review.py).
- APIs/UI/models: /loans/; /api/loans/ (see urls.py); Loan, LoanPaymentHistory, LoanImportDocument, LoanClosureDocument, LoanForeclosureSnapshot.
- Tests: [tests/test_loan_money_runtime.py](../tests/test_loan_money_runtime.py), [tests/test_loan_lifecycle_and_reports.py](../tests/test_loan_lifecycle_and_reports.py), [tests/test_loan_related_money_runtime.py](../tests/test_loan_related_money_runtime.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Heuristic matching is reviewable; subscription false positives can be reversed. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Preserve settlement allocations and no-double-post tests.

### LOAN-04 — Foreclosure and prepayment scenarios

**COMPLETE_VERIFIED** · Loans and liabilities · P2.

- Source: [apps/loans/services/loan_intelligence.py](../apps/loans/services/loan_intelligence.py), [apps/loans/models.py](../apps/loans/models.py), [apps/loans/urls.py](../apps/loans/urls.py), [apps/loans/services/loan_foreclosure_service.py](../apps/loans/services/loan_foreclosure_service.py).
- APIs/UI/models: /loans/; /api/loans/ (see urls.py); Loan, LoanPaymentHistory, LoanImportDocument, LoanClosureDocument, LoanForeclosureSnapshot.
- Tests: [tests/test_loan_money_runtime.py](../tests/test_loan_money_runtime.py), [tests/test_loan_lifecycle_and_reports.py](../tests/test_loan_lifecycle_and_reports.py), [tests/test_loan_foreclosure_money.py](../tests/test_loan_foreclosure_money.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Fees and payoff must come from reviewed lender evidence, not guessed quotes. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Keep hypothetical scenarios separate from posting.

### LOAN-05 — Closure extraction, verification and evidence status

**COMPLETE_VERIFIED** · Loans and liabilities · P2.

- Source: [apps/loans/services/loan_intelligence.py](../apps/loans/services/loan_intelligence.py), [apps/loans/models.py](../apps/loans/models.py), [apps/loans/urls.py](../apps/loans/urls.py), [apps/loans/services/loan_closure_parser.py](../apps/loans/services/loan_closure_parser.py).
- APIs/UI/models: /loans/; /api/loans/ (see urls.py); Loan, LoanPaymentHistory, LoanImportDocument, LoanClosureDocument, LoanForeclosureSnapshot.
- Tests: [tests/test_loan_money_runtime.py](../tests/test_loan_money_runtime.py), [tests/test_loan_lifecycle_and_reports.py](../tests/test_loan_lifecycle_and_reports.py), [tests/test_loan_verification.py](../tests/test_loan_verification.py), [tests/test_loan_verification_api.py](../tests/test_loan_verification_api.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Uploaded closure evidence is not automatically verified solely because parsing succeeded. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Accept actual lender evidence under owner review.

### LOAN-06 — Multi-loan aggregation and consolidation

**COMPLETE_VERIFIED** · Loans and liabilities · P2.

- Source: [apps/loans/services/loan_intelligence.py](../apps/loans/services/loan_intelligence.py), [apps/loans/models.py](../apps/loans/models.py), [apps/loans/urls.py](../apps/loans/urls.py).
- APIs/UI/models: /loans/; /api/loans/ (see urls.py); Loan, LoanPaymentHistory, LoanImportDocument, LoanClosureDocument, LoanForeclosureSnapshot.
- Tests: [tests/test_loan_money_runtime.py](../tests/test_loan_money_runtime.py), [tests/test_loan_lifecycle_and_reports.py](../tests/test_loan_lifecycle_and_reports.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Consolidation is an authorized application workflow; assistant cannot silently execute it. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Retain original loan lineage and cash-flow tests.

### LOAN-07 — Loan forecasting and cross-module liabilities

**IMPLEMENTED_NOT_ACCEPTED** · Loans and liabilities · P2.

- Source: [apps/loans/services/loan_intelligence.py](../apps/loans/services/loan_intelligence.py), [apps/loans/models.py](../apps/loans/models.py), [apps/loans/urls.py](../apps/loans/urls.py).
- APIs/UI/models: /loans/; /api/loans/ (see urls.py); Loan, LoanPaymentHistory, LoanImportDocument, LoanClosureDocument, LoanForeclosureSnapshot.
- Tests: [tests/test_loan_money_runtime.py](../tests/test_loan_money_runtime.py), [tests/test_loan_lifecycle_and_reports.py](../tests/test_loan_lifecycle_and_reports.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Projection is amortization/assumption based, not a calibrated personal prediction. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Verify real payment histories and forecast uncertainty.

### LOAN-08 — Broad real-document/lender acceptance

**IMPLEMENTED_NOT_ACCEPTED** · Loans and liabilities · P2.

- Source: [apps/loans/services/loan_intelligence.py](../apps/loans/services/loan_intelligence.py), [apps/loans/models.py](../apps/loans/models.py), [apps/loans/urls.py](../apps/loans/urls.py).
- APIs/UI/models: /loans/; /api/loans/ (see urls.py); Loan, LoanPaymentHistory, LoanImportDocument, LoanClosureDocument, LoanForeclosureSnapshot.
- Tests: [tests/test_loan_money_runtime.py](../tests/test_loan_money_runtime.py), [tests/test_loan_lifecycle_and_reports.py](../tests/test_loan_lifecycle_and_reports.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Synthetic parser/closure tests and older reviewed documents do not cover every lender/layout. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Run an approved redacted/private-copy lender acceptance corpus.

### INV-01 — Portfolio register, valuation and allocation

**COMPLETE_VERIFIED** · Investments · P2.

- Source: [apps/investments/services/portfolio_intelligence.py](../apps/investments/services/portfolio_intelligence.py), [apps/investments/models.py](../apps/investments/models.py), [apps/investments/urls.py](../apps/investments/urls.py).
- APIs/UI/models: /investments/; /api/investments/ (see urls.py); Investment; optional external evidence.
- Tests: [tests/test_investment_money.py](../tests/test_investment_money.py), [tests/test_investment_projection.py](../tests/test_investment_projection.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Values can be entered snapshots; cached external quotes have freshness metadata. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Accept owner portfolio and reconcile to broker evidence.

### INV-02 — Investment PDF imports and corrections

**IMPLEMENTED_NOT_ACCEPTED** · Investments · P2.

- Source: [apps/investments/services/portfolio_intelligence.py](../apps/investments/services/portfolio_intelligence.py), [apps/investments/models.py](../apps/investments/models.py), [apps/investments/urls.py](../apps/investments/urls.py).
- APIs/UI/models: /investments/; /api/investments/ (see urls.py); Investment; optional external evidence.
- Tests: [tests/test_investment_money.py](../tests/test_investment_money.py), [tests/test_investment_projection.py](../tests/test_investment_projection.py), [tests/test_document_center_and_statement_import.py](../tests/test_document_center_and_statement_import.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Parser/import/review exists; generalized broker layout accuracy is not established. Existing owner/session controls; canonical data availability; acceptance plan.
- Current local extension: [field receipts](../apps/investments/services/document_evidence.py), [owner APIs](../apps/ml_engine/api/investment_evidence.py), [receipt/migration tests](../tests/test_investment_evidence.py), [grounding tests](../tests/test_investment_grounding.py), owner citations and real-local synthetic inference are implemented/verified. Next: real-document/layout acceptance and remaining broad document knowledge; no independent market/broker authenticity is claimed. Production remains unchanged.
- Bounded INV-02/SCOPE-01 acceptance (2026-10-26): [actual PDF regressions](../tests/test_investment_import_acceptance.py) and Chrome prove account-aware extraction/dedup/upsert/receipt isolation, safe reimport, rollback and corrected-zero/cents retry, including Generic/unknown institution identity. Positions show masked account suffixes. See the current evidence checkpoint above. Full status stays IMPLEMENTED_NOT_ACCEPTED: independent broker/layout/OCR and real-account coverage remain unverified; unknown legacy accounts are preserved, not silently reconciled.

- Bounded INV-02/SCOPE-02 (2026-10-26): [synthetic representative layout acceptance](../tests/test_investment_layout_acceptance.py) covers labelled fund/symbol tables, account identity, raw source money, totals, duplicate conflicts, owner correction/retry and safe review. UI/Chrome/Axe evidence is in the checkpoint above. OCR output requires owner review; mocked OCR confidence/provenance is not accuracy evidence. Broad broker/layout/OCR and authorized real-account acceptance remains outstanding; no capability promotion.

### INV-03 — Returns and planning projections

**COMPLETE_VERIFIED** · Investments · P2.

- Source: [apps/investments/services/portfolio_intelligence.py](../apps/investments/services/portfolio_intelligence.py), [apps/investments/models.py](../apps/investments/models.py), [apps/investments/urls.py](../apps/investments/urls.py).
- APIs/UI/models: /investments/; /api/investments/ (see urls.py); Investment; optional external evidence.
- Tests: [tests/test_investment_money.py](../tests/test_investment_money.py), [tests/test_investment_projection.py](../tests/test_investment_projection.py), [tests/test_user_data_browser.py](../tests/test_user_data_browser.py). **32 backend / two actual Chrome PASS**, zero skips; independent annuity/chart values, cents, empty/zero/negative cases, owner boundaries, invalid input preservation, cache rollover and unavailable/corrected forecast. Evidence: `artifacts/investment-81f88b8/checkpoint.json`; inspected desktop/390px screenshots.
- Acceptance: verified local nominal 12-month planning with recorded month zero, beginning-of-month contributions, entered annual percentage / 1200 monthly rate and explicit uncertainty. Ordinary synthetic owner UI/API acceptance; no private account or provider access.
- Limitations/dependencies: Not guaranteed/live returns, inflation forecasts, suitability or currency conversion. Invalid/unrepresentable forecasts abstain without changing holdings; external/provider and money/currency approvals remain separate.
- Next: Outcome calibration and inflation/real-return planning require their own evidence and scope; do not repeat this nominal-projection acceptance.

### INV-04 — Risk classification and recommendations

**PARTIALLY_IMPLEMENTED** · Investments · P2.

- Source: [apps/investments/services/portfolio_intelligence.py](../apps/investments/services/portfolio_intelligence.py), [apps/investments/models.py](../apps/investments/models.py), [apps/investments/urls.py](../apps/investments/urls.py).
- APIs/UI/models: /investments/; /api/investments/ (see urls.py); Investment; optional external evidence.
- Tests: [tests/test_investment_money.py](../tests/test_investment_money.py), [tests/test_investment_projection.py](../tests/test_investment_projection.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Allocation/watchlist logic is heuristic, supported by available sources; suitability accuracy is unverified. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Define risk evidence and acceptance; never present as certified advice.

### INV-05 — AMFI/Yahoo market evidence and historical performance

**IMPLEMENTED_NOT_ACCEPTED** · Investments · P2.

- Source: [portfolio intelligence](../apps/investments/services/portfolio_intelligence.py), [verified intelligence](../apps/integrations/services/verified_intelligence.py), [investment API](../apps/investments/views.py), [models](../apps/investments/models.py), [URLs](../apps/investments/urls.py).
- APIs/UI/models: /investments/; /api/investments/; Investment; optional external evidence.
- Tests: [AMFI](../tests/test_investment_market_acceptance.py), [Yahoo](../tests/test_yahoo_market_acceptance.py), [money](../tests/test_investment_money.py), [projection](../tests/test_investment_projection.py), [Chrome](../tests/test_user_data_browser.py). Original56 AMFI and80 Yahoo backend totals overlap; Chrome/Axe receipts retained separately in EXECUTION_STATE/CONSOLIDATION_STATE.
- Acceptance: SCOPE-01 AMFI complete at79a26ae/run40292154135 PASS, already in canonical development. SCOPE-02 Yahoo complete100% atdaed068/run40325761619 all3 PASS; source reconciled into local candidate only, PR18 still review-blocked. Identity/date/close/dated baseline, source/cache expiry, unavailable recovery and unchanged owned records retained. Candidate results require separate receipts.
- Limitations/dependencies: Full capability/live terms/quota, real accounts and exchange-close correctness remain unaccepted. Seven-calendar-day bound is not an exchange calendar. No BETTER adapter, currency inference, FX or holding revaluation. Cross-domain risk/career defaults remain outside this scope.
- Next: Obtain mandatory review and validate permitted integration; retain both bounded receipts. Do not repeat or promote completed synthetic scope into full capability acceptance.
### INV-06 — Long-term investment planning

**PARTIALLY_IMPLEMENTED** · Investments · P2.

- Source: [apps/investments/services/portfolio_intelligence.py](../apps/investments/services/portfolio_intelligence.py), [apps/investments/models.py](../apps/investments/models.py), [apps/investments/urls.py](../apps/investments/urls.py).
- APIs/UI/models: /investments/; /api/investments/ (see urls.py); Investment; optional external evidence.
- Tests: [tests/test_investment_money.py](../tests/test_investment_money.py), [tests/test_investment_projection.py](../tests/test_investment_projection.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Growth scenarios exist; owner-specific goals, full portfolio risk calibration and currency policy are incomplete. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Reuse projection engine when implementing approved goals.

### INV-07 — Persistent portfolio alerts

**PARTIALLY_IMPLEMENTED** · Investments · P2.

- Source: [local review-reminder service](../apps/investments/services/review_alerts.py), [owner API](../apps/investments/alert_views.py), [vault reset/expiry](../apps/ml_engine/services/persistent_memory.py), [investment UI](../static/js/investments.js), [template](../templates/investments/list.html).
- APIs/UI/models: `/api/investments/review-alerts/` and `/investments/`; existing Investment records read only, opt-in/reminders in existing encrypted owner vault; no schema change.
- Tests: 129 broader backend PASS, eight final focused PASS (overlapping), two Chrome workflows PASS plus one overlapping final rerun. Exact receipts and desktop/390px views in the resume checkpoint above. Linux API secure-failure coverage extended.
- Acceptance: Synthetic local record-review consent, encrypted reopen, owner/CSRF, read/dismiss/resolved lifecycle, correction/deletion/reset/retention, future-date abstention and bounded on-request checks accepted. Money remains unchanged; no source/market valuation is inferred from record edit dates.
- Limitations/dependencies: Monetary thresholds require approved currency/valuation evidence. No background/external delivery, price/trading signal or normal real-account/release acceptance; therefore this capability remains partial.
- Next: Preserve the accepted local lifecycle; obtain the gated valuation/currency decisions before monetary rules. Continue independent AI readiness/document-quality work.

### INV-08 — Investment contribution to net worth

**COMPLETE_VERIFIED** · Investments · P2.

- Source: [apps/investments/services/portfolio_intelligence.py](../apps/investments/services/portfolio_intelligence.py), [apps/investments/models.py](../apps/investments/models.py), [apps/investments/urls.py](../apps/investments/urls.py).
- APIs/UI/models: /investments/; /api/investments/ (see urls.py); Investment; optional external evidence.
- Tests: [tests/test_investment_money.py](../tests/test_investment_money.py), [tests/test_investment_projection.py](../tests/test_investment_projection.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Canonical investment totals feed the baseline; unknown currency is not silently converted. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Preserve source amounts and reconciliation.

### DOC-01 — Bounded PDF/image upload and OCR

**COMPLETE_VERIFIED** · Document intelligence · P2.

- Source: [alfred_ai/services/document_extraction.py](../alfred_ai/services/document_extraction.py), [alfred_ai/services/document_review.py](../alfred_ai/services/document_review.py), [alfred_ai/views.py](../alfred_ai/views.py), [static/js/documents.js](../static/js/documents.js), [alfred_ai/services/upload_limits.py](../alfred_ai/services/upload_limits.py).
- APIs/UI/models: /documents/; document-center actions in alfred_ai/urls.py; module-owned upload records; DocumentParserLearningMemory; `/api/ai/document-corpus/` consent/list, `/search/`, owner deletion; additive encrypted vault table distinct from verified memories/history/sync.
- Tests: [tests/test_document_extraction.py](../tests/test_document_extraction.py), [tests/test_document_review_and_retry.py](../tests/test_document_review_and_retry.py), [tests/test_upload_limits.py](../tests/test_upload_limits.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: OCR requires supported binaries; missing OCR degrades to review. Raw payloads are not safe log content. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Accept more layouts and native OCR availability.

### DOC-02 — Bank/loan/investment extraction and classification

**COMPLETE_VERIFIED** · Document intelligence · P2.

- Source: [alfred_ai/services/document_extraction.py](../alfred_ai/services/document_extraction.py), [alfred_ai/services/document_review.py](../alfred_ai/services/document_review.py), [alfred_ai/views.py](../alfred_ai/views.py), [static/js/documents.js](../static/js/documents.js).
- APIs/UI/models: /documents/; document-center actions in alfred_ai/urls.py; Module-owned upload records; DocumentParserLearningMemory; no universal document-knowledge model.
- Tests: 55 extraction/document-center/statement/investment evidence plus 15 loan-evidence checks = 70 fresh backend PASS; four actual Chrome PASS; zero skips. System/drift PASS. `artifacts/doc02-ed9e333/` above. Unchanged review/retry receipts are historical, not fresh totals.
- Acceptance: Generated real statement/loan PDF imports and replay, document-type/parser metadata, malformed/partial review fallback, immutable original extraction, reviewed corrections and stale/revoked evidence, Decimal reconciliation, owner/CSRF/isolation and actual desktop/narrow-screen review workflows accepted locally. No business-code changes were necessary.
- Limitations/dependencies: This is bounded known-layout and reviewed-field acceptance; OCR-stub tests do not establish real OCR engine accuracy. Arbitrary PDF/photo comprehension, independent source authentication, currency compatibility, normal-account and packaged/native acceptance remain unverified and are not counted here.
- Next: Preserve these extraction/provenance contracts while expanding DOC-06 knowledge and DOC-07 grounded questions; continue explicit abstention for unsupported layouts/evidence.

### DOC-03 — Confidence, metadata and provenance

**COMPLETE_VERIFIED** · Document intelligence · P2.

- Source: [alfred_ai/services/document_extraction.py](../alfred_ai/services/document_extraction.py), [alfred_ai/services/document_review.py](../alfred_ai/services/document_review.py), [alfred_ai/views.py](../alfred_ai/views.py), [static/js/documents.js](../static/js/documents.js).
- APIs/UI/models: /documents/; document-center actions in alfred_ai/urls.py; Module-owned upload records; DocumentParserLearningMemory; no universal document-knowledge model.
- Tests: [tests/test_document_extraction.py](../tests/test_document_extraction.py), [tests/test_document_review_and_retry.py](../tests/test_document_review_and_retry.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Parser confidence is not proof that an extracted fact is true; verification remains separate. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Preserve source/version/field review distinction.

### DOC-04 — Field corrections, visual review and retry

**COMPLETE_VERIFIED** · Document intelligence · P2.

- Source: [alfred_ai/services/document_extraction.py](../alfred_ai/services/document_extraction.py), [alfred_ai/services/document_review.py](../alfred_ai/services/document_review.py), [alfred_ai/views.py](../alfred_ai/views.py), [static/js/documents.js](../static/js/documents.js).
- APIs/UI/models: /documents/; document-center actions in alfred_ai/urls.py; Module-owned upload records; DocumentParserLearningMemory; no universal document-knowledge model.
- Tests: [tests/test_document_extraction.py](../tests/test_document_extraction.py), [tests/test_document_review_and_retry.py](../tests/test_document_review_and_retry.py), [tests/test_document_retry_integrity.py](../tests/test_document_retry_integrity.py), [tests/test_document_review_browser.py](../tests/test_document_review_browser.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Corrections update supported module records; stale retries cannot overwrite newer accepted edits. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Retain browser and integrity regressions.

### DOC-05 — Document deduplication and source lineage

**COMPLETE_VERIFIED** · Document intelligence · P2.

- Source: [alfred_ai/services/document_extraction.py](../alfred_ai/services/document_extraction.py), [alfred_ai/services/document_review.py](../alfred_ai/services/document_review.py), [alfred_ai/views.py](../alfred_ai/views.py), [static/js/documents.js](../static/js/documents.js).
- APIs/UI/models: /documents/; document-center actions in alfred_ai/urls.py; Module-owned upload records; DocumentParserLearningMemory; no universal document-knowledge model.
- Tests: [tests/test_document_extraction.py](../tests/test_document_extraction.py), [tests/test_document_review_and_retry.py](../tests/test_document_review_and_retry.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Module identities differ; not a universal semantic document deduplication service. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Preserve account/source fingerprints.

### DOC-06 — General searchable document knowledge

**COMPLETE_VERIFIED** · Document intelligence · P2.

- Source: [alfred_ai/services/document_extraction.py](../alfred_ai/services/document_extraction.py), [alfred_ai/services/document_review.py](../alfred_ai/services/document_review.py), [alfred_ai/views.py](../alfred_ai/views.py), [static/js/documents.js](../static/js/documents.js).
- APIs/UI/models: /documents/; document-center actions in alfred_ai/urls.py; Module-owned upload records; DocumentParserLearningMemory; no universal document-knowledge model.
- Tests: [corpus lifecycle/upload/privacy](../tests/test_document_corpus.py), [one-off document search](../tests/test_document_knowledge.py), [actual Chrome](../tests/test_user_data_browser.py), [unsupported platform refusal](../tests/test_memory_platform.py). 2026-10-25 receipts: 167 integration, 30 overlapping final guards and two actual Chrome PASS; earlier financial-corpus 167 integration scope differs and overlaps, not an additive total.
- Acceptance: bounded local Windows PDF/text keyword ingestion/index/retrieval accepted with real DPAPI, private originals and actual desktop/390px both-theme browser evidence above. No normal-account, real-Linux, native/package, provider or production acceptance claimed.
- Limitations/dependencies: General PDF text layers and UTF-8 `.txt`, plus existing financial retained extraction, within explicit processing/storage/retention quotas; scanned/image-only PDFs, other general formats, semantic comprehension and arbitrary Q&A remain unsupported (DOC-07). Existing owner/session controls and linked-source availability remain required. Older-binary rollback requires clearing retained copies first; backups have separate retention.
- Current local scope: reviewed bank transactions, exact closure citations, owner-confirmed investment/loan-import fields and applied-payment references have canonical assistant/source revision/liveness checks and local acceptance above. Larger linked histories now support bounded paginated explicit source selection with exact private citations; wrong-domain questions abstain. Arbitrary document search/Q&A remains unimplemented.
- Current retrieval slice: the original one-off selected loan/investment/bank search remains available without retention. Explicit consent additionally enables encrypted text/index copies, selected multi-document keyword retrieval and vault lifecycle controls, with exact private original links/offsets and source/correction revalidation. No AI inference or financial authority; unavailable/changed evidence abstains. [Retrieval service](../apps/ml_engine/services/document_knowledge.py), [encrypted corpus](../apps/ml_engine/services/document_corpus.py), [corpus regression](../tests/test_document_corpus.py), [one-off regression](../tests/test_document_knowledge.py). The 2026-10-25 checkpoint records 167 backend and actual Chrome evidence for this bounded slice.
- General corpus: explicit PDF/text upload, encrypted originals with owner-only attachment endpoints, full supported text/token index, citations, selected search and deletion/expiry/reset are implemented and accepted in the scope above. Upload and index stay distinct from verified facts/history/sync; no financial writes or model calls. Missing matches do not prove absence.
- Next: preserve these contracts and proceed to DOC-07 grounded Q&A; keyword passages establish searchable document knowledge, not document understanding. Fresh CI/release/normal-account acceptance remains separately tracked.

### DOC-07 — AI Q&A over arbitrary financial documents

**PARTIALLY_IMPLEMENTED** · Document intelligence · P2.

- Whole-extraction extension (2026-10-25): explicit `context_mode=full_extraction` supplies every selected retained-text character within the unchanged six-passage/4096-byte local request; otherwise returns `context_limit` without inference or partial evidence. Exact citations, owner/revision invalidation and no-cloud/no-history policy are preserved. Documents UI exposes the choice and context coverage; keyword mode stays default. Fresh evidence: **159 backend + five integrated Chrome + four real-local synthetic cases PASS**, zero skips; see active checkpoint. [Full-context regressions](../tests/test_document_full_context.py). This accepts bounded retained-text context, not complete original extraction, OCR, broad independent accuracy or financial authority.

- Accepted local extension (2026-10-25): encrypted corpus Q&A through `/api/ai/document-corpus/question/` and Documents. Explicitly selected 1–3 owned documents plus keywords supply at most six exact excerpts; fixed local structured inference selects indices, never authors financial prose or citations. Revalidate original/correction/owner/retention after inference; malformed, partial, unavailable, stale or insufficient answers fail closed. Conflicts retain separate original citations without reconciliation. [Question service](../apps/ml_engine/services/document_questions.py), [regressions](../tests/test_document_questions.py), [opt-in actual local tests](../tests/test_document_questions_ollama.py). The active checkpoint binds 176 integration backend, actual Chrome and six real-local synthetic cases to source. This is keyword-bounded extractive evidence, not arbitrary full-document/OCR comprehension, independent accuracy or financial authority; count remains partial.
- Source: [alfred_ai/services/document_extraction.py](../alfred_ai/services/document_extraction.py), [alfred_ai/services/document_review.py](../alfred_ai/services/document_review.py), [alfred_ai/views.py](../alfred_ai/views.py), [static/js/documents.js](../static/js/documents.js), [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py).
- APIs/UI/models: /documents/; document-center actions in alfred_ai/urls.py; Module-owned upload records; DocumentParserLearningMemory; no universal document-knowledge model.
- Tests: [tests/test_document_extraction.py](../tests/test_document_extraction.py), [tests/test_document_review_and_retry.py](../tests/test_document_review_and_retry.py), [tests/test_document_grounding_acceptance.py](../tests/test_document_grounding_acceptance.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Local hybrid grounding supports canonical financial facts, owner-reviewed bank/investment/loan fields and at most three explicitly selected reviewed records from one supported document, available through the existing assistant picker. Encrypted corpus questions additionally support up to three explicitly selected retained documents in keyword or bounded whole-extraction mode. Exact private citations and complete retained context do not establish original authenticity, extraction completeness or general answer accuracy. Longer/arbitrary original documents, OCR and broader independent quality remain unsupported or unaccepted. Existing owner/session controls, canonical records and reviewed source revisions are required; no unknown-currency totals or private cloud fallback.
- Local evidence: canonical adapter/API and assistant/document-center JavaScript reuse; backend b0bc54a, UI 7cccbc1, explicit reviewed-field 9d2fd78 and exact-question d18d1d1 gates above. Councils 3461f90aeab752ca / e0405cf5a302cee6 COMPLETE: **97 backend + 3 Chrome / 78 backend + 1 Chrome PASS**, separate real-local synthetic acceptances; overlapping counts are not added. Missing/unreviewed fields abstain before inference, zero remains valid, current corrections/citations remain authoritative. [Selection/race tests](../tests/test_financial_source_selection.py), [real-local test](../tests/test_canonical_ollama.py), [Chrome flows](../tests/test_user_data_browser.py). No new migrations or dependencies.
- Current bounded extensions: explicit recorded category/classification and statement-period answers use current reviewed bank facts, per-record citations and revalidation without memory/model/cloud/history. Statement periods additionally require complete matching retained/current boundaries, an in-range transaction and exactly one explicitly selected statement; missing, conflicting, ambiguous and cross-document periods abstain. Backend privacy/selection/retention guards and desktop/mobile Chrome evidence are in the corresponding checkpoints above. These do not implement arbitrary document knowledge.
- Packaged evidence: exact source `3bc75ac` passed ten compiled HTTP/Chrome period/classification checks, including separate accounts, foreign citations, missing/conflicting boundaries, ambiguous periods, zero generation and financial/original invariance. Fresh package also passed all 35 native AI/restart/recovery checks; this remains bounded synthetic evidence, not arbitrary-document or normal-account acceptance. Receipts: `artifacts/windows-integrated-20261023/`.
- Next: Preserve reviewed bank transaction dates at 98a3c89, recorded-label questions and current source/correction/revocation/citation safeguards. Arbitrary PDF/OCR Q&A still requires separately accepted extraction, retention, relevance and provenance; do not infer it from these bounded record questions. No implicit monetary totals, currency/authenticity inference or cloud fallback.

### DOC-08 — Loan closure document Q&A and abstention

**COMPLETE_VERIFIED** · Document intelligence · P2.

- Source: [alfred_ai/services/document_extraction.py](../alfred_ai/services/document_extraction.py), [alfred_ai/services/document_review.py](../alfred_ai/services/document_review.py), [alfred_ai/views.py](../alfred_ai/views.py), [static/js/documents.js](../static/js/documents.js), [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py).
- APIs/UI/models: /documents/; document-center actions in alfred_ai/urls.py; Module-owned upload records; DocumentParserLearningMemory; no universal document-knowledge model.
- Tests: [tests/test_document_extraction.py](../tests/test_document_extraction.py), [tests/test_document_review_and_retry.py](../tests/test_document_review_and_retry.py), [tests/test_document_grounding_acceptance.py](../tests/test_document_grounding_acceptance.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Structured verified closure fields only; deleted/stale/conflicting evidence is rejected or abstained. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Exact owner-only closure citation/file digest/revision checks implemented at 9a02f16; tests/test_closure_citations.py. No-file legacy metadata explicitly limited.

### DOC-09 — Document deletion and retention

**PARTIALLY_IMPLEMENTED** · Document intelligence · P2.

- Source: [alfred_ai/services/document_extraction.py](../alfred_ai/services/document_extraction.py), [alfred_ai/services/document_review.py](../alfred_ai/services/document_review.py), [alfred_ai/views.py](../alfred_ai/views.py), [static/js/documents.js](../static/js/documents.js), [alfred_ai/services/upload_privacy.py](../alfred_ai/services/upload_privacy.py).
- APIs/UI/models: /documents/; document-center actions in alfred_ai/urls.py; Module-owned upload records; DocumentParserLearningMemory; no universal document-knowledge model.
- Tests: [tests/test_document_extraction.py](../tests/test_document_extraction.py), [tests/test_document_review_and_retry.py](../tests/test_document_review_and_retry.py), [tests/test_upload_privacy_retention.py](../tests/test_upload_privacy_retention.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Owner deletion/raw cleanup switches exist; native vault retention and historic backups retain data under separate policies. Source/non-native DEBUG media route served a synthetic file anonymously; native owner media is protected. No current live exposure asserted. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Unify disclosed retention across raw uploads, metadata, indexes and recovery. Reuse media ownership across source/native profiles (AUD-11).

### AI-01 — Ollama local inference

**COMPLETE_VERIFIED** · ALFRED intelligence · P2.

- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- APIs/UI/models: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py; User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Installed local model/digest and bounded response validation; actual availability can change. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Recheck local model as operational acceptance, not paid fallback.

### AI-02 — Ollama embeddings and similarity retrieval

**COMPLETE_VERIFIED** · ALFRED intelligence · P2.

- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js), [apps/ml_engine/services/local_embeddings.py](../apps/ml_engine/services/local_embeddings.py).
- APIs/UI/models: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py; User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Local embed vector validation and relevant retrieval exist; real personalized quality still needs outcomes. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Maintain semantic benchmark and abstention fixtures.

### AI-03 — Persistent encrypted memory/index/journal

**COMPLETE_VERIFIED** · ALFRED intelligence · P2.

- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- APIs/UI/models: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py; User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py), [tests/test_memory_privacy.py](../tests/test_memory_privacy.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Application-layer memory encryption is not encryption of every financial SQLite file; Windows recovery key portability remains separate. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Preserve at-rest/index protection and independently recoverable keys.

### AI-04 — Owner isolation and memory access

**COMPLETE_VERIFIED** · ALFRED intelligence · P2.

- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- APIs/UI/models: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py; User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Memories are owner scoped; family finance consent does not grant memory sharing. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Test revoked permissions independently.

### AI-05 — Verification, confidence and provenance separation

**COMPLETE_VERIFIED** · ALFRED intelligence · P2.

- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js), [apps/ml_engine/services/memory_learning.py](../apps/ml_engine/services/memory_learning.py).
- APIs/UI/models: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py; User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py), [tests/test_memory_learning.py](../tests/test_memory_learning.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: AI hypotheses never become canonical financial authority; reviewed/user-confirmed states have schema mapping. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Keep human confirmation distinct from source verification.

### AI-06 — Deduplication, relevance and insufficient-evidence abstention

**COMPLETE_VERIFIED** · ALFRED intelligence · P2.

- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- APIs/UI/models: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py; User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py), [tests/test_memory_learning.py](../tests/test_memory_learning.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Quality assertions cover synthetic memory queries, not broad real-world model accuracy. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Grow reviewed relevance evaluation without private uploads.

### AI-07 — Memory corrections, feedback and conflict safety

**COMPLETE_VERIFIED** · ALFRED intelligence · P2.

- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js), [apps/ml_engine/services/memory_learning.py](../apps/ml_engine/services/memory_learning.py).
- APIs/UI/models: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py; User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Stale edits conflict rather than overwrite; accept/reject review actions exist. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Preserve drafts, provenance and supersession.

### AI-08 — Delete/reset/retention and resurrection protection

**COMPLETE_VERIFIED** · ALFRED intelligence · P2.

- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- APIs/UI/models: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py; User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py), [tests/test_memory_privacy.py](../tests/test_memory_privacy.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Tombstones/key revocation/trusted checkpoints protect current restore; historical recoverable backups may retain prior data. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Never promise irreversible historic erasure.

### AI-09 — Conversation UI, provider status and evidence cards

**COMPLETE_VERIFIED** · ALFRED intelligence · P2.

- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- APIs/UI/models: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py; User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py), [tests/test_intelligence_ui.py](../tests/test_intelligence_ui.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Session-local conversation display; status does not imply real OpenAI access. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Perform normal real-account UI acceptance.

### AI-10 — Persistent general conversation history

**IMPLEMENTED_NOT_ACCEPTED** · ALFRED intelligence · P2.

- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- APIs/UI/models: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py; User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: New-conversation action clears current UI; no dedicated persisted general chat model/event history demonstrated. Travel messages are separate. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Encrypted consent/owner/restart/retention/history APIs and UI implemented (20b916e); tests/test_conversation_history.py. Operator activation OFF pending retention and recovery approval.

### AI-11 — Financial grounding and numeric/currency suppression

**COMPLETE_VERIFIED** · ALFRED intelligence · P2.

- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- APIs/UI/models: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py; User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py), [tests/test_intelligence_currency.py](../tests/test_intelligence_currency.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Six canonical finance metrics use controlled Decimal source cards, currency=None when unrecorded; prose financial numbers are suppressed. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Typed canonical source facts and post-inference revalidation at df386be/b49c141/179db89; tests/test_canonical_evidence.py and tests/test_canonical_grounding.py. Unknown currency and unsupported totals withheld.

### AI-12 — Cross-module personal reasoning

**PARTIALLY_IMPLEMENTED** · ALFRED intelligence · P2.

- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- APIs/UI/models: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py; User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Finance baseline, Travel preferences, verified closure evidence and general owned memories are supported; not all module histories. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Bounded owner-scoped expense/budget/loan/investment/baseline records and reviewed bank/closure sources now implemented; arbitrary cross-module Q&A remains partial.

### AI-13 — Offline/model-outage behavior and consent fallback

**COMPLETE_VERIFIED** · ALFRED intelligence · P2.

- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- APIs/UI/models: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py; User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Ollama outage yields safe local state; cloud does not silently activate. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Recheck drafts/retry and public-consent paths.

### AI-14 — Background learning pipeline

**IMPLEMENTED_NOT_ACCEPTED** · ALFRED intelligence · P2.

- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js), [apps/ml_engine/training/orchestrator.py](../apps/ml_engine/training/orchestrator.py), [apps/ml_engine/services/memory_learning.py](../apps/ml_engine/services/memory_learning.py).
- APIs/UI/models: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py; User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py), [tests/test_ml_training_orchestrator.py](../tests/test_ml_training_orchestrator.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Candidate extraction/evaluation and scheduled training paths exist; genuine outcome sufficiency is model dependent. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Run sustained eligible training with consent and reviewed outcomes.

### AI-15 — Model registry and serving readiness

**IMPLEMENTED_NOT_ACCEPTED** · ALFRED intelligence · P2.

- Source: [bounded readiness snapshot](../apps/ml_engine/training/orchestrator.py), [owner API](../apps/ml_engine/api/views.py), [freshness](../apps/ml_engine/models/training_state.py), [quality gates](../apps/ml_engine/training/quality.py), [AI UI](../static/js/intelligence.js), [template](../templates/ai_insights.html), [registry](../apps/ml_engine/core/alfred_registry.py).
- APIs/UI/models: `/api/ai/runtime-status/?serving_readiness=1` and `/ai/insights/`; AdaptiveModelState, existing registry/adapter gates. Metadata only; no model/training/provider activation or canonical financial authority.
- Tests: 45 final focused backend PASS, four Chrome workflows PASS with one overlapping final rerun. [Acceptance/privacy/fallback tests](../tests/test_serving_readiness.py), [existing readiness](../tests/test_ml_readiness.py), [registry recovery](../tests/test_model_registry_recovery.py). Receipts in the active checkpoint above.
- Acceptance: Bounded synthetic registry eligibility, deterministic adapter fallback, private-field omission, sample/quality/proxy/freshness gates, missing/corrupt artifacts, invalid scores/future completion, error/refresh and desktop/390px workflow PASS. Eligibility does not establish executable artifacts or real predictive accuracy; actual adapters revalidate.
- Limitations/dependencies: Full capability remains unaccepted pending genuine per-model held-out outcomes. No model promotion, calibrated confidence, live provider, package, normal real-account or production acceptance claimed.
- Next: Obtain an authorized reviewed outcome contract; validate each real model without weakening the newly accepted gates.

### AI-16 — Retrieval/model quality and drift monitoring

**PARTIALLY_IMPLEMENTED** · ALFRED intelligence · P2.

- Source: [MemoryLearning.evaluate](../apps/ml_engine/services/memory_learning.py), [reviewed cohort policy/comparisons](../apps/ml_engine/services/retrieval_quality.py), [encrypted retrieval](../apps/ml_engine/services/persistent_memory.py), [local embeddings](../apps/ml_engine/services/local_embeddings.py), [Memory UI](../static/js/memory.js), [settings template](../templates/settings/memory.html).
- APIs/UI/models: owner-only /api/ai/memories/learning/ and /settings/; existing User and encrypted MemoryStore. Queries/results are page-only, not training data or canonical financial authority.
- Tests: [cohort policy and comparisons](../tests/test_retrieval_quality.py), [real-local reviewed cohorts](../tests/test_retrieval_quality_ollama.py), [multi-case/privacy/deadline](../tests/test_memory_evaluation.py), [learning compatibility](../tests/test_memory_learning.py), [Chrome](../tests/test_user_data_browser.py). Fresh 2026-10-25 safeguard validation: 70 backend PASS (`artifacts/ci-repair-ac05515/ai16-safeguards.json`); no real inference, threshold change or promotion. Historical measured synthetic metrics remain scoped below, not general accuracy.
- Acceptance: backend/Chrome and actual local execution PASS. Legacy 24-case reference quality **REJECT**; frozen experimental protocol development precision **1.0/1.0**, recall **1.0/0.875**. Independent 12-case holdout precision **0.80→1.00**, recall/citation identity/abstention **1.00**, zero candidate retrieval errors/owner violations; **review eligible only**. Broader/distinct-model, sustained outcome, real-account and production acceptance PENDING. No external provider or private protocol migration enabled.
- Limitations/dependencies: current-source rejection, model/cohort identity, explicit quality/drift thresholds, readable fictional source misses and owner/index safety checks exist. Sustained drift, calibration and chronological production quality remain unestablished. Citation identity/owner labels never prove claim truth or bank authenticity; same-model reference reuse is not independent candidate evidence.
- Next: Preserve frozen policy and this independent held-out result; future policy tuning requires another independently reviewed unseen contract. Establish broader/chronological evaluation before any private model migration or promotion; this 12-case success is not general accuracy or sustained drift.

### AI-17 — Autonomous user task execution

**NOT_IMPLEMENTED** · ALFRED intelligence · P2.

- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js).
- APIs/UI/models: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py; User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Current assistant is read-only; no approved general autonomous mutations, planner/executor or financial action agent. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Confirm scope and human approval policy before implementation.

### AI-18 — Voice assistant

**NOT_IMPLEMENTED** · ALFRED intelligence · P2.

- Source: [apps/ml_engine/services/hybrid_intelligence.py](../apps/ml_engine/services/hybrid_intelligence.py), [apps/ml_engine/services/persistent_memory.py](../apps/ml_engine/services/persistent_memory.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py), [static/js/intelligence.js](../static/js/intelligence.js), [apps/ml_engine/services/voice_assistant.py](https://github.com/sourabh48/alfred_ai/blob/3932f391aa4eed7b3200ad3b034f7991435e01e4/apps/ml_engine/services/voice_assistant.py).
- APIs/UI/models: /ai/insights/; memory/learning/reasoning API paths in apps/ml_engine/api/urls.py; User; encrypted MemoryStore SQLite/index/journal, not canonical financial authority.
- Tests: [tests/test_hybrid_intelligence.py](../tests/test_hybrid_intelligence.py), [tests/test_persistent_memory.py](../tests/test_persistent_memory.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Legacy service imports optional external speech libraries and has no demonstrated routed UI/caller. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Unrouted voice prototype retired by M17; no working accepted voice assistant. Future scope requires confirmation.

### OPENAI-01 — Responses API request/response adapter

**COMPLETE_VERIFIED** · Optional OpenAI · P2.

- Source: [apps/ml_engine/services/memory_reasoning.py](../apps/ml_engine/services/memory_reasoning.py), [apps/ml_engine/api/memory.py](../apps/ml_engine/api/memory.py), [alfred_ai/settings.py](../alfred_ai/settings.py).
- APIs/UI/models: Memory reasoning/policy API; operator key configuration command; Owner reasoning policy and encrypted key; atomic local budget reservations.
- Tests: [tests/test_memory_reasoning.py](../tests/test_memory_reasoning.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. DISABLED; paid acceptance NOT_RUN.
- Limitations/dependencies: Pinned endpoint, schema/model/usage validation and bounded public-query adapter are synthetic tested; no paid acceptance. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Keep real access OFF until separately approved.

### OPENAI-02 — Model compatibility and current price review

**PARTIALLY_IMPLEMENTED** · Optional OpenAI · P1.

- Source: [apps/ml_engine/services/memory_reasoning.py](../apps/ml_engine/services/memory_reasoning.py), [apps/ml_engine/api/memory.py](../apps/ml_engine/api/memory.py), [alfred_ai/settings.py](../alfred_ai/settings.py).
- APIs/UI/models: Memory reasoning/policy API; operator key configuration command; Owner reasoning policy and encrypted key; atomic local budget reservations.
- Tests: [tests/test_memory_reasoning.py](../tests/test_memory_reasoning.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. Official documentation reviewed 2026-10-15; no account availability call.
- Limitations/dependencies: Pinned gpt-4.1-mini-2025-04-14 is deprecated; documented retirement 2027-01-14. Verified $0.40/$1.60 per million still matches code. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Select/test replacement with current official rates before enabling; no silent model switch.

### OPENAI-03 — Encrypted key provisioning and owner consent

**COMPLETE_VERIFIED** · Optional OpenAI · P2.

- Source: [apps/ml_engine/services/memory_reasoning.py](../apps/ml_engine/services/memory_reasoning.py), [apps/ml_engine/api/memory.py](../apps/ml_engine/api/memory.py), [alfred_ai/settings.py](../alfred_ai/settings.py).
- APIs/UI/models: Memory reasoning/policy API; operator key configuration command; Owner reasoning policy and encrypted key; atomic local budget reservations.
- Tests: [tests/test_memory_reasoning.py](../tests/test_memory_reasoning.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Masked operator provisioning plus owner policy and per-request public consent; no browser key leakage. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Use account-scoped approved keys; never expand to private financial content.

### OPENAI-04 — Privacy classification and sensitive-data filtering

**COMPLETE_VERIFIED** · Optional OpenAI · P2.

- Source: [apps/ml_engine/services/memory_reasoning.py](../apps/ml_engine/services/memory_reasoning.py), [apps/ml_engine/api/memory.py](../apps/ml_engine/api/memory.py), [alfred_ai/settings.py](../alfred_ai/settings.py).
- APIs/UI/models: Memory reasoning/policy API; operator key configuration command; Owner reasoning policy and encrypted key; atomic local budget reservations.
- Tests: [tests/test_memory_reasoning.py](../tests/test_memory_reasoning.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Public-only boundary rejects sensitive context; store:false is not a zero-retention promise. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Explain provider monitoring retention and keep private queries local.

### OPENAI-05 — Daily token and monetary spending caps

**COMPLETE_VERIFIED** · Optional OpenAI · P2.

- Source: [apps/ml_engine/services/memory_reasoning.py](../apps/ml_engine/services/memory_reasoning.py), [apps/ml_engine/api/memory.py](../apps/ml_engine/api/memory.py), [alfred_ai/settings.py](../alfred_ai/settings.py).
- APIs/UI/models: Memory reasoning/policy API; operator key configuration command; Owner reasoning policy and encrypted key; atomic local budget reservations.
- Tests: [tests/test_memory_reasoning.py](../tests/test_memory_reasoning.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Atomic upper-bound reservations include failure costs; current-day price-review gate and strict usage validation. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Reverify pricing/model caps before approved paid tests.

### OPENAI-06 — Fallback, timeout, redacted diagnostics and UI

**COMPLETE_VERIFIED** · Optional OpenAI · P2.

- Source: [apps/ml_engine/services/memory_reasoning.py](../apps/ml_engine/services/memory_reasoning.py), [apps/ml_engine/api/memory.py](../apps/ml_engine/api/memory.py), [alfred_ai/settings.py](../alfred_ai/settings.py).
- APIs/UI/models: Memory reasoning/policy API; operator key configuration command; Owner reasoning policy and encrypted key; atomic local budget reservations.
- Tests: [tests/test_memory_reasoning.py](../tests/test_memory_reasoning.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Ollama-first, no uncontrolled automatic paid retries; UI availability is not billing authorization. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Accept actual configured provider only under approval.

### OPENAI-07 — Real paid-provider acceptance

**BLOCKED_APPROVAL** · Optional OpenAI · P2.

- Source: [apps/ml_engine/services/memory_reasoning.py](../apps/ml_engine/services/memory_reasoning.py), [apps/ml_engine/api/memory.py](../apps/ml_engine/api/memory.py), [alfred_ai/settings.py](../alfred_ai/settings.py).
- APIs/UI/models: Memory reasoning/policy API; operator key configuration command; Owner reasoning policy and encrypted key; atomic local budget reservations.
- Tests: [tests/test_memory_reasoning.py](../tests/test_memory_reasoning.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. BLOCKED_APPROVAL
- Limitations/dependencies: Not authorized; no real request made. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Obtain model/provider consent and bounded synthetic-only spending authorization.

### SYNC-01 — Provider-neutral mock sync protocol

**COMPLETE_VERIFIED** · Encrypted intelligence synchronization · P2.

- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- APIs/UI/models: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks; Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Mock transport proves encrypted protocol behavior, not real remote service acceptance. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Keep mock receipts explicitly synthetic.

### SYNC-02 — Non-AWS encrypted object adapter (AWS withdrawn)

**NOT_IMPLEMENTED** · Encrypted intelligence synchronization · P2.

- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- APIs/UI/models: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks; Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. Synthetic S3 server only; no real account acceptance.
- Limitations/dependencies: AWS endpoint/account ownership restrictions; not arbitrary Azure/Drive/S3-compatible endpoint support. IAM/account unselected. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: AWS is permanently withdrawn, not a deliverable. Non-AWS replacement adapter remains unimplemented; R2 is a candidate, not approved/configured/live-tested.

### SYNC-03 — Startup/periodic/bounded shutdown sync

**COMPLETE_VERIFIED** · Encrypted intelligence synchronization · P2.

- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- APIs/UI/models: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks; Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py), [tests/test_memory_sync_runtime.py](../tests/test_memory_sync_runtime.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Native lifecycle and local retry state are tested; no real remote upload occurred. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Accept lifecycle under authorized provider faults.

### SYNC-04 — Offline durable retry and interrupted upload recovery

**COMPLETE_VERIFIED** · Encrypted intelligence synchronization · P2.

- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- APIs/UI/models: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks; Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Local-first changes and bounded retries preserve dirty state. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Exercise real provider disconnects only after approval.

### SYNC-05 — Authenticated versioned encrypted snapshots

**COMPLETE_VERIFIED** · Encrypted intelligence synchronization · P2.

- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- APIs/UI/models: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks; Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Client-authenticated ciphertext; immutable application snapshots differ from bucket object versioning. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Keep crypto/schema/version/size checks.

### SYNC-06 — Concurrent conflict detection and ownership

**COMPLETE_VERIFIED** · Encrypted intelligence synchronization · P2.

- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- APIs/UI/models: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks; Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Conditional writes, owner prefixes and validated events; real multi-device race acceptance pending. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Run two synthetic devices under approved provider.

### SYNC-07 — Tombstones, revocation and remote pruning

**COMPLETE_VERIFIED** · Encrypted intelligence synchronization · P2.

- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- APIs/UI/models: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks; Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Deletion propagation/checkpoint prevents resurrection; historical backups may retain revoked data. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Disclose retained snapshots/keys and test approved pruning.

### SYNC-08 — Trusted high-water checkpoint

**COMPLETE_VERIFIED** · Encrypted intelligence synchronization · P2.

- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- APIs/UI/models: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks; Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Separately protected checkpoint required for remote rollback detection; a copied DPAPI blob is not a portable key. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Accept new-profile key/checkpoint recovery separately.

### SYNC-09 — Portable keys and independent multi-device/device-loss recovery

**BLOCKED_APPROVAL** · Encrypted intelligence synchronization · P1.

- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- APIs/UI/models: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks; Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Profile-independent key/archive restore is unverified; cancelled passphrase flow and release-specific M15 waiver stay scoped. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: User selects a genuinely portable secure recovery method; do not restart cancelled dialogs.

### SYNC-10 — Real provider activation, costs and IAM acceptance

**BLOCKED_APPROVAL** · Encrypted intelligence synchronization · P2.

- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- APIs/UI/models: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks; Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. BLOCKED_APPROVAL
- Limitations/dependencies: Real sync remains disabled; region/bucket/account and spending/least-privilege acceptance not selected. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Obtain provider selection and separate synthetic-only authorization.

### SYNC-11 — Full application/cloud backup

**NOT_IMPLEMENTED** · Encrypted intelligence synchronization · P2.

- Source: [apps/ml_engine/services/memory_sync.py](../apps/ml_engine/services/memory_sync.py), [apps/ml_engine/services/memory_cloud.py](../apps/ml_engine/services/memory_cloud.py), [alfred_ai/native_tasks.py](../alfred_ai/native_tasks.py).
- APIs/UI/models: Memory sync/status/checkpoint endpoints in ML API; native lifecycle hooks; Encrypted MemoryStore, authenticated snapshots, owner journal, protected trusted checkpoint.
- Tests: [tests/test_memory_sync.py](../tests/test_memory_sync.py), [tests/test_memory_cloud.py](../tests/test_memory_cloud.py), [tests/test_memory_checkpoint.py](../tests/test_memory_checkpoint.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Memory sync does not synchronize canonical Django databases/media/config or raw SQLite/WAL. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Keep approved application backup tooling separate from memory protocol.

### TRAVEL-01 — Conversational discovery and saved preferences

**COMPLETE_VERIFIED** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Structured intent/state and correction rules, not unconstrained generative Travel reasoning. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Preserve state history and explicit confirmed preferences.

### TRAVEL-02 — Source-backed new destinations and novelty

**IMPLEMENTED_NOT_ACCEPTED** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: bounded synthetic destination novelty/source provenance accepted2026-10-27: case/spacing and owner-isolated recorded visits/rejections, failed/empty/filtered provider fallback, read-time expiry and invalid-clock abstention, escaped guide links and explicit static references. Batch123 backend/3 Chrome/8 global Axe PASS; active checkpoint and artifacts/travel-discovery-20261027. Full real-account destination accuracy and live provider/terms acceptance remain PENDING; this does not promote the parent capability.
- Limitations/dependencies: Dynamic Wikivoyage/provider discovery and saved history exist; absent visits are not proof of never visiting. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Accept actual intended destinations/sources under current terms.

### TRAVEL-03 — Large candidate pools, show-more batches and comparison

**COMPLETE_VERIFIED** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: bounded local synthetic workflow PASS: 169 integration backend, six overlapping final pool tests and one actual Chrome; see active 2026-10-25 checkpoint. Source availability may yield fewer than 20 candidates; this is not live destination accuracy, booking or permit acceptance.
- Limitations/dependencies: At most 20 distinct available source candidates are persisted; only three are enriched/displayed per batch. Existing owner/session controls; canonical data availability; acceptance plan.
- Accepted: existing session JSON retains a deduplicated 20-item pool with three-item worker batches, cursor/reopen/Previous, current-batch comparison, explicit selection, rejection revalidation, context invalidation and supersession. [Pool regressions](../tests/test_travel_candidate_pool.py). No new schema/provider or currency arithmetic. Next: TRAVEL-04 ordered multi-stop itinerary foundation; cross-batch shortlists and live inventory remain outside this bounded acceptance.

### TRAVEL-04 — Multiple destinations and day-wise itineraries

**PARTIALLY_IMPLEMENTED** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Owned manual 2–5 stop motorcycle/car itineraries, dated days, reorder/remove, shared Decimal budgets, invalidation, save/reopen and desktop/390px Chrome accepted (104 backend/10 Chrome). Bounded estimated-order preview and explicit confirmation additionally accepted (14 focused backend/11 integrated Chrome plus final affected cosmetic recheck; overlapping totals). Distances and optimized stop order are allowances; verified inter-stop roads, transport connections and independent route acceptance remain incomplete. No permits, bookings, fastest/cheapest route or availability certified.
- Next: Verify inter-stop routing and feasibility using approved provider evidence; keep unknown road legality and availability explicit. Independent DOC-07 quality work can continue meanwhile.

### TRAVEL-05 — Budget summaries and estimates

**COMPLETE_VERIFIED** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/costs.py](../apps/mobility/services/travel/costs.py), [apps/mobility/services/travel/money.py](../apps/mobility/services/travel/money.py).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Live quote, estimate, unknown and cached data remain distinct; legacy INR convention and scenario assumptions. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Keep canonical recorded spend separate from quoted planning costs.

### TRAVEL-06 — Motorbike/pillion and vehicle-aware planning

**COMPLETE_VERIFIED** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Profile and trip constraints affect planning; safety/road legality cannot be guaranteed by a car route. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Accept normal rider/pillion scenarios and honest limits.

### TRAVEL-07 — Scenic and truly alternative routes

**PARTIALLY_IMPLEMENTED** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/providers/routing.py](../apps/mobility/services/travel/providers/routing.py).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: 147 affected backend and twelve actual Chrome PASS, zero skips; final one-case responsive capture recheck overlaps the twelve. Receipts: `artifacts/ci-repair-ac05515/travel-route-accepted.json`, `travel-route-integration.json`, and `artifacts/travel-routes-90abb28/accepted-browser/browser_regression_summary.json`. New `tests/test_travel_route_choices.py` is in the required backend profile.
- Acceptance: Bounded synthetic alternative requests/explicit choice, citations, current evidence/revision checks, retry/busy handling, save/reopen, Decimal reconciliation and desktop/390px UI accepted. Live-provider, independent scenic/route quality and real-account/release acceptance remain PENDING.
- Limitations/dependencies: Alternatives only after a current single-route result of at most 100 km. Distinct normalized geometries do not verify different roads/actual overlap, scenic quality, motorcycle legality, closures or traffic. No provider activation, new keys or long-route availability claim. A missing confirmed route requires review; no other route is silently substituted.
- Local routing validation: request/GeoJSON coordinate shape, bounds and finite elevation are now checked before use; malformed responses are unavailable and cannot become LIVE cached/map routes. Cache v2 excludes legacy normalization while preserving old snapshots. The route-validation checkpoint above records 86 passing provider/planner/continuation tests; this does not establish alternate/scenic route quality.
- Next: Preserve the accepted bounded selection unit; obtain independently reviewed legal/scenic route evidence before broader verification. Continue the independent TRAVEL-08 restriction evidence/abstention gap without claiming car routing is bike-legal.

### TRAVEL-08 — Expressway avoidance and motorcycle road restrictions

**PARTIALLY_IMPLEMENTED** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: 160 affected backend integration PASS, final 21 focused PASS (20 overlap), 13 actual Chrome PASS and two final overlapping Chrome rechecks; zero skips. New `tests/test_travel_restrictions.py` is in the required backend profile. Receipts: `artifacts/ci-repair-ac05515/travel08-backend-accepted.json`, `travel08-final-focused.json`, and `artifacts/travel-restrictions-7a0b912/{accepted-browser,final-browser}/browser_regression_summary.json`.
- Acceptance: Local manual public-reference review/withdrawal, exact route/trip binding, owner/session/CSRF/revision controls, citations/expiry/receipt validation, all four qualified statuses, retry/draft handling, unchanged finance/itinerary and desktop/390px UI accepted with synthetic fixtures. VERIFIED describes an owner-reviewed reference, not independently verified law or legal clearance.
- Limitations/dependencies: Indian government reference-host policy only; no automatic fetching/authentication or live provider activation. Prohibition/conditional claims only; whole-route permission unsupported. Highway avoidance is broader than expressways; motorcycle_legal/closures remain UNKNOWN. Independent authority authenticity, road/expressway coverage, current conditions, global rules and real-account/release acceptance remain incomplete.
- Next: Obtain independently authenticated route-applicable restrictions or abstain; never label car routing bike-legal. Preserve this bounded workflow and continue the independent TRAVEL-09 road-detour/provenance gap.

### TRAVEL-09 — Route corridor stops and real detour distance

**PARTIALLY_IMPLEMENTED** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/discovery.py](../apps/mobility/services/travel/discovery.py).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Current sampled crow-flight corridor ranking is not verified road-detour distance. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Add bounded road-network detours and uncertain labels.

### TRAVEL-10 — Camping and attraction discovery

**COMPLETE_VERIFIED** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/providers/places.py](../apps/mobility/services/travel/providers/places.py).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: 47 backend + one actual Chrome PASS, zero skips; `artifacts/places-5c88944/`. Synthetic local/API/UI freshness, provenance, invalid clocks, partial/offline/cache and owner isolation accepted; desktop/narrow-screen screenshots inspected. No live provider/booking/permit claim.
- Limitations/dependencies: OSM/wiki POIs are not bookable camping availability or verified opening hours. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Retain read-time abstention and source/check/expiry receipts. Live location accuracy, opening, bookable availability and permits require their own authorized evidence.

### TRAVEL-11 — Hotel live availability

**BLOCKED_EXTERNAL** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/providers/accommodation.py](../apps/mobility/services/travel/providers/accommodation.py).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. REQUIRES_CREDENTIALS/CONTRACT; NOT_REAL_LIVE_TESTED.
- Limitations/dependencies: Duffel Stays adapter exists but account/service rights and live authorization are missing. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Select provider/contract and approve limited synthetic traveler queries.

### TRAVEL-12 — Flight live availability

**BLOCKED_EXTERNAL** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/providers/transport.py](../apps/mobility/services/travel/providers/transport.py).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. REQUIRES_CREDENTIALS/CONTRACT; NOT_REAL_LIVE_TESTED.
- Limitations/dependencies: Duffel Flights adapter exists, intentionally disabled without approved access; research links are not offers. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Authorize provider and capped synthetic availability acceptance.

### TRAVEL-13 — Train live seat/fare/waitlist inventory

**BLOCKED_EXTERNAL** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/providers/transport.py](../apps/mobility/services/travel/providers/transport.py).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: IndianRailProvider returns unavailable; pasted timetables are USER_PROVIDED, seat inventory UNKNOWN. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Obtain authorized contract/API; no scraping.

### TRAVEL-14 — Bus live inventory

**NOT_IMPLEMENTED** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/links.py](../apps/mobility/services/travel/links.py).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Link-outs exist; no live bus booking/inventory adapter is demonstrated. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Confirm approved provider before building live integration.

### TRAVEL-15 — Live permits and road closure confirmation

**PARTIALLY_IMPLEMENTED** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/providers/permits.py](../apps/mobility/services/travel/providers/permits.py).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Dated official references exist; no verified live permit availability or closure service. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Maintain reviewed effective-date references and unknown state.

### TRAVEL-16 — Weather, horizons and replanning

**COMPLETE_VERIFIED** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/providers/weather.py](../apps/mobility/services/travel/providers/weather.py).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Forecast horizon and stale/unknown guards are implemented; free service limits/terms apply. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Validate permitted service and current dates.

### TRAVEL-17 — GeoJSON mapping and optional tiles

**COMPLETE_VERIFIED** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/mapping.py](../apps/mobility/services/travel/mapping.py).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Local route geometry works without tiles; public tile use requires policy/attribution. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Keep tile requests explicit and no offline bulk download.

### TRAVEL-18 — Google Maps API integration and offline map packages

**NOT_IMPLEMENTED** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Map link-outs/Leaflet are not authenticated Google Maps integration or offline tile bundles. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Confirm product/provider choice and storage rights before implementation.

### TRAVEL-19 — Photos, GPS/date inference and trip galleries

**COMPLETE_VERIFIED** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel_media.py](../apps/mobility/services/travel_media.py).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: Generated private JPEG/PNG, EXIF date/GPS, explicit owner association and gallery accepted: 56 backend integration + ten final focused (eight overlap), one actual Chrome PASS, zero skips. Receipts `artifacts/media-0dc9e66/`; both theme/mobile screenshots inspected. Source-only; no public upload/provider or packaged claim.
- Limitations/dependencies: TripPhoto and EXIF review exist; inferred locations need user confirmation. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Preserve private/confirmed associations and opt-ins. Evaluate additional authorized camera/EXIF layouts separately; unknown EXIF timezones use the disclosed application timezone and do not establish location authenticity.

### TRAVEL-20 — Video management and social Travel profile

**NOT_IMPLEMENTED** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Image/gallery paths do not establish video ingestion or an Instagram-style publish/privacy lifecycle. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Confirm local/private versus public scope before adding models.

### TRAVEL-21 — Freshness, cache, quotas and safe external HTTP

**COMPLETE_VERIFIED** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/cache.py](../apps/mobility/services/travel/cache.py), [alfred_ai/services/public_http.py](../alfred_ai/services/public_http.py).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py), [tests/test_travel_http.py](../tests/test_travel_http.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Existing provider states/source labels and bounded transport reject unsafe destinations; live provider status remains independent. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Maintain T02/T12 and M14 protections.

### TRAVEL-22 — Provider telemetry retention and selective invalidation

**COMPLETE_VERIFIED** · Travel · P1.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js), [apps/mobility/services/travel/cache.py](../apps/mobility/services/travel/cache.py).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: TravelProviderRequest persists without production cleanup; current quotas and active work constrain deletion. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: M16 bounded telemetry retention and selective invalidation implemented; tests/test_travel_retention.py and tests/test_travel_refresh.py; local frozen 4aa7ac70 gate.

### TRAVEL-23 — API budgets and provider terms compliance

**IMPLEMENTED_NOT_ACCEPTED** · Travel · P2.

- Source: [apps/mobility/services/travel_conversation.py](../apps/mobility/services/travel_conversation.py), [apps/mobility/services/travel/research.py](../apps/mobility/services/travel/research.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [static/js/travel_planner.js](../static/js/travel_planner.js).
- APIs/UI/models: /mobility/; travel routes in apps/mobility/urls.py; TravelPlan, TravelPlanningSession, TravelMessage, TravelResearchEvidence, TravelProviderState, TravelProviderRequest, preferences/history/media.
- Tests: [tests/test_travel_planner.py](../tests/test_travel_planner.py), [tests/test_travel_providers.py](../tests/test_travel_providers.py), [tests/test_travel_continuation.py](../tests/test_travel_continuation.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Bounded unit 2026-10-31 (source/test only, branch `batch/fast-dev-20261031`): `budget_status` is now the single source for enforcement and the staff panel, reporting used/remaining local budget per minute/hour/day/month; the panel separates it from provider-reported quota. Window parity, window expiry, cached evidence on exhaustion with no call, staff-only access and no secret disclosure: 56 Travel backend and one actual Chrome PASS, zero skips. Existing Brave terms opt-out cache isolation was reviewed and retained. No provider was called or activated.
- Limitations/dependencies: Application quotas/paid opt-ins/storage flags exist; provider-specific plan rights and current account limits need acceptance. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Use current register and contract-specific approval.

### CAREER-01 — Resume upload, extraction and review

**COMPLETE_VERIFIED** · Career · P2.

- Source: [apps/career/services/job_intelligence.py](../apps/career/services/job_intelligence.py), [apps/career/services/resume_intelligence.py](../apps/career/services/resume_intelligence.py), [apps/career/urls.py](../apps/career/urls.py), [static/js/career.js](../static/js/career.js).
- APIs/UI/models: /career/; /api/career/ (see urls.py); CareerProfile, CareerResume, CareerResumeLearningMemory, CareerJobAnalysis.
- Tests: [tests/test_career_resume_upload.py](../tests/test_career_resume_upload.py), [tests/test_career_recruiter_and_evidence.py](../tests/test_career_recruiter_and_evidence.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: OCR/layout diversity still needs acceptance; protected diagnostics/resource budgets are implemented. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Expand authorized reviewed CV corpus.

### CAREER-02 — Skill-gap and recruiter/JD matching

**COMPLETE_VERIFIED** · Career · P2.

- Source: [apps/career/services/job_intelligence.py](../apps/career/services/job_intelligence.py), [apps/career/services/resume_intelligence.py](../apps/career/services/resume_intelligence.py), [apps/career/urls.py](../apps/career/urls.py), [static/js/career.js](../static/js/career.js).
- APIs/UI/models: /career/; /api/career/ (see urls.py); CareerProfile, CareerResume, CareerResumeLearningMemory, CareerJobAnalysis.
- Tests: `tests.test_career_matching_acceptance` plus recruiter/resume/adaptive, baseline/risk freshness, document review/retry, public-HTTP and error regressions: 93 backend PASS; three actual Chrome integration PASS (matching plus budget/place regressions), zero skips. Receipts: `artifacts/career-7ede529/` above.
- Acceptance: Reviewed deterministic overlap/gap fixtures, unchanged scoring weights, numbered captured resume/JD sources, source stability across later uploads and document corrections, ownership/session/CSRF, explicit abstention and actual desktop/mobile workflow accepted locally with synthetic data. Financial records unchanged.
- Limitations/dependencies: Catalog-based extraction is capped at 20 listed terms; optional/negated/conflicting requirements require review and withhold overall scoring. Missing terms do not prove absent skills. Role/company extraction remains heuristic; no calibrated hiring probability, genuine recruiter outcome accuracy or live employer verification. Legacy results without source references must be reanalyzed before reliance.
- Next: Preserve these source/uncertainty contracts during CAREER-04/07/08; collect genuinely reviewed outcomes before any predictive-quality claim.

### CAREER-03 — Job discovery and recommendations

**IMPLEMENTED_NOT_ACCEPTED** · Career · P2.

- Source: [job intelligence](../apps/career/services/job_intelligence.py), [owner API](../apps/career/views.py), [Career UI](../static/js/career.js), [template](../templates/career/list.html).
- APIs/UI/models: /career/; /api/career/dashboard/; existing owned CareerProfile and cache.
- Tests: [discovery](../tests/test_career_discovery_acceptance.py), [geography](../tests/test_career_location_acceptance.py), [matching](../tests/test_career_matching_acceptance.py), [recruiter/evidence](../tests/test_career_recruiter_and_evidence.py), [Chrome](../tests/test_user_data_browser.py). Original66 Discovery and56 Geography backend totals overlap. Both suites are retained on the local reconciliation candidate and backend profile.
- Acceptance: SCOPE-01 provenance/unknown/stale labels, safe URLs, canonical duplicates, bounded failures and owner-cache expiry atd8f57be retains local66 backend/12 metadata/one Chrome/four overlapping Axe/privacy0. Exact-head run40336191319 cancelled after Selenium exceeded30m; fresh local66 PASS does not replace CI. SCOPE-02 source1c5f11e/checkpointdc96b19 retains56 backend/12 metadata/one Chrome/four overlapping Axe/privacy0; no CI. Country/state restrictions, missing/ambiguous/negative geography, focused dropdown response ordering and unsaved edits coexist with Discovery on the local candidate only. Both scopes remain95% pending their required gates; no canonical integration claimed.
- Limitations/dependencies: Full CAREER-03, arbitrary/live geography, work permits/legal eligibility, listing availability, provider terms, real accounts, manual screen-reader and packaged acceptance remain unaccepted. No provider/schema/currency/financial writes or application sending.
- Next: Finish consolidated candidate verification; obtain required independent review and authorized exact-head CI before integration. Stage7 selection follows consolidation, not blocked-merge bypass.
### CAREER-04 — Recruiter email/attachment processing

**PARTIALLY_IMPLEMENTED** · Career · P2.

- Source: [apps/career/services/job_intelligence.py](../apps/career/services/job_intelligence.py), [apps/career/services/resume_intelligence.py](../apps/career/services/resume_intelligence.py), [apps/career/urls.py](../apps/career/urls.py), [static/js/career.js](../static/js/career.js), [apps/integrations/services/email_integration.py](../apps/integrations/services/email_integration.py).
- APIs/UI/models: /career/; /api/career/ (see urls.py); CareerProfile, CareerResume, CareerResumeLearningMemory, CareerJobAnalysis.
- Tests: [tests/test_career_resume_upload.py](../tests/test_career_resume_upload.py), [tests/test_career_recruiter_and_evidence.py](../tests/test_career_recruiter_and_evidence.py), [tests/test_career_matching_acceptance.py](../tests/test_career_matching_acceptance.py), [tests/test_user_data_browser.py](../tests/test_user_data_browser.py). Fresh scoped evidence: 81 backend and 5 integrated actual Chrome PASS, zero skips; see manual recruiter checkpoint above.
- Acceptance: PASS for synthetic manual-equivalent JD/attachment intake, explicit owned resume selection, source references, abstention, error/retry, correction/reopen and ownership/CSRF. Desktop/390px captures inspected. This is not live-mail, real-account, predictive-quality or packaged acceptance.
- Limitations/dependencies: Automatic mail access is not an accepted integrated workflow and remains off. Career Ops repository identity is unverified; repository-dependent conversion is deferred independently. The retired OAuth prototypes must not be revived.
- Next: Preserve accepted manual source/correction/retry contracts. Automatic mailbox processing requires separately approved provider access, a reviewed integration and live acceptance; continue independent DOC/AI work meanwhile.

### CAREER-05 — Application and opportunity outcome tracking

**COMPLETE_VERIFIED** · Career · P2.

- Source: [apps/career/services/job_intelligence.py](../apps/career/services/job_intelligence.py), [apps/career/services/resume_intelligence.py](../apps/career/services/resume_intelligence.py), [apps/career/urls.py](../apps/career/urls.py), [static/js/career.js](../static/js/career.js).
- APIs/UI/models: /career/; /api/career/ (see urls.py); CareerProfile, CareerResume, CareerResumeLearningMemory, CareerJobAnalysis.
- Tests: [outcome workflow/ownership/precision](../tests/test_career_outcome_workflow.py), [Career compatibility](../tests/test_career_adaptive_intelligence.py), [owner UI](../tests/test_user_data_browser.py). **45 focused backend + one actual Chrome PASS**, zero skips; receipts at `artifacts/career-outcome-ec9c161/`.
- Acceptance: TECHNICAL_PASS, isolated owner-reported accepted/rejected history, pagination, safe correction, source lineage, concurrent/stale edits, financial invariance and desktop/390px UI. Normal-account/employer/provider acceptance remains NOT_RUN.
- Limitations/dependencies: Reports are owner statements, not independent employer verification. No universal ATS/automatic apply, learned salary accuracy, outcome-corpus maturity, currency conversion or mixed-currency validation is claimed. Existing schema/currency behavior and all activation gates are preserved.
- Next: Retain these source and correction guards; independently evaluate approved genuine outcomes before changing learning-maturity claims.

### CAREER-06 — Salary/location evidence and progression

**IMPLEMENTED_NOT_ACCEPTED** · Career · P2.

- Source: [apps/career/services/job_intelligence.py](../apps/career/services/job_intelligence.py), [apps/career/services/resume_intelligence.py](../apps/career/services/resume_intelligence.py), [apps/career/urls.py](../apps/career/urls.py), [static/js/career.js](../static/js/career.js), [apps/career/services/projection_engine.py](../apps/career/services/projection_engine.py).
- APIs/UI/models: /career/; /api/career/ (see urls.py); CareerProfile, CareerResume, CareerResumeLearningMemory, CareerJobAnalysis.
- Tests: [tests/test_career_resume_upload.py](../tests/test_career_resume_upload.py), [tests/test_career_recruiter_and_evidence.py](../tests/test_career_recruiter_and_evidence.py), [tests/test_career_projection_confidence.py](../tests/test_career_projection_confidence.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Bounded unit 2026-10-31 (source/test only, branch `batch/fast-dev-20261031`): repeated-currency ranges keep both bounds; EUR/GBP are no longer labelled INR and unstated currency stays unknown (only lakh/crore/LPA imply INR); week/day periods annualize and unknown JSON-LD units abstain; malformed/non-finite JSON-LD and extreme values abstain; page text needs pay wording, so `$50M funding` is not salary. Benchmarks use one currency cohort with no conversion, even splits abstain, foreign/unknown bands are not compared with rupee income, assumed annual periods are counted and labelled, outcome medians abstain across currencies, and the UI shows the real currency. [tests/test_career_salary_evidence.py](../tests/test_career_salary_evidence.py): 43 failures/errors before the fix; 89 focused Career backend and one actual Chrome PASS after, zero skips. No schema or stored-record change.
- Limitations/dependencies: Career salary storage remains float. Owner-entered outcomes without a currency still default to INR. Unstated pay periods remain an annual assumption, labelled but not resolved. Non-INR/USD/EUR/GBP codes in free text stay unknown. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Expand approved real evidence; salary-sample accuracy and FIN-CURRENCY remain unaccepted.

### CAREER-07 — Interview preparation

**PARTIALLY_IMPLEMENTED** · Career · P2.

- Source: [apps/career/services/job_intelligence.py](../apps/career/services/job_intelligence.py), [apps/career/services/resume_intelligence.py](../apps/career/services/resume_intelligence.py), [apps/career/urls.py](../apps/career/urls.py), [static/js/career.js](../static/js/career.js).
- APIs/UI/models: /career/; /api/career/ (see urls.py); CareerProfile, CareerResume, CareerResumeLearningMemory, CareerJobAnalysis.
- Tests: [tests/test_career_resume_upload.py](../tests/test_career_resume_upload.py), [tests/test_career_recruiter_and_evidence.py](../tests/test_career_recruiter_and_evidence.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Study recommendations exist; no demonstrated interactive verified interview-coach workflow. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Confirm desired local coaching scope and reuse skill gaps.

### CAREER-08 — Predictive career forecasting and timing

**PARTIALLY_IMPLEMENTED** · Career · P2.

- Source: [apps/career/services/job_intelligence.py](../apps/career/services/job_intelligence.py), [apps/career/services/resume_intelligence.py](../apps/career/services/resume_intelligence.py), [apps/career/urls.py](../apps/career/urls.py), [static/js/career.js](../static/js/career.js).
- APIs/UI/models: /career/; /api/career/ (see urls.py); CareerProfile, CareerResume, CareerResumeLearningMemory, CareerJobAnalysis.
- Tests: [tests/test_career_resume_upload.py](../tests/test_career_resume_upload.py), [tests/test_career_recruiter_and_evidence.py](../tests/test_career_recruiter_and_evidence.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Heuristic/model-backed modes and confidence exist; calibrated genuine future outcome accuracy is unverified. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Collect consenting outcomes and evaluate chronological holdout.

### FAMILY-01 — Family relationships and invitation lifecycle

**COMPLETE_VERIFIED** · Family, relationships and risk · P2.

- Source: [apps/family/services.py](../apps/family/services.py), [apps/family/models.py](../apps/family/models.py), [apps/family/urls.py](../apps/family/urls.py).
- APIs/UI/models: /family/; family relationship/financial-sharing APIs; Dependent, FamilyAccountLink; owner-scoped financial baseline.
- Tests: [tests/test_family_account_links.py](../tests/test_family_account_links.py), [tests/test_family_invitation_throttling.py](../tests/test_family_invitation_throttling.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Accepted relationships alone do not authorize financial sharing. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Complete normal user invite/revoke acceptance.

### FAMILY-02 — Explicit financial opt-in and revocation

**COMPLETE_VERIFIED** · Family, relationships and risk · P2.

- Source: [apps/family/services.py](../apps/family/services.py), [apps/family/models.py](../apps/family/models.py), [apps/family/urls.py](../apps/family/urls.py), [apps/family/migrations/0004_financial_sharing_opt_in.py](../apps/family/migrations/0004_financial_sharing_opt_in.py).
- APIs/UI/models: /family/; family relationship/financial-sharing APIs; Dependent, FamilyAccountLink; owner-scoped financial baseline.
- Tests: [tests/test_family_account_links.py](../tests/test_family_account_links.py), [tests/test_family_invitation_throttling.py](../tests/test_family_invitation_throttling.py), [tests/test_family_consent_migration.py](../tests/test_family_consent_migration.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: family.0004 reset historical grants OFF at M14 deployment; owner consent governs shared summaries. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Never equate relationship membership with consent.

### FAMILY-03 — Invitation throttling and concurrent acceptance

**COMPLETE_VERIFIED** · Family, relationships and risk · P2.

- Source: [apps/family/services.py](../apps/family/services.py), [apps/family/models.py](../apps/family/models.py), [apps/family/urls.py](../apps/family/urls.py).
- APIs/UI/models: /family/; family relationship/financial-sharing APIs; Dependent, FamilyAccountLink; owner-scoped financial baseline.
- Tests: [tests/test_family_account_links.py](../tests/test_family_account_links.py), [tests/test_family_invitation_throttling.py](../tests/test_family_invitation_throttling.py), [tests/test_family_invitation_atomic.py](../tests/test_family_invitation_atomic.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Existing account-isolated atomic throttles apply independently of authorization. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Preserve 429/no-mutation/expiry regressions.

### FAMILY-04 — Cross-account isolation

**COMPLETE_VERIFIED** · Family, relationships and risk · P2.

- Source: [apps/family/services.py](../apps/family/services.py), [apps/family/models.py](../apps/family/models.py), [apps/family/urls.py](../apps/family/urls.py).
- APIs/UI/models: /family/; family relationship/financial-sharing APIs; Dependent, FamilyAccountLink; owner-scoped financial baseline.
- Tests: [tests/test_family_account_links.py](../tests/test_family_account_links.py), [tests/test_family_invitation_throttling.py](../tests/test_family_invitation_throttling.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Family financial summaries require consent; personal memories/documents remain owner scoped. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Retain revoked/foreign-ID negative tests.

### FAMILY-05 — Relationship alignment and family growth

**IMPLEMENTED_NOT_ACCEPTED** · Family, relationships and risk · P2.

- Source: [apps/family/services.py](../apps/family/services.py), [apps/family/models.py](../apps/family/models.py), [apps/family/urls.py](../apps/family/urls.py), [apps/family/views.py](../apps/family/views.py), [apps/relationship/services/relationship_intelligence.py](../apps/relationship/services/relationship_intelligence.py).
- APIs/UI/models: /family/; family relationship/financial-sharing APIs; Dependent, FamilyAccountLink; owner-scoped financial baseline.
- Tests: [tests/test_family_account_links.py](../tests/test_family_account_links.py), [tests/test_family_invitation_throttling.py](../tests/test_family_invitation_throttling.py), [tests/test_investment_and_relationship_advisory.py](../tests/test_investment_and_relationship_advisory.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Bounded unit 2026-10-31 (source/test only, branch `batch/fast-dev-20261031`): reproduced a "Good 72.57" verdict with no income, a perfect Planning score when external context was absent, unset partner fields scored as measured zero, and API acceptance of out-of-range values (NaN caused a server error). Alignment now abstains without income, drops and reweights unavailable factors with the original weights, blends the model only on complete inputs, and reports coverage; new API writes are bounded and finite while legacy records stay readable and unrewritten; the chart no longer invents fallback values. 46 related backend and one new actual Chrome PASS, zero skips. Complete inputs keep the existing formula; no schema change.
- Limitations/dependencies: Grounded inputs plus bounded model blend; 8% family projection is already labelled heuristic, not guaranteed. A partner score or compatibility input of exactly 0 is treated as not provided. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Evaluate outcomes rather than reopen an already-labelled assumption.

### FAMILY-06 — Behavioral signals and personalization

**IMPLEMENTED_NOT_ACCEPTED** · Family, relationships and risk · P2.

- Source: [apps/family/services.py](../apps/family/services.py), [apps/family/models.py](../apps/family/models.py), [apps/family/urls.py](../apps/family/urls.py), [apps/behavioral/services.py](../apps/behavioral/services.py).
- APIs/UI/models: /family/; family relationship/financial-sharing APIs; Dependent, FamilyAccountLink; owner-scoped financial baseline.
- Tests: [tests/test_family_account_links.py](../tests/test_family_account_links.py), [tests/test_family_invitation_throttling.py](../tests/test_family_invitation_throttling.py), [tests/test_behavioral_linkage.py](../tests/test_behavioral_linkage.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Bounded unit 2026-10-31 (source/test only, branch `batch/fast-dev-20261031`): reproduced an empty spending week scored as 0.0, which turned manual stress 8 into 5.2, padded the series with zeros that could fake a trend, and lost its "No debit activity" driver. Empty windows are now marked, excluded from the blend and Behavior pressure average, and skipped in the series, with the existing fallback only when nothing remains. The Risk signal API now rejects values outside 0-100 and non-finite values (`NaN` previously raised a database error); legacy records stay readable and unrewritten. 74 affected backend and one actual Chrome PASS, zero skips. No schema or JavaScript change.
- Limitations/dependencies: Manual signals and derived pressure maps exist; clinical/personal prediction accuracy not established. Manual logs and spending weeks are still paired by position, not date, and the stress chart's T-n labels do not show skipped weeks. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Obtain consent and labelled outcomes; avoid medical certainty.

### FAMILY-07 — Financial/health/relocation risk intelligence

**IMPLEMENTED_NOT_ACCEPTED** · Family, relationships and risk · P2.

- Source: [apps/family/services.py](../apps/family/services.py), [apps/family/models.py](../apps/family/models.py), [apps/family/urls.py](../apps/family/urls.py), [apps/risk/services/risk_intelligence.py](../apps/risk/services/risk_intelligence.py).
- APIs/UI/models: /family/; family relationship/financial-sharing APIs; Dependent, FamilyAccountLink; owner-scoped financial baseline.
- Tests: [tests/test_family_account_links.py](../tests/test_family_account_links.py), [tests/test_family_invitation_throttling.py](../tests/test_family_invitation_throttling.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Bounded unit 2026-10-31 (source/test only, branch `batch/fast-dev-20261031`): reproduced phantom risk where an account with no logs scored 48 Health from "0h sleep", a no-vehicle account scored 32.5 Mobility, unset sleep raised Health from 11 to 59, and an abstained job fit counted as a 100 gap. Never-recorded inputs now add no risk; each category reports coverage and missing inputs; insufficient categories are excluded from highest/average; trends say insufficient history or not tracked instead of stable; output states uncalibrated heuristic, not diagnosis. Recorded values still score as before. 89 related backend, one new actual Chrome and 27 browser-plan PASS, zero skips. Canonical financial baseline untouched; no schema change.
- Limitations/dependencies: Risk scores mix history, heuristic weights and external context; not calibrated diagnosis/prediction. An explicit stress score of 0 cannot be told apart from an unset one. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Document confidence and evaluate actual outcomes.

### BIKE-01 — Vehicle profiles and Hunter 350 catalog support

**IMPLEMENTED_NOT_ACCEPTED** · Bike and mobility · P2.

- Source: [apps/mobility/services/bike_service_intelligence.py](../apps/mobility/services/bike_service_intelligence.py), [apps/mobility/services/bike_catalog.py](../apps/mobility/services/bike_catalog.py), [apps/mobility/urls.py](../apps/mobility/urls.py).
- APIs/UI/models: /bike-service/ and /api/mobility/; supported routes in root URLs; BikeProfile, BikeServiceRecord, FuelRefillLog, BikeIssueReport, BikeDocument, BikeConditionSnapshot.
- Tests: [tests/test_mobility_vehicle_dashboard.py](../tests/test_mobility_vehicle_dashboard.py), [tests/test_vehicle_accounting.py](../tests/test_vehicle_accounting.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Catalog and profile defaults exist; official current model/service variants need acceptance. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Verify manufacturer/model data and owner's actual vehicle.

### BIKE-02 — Service records, fuel and costs

**COMPLETE_VERIFIED** · Bike and mobility · P2.

- Source: [apps/mobility/services/bike_service_intelligence.py](../apps/mobility/services/bike_service_intelligence.py), [apps/mobility/services/bike_catalog.py](../apps/mobility/services/bike_catalog.py), [apps/mobility/urls.py](../apps/mobility/urls.py).
- APIs/UI/models: /bike-service/ and /api/mobility/; supported routes in root URLs; BikeProfile, BikeServiceRecord, FuelRefillLog, BikeIssueReport, BikeDocument, BikeConditionSnapshot.
- Tests: [tests/test_mobility_record_acceptance.py](../tests/test_mobility_record_acceptance.py), [tests/test_mobility_vehicle_dashboard.py](../tests/test_mobility_vehicle_dashboard.py), [tests/test_mobility_money.py](../tests/test_mobility_money.py), [tests/test_vehicle_accounting.py](../tests/test_vehicle_accounting.py), [tests/test_user_data_browser.py](../tests/test_user_data_browser.py). **35 backend / one actual Chrome PASS**, zero skips; `artifacts/vehicle-95f30bc/checkpoint-accepted.json` and inspected desktop/390px screenshots.
- Acceptance: local ordinary-owner service/refill CRUD, linked profile isolation, Decimal cost/measurement precision, derived mileage/price, safe server-date defaults, cache corrections and usable mobile/desktop history verified with synthetic data. Foreign records and financial totals preserved.
- Limitations/dependencies: Costs already use Decimal fields and existing migration receipts; quantities remain measurements. Owner-entered history is not invoice/odometer authenticity, tank calibration or predictive service accuracy. Native/package/private-account/provider acceptance remains separate.
- Next: BIKE-04 document/invoice review acceptance; preserve source lineage and owner scope, without claiming real-document authenticity from fixtures.

### BIKE-03 — Maintenance prediction and condition tracking

**PARTIALLY_IMPLEMENTED** · Bike and mobility · P2.

- Source: [apps/mobility/services/bike_service_intelligence.py](../apps/mobility/services/bike_service_intelligence.py), [apps/mobility/services/bike_catalog.py](../apps/mobility/services/bike_catalog.py), [apps/mobility/urls.py](../apps/mobility/urls.py).
- APIs/UI/models: /bike-service/ and /api/mobility/; supported routes in root URLs; BikeProfile, BikeServiceRecord, FuelRefillLog, BikeIssueReport, BikeDocument, BikeConditionSnapshot.
- Tests: [tests/test_mobility_vehicle_dashboard.py](../tests/test_mobility_vehicle_dashboard.py), [tests/test_vehicle_accounting.py](../tests/test_vehicle_accounting.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Rules, condition snapshots and optional service model exist; prediction quality is unverified. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Evaluate real service outcomes; label intervals/part-life assumptions.

### BIKE-04 — Insurance/service documents and invoice review

**IMPLEMENTED_NOT_ACCEPTED** · Bike and mobility · P2.

- Source: [apps/mobility/services/bike_service_intelligence.py](../apps/mobility/services/bike_service_intelligence.py), [apps/mobility/services/bike_catalog.py](../apps/mobility/services/bike_catalog.py), [apps/mobility/urls.py](../apps/mobility/urls.py), [apps/mobility/services/bike_document_ai.py](../apps/mobility/services/bike_document_ai.py).
- APIs/UI/models: /bike-service/ and /api/mobility/; supported routes in root URLs; BikeProfile, BikeServiceRecord, FuelRefillLog, BikeIssueReport, BikeDocument, BikeConditionSnapshot.
- Tests: [tests/test_mobility_vehicle_dashboard.py](../tests/test_mobility_vehicle_dashboard.py), [tests/test_vehicle_accounting.py](../tests/test_vehicle_accounting.py), [tests/test_bike_document_parser.py](../tests/test_bike_document_parser.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: Local synthetic PDF import/review/replay accepted with 24 backend and one actual Chrome PASS (zero skips); receipts `artifacts/invoice-3c09291/`. Approved real invoice/insurance layouts remain PENDING; this is source-only evidence.
- Limitations/dependencies: Extraction, relevance checks and linked service updates exist; layout/identity review is essential. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Accept approved real invoice/insurance layouts. No-duplicate posting is verified for byte replay/concurrent upload and complete identity conflicts; incomplete/legacy identifiers still require review.

### BIKE-05 — Spare parts and service recommendations

**PARTIALLY_IMPLEMENTED** · Bike and mobility · P2.

- Source: [apps/mobility/services/bike_service_intelligence.py](../apps/mobility/services/bike_service_intelligence.py), [apps/mobility/services/bike_catalog.py](../apps/mobility/services/bike_catalog.py), [apps/mobility/urls.py](../apps/mobility/urls.py).
- APIs/UI/models: /bike-service/ and /api/mobility/; supported routes in root URLs; BikeProfile, BikeServiceRecord, FuelRefillLog, BikeIssueReport, BikeDocument, BikeConditionSnapshot.
- Tests: [tests/test_mobility_vehicle_dashboard.py](../tests/test_mobility_vehicle_dashboard.py), [tests/test_vehicle_accounting.py](../tests/test_vehicle_accounting.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Model/class heuristics and suggestions exist; no verified live price/parts-inventory service. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Use authoritative compatibility and mark estimates.

### BIKE-06 — Travel integration and vehicle net-worth relationship

**COMPLETE_VERIFIED** · Bike and mobility · P2.

- Source: [apps/mobility/services/bike_service_intelligence.py](../apps/mobility/services/bike_service_intelligence.py), [apps/mobility/services/bike_catalog.py](../apps/mobility/services/bike_catalog.py), [apps/mobility/urls.py](../apps/mobility/urls.py).
- APIs/UI/models: /bike-service/ and /api/mobility/; supported routes in root URLs; BikeProfile, BikeServiceRecord, FuelRefillLog, BikeIssueReport, BikeDocument, BikeConditionSnapshot.
- Tests: [tests/test_mobility_vehicle_dashboard.py](../tests/test_mobility_vehicle_dashboard.py), [tests/test_vehicle_accounting.py](../tests/test_vehicle_accounting.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Vehicle utility/valuation assumptions and route wear affect existing baseline/planner; no guaranteed road legality. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Keep confirmed profile inputs and canonical reconciliation.

### COUNCIL-01 — Multiple ML inference roles and registry routing

**IMPLEMENTED_NOT_ACCEPTED** · AI Council and developer intelligence · P2.

- Source: [apps/ml_engine/core/alfred_registry.py](../apps/ml_engine/core/alfred_registry.py), [apps/ml_engine/self_improve/advanced_engine.py](https://github.com/sourabh48/alfred_ai/blob/3932f391aa4eed7b3200ad3b034f7991435e01e4/apps/ml_engine/self_improve/advanced_engine.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py).
- APIs/UI/models: ML runtime status; no routed self-improvement/coding-council API; AdaptiveModelState/AdaptiveTrainingRun; Codex skills are tools outside the application.
- Tests: [tests/test_ml_readiness.py](../tests/test_ml_readiness.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Inference adapters are specialized predictions, not development planning/coding/review agents. Existing owner/session controls; canonical data availability; acceptance plan.
- Local persistence extension: registry stores version/training metadata; actual serving readiness uses specialized adapters/model state. Atomic receipt replacement, failed-write/corrupt-input preservation and same-process threaded merge accepted with 28 backend PASS (six registry checks), zero skips; `artifacts/registry-de7a498/`. No multi-process writer, genuine model-quality or application agent acceptance claimed.
- Next: Accept specialized inference role routing and genuine held-out outcomes; do not repeat the completed persistence regression or describe metadata receipts as planning/coding agents.

### COUNCIL-02 — Planning/coding/review/security multi-agent application

**PARTIALLY_IMPLEMENTED** · AI Council and developer intelligence · P2.

- Source: [development Council](../scripts/development_council.py), [existing skills](../.agents/skills/alfred-project-context/SKILL.md), [reused local transport/digest checks](../apps/ml_engine/services/local_embeddings.py).
- APIs/UI/models: development-only CLI and local escaped HTML status; owner-protected operational SQLite under ignored artifacts. No coding/production HTTP endpoint.
- Tests: [Council contracts](../tests/test_development_council.py); actual focused counts/evidence above.
- Acceptance: disposable contracts and five actual scoped host-mediated cycles PASS, including v2 independent actor/source/test/commit routing at d5078b9 (**30 backend + 1 status-browser flow**, overlaps combined evidence). Two later bounded local advisories produced signals/proposals only, never role approval; earlier blocked advice preserved. No unattended development/production or general model-review quality claim.
- Limitations/dependencies: deterministic Planner, Codex-host/human Developer/Reviewer/Security, isolated Tester and commit-verifying Coordinator. Optional local advice never approves a role. No autonomous patch execution, production operations, paid-provider routing or quota bypass.
- Next: Seven-role extension f649da6 and actual v3 DOC-07 backend/UI/field and DOC-06 filter cycles are complete. Continue subsequent approved local tasks using current-source independent reviews, tests and Guardian checks. Preserve legacy receipts/budgets; no rebuild, paid fallback, automatic patch/Git/production execution or deployment approval.

### COUNCIL-03 — Experimental self-improvement engine

**NOT_IMPLEMENTED** · AI Council and developer intelligence · P1.

- Source: [apps/ml_engine/core/alfred_registry.py](../apps/ml_engine/core/alfred_registry.py), [apps/ml_engine/self_improve/advanced_engine.py](https://github.com/sourabh48/alfred_ai/blob/3932f391aa4eed7b3200ad3b034f7991435e01e4/apps/ml_engine/self_improve/advanced_engine.py), [apps/ml_engine/api/urls.py](../apps/ml_engine/api/urls.py).
- APIs/UI/models: ML runtime status; no routed self-improvement/coding-council API; AdaptiveModelState/AdaptiveTrainingRun; Codex skills are tools outside the application.
- Tests: [tests/test_ml_readiness.py](../tests/test_ml_readiness.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: advanced_engine imports absent patch_generator; SelfImproveAPI is not routed. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Unsafe experimental self-editing prototype retired by M17. Retirement is not delivery of a safe human-approved AI Council; no autonomous production code writes.

### COUNCIL-04 — Persistent tasks, conflicts and usage-limit recovery

**PARTIALLY_IMPLEMENTED** · AI Council and developer intelligence · P2.

- Source: [persistent Council task state](../scripts/development_council.py).
- APIs/UI/models: transactional task revisions, duplicate objectives, current-source role receipts, two-attempt limits, interrupted-worker leases and resumable host-commit verification.
- Tests: [Council contracts](../tests/test_development_council.py), including restart and stale-source failures.
- Acceptance: disposable interruption/race/legacy-history contracts and five actual task/commit reloads PASS; context reuse verified without provider calls. Host usage limits remain blocked handoffs, not quota bypass or simulated success.
- Limitations/dependencies: SQLite/HTML holds only safe operational metadata; PROJECT_STATUS remains the single tracker. No scheduler launching endless task loops; no cloud context export or replacement Codex authentication.
- Next: Retained structured decisions, idempotence, bounded overflow and current-source independence are complete at 97ed191 with actual seven-role acceptance. Finish the explicitly requested consolidation and release checks before selecting another safe task. Keep usage/cost uncertainty and operational approvals visible; no automatic production authority.

### COUNCIL-05 — AI development budget and human Git approval

**PARTIALLY_IMPLEMENTED** · AI Council and developer intelligence · P2.

- Source: [Council policy and evidence](../scripts/development_council.py), [existing release boundary](../scripts/release_gate.py).
- APIs/UI/models: bounded contexts/reservations/output/iterations, shared execution deadline, explicit host reviews and authorization reference for exact immutable commit verification. No Council Git writes.
- Tests: [Council budget/scope/approval contracts](../tests/test_development_council.py).
- Acceptance: synthetic budget/failure/approval contracts and five authorized scoped source/commit cycles PASS. New-task reservations cap at 8192 tokens/two advisory attempts; existing task limits retained, interrupted reservations never refunded. Legacy BLOCKED and later ADVISORY_ONLY remain distinct and neither approves roles; paid Council providers remain unapproved/unimplemented.
- Limitations/dependencies: host attestations are explicit operator/Codex evidence, not cryptographic proof of account quota. Token values are conservative reservations; no invented measured usage. Previous deployment/recovery approvals never authorize Council production changes.
- Next: Keep source verification, development commit authorization and production approval separate; no automatic fallback/spending/deployment.

### RUNTIME-01 — Native launcher, tray, worker and scheduler

**COMPLETE_VERIFIED** · Windows, deployment and release · P1.

- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec).
- APIs/UI/models: /health/native/; local launcher/tray; operator CLI; Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Historical native acceptance passed; initial health failed, later /health/live/ 200 and native 404 on runserver. Actual data/worker identity remains unconfirmed. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Diagnose current availability under a separately authorized operational task.

### RUNTIME-02 — Restart persistence and local data isolation

**COMPLETE_VERIFIED** · Windows, deployment and release · P2.

- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec).
- APIs/UI/models: /health/native/; local launcher/tray; operator CLI; Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Native data-directory and durable queue survive tested process restarts; not proof of a fresh Windows profile restore. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Keep explicit restored-runtime selection.

### RUNTIME-03 — Windows sign-in and sustained scheduled observation

**IMPLEMENTED_NOT_ACCEPTED** · Windows, deployment and release · P2.

- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec).
- APIs/UI/models: /health/native/; local launcher/tray; operator CLI; Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Startup registration and process tests exist; real sign-in and full sustained eligible cleanup/training still need evidence. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Run operator acceptance separately without automatic production restart.

### RUNTIME-04 — Portable package and static assets

**COMPLETE_VERIFIED** · Windows, deployment and release · P2.

- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec).
- APIs/UI/models: /health/native/; local launcher/tray; operator CLI; Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Current evidence: exact clean source `3bc75ac` produced a fresh bundle/installer/ZIP with **10,393 paths**, zero private runtime paths and embedded commit/tree identity. All four executable/distribution hashes and ZIP provenance rechecked around acceptance. **35 packaged native + six installer + ten period/classification HTTP/Chrome checks PASS**; source gate **1,108 backend + 74 Chrome PASS**, zero skips. Metadata, receipts and independent-PC kit: `artifacts/windows-integrated-20261023/`. Earlier `0bb6930` CSV/correction and failed CPU-native receipts are preserved separately.
- Limitations/dependencies: same-host synthetic package acceptance only, using the qualified isolated Vulkan runtime for real-model reasoning within the unchanged deadline. Installed runtime, fresh-PC/normal-account and GUI/manual acceptance remain distinct. Existing owner/session controls and all approval boundaries retained.
- Next: Use the exact `3bc75ac` package/manifest and independent-PC acceptance kit; preserve historical failures and do not relabel the package after tracker-only commits.

### RUNTIME-05 — Install/upgrade/uninstall on separate PC

**IMPLEMENTED_NOT_ACCEPTED** · Windows, deployment and release · P2.

- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec), [scripts/verify_windows_installer.py](../scripts/verify_windows_installer.py).
- APIs/UI/models: /health/native/; local launcher/tray; operator CLI; Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py), [tests/test_windows_setup.py](../tests/test_windows_setup.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Current evidence: fresh exact-source `3bc75ac` installer completed **six same-host synthetic lifecycle checks**: install/startup without system Python, upgrade retaining account/session/totals/file, failed-shutdown uninstall guard, data retention and ownership-aware startup cleanup. Original startup/desktop state restored; test ports released. Receipt: `artifacts/windows-integrated-20261023/installer-report.json`; earlier `0bb6930` receipt remains preserved.
- Limitations/dependencies: this was a fresh test directory on the development PC, not an independent clean-PC/reboot/normal-account acceptance. Status remains IMPLEMENTED_NOT_ACCEPTED.
- Next: run the shipped acceptance kit on an independent authorized Windows machine; do not relabel this same-host proof.

### RUNTIME-06 — Offline startup and local model prerequisites

**IMPLEMENTED_NOT_ACCEPTED** · Windows, deployment and release · P2.

- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec).
- APIs/UI/models: /health/native/; local launcher/tray; operator CLI; Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Current evidence: exact-source `3bc75ac` package passed **all 35 native checks**, including real local embeddings/reasoning, owned-memory/document grounding, injection exclusion/abstention, outage/restart and encrypted-vault recovery. Cloud disabled; cached `all-minilm:latest` and unchanged `qwen3.5:4b`, 30-second deadline preserved. Receipt: `artifacts/windows-integrated-20261023/native-fresh-report.json`. Historical CPU failures and their unavailable/retry screenshots remain preserved.
- Limitations/dependencies: independent-host offline prerequisites and operator runtime adoption remain unaccepted. Synthetic local success does not establish general model quality or a currency/provider/history approval.
- Previous CPU diagnostic: four bounded synthetic calls passed, but the subsequent packaged loan-document request exceeded the unchanged deadline after 12 checks. Evidence: `artifacts/ai-runtime-8e8af9355b/`. The later explicitly authorized isolated Vulkan evaluation supersedes that blocker only in its tested environment; no installed-driver/model/residency/timeout changes.
- Latest accepted isolated remediation: official signed/hash-verified Ollama v0.40.9 with its Vulkan backend uses RX6700XT (33/33 layers), unchanged model/options/deadline; four benchmarks and all 35 checks against both unchanged package `0bb6930` and fresh package `3bc75ac` PASS. Owned server/children stopped after testing; installed runtime remains unchanged. Separate-PC/offline-prerequisite/operator adoption remains unaccepted. See Vulkan and fresh Windows checkpoints.
- Next: obtain an operator decision before adopting the staged runtime; execute the shipped independent-host kit with its declared model/runtime prerequisites. Do not repeat passing same-host native checks without relevant changes.

### RUNTIME-07 — Local backup, encrypted restore and rollback

**COMPLETE_VERIFIED** · Windows, deployment and release · P2.

- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec), [scripts/verify_private_recovery.py](../scripts/verify_private_recovery.py), [scripts/prepare_encrypted_recovery.ps1](../scripts/prepare_encrypted_recovery.ps1).
- APIs/UI/models: /health/native/; local launcher/tray; operator CLI; Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py), [tests/test_private_recovery_verifier.py](../tests/test_private_recovery_verifier.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Dated independent local pre-M15 restore/rehearsal passed; no new backup or live DB read in this audit. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Require fresh approved consistent backup before future promotion.

### RUNTIME-08 — Off-device/device-loss disaster recovery

**BLOCKED_APPROVAL** · Windows, deployment and release · P1.

- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec).
- APIs/UI/models: /health/native/; local launcher/tray; operator CLI; Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: HDD copy user reported; portable independent key/restore unverified. Historical M15 waiver does not extend to future releases. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Wait for explicit recoverable method/acceptance without repeated cancelled dialogs.

### RUNTIME-09 — Filesystem protection of private DB/config

**IMPLEMENTED_NOT_ACCEPTED** · Windows, deployment and release · P1.

- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec).
- APIs/UI/models: /health/native/; local launcher/tray; operator CLI; Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Read-only ACL review found Authenticated Users/local Users read grants; DB has plaintext SQLite header. No exploitation or secret values observed. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Least-privilege creation/repair implementation tested in disposable Windows paths; tests/test_private_storage.py. Production ACL remediation requires authorization.

### RUNTIME-10 — Session/CSRF/auth/upload/HTTP/diagnostic safeguards

**COMPLETE_VERIFIED** · Windows, deployment and release · P2.

- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec), [alfred_ai/services/public_http.py](../alfred_ai/services/public_http.py), [alfred_ai/services/upload_limits.py](../alfred_ai/services/upload_limits.py), [apps/loans/diagnostics.py](../apps/loans/diagnostics.py).
- APIs/UI/models: /health/native/; local launcher/tray; operator CLI; Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py), [tests/test_api_session_security.py](../tests/test_api_session_security.py), [tests/test_upload_limits.py](../tests/test_upload_limits.py), [tests/test_loan_diagnostics.py](../tests/test_loan_diagnostics.py). Dated exact-source M15/M14 release regression evidence at 3932f391; technical scope only. See evidence ledger; audit reruns are separately identified.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: M14 completed controls remain in exact M15 source; do not restart resolved endpoint audits. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Keep relevant security regressions and deployment isolation.

### RUNTIME-11 — Dependency security and reproducible builds

**IMPLEMENTED_NOT_ACCEPTED** · Windows, deployment and release · P1.

- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec), [requirements.txt](../requirements.txt), [constraints/windows-py312.txt](../constraints/windows-py312.txt).
- APIs/UI/models: /health/native/; local launcher/tray; operator CLI; Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Django 6.0.8 has subsequent 6.0.9 security patch; pip check passes but does not establish security. Build-tool availability/locks need follow-up. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Django 6.0.9 isolated dependency and repeat-package gate complete at 4aa7ac70. Independent clean-PC replay still pending.

### RUNTIME-12 — GitHub CI and branch/source protection

**PARTIALLY_IMPLEMENTED** · Windows, deployment and release · P1.

- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec), [.github/workflows/browser-regression.yml](../.github/workflows/browser-regression.yml).
- APIs/UI/models: /health/native/; local launcher/tray; operator CLI; Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: PR/manual browser workflow exists; Pages run is not backend acceptance. Fresh M15 backend CI/required checks not confirmed. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: M20 publish approved CI changes and verify actual remote checks.

### RUNTIME-13 — M20 automated source/finance/privacy/backup gates

**COMPLETE_VERIFIED** · Windows, deployment and release · P1.

- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec), [artifacts/audit/ALFRED_MASTER_AUDIT_CONTINUATION.md](../artifacts/audit/ALFRED_MASTER_AUDIT_CONTINUATION.md).
- APIs/UI/models: /health/native/; local launcher/tray; operator CLI; Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Prior combined 65 tests plus overlapping later narrow runs; audit reproduced 2 gate gaps. No final full gate result.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Development-only 0052410 has partial focused evidence; full gate interrupted. Synthetic ignored-file overwrite and JSON credential misses are confirmed. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Existing M20 source/operator/privacy/financial/restore/approval gates fixed and executed; scripts/release_gate.py, tests/test_release_gate.py; frozen 4aa7ac70 local gate. Remote CI not demonstrated.

### RUNTIME-14 — M21 rehearsal, failure injection and rollback acceptance

**IMPLEMENTED_NOT_ACCEPTED** · Windows, deployment and release · P1.

- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec), [artifacts/audit/ALFRED_MASTER_AUDIT_CONTINUATION.md](../artifacts/audit/ALFRED_MASTER_AUDIT_CONTINUATION.md).
- APIs/UI/models: /health/native/; local launcher/tray; operator CLI; Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py). Code/helper tests present; no complete actual M21 acceptance receipt.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: M20 branch contains orchestration/tests; full native/browser/packaged rehearsal was not executed. Real acceptance remains open. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: M21 actual disposable promotion/failure/restore/source-rollback/browser rehearsal PASS at 4aa7ac70; scripts/release_acceptance.py. Separate PC, normal account and device-loss acceptance remain open.

### RUNTIME-15 — Local/LAN hosting and optional Docker stack

**IMPLEMENTED_NOT_ACCEPTED** · Windows, deployment and release · P2.

- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec), [docker-compose.local.yml](../docker-compose.local.yml), [docs/LOCAL_HOSTING.md](../docs/LOCAL_HOSTING.md).
- APIs/UI/models: /health/native/; local launcher/tray; operator CLI; Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py), [tests/test_local_stack_ops.py](../tests/test_local_stack_ops.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Loopback/local native is current target; Compose/Celery profiles exist but do not prove present sustained Docker acceptance. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Keep local privacy; no new public cloud hosting wiring.

### RUNTIME-16 — Real-account and manual accessibility acceptance

**BLOCKED_APPROVAL** · Windows, deployment and release · P1.

- Source: [alfred_native.py](../alfred_native.py), [alfred_ai/durable_queue.py](../alfred_ai/durable_queue.py), [scripts/package_windows_release.py](../scripts/package_windows_release.py), [packaging/ALFRED.spec](../packaging/ALFRED.spec).
- APIs/UI/models: /health/native/; local launcher/tray; operator CLI; Isolated data directory, SQLite queue, registry and native runtime metadata.
- Tests: [tests/test_native_runtime.py](../tests/test_native_runtime.py), [tests/test_native_launcher.py](../tests/test_native_launcher.py), [tests/test_durable_queue.py](../tests/test_durable_queue.py), [tests/test_user_data_browser.py](../tests/test_user_data_browser.py). Source/test presence reviewed; full execution or product accuracy not newly established. See evidence ledger for any covered synthetic scope.
- Acceptance: PENDING; no normal existing-account visual acceptance performed by this audit. NOT_APPLICABLE for local logic; configured/live provider claims require separate evidence.
- Limitations/dependencies: Synthetic Chrome/HTTP success does not replace normal sign-in, screen-reader and actual account checks. Existing owner/session controls; canonical data availability; acceptance plan.
- Next: Owner signs in normally under acceptance checklist; no password in chat.

## Preserved technical decisions and dated implementation evidence

The following dated ledger preserves unique migration policies, C1–C10, exact commits, commands, evidence paths and limitations. Earlier words such as “next”, “active” or “pending” apply to their dated checkpoint; current execution and 143-feature statuses above take precedence. Production claims describe historical deployment evidence, not fresh runtime health.

<details>
<summary>Dated implementation ledger and currency decision contract</summary>

### Earlier project implementation ledger

## Active post-audit implementation — 2026-10-15

Production remains 3932f391; audit baseline bced104 is preserved. Isolated work:
F:/ALFRED_DEV/post-audit, feature/ai-ground-bank-20261016. Audit is complete;
the 143-feature inventory is not regenerated. AWS is decommissioned by the user;
older activation advice is superseded. No live configuration, ACL, database,
service, paid provider or GitHub operation is authorized here.

### AI-GROUND Phase 2 — individual canonical financial records, 2026-10-16–17

Based exactly on `1b80138d470150de8f9fc1d1be831af1cecc8941`, on the same isolated
feature/ai-ground-bank-20261016 branch. Source unit
`df386be6938e533cff5b9e20af11ba015672ee9a` adds
[canonical evidence](../apps/ml_engine/services/canonical_evidence.py),
[read-only owner APIs](../apps/ml_engine/api/financial_evidence.py),
`/api/ai/financial-evidence/` and owner-only
`/ai/financial-records/<kind>/<id>/` citation views. Supported kinds: expense,
budget, loan, investment and baseline. Each amount has exact decimal text, explicit
currency null/not_recorded, record identity, source field, applicable date,
evidence status and content revision. No new model, migration, dependency or money
calculation. Existing FIN-MONEY conversions and bank provenance remain intact.
Assistant unit: `b49c14125af6b60c51b8965e8c221cf7ecc8f35e`.
Final source-boundary unit/last validated runtime source:
`179db89625e4d77ef2f90bd221707397f2c4f2b1`. This closing checkpoint changes
documentation only; verify actual HEAD before the next implementation unit.

Canonical means the currently stored record, **not independent third-party proof**.
Manual expenses are user recorded; bank imports still require the existing receipt
confirmation/revocation/file checks and redirect to their original citation.
Budget has no approval state: saved records are labeled approval_not_recorded;
conflicting same-period aliases abstain. No approval is invented. Loans expose
confirmed contract fields, persisted EMI/outstanding/paid values and the latest
applied-payment reference. Missing balance is unavailable, never principal or zero.
Estimated or contradictory closure/status records require review. No new EMI,
amortization or repayment forecast calculator is introduced. Portfolio positions
use current corrected register values, never old extraction text or assumed live
market prices; source imports are explicitly not field-verified. Foreign parent,
payment or import-document links fail closed, including Family-sharing accounts.

Baseline reuse adds optional `fresh=True` to the existing resolver, preserving its
default behavior/calculations. Grounding reloads the owner and bypasses cached
financial results. Only supported single reported-income/housing fields are
available; totals/derived income requiring currency/source compatibility are
withheld. The existing canonical baseline itself is not changed. Currency C1–C10
remains unapproved: no FX, aggregation of unknown denominations, backfill or INR
inference. Exact stored values/identities/fingerprints are preserved.

Final source-boundary correction (2026-10-17): reported monthly income additionally
requires an exact match to a positive stored User.monthly_income. The existing
canonical resolver can label a Career salary fallback reported_monthly_income
when the User field is empty; that fallback remains unchanged for legacy financial
services but is not promoted into an explicitly reported User fact. A synthetic
regression proves the original fallback remains 10000.00 while grounding withholds
it. `baseline-source-boundary-corrected`: **32 backend PASS**, zero failures/skips
(source/hybrid/currency). The initial regression fixture omitted required Career
experience; its safe failure receipt is retained and the fixture corrected.
Final changed-source privacy/link/identity validation PASS: 25 files, 74 local
references, zero findings; FIN-CURRENCY contract and frozen/master SHAs unchanged.
Final AST-only graph update and JavaScript/diff checks PASS. No new schema/dependency.

`artifacts/post-audit/ai-ground-canonical-20261016/canonical-source-verified`:
**46 backend PASS**, zero failures/skips (new sources, financial baseline, existing
bank provenance/hybrid). Synthetic financial-row and canonical Decimal baseline
comparisons show zero mismatches. Owner/Family/citation/session denial, corrected
precedence, budget/loan conflicts, null balance, original evidence, bank revocation
and read-only API semantics are covered. `canonical-system`: system and migration
drift PASS; no schema change or old money migration rehearsal needed.

The assistant now supports `scope=financial_records`, `record_type` and `record_id`
through the existing hybrid/API/UI. Sources revalidate after inference, including
edits, deletion/reparenting, newly conflicting budgets, loan payment linkage and
bank revocation. Explicit cloud consent is refused and local outage cannot fall
back to OpenAI. Original text, notes, asset/account labels and private citation URLs
are excluded from financial tool prompts; only allowlisted structured fields enter
local inference. Model numeric/currency prose is suppressed; exact source cards
remain authoritative. No automatic memory promotion or conversation activation.

The initial supported questions are deliberately bounded English record requests,
for example “Explain this record”, “Show my loan status” and “Review recorded
values”. Unrecognized questions, forecasts, approvals, FX and totals abstain before
retrieval/inference. This is not arbitrary financial advice/Q&A. Existing finance
source keys remain, but unknown-currency totals are null/unavailable in assistant
output; supported reported-income/housing fields remain readable. Financial
dashboard/calculation APIs and stored baseline results are unchanged. Test/browser
expectations are updated only for this necessary currency-safety boundary.

`canonical-combined-final`: **149 backend PASS**, zero failures/skips (sources,
hybrid, source races/conflicts, money/financial baseline, bank, history, uploads/
retry, session/CSRF, reset and loan-document grounding compatibility). Financial
rows, raw identities/fingerprints and canonical Decimal baseline have zero
mismatches. `canonical-browser-focused`: **4 Chrome PASS**, zero failures/skips:
multi-domain sources, owner citations/corrections/mobile, unsupported/stale drafts,
bank review/correction and history outage/conflict. Desktop/mobile screenshots
reviewed. Counts overlap earlier focused runs and are not summed.

**Separate actual local acceptance:** `canonical-real-ollama`, **1 PASS**, zero
skips/failures. Required installed local qwen3.5:4b/all-minilm models were detected
without installation/configuration changes. A disposable synthetic expense and
explicitly verified synthetic memory exercised real embeddings, one bounded local
inference, typed owner source, encrypted-vault reopening and other-owner exclusion.
No production database, paid call, external cloud, model download or live Ollama
configuration change. This proves the bounded local path, not financial advice
accuracy or broad model evaluation. The opt-in test is separate from mocked gates:
[real acceptance](../tests/test_canonical_ollama.py).

Example synthetic source: `canonical-investment-2`, corrected current value
**3456.78**, currency null/not_recorded, provenance
`investments.Investment.current_value`, owner-only
`/ai/financial-records/investment/2/`. Loan EMI is the exact persisted contractual
amount with Loan field provenance, not a new amortization estimate. Budget approval
and actual market freshness remain explicitly unrecorded. Full document Q&A,
approved currency/aggregation and separate-PC/real-account/package acceptance are
not claimed. The next independent verified-document unit, exact loan-closure
citations, is now implemented below; no arbitrary PDF ingestion was added.
Integrated system/migration drift checks PASS. Changed-source privacy/link/identity
validation PASS: 23 files, 74 local references, zero findings, unchanged C1–C10 and
frozen/master SHAs. JavaScript syntax/diff checks and AST-only graph update PASS.
History activation, OpenAI and cloud sync OFF; AWS retired. Production DOWN remains
the prior finding, without new operational checks or repair. Production source/data,
backups, frozen `4aa7ac70` and GitHub master are unchanged.

### AI-GROUND — exact loan-closure citations and retained-file liveness, 2026-10-16

Follow-on to canonical source/assistant commits above. The existing verified loan
closure scope now cites `/documents/loan-closures/<id>/`, with an owner-only
`/api/ai/closure-evidence/<id>/` API and the shared private record view. Citation
links reopen the existing document selector, including older owned records. No new
parser, financial write, money calculation, model, migration or dependency.
Implementation source: `9a02f168ea1394282ec77e4afc7ca5da2e002fbe`.

Reuses the bank private-file helper as `file_reference`: same media-root boundary,
bounded byte reads, private-media authorization and no raw text. Closure revision
includes owner/loan linkage, current canonical amount/date, verification/update
state and retained-file bytes. Missing/inaccessible retained files reject the
answer; replacement/removal during inference invalidates it. Anonymous/foreign/
withdrawn citation access is denied. Limits return safe 413; stale sources return
safe conflict responses with references. No parser paths, OCR, notes, filenames or
private citation URLs enter local document prompts or cloud providers.

Legacy verified metadata with an empty file field is still a recorded source,
explicitly **not_retained**, with no download and no independent bank authenticity
claim. A nonempty path whose file disappeared is not silently treated as legacy
metadata. No verification timestamp is invented from updated_at. Source money keeps
exact decimal text, unknown currency, record/date/revision and field provenance.
Historical encrypted transcripts keep reference metadata only; no fact promotion.

`closure-citations-focused`: **81 backend PASS**, zero failures/skips, including
canonical/bank/history/loan-source compatibility and synthetic no-financial-write
checks. `closure-browser-final`: **3 Chrome PASS**, zero failures/skips: exact
closure citation/file disappearance/metadata limit, existing currency source cards
and bank confirmation/correction/withdrawal. Screenshots reviewed. These three
flows are distinct from the four canonical browser flows above; backend counts
overlap and are not added. Final system/drift checks PASS.
`grounding-final-backend`: **154 backend PASS**, zero failures/skips on the combined
canonical/bank/closure/history/finance/session source after closure integration.
Earlier 149/81 runs are supporting evidence, not extra test totals.

Remaining verified-document gap: field-level verification/provenance for investment
and other document extractions before treating them as verified external facts.
Current portfolio register retrieval is available with honest unverified-import
labels, not verified PDF Q&A. Next safe action: inspect the existing investment
document-review/correction contract and implement a bounded owner-confirmed field
receipt, preserving original extraction and canonical values, with stale/deleted/
foreign evidence abstention. No approved currency schema, budget approval state,
actual live market pricing or production acceptance is implied.

### AI-GROUND — bank-statement provenance and local assistant, 2026-10-16

Based exactly on AI-HISTORY `20b916ee00867b0f0cdcb5c758c697762fda897b`; its
encryption, retention and default-OFF operator gate are preserved. Provenance unit
`35bf1a9e7377f7fa8ecd23f09b753dcddef09033` adds
[statement evidence](../apps/expenses/services/statement_evidence.py),
[owner APIs](../apps/ml_engine/api/statements.py) and an authorized
`/documents/statements/<document>/transactions/<record>/` review page. Import
snapshots preserve original structured values, parser monetary identity, dates,
document label and fingerprint. Corrected canonical Expense values take precedence;
neither the original snapshot nor the existing import fingerprint is rewritten.
Duplicate imports retain their original source link; no duplicate alternate
provenance is invented. Raw PDF/OCR text is not copied into new diagnostic or memory
fields. Existing owner-only private-media downloads are reused.

Assistant integration/last fully validated runtime source:
`0778a2f8e0261bd775c05504b5f5ca4326b37ecf`. This closing checkpoint is
documentation-only; verify actual HEAD before continuing on this branch.

Explicit record confirmation is separate from parser success and from trusted
long-term memory. File bytes, source/owner/account linkage, date bounds, parser
state, canonical edits, duplicate/conflicting records and revocation invalidate
verification. Generation-fenced reviews reject stale confirmation requests. Owner
confirmation is **not independent bank authentication**. Missing, partial or
conflicting sources cannot be confirmed. Family financial-sharing consent does not
grant access to these private documents. No amounts, balances or memories are
modified by the review API; consent can be withdrawn without deleting transactions.

One additive migration, `expenses.0006_statement_transaction_evidence`, creates
only derived receipts. No historical backfill, currency inference, dependency or
financial-column change. Legacy original extraction is explicitly “not retained”;
an owner may review a current legacy row against its file without fabricating an
original snapshot. Forward/reverse synthetic rehearsal independently restores a
consistent SQLite copy, checks integrity/foreign keys, and proves all pre-existing
table digests unchanged apart from migration history. Reversing drops only new
receipts; preserve a backup and disable citation consumers before a reviewed source
downgrade. Original financial records/files remain intact. Nothing applied live.

Evidence: `artifacts/post-audit/ai-ground-bank-20261016/`.
`provenance-core-integration`: **53 backend PASS**, zero failures/skips, covering
provenance, ownership/CSRF, duplicate/transfer preservation, correction precedence,
atomic failed imports, migration/rollback and reset. Canonical Decimal baseline and
financial-row comparisons show zero mismatches. A reproduced saved-date correction
bug is fixed in the existing retry helper: accepted statement dates survive retry.
System, drift, disposable migration and pending-migration checks PASS.
`provenance-browser-final`: **1 Chrome PASS**, zero failures/skips: owner review,
correction, withdrawal and mobile layout; desktop/mobile screenshots reviewed.
Earlier browser timing/helper failures are preserved and corrected, not counted.

The next bounded unit connects reviewed records to the existing
[hybrid assistant](../apps/ml_engine/services/hybrid_intelligence.py), API and UI
with `scope=bank_statements` plus one owned `transaction_id`. The recent menu is
bounded; a citation can reopen an older record through the same owner API. Source
cards show document name, statement period, transaction date/reference, verification,
limitations and **current** exact-decimal amounts. Corrected amounts require fresh
confirmation; original extraction remains on the review page. Missing balances
remain unavailable. No totals, FX, new money arithmetic or financial write tools.

Unreviewed/partial/conflicting/missing sources return `insufficient_evidence` before
memory retrieval or inference; the UI preserves the question and offers source
review/retry. Deleted, reparented or changed sources and confirmation revocation/
reconfirmation during inference reject the answer. Missing accounts fail closed.
Names, original OCR/PDF text, account numbers, transaction descriptions and private
citation URLs do not enter the bank tool prompt. Only bounded structured canonical
fields are supplied locally. Explicit cloud consent is refused for this scope;
local model failure cannot fall back to OpenAI. The existing numeric/currency
narrative suppression applies, so only source cards display financial values.
Suggestions remain unverified and require explicit review; no automatic learning.

History remains operator-disabled. Synthetic-only compatibility checks prove a
local model turn can retain encrypted reference-only history, while an evidence
warning is never saved as a model turn. Existing question digests stay unchanged
unless a transaction selection is supplied. Pagehide clears private selection and
answers; CSRF/session authorization and owner-only citation/download checks remain.

`bank-grounding-integration`: **202 backend PASS**, zero failures/skips, covering
bank provenance/import/review, existing loan grounding, history, privacy, upload
limits, session security and reset. This run includes the nine source-mutation
cases during inference. A final added null-balance/new-conflict case passes
separately (`bank-null-conflict-final`, **1 PASS**); runs are not added to earlier
overlapping totals. Final `bank-final-source`: **34 backend PASS**, zero failures/
skips, rechecks all 11 bank-grounding cases plus history/UI on the final source.
`bank-browser-final`: **4 Chrome PASS**, zero failures/skips:
bank review→answer→correction, outage/revocation/draft/pagehide, and existing
memory/finance/Travel/source and currency-card compatibility. The bank flow also
reopens a record outside the recent menu. Desktop/mobile screenshots reviewed;
synthetic example: “Synthetic September statement.pdf”, period 2026-09-01 to
2026-09-30, `bank-statement-1-transaction-21`, current amount **7.77**, original
**2.68**, **currency not recorded**, owner-only
`/documents/statements/1/transactions/21/`. IDs are synthetic examples, not live IDs.
An initial browser expectation used different punctuation from the established
money formatter; the test now checks the existing formatter. No runtime financial
format or currency convention was changed to satisfy the test.

Remaining grounding scope: reviewed linked bank transactions, verified loan closure
evidence and owner-verified memories, **not arbitrary PDF Q&A or whole-statement
completeness**. No automatic historical evidence backfill or inferred alternate
source link for duplicates. Real-account/private-document, actual model narrative
quality and packaged acceptance remain unperformed for this source. Next safe
AI-GROUND unit is bounded owner-scoped canonical expense/budget/portfolio evidence
selection with provenance/uncertainty; keep aggregate/currency work gated by C1–C10.
Changed-source privacy/link/identity validation PASS: 21 files, 71 local references,
zero findings; currency contract text and frozen/master identities unchanged.
JavaScript syntax, diff checks and AST-only graph update PASS. No new dependency.
Currency remains unrecorded; C1–C10 below remain unapproved. History activation,
OpenAI and real cloud sync remain OFF; AWS stays retired. Frozen `4aa7ac70`,
production, its database, backups and GitHub are unchanged. Production DOWN is the
prior read-only observation, not a fresh health check or a repair claim.

### AI-HISTORY — safe local slice implemented, private activation gated, 2026-10-16

Based on FIN-CURRENCY review `bdabc389764119d95e2a002946b8fa8088c1bc6b`.
Backend implementation: `e9254953d35cf430e10046aeb92d3c7c7b6654e8`;
UI/validated runtime source: `ddbca7e140ada74f41795e99e16eb7267acfdf8c`.
This closing checkpoint changes documentation only, not tested runtime behavior.
Currency C1–C10 recommendations below remain unapproved; no currency migration.
Private history is independently implemented in the existing M15 vault, not a
second memory engine: [service](../apps/ml_engine/services/conversation_history.py),
[session APIs](../apps/ml_engine/api/conversations.py),
[regressions](../tests/test_conversation_history.py).

**Disabled by default:** `ALFRED_CONVERSATION_HISTORY_AUTHORIZED=false`. Audit
UNIT 9 and the existing recovery guide leave private-use retention/recovery
approval outstanding. Only isolated synthetic tests enable the operator flag.
Even when available, each owner must explicitly opt in and choose 1–30 days;
there is no inherited memory consent or automatic retention choice. No key export,
rotation, passphrase dialog, real provider activation or production repair.

Reuses current-user DPAPI master key, owner hash, restricted vault directory and
Fernet encryption. Two additive private-vault tables store encrypted policy and
per-conversation encrypted records/wrapped keys; titles, text, timestamps and
request digests are encrypted. Only opaque IDs/owner hashes are outside ciphertext.
No new Django migrations, dependencies, financial tables, plaintext chat index,
embeddings, memory events or cloud snapshots. Existing vault upgrade preserves
verified memories and key bytes. Missing/wrong keys and tampering fail closed.

Session-only `/api/ai/conversations/`, `policy/`, `clear/` and `<id>/` support
create/list/reopen/delete, opt-out and confirmed clear. Responses are private,
no-store; CSRF and owner isolation apply even to accepted financial-sharing Family
members. History-enabled `/api/ai/personal-insights/` requires revision/request ID,
rechecks the current session after inference and rejects stale policy generations,
expiry, deletion, reset and concurrent edits. An expired/logged-out session is
flushed so Django's save-every-request cannot revive it. Successful turns commit
atomically; retries are idempotent, errors retain no partial turn. Limits: 50
conversations/owner, 20 turns/conversation, 256 KiB encrypted-record plaintext cap.

Saved answers remain **AI hypotheses**, not verified memories or financial facts.
Source references are historical metadata; canonical source values are not copied.
Existing current-source grounding/numeric suppression remains authoritative. Old
turns are reviewable transcripts, not new model context. History requests refuse
cloud fallback; no transcript enters OpenAI, synchronization, retrieval or learning.
Only the pre-existing explicit memory-review workflow can propose a separate fact.

Retention is absolute from creation, never extended by activity or later policy
lengthening; shortening applies immediately. Existing startup/scheduled memory
expiry also cleans history. Delete/clear removes current rows and wrapped keys;
full owner reset/account deletion also disables history, selected-memory reset
does not. Verified-memory journal recovery cannot resurrect deleted transcripts.
Old backups can still contain decryptable copies; **no irreversible erasure or
portable device-loss recovery claim**. Current-profile recovery only is tested.
Before source downgrade to a binary without history cleanup, disable and clear
history, verify zero rows/disabled policies, or obtain an explicitly reviewed
compatible restore plan. Do not blindly drop vault tables or restore old copies.

Core evidence: `artifacts/post-audit/ai-history-20261016/`. `history-focused-fixed`:
12 PASS; actual `history-core-integration`: **125 backend PASS**, zero failures/
skips (history, vault, privacy/sync, hybrid/financial display, session/CSRF, reset).
Counts are overlapping, not additive. System, migration drift, full disposable
Django migration and no-pending-migration checks PASS. Separate
`history-financial-reconciliation-fixed`: one PASS, zero financial-row or canonical
Decimal baseline differences across save/clear/opt-out. Initial focused
failures and safe diagnostics are preserved.

The existing [assistant page](../templates/ai_insights.html) and
[JavaScript](../static/js/intelligence.js) now provide consent/retention choice,
conversation titles, navigation/reopen, new conversation, delete, clear and disable.
Page-only remains the default; opting in does not import earlier page-only turns.
Historical hypotheses have saved timestamps, source-reference limitations and no
copied source amounts or fact-promotion button. No transcript/draft is placed in
browser storage. Logout/permission loss/pagehide clears private DOM; restored
pages fetch the current session. Stale edits require reopening, preserve drafts
and never append silently. Deletion/expiry/clear detected on a rejected save also
removes stale displayed turns. Model failures retain the draft and retry identity.
New answers continue to use only current verified sources, not historical turns.

`history-ui-backend`: **53 PASS**, zero failures/skips, including 14 history tests,
hybrid/current-source grounding, Decimal/currency display, session and UI contracts.
`history-rollback-process`: one strengthened regression PASS separately; a fresh
process reopens ciphertext, then the exact pre-history MemoryStore from bdabc389
reads preserved verified memories after explicit disable+clear. No key bytes or
financial values changed. These overlapping runs are not combined into a total.
Final `history-browser-validated`: **5 Chrome PASS**, zero failures/skips, synthetic consent,
reload/reopen, deletion/clear/disable/other owner, outage/retry/stale edit, operator
gate/logout/cached-page cleanup, and existing responsive page-only assistant.
The fifth flow verifies that explicit public-only mock fallback still works for
page-only questions while persistent history refuses it. Real OpenAI remains OFF.
Screenshot review exposed stale displayed turns after another tab's clear; the
UI refreshes history on conflict and clears those turns while retaining the draft.
A diagnostic rerun exposed a composer readiness race during history navigation;
composer/new/history controls now lock for the operation and tests wait for the
visible ready state. That five-flow final run includes both corrections. Earlier
failed `history-browser-revocation` and passing isolated conflict diagnostic are
preserved, not accepted as the final gate. Reviewed screenshots accompany the
validated run. Existing source-card and currency browser checks run separately
because this UI refactors their shared renderer: `history-browser-source-resumed`,
**2 Chrome PASS**, zero failures/skips. These are distinct from the five history/
assistant flows, not reused historical counts. The previous source-compatibility
invocation was interrupted with no receipt and is not counted as passed.
JavaScript syntax and diff checks PASS. No fresh native package or full release
suite was warranted/run; the frozen candidate is not rebuilt.

**Remaining approval-sensitive decisions:** approve the explicit 1–30-day absolute
retention contract and current-profile-only recovery risk or a separately verified
portable recovery design before operator activation/private acceptance. Select
backup retention/restore reconciliation for old transcript copies; the M15 waiver
does not cover this feature. No canceled key-sealing workflow is resumed. Real-
account history, separate-PC recovery and packaged acceptance are not claimed.
Next independent safe implementation is AI-GROUND reviewed bank-statement
document provenance/citations beyond current memory/loan scope, with owned-live
evidence and stale/deleted abstention; do not repeat accepted loan grounding. Broader
currency-aware financial tools still wait for C1–C10 approval. Do not start a new
audit or rebuild existing M15 memory/sync/Ollama components.
Production DOWN is preserved from the prior read-only checkpoint, not repaired.
Frozen `4aa7ac70`, live source/database, backups and GitHub remain unchanged.
Changed-source privacy/identity/link checks PASS: 14 files, 68 local references,
zero findings; C1–C10 contract byte content unchanged, no new migration/dependency.
AST-only graph update PASS. Evidence receipts and screenshots remain under the
existing AI-HISTORY evidence directory, not in private backups or GitHub.

### FIN-MONEY — User, Career and Mobility tail complete locally, 2026-10-16

User source: `2f48d3edf50555299e4072dfd2f9441a3b435af9`; Career source:
`f8c7ebb2400113713ba640e43e76d8340e4607b5`; Mobility source:
`ddb7fca22588f469ff4086766d014732f393cc6c`, based on Career. This documentation
checkpoint follows that tested source. All audited tail register
fields are now Decimal cents in development; the earlier Budget unit is retained
without repeating its migration tests. No production remediation/deployment is
claimed. Frozen release `4aa7ac70` remains unchanged and is not this new source.

Mobility scope: BikeProfile estimated_market_value/monthly_income_support,
BikeServiceRecord.cost, FuelRefillLog.total_cost, TravelPlan.budget,
TripLog.spend_amount, BikeIssueReport projected_cost/nullable actual_cost,
BikeDocument.premium_amount. Reuses M13 finite bounded 14/2 HALF_UP storage and
numeric API fields. Existing signed-value rules and Travel API negative-budget
rejection remain; null actual cost differs from zero. Measurements, rates,
confidence, raw parsed evidence and fingerprints remain unchanged.

`mobility.0013_mobility_money_decimal` is the sole Mobility schema unit, depending
on mobility.0012, the existing expenses.0005 policy and swappable User. It validates
all source amounts/parent owners before capture, retains owned originals and
typed source/parent links, and applies normalized cents with markers. Reverse
restores only unchanged applied values with matching source/owner/parents; edits,
new rows and deleted records survive safely. Reset removes owned orphan evidence.
No currency column, inference, dependency upgrade or unrelated migration.

Derived boundaries were updated where Decimal money met float quantities or JSON:
canonical vehicle cost accumulation, fuel/cost-per-km output, service model
features, dashboards/cache, saved-plan state/preferences/feedback and document
review fallback. Money remains Decimal through canonical accumulation; existing
numeric API/JSON and statistical model contracts are preserved. Initial tests
reproduced mixed-type and Travel JSON failures; regression evidence is retained.

Final `money-integration-final`: **156 backend PASS**, zero failures/skips in one
actual combined run covering User/Career/Mobility, profile boundaries, canonical
finance, projections, reset, vehicle accounting, APIs, extraction/review and Travel.
Final `mobility-browser-final`: **3 Chrome PASS**, vehicle accounting, invoice-cent
correction and saved-plan desktop/mobile reload; screenshots reviewed and Travel
console empty. Earlier User two/Career one focused Chrome flows also passed.
Final system/drift/exact Mobility migration-plan checks PASS. New migration tests
cover originals, nullable zero, finite/boundary inputs, owner/parent guards,
idempotence, edits/deletion and zero cent-history canonical baseline mismatches.
`three-domain-rehearsal-verified`: one enhanced rehearsal PASS after the combined
run, starting with all three preceding schemas and asserting exactly the three
User/Career/Mobility migrations. Independent SQLite backup/restore, integrity/FKs,
converted monetary equality, unrelated typed rows, family permissions, account/
transfer fingerprints, exact reverse and source bytes reconcile with zero
unexpected mismatches. Converted SQLite numeric affinity can change a zero's
storage type; compare its exact value while keeping strict type hashes for all
unconverted columns. This is not a financial discrepancy or a waived check.
`mobility-outputs-final`: one strengthened output regression PASS, exact numeric
dashboard totals and HALF_UP fuel-price/cost-per-km formatting. These two
post-combined test enhancements changed assertions only, not runtime source;
their counts are reported separately, not added to 156.
Evidence: `artifacts/post-audit/fin-money-profiles-20261016/`; failed initial runs
remain diagnostic evidence, not accepted outcomes. No full release/package gate.

Production read-only check at 2026-10-16 09:20 UTC: no port-8000 listener or
production runtime process; HEAD remains 3932f391. Prior stale pre-reboot state is
preserved. No restart, repair, live DB access, backup/ACL/key/remote action. AWS
retired; real OpenAI/cloud OFF. Next is the separate currency design below and a
future authorized candidate integration/release gate, not a production migration.
Changed-source credential/private-path scan: PASS, 28 files, no findings;
AST-only graph update completed successfully. No external scan/API used.

### FIN-CURRENCY — reviewed decision contract, 2026-10-16

Review baseline: `feb650834deb782f0b3f813d4c9231b911eb5255`, isolated worktree
F:/ALFRED_DEV/post-audit. **REVIEW COMPLETE; CONTRACT NOT APPROVED; SCHEMA BLOCKED.**
Budget/User/Career/Mobility conversions are complete and not reopened. No runtime,
schema, migration, provider or historical value changes are authorized by this
review. The recommendations below are proposals, not approved defaults in code.

#### Actual execution boundaries and proposed ownership

| Domain | Inspected implementation today | Proposed currency owner after approval |
| --- | --- | --- |
| Banking / Expenses | [models](../apps/expenses/models.py), [serializers](../apps/expenses/serializers.py), [statement parser](../apps/expenses/services/statement_import.py), [posting/deduplication](../apps/expenses/services/statement_lifecycle.py), [identity](../apps/expenses/services/transaction_intelligence.py): numeric amounts; no canonical currency field or parser currency contract. Account uniqueness is user + account_number. | Account denomination plus immutable transaction settlement denomination and statement evidence. Explicitly confirmed account currency may prefill a **new** posting, never relabel history. Foreign merchant amount/fee/booked FX need separate evidence; account number alone may not identify a multi-currency subaccount. |
| Loans / settlement / closure | [models](../apps/loans/models.py), [API](../apps/loans/serializers.py), [PDF parser](../apps/loans/services/loan_pdf_parser.py), [import](../apps/loans/views.py), [settlement](../apps/loans/services/loan_foreclosure_service.py): Decimal contract/payment/closure amounts, no denomination guard. | Loan contract denomination owns principal/EMI/balance; child evidence records its actual source denomination. Cross-currency payment needs explicit bank-booked credited amount/rate/fees, never a reference-rate guess. |
| Investments | [models](../apps/investments/models.py), [serializers](../apps/investments/serializers.py), [imports](../apps/investments/services/portfolio_intelligence.py), [summary/growth](../apps/investments/views.py): InvestmentCurrencySerializerField validates **amounts**, not ISO codes; totals have no currency partition. | Explicit position valuation/cost-basis denomination; each source quote keeps its own denomination/as-of. Asset units such as crypto are not fiat currency codes. Do not subtract cost from valuation or combine SIPs without compatible denomination. |
| User / Career income / rent | [User fields](../apps/users/models.py), [profile API](../apps/users/serializers.py), [Career model](../apps/career/models.py), [income selection](../apps/career/services/income_intelligence.py), [opportunity form](../apps/career/forms.py), [job evidence](../apps/career/services/job_intelligence.py): profile salary has no currency; opportunity JSON carries currency/period but contains INR fallbacks and `$` -> USD interpretation. | Separate currency for each income/rent input or a reviewed income-source record; do not make one User.country/profile default authoritative for all amounts. Career salary period must stay explicit alongside currency; advisory job JSON never labels profile history. |
| Budgets / savings / cash flow | [Budget](../apps/budgets/models.py), [API](../apps/budgets/serializers.py), [plan selection](../apps/budgets/services/budget_intelligence.py), [canonical baseline](../apps/expenses/services/financial_intelligence.py): month-based plans and derived income/obligation/savings totals lack currency partitions. | One denomination per Budget; spend and utilization only compare compatible amounts. Derived savings/cash flow inherit a validated input group, not a display locale. No automatic correction of recorded Budget.spent. |
| Mobility / Travel | [registers](../apps/mobility/models.py), [APIs](../apps/mobility/serializers.py), [plan persistence](../apps/mobility/services/travel_conversation.py), [budget](../apps/mobility/services/travel/costs.py), [quote precision](../apps/mobility/services/travel/money.py), [stays](../apps/mobility/services/travel/providers/accommodation.py), [flights](../apps/mobility/services/travel/providers/transport.py): stored amounts lack codes; Travel estimates explicitly use INR; provider quote strings carry currency and sometimes a separate due-at-property currency. Only matching INR whole-trip quotes qualify in the current budget evidence path; no FX. | Each valuation, receipt, fuel cost, trip spend and quote owns denomination. Plan budget is a **target** denomination, not all trip transactions' currency. Retain raw provider scale, freshness, scope and separate fee/property currency; never equate an estimate with a booked price. |
| Family / tax / risk / reports | [Family totals](../apps/family/views.py) sum consented member baselines; [Indian tax policy](../apps/ml_engine/services/tax_policy.py) and [deductions](../apps/ml_engine/services/tax_optimizer.py) use amounts without a record currency contract. [Report API](../apps/reports/views.py) lists owned GeneratedReport file references, not a currency-aware export engine. | Preserve owner consent before grouping summaries. Indian tax inputs need explicit INR eligibility; country/policy does not prove a historical record's currency. Reports/ratios/forecasts carry source groups, as-of, completeness and FX basis; no universal scalar across currencies. |
| UI / AI / cache | [formatter](../static/js/app.js) uses legacy INR; [source_context/present_answer](../apps/ml_engine/services/hybrid_intelligence.py) emit currency null/not_recorded and suppress unsupported numeric prose; [baseline/revision](../apps/expenses/services/financial_intelligence.py) and [relationship matching](../apps/expenses/services/financial_relationships.py) have no currency partition. | Locale only formats. AI may cite certified structured groups, never supply code/rate/amount. Currency/provenance corrections invalidate owner caches and derived reports; they never enlarge Family access or private memory/document access. |

#### Decision matrix

| ID / decision required | Recommended safe contract | Blocking condition / current behavior |
| --- | --- | --- |
| C1 — ownership and denomination changes | Recommend metadata on existing records, per monetary input where a row can differ (User income/rent and BikeProfile value/income support); a common code only for an explicitly same-denomination contract/position/Budget. Retain source, confirmation basis, actor/time and prior value. Do not add a parallel financial register. | Approve this ownership layout, parent/child invariants and multi-currency account identity. Account/loan denomination cannot silently change after postings. Salary period also needs evidence; currency approval does not authorize inferring historical periods or rescaling salaries. No model changes now. |
| C2 — unknown historical currency | Persist null; API currency null + not_recorded. Unknown is a state, not an ISO code (`UNKNOWN`/`XXX` must not stand for guessed currency). Corrections require reviewed independent evidence or explicit owner attestation, with provenance. | Already a user constraint: never backfill from INR labels, location, model prose, ambiguous symbols, existing advisory defaults or a newly set account preference. Zero amount does not establish currency. |
| C3 — mixed totals / missing coverage | Certified totals, net worth, budgets, percentages and family sums operate per **known matching** currency. Unknown records remain a review collection with counts/source values, **not a certified unknown-currency subtotal**. Missing components make results incomplete, not zero. | Approve legacy scalar behavior before known mixed records can enter calculations. Existing canonical totals are legacy arithmetic conventions, not proven same-currency financial facts. |
| C4 — ISO codes and precision | Version an offline reviewed ISO 4217 registry: uppercase alphabetic code, validity dates and minor unit. Preserve valid historical withdrawn codes. Proposed initial posting allowlist INR/USD/EUR/GBP fits current 14/2 storage; not a claim that these are configured today. | Approve initial supported set and scale policy. Current cent quantizers cannot preserve three-decimal monetary input; do not silently round unsupported currencies, fund/metal units or crypto into cents. Retain provider evidence separately. No registry download at app startup. |
| C5 — reporting currency | Optional owner-selected reporting preference controls presentation/derived conversion only. It never supplies record denomination or labels historical amounts. | Decide whether an overall converted report is needed in phase one. Recommended first delivery: grouped totals with **FX disabled**; no reporting base selected automatically. |
| C6 — FX source, purpose and freshness | Reference FX is optional, read-only valuation evidence: base/quote, rate direction/precision, provider, effective date, fetched time, publication calendar, source/hash and policy version. Use an on-or-before as-of fixing; never a future rate. Certified conversion requires the expected published fixing; missing/stale/suspended pairs abstain. Round final derived amounts only under an approved policy. | No FX engine or approved source exists. A future reference feed must not supply actual settlement/tax filing values. ECB is an informational candidate, not selected or authorized; actual booked FX remains bank evidence. Approve source coverage/terms, historical-date policy, staleness/calendar and rounding before activation. |
| C7 — API/UI compatibility | Proposed additive typed money evidence uses exact decimal text + code/null + status/provenance, with per-currency groups/completeness. Preserve existing numeric fields during an agreed transition; missing totals are not coerced to zero. Clearly distinguish legacy-assumption output from certified output. | Choose versioned endpoint/opt-in versus coordinated contract change. A known mixed input cannot continue through an unlabeled legacy scalar: reject incompatible writes or make the total explicitly unavailable under the approved API. Existing consumers must be inventoried at cutover. |
| C8 — imports / matching / corrections | Preserve original amount text, parser evidence, owner/account links, transfer legs and historical fingerprints. Currency candidates stay unverified until approved evidence resolves ambiguity/conflict. Gate new transfer/loan-payment/portfolio matching on compatible denomination; cross-FX allocation needs explicit evidence. | Do not rewrite existing deduplication hashes/signatures. Approve versioned rules for genuinely distinct new multi-currency postings, reimport/correction idempotence and atomic rejection with no partial financial writes. |
| C9 — reports, caches and privacy | Every new report/AI amount identifies source currency, as-of, completeness and any FX estimate separately. Invalidation keys include currency/provenance/policy revisions. Apply existing owner/Family consent filtering **before** grouping. | Reports, tax, Career comparisons, budget utilization, family aggregation, model features and display helpers must be covered before mixed-currency activation. No private amount or account data is sent to a rate provider. |
| C10 — reversible migration / downgrade | After approval, separate expand-only nullable metadata migrations by domain, no money rewrite/backfill/default INR. Keep owner-scoped original metadata and guarded correction history; rehearse exact counts, values, identities, ownership, forward/reverse and independent restore. | Reversibility is conditional: refuse downgrade if it would erase new denomination/FX semantics or make an old app combine mixed data. Preserve evidence and require an explicitly reviewed source/data rollback path; never blindly drop metadata or inherit the M15 recovery waiver. |

**Approval package:** (1) record/profile/account ownership C1; (2) grouped/incomplete
totals and API transition C3/C7; (3) supported ISO set/precision C4; (4) guarded
metadata migration/downgrade C8/C10. C2 and privacy boundaries remain mandatory.
C5/C6 can safely be deferred by approving grouped-only operation with no FX;
provider approval is not required just to finish the local metadata contract.
Do not enable mixed-currency writes before all relevant consumers are guarded.

Required post-approval regressions: explicit/unknown/ambiguous/withdrawn codes;
supported/unsupported scales; account/transaction/loan/position/profile currency
conflicts; mixed and incomplete owner/Family totals; consent revocation; numeric
API transition; import/reimport/fingerprint stability; cache/report invalidation;
no LLM override; later FX calendar/weekend/stale/missing/future-rate cases; guarded
forward/reverse with post-migration edits and independent restore. Existing
[AI currency tests](../tests/test_intelligence_currency.py) cover presentation,
not an ISO/FX/accounting implementation. No completed Decimal suite was repeated.

Standards checked read-only on 2026-10-16: [SIX ISO 4217 maintenance lists](https://www.six-group.com/en/products-services/financial-information/market-reference-data/data-standards.html)
provide current/historical codes and minor units. [ECB reference-rate documentation](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)
describes working-day publication around 16:00 CET and discourages transaction use.
These are documentation checks, not real-provider acceptance, a chosen service,
API integration or authorization. No rate values were imported.

Next safe action: approve or amend C1/C3/C4/C7/C8/C10, explicitly keep C5/C6 OFF,
then implement only the first approved nullable metadata domain and its synthetic
rehearsal. This review itself is complete, not blocked by production downtime.
The next independent roadmap item, AI-HISTORY, needs its own encrypted storage/
retention/recovery contract (UNIT 9); AI-GROUND finance tools depend on currency.
AI-HISTORY contract work can proceed independently while currency approval waits;
it must preserve existing encrypted memory and require explicit history consent.

### FIN-MONEY — Career salary complete locally, 2026-10-16

User implementation committed as `2f48d3edf50555299e4072dfd2f9441a3b435af9`.
CareerProfile.last_salary now uses the existing bounded finite Decimal-cent field
and numeric serializer, preserving the previous signed-value policy. Experience,
scores, confidence, raw resume evidence and income/projection rules are unchanged.
New migration `career.0005_career_salary_decimal` depends on career.0004 plus the
existing User dependency. Owned original snapshots, applied markers, guarded
reverse and owner/orphan reset follow M13. No currency inference or production use.

Evidence in `artifacts/post-audit/fin-money-profiles-20261016`: career-focused
15 PASS; career-integration **63 backend PASS**, including canonical baseline,
projection and document correction/retry; career-contract-final one full-PUT
contract PASS; career-browser-final **one Chrome PASS**, salary save/reload and
experience preserved. Initial browser fixture sent blank skills and correctly
received HTTP 400 under the existing required-skills API contract; fixture now
supplies skills, and an explicit backend regression verifies both outcomes.
Failed diagnostic receipts remain. Zero final skips/failures. System/drift and
exact one-Career-migration plan PASS. Synthetic alias backup/restore, integrity/FK,
forward/reverse, raw evidence/parent/owner preservation and unrelated financial/
family row hashes reconcile. Cent-valued salary fallback baseline unchanged.

At this Career checkpoint, Mobility was next; it is now completed above. No new
full release/package gate and no change to frozen 4aa7ac70 or production 3932f391.

### FIN-MONEY — User income/rent complete locally, 2026-10-16

Based on FIN-MONEY checkpoint `814d4dad`, same isolated branch. User
monthly_income/variable_income/rent_or_emi persist bounded Decimal cents. Existing
strict finite/non-negative/two-decimal input validation and numeric API outputs
remain; signup optional blanks remain zero. Rates/model features and income-mode
heuristics were not redefined. No historical currency inference or new currency
field. Frozen runtime candidate 4aa7ac70 and production 3932f391 unchanged.

New migration: `users.0003_user_money_decimal`, depending on users.0002 only.
It atomically validates all profiles, retains original float representations and
HALF_UP normalized cents in UserMoneySnapshot, and applies with markers. Reverse
only restores unchanged, applied, correctly linked values; new accounts and edits
survive. Passwords, groups, sessions, identifiers, consents and related financial
records are preserved. Owner reset/account deletion removes owned evidence.
Snapshots remain private canonical-DB evidence, never profile API fields.

Evidence: `artifacts/post-audit/fin-money-profiles-20261016/`: user-focused
20 PASS; user-integration **98 backend PASS** (includes focused scope), no skips
or failures; user-browser **two Chrome PASS** (profile cent save/reload and tax);
user-rehearsal-final **one enhanced rehearsal PASS**, adding nonempty family data.
SQLite backup/independent restore, integrity/FKs, alias isolation, original source
bytes, exact reverse and unrelated typed row hashes all reconcile. Cent-valued
history has zero canonical baseline mismatches. Existing login/session/group
compatibility verified synthetically. user-checks system/drift PASS and plan is
exactly the one User migration from the preceding schema. No production DB access.

Read-only operational recheck: production port 8000 has no listener or runtime
process; the prior stale pre-reboot runtime finding remains. No start/stop/repair.
The subsequent Career and Mobility conversions are completed above. Currency
metadata/FX policy stays separate; no deployment or provider activation authorized.

### Banking regression and production diagnosis — 2026-10-16

Development starts at `08f39a88`; frozen runtime candidate `4aa7ac70` and its
package remain unchanged. Read-only production diagnosis: no port-8000 listener,
HTTP connection fails, no production server/worker process or matching Windows
service. Native scheduler belongs to that absent worker. Recorded supervisor
11376/worker 7740 are absent; `runtime.json` says running but predates the latest
Windows boot (2026-10-15 13:40 UTC), as do both runtime logs. Current-user ALFRED
autostart is not registered. Consistent with no restart after reboot; a crash
cause is not established. No live database was opened or service action taken.
Operator action is required to restore service using the documented explicit
`F:/ALFRED/restored-runtime` data directory, not an implicit launcher default.

The intermittent Banking workflow was reproduced in isolation: it actually
fails on Loan sorting with `StaleElementReferenceException`. The refresh root
covered only the hero, excluding form/table controls; an in-flight refresh could
also replace rows after interaction began. The root now encloses the workspace
and late background responses recheck the existing interaction guard. Foreground
actions remain immediate; the next idle refresh fetches fresh data.

Evidence under `artifacts/post-audit/fin-money-20261016`: production-health.json;
banking-baseline-1/diagnostic.json (original failure); loan-race-before and
loan-race-fixed (preserved deterministic failures); loan-race-scope-fixed
(13 PASS: two Chrome workflows + eleven HTTP/UI contract tests); banking-fixed-0
through -2 (three additional independent runs of the original workflow PASS).
Zero skips in successful runs. No full gate or package rebuild. Correction commit:
`0e7e1df35c5afe279050253b97e92ad0ecfc04fc`. Historical currency stays unrecorded.

### FIN-MONEY — Budget register complete locally, 2026-10-16

Verified implementation: `cd696572f0a3ce69260fb1cf212ce700836fb453`; later
documentation-only checkpoints do not change that tested runtime source.

Scope: `Budget.base_budget`, `inflation_adjusted`, `spent`, their model/form/API
boundaries, dashboard amounts and owner reset. Reuses Expense money helpers and
the existing M13 original-snapshot/guarded-reverse pattern. Money is Decimal cents
with HALF_UP normalization, finite/non-negative validation and maximum stored
amount `999999999999.99`; numeric API fields remain compatible. Dashboard stored
amounts and actual Expense accumulation stay Decimal until numeric output;
statistical suggestions/forecasts remain estimates. No balance, loan, investment,
transfer identity or ownership algorithm was replaced.

Pending development migration: [budgets.0002_budget_money_decimal](../apps/budgets/migrations/0002_budget_money_decimal.py),
depending only on budgets.0001 and the existing swappable User dependency.
It validates the complete register, retains exact original float representations
and independent normalized values in owned snapshots, then applies cents with
markers atomically. Invalid historical amounts block conversion without partial
evidence or financial writes. Reverse restores original precision only for
unchanged, applied, still-owned fields; corrections/new rows remain, deleted rows
are not recreated. Owner reset removes owned snapshots, including orphan evidence.
Snapshots are private canonical-DB recovery evidence, not encrypted AI memories.
No currency column/backfill or FX assumption is introduced; legacy screen INR
conventions remain unchanged. Other domain conversions and currency design are
separate work; see newer FIN-MONEY checkpoints above for current progress.

Validation evidence under `artifacts/post-audit/fin-money-20261016/`:
- `budget-focused/receipt.json`: 14 focused tests PASS (included in the combined run).
- `budget-integration/receipt.json`: **74 backend PASS**, zero failures/skips:
  Budget runtime/migrations, canonical baseline, user-data acceptance/reset,
  abuse limits, family boundaries and Expense identity.
- `finance-browser-final/receipt.json`: **three Chrome workflows PASS**, zero
  failures/skips (delayed Loan response, Banking/filter navigation, sample finance).
- `configuration/receipt.json`: system/drift checks PASS; synthetic baseline plan
  contains exactly the one Budget migration. New tests are in the existing M20
  backend selection; no completed M20/M21 gate was rerun.

The file-backed synthetic rehearsal uses SQLite backup and an independent restore,
checks integrity/FKs, forwards on a separate alias, compares all unrelated tables
with typed row hashes (accounts, transfer fingerprints/legs, loans, investments,
family and owners), reverses to exact original row hashes, and proves source bytes
unchanged. No real private records or backup material were used. Screenshots of
the corrected Loan table and final finance workflow were reviewed.

**Local unit PASS; FIN-MONEY overall PARTIAL; no deployment authorization.**
Production still 3932f391; new migration is not applied there. Frozen 4aa7ac70
and package evidence remain their own immutable scope. No native rebuild/full
release gate for this new unit yet. Existing clean-PC/installer, normal-account,
independent device-loss/key recovery and remote CI/protection acceptance remain
pending. The next unit at this Budget checkpoint was User income/rent; newer
checkpoints above supersede that next action. Never infer historical currency.

### Verified local runtime candidate — 2026-10-16

Frozen branch `release/post-audit-runtime-20261016` points exactly to
`4aa7ac70fa27c1410e695470af5c3987235244b1`. It integrates 28 commits / 156 changed
tracked paths since M15 `3932f391`; the source manifest is authoritative for that
inventory. Production and GitHub master remain at `3932f391`; their source and
operator files were not changed. Documentation checkpoints after the frozen
commit do not change the tested source or substitute their HEAD for this SHA.

**Local technical decision PASS; production promotion BLOCKED and unauthorized.**
Exact-source combined results: **797 backend / 40 Chrome / 34 source-native/Ollama
checks PASS, zero failures/skips**. Source/privacy, system and migration-drift
checks passed; no new migration. Earlier dependency changes remain explicitly
declared: Django 6.0.9 and removal of nine retired direct SDK requirements.
Evidence: `artifacts/release-gates/post-audit-quiescence-20261016/release.json`.

Actual M21 at `F:/ALFRED_DEV/post-audit-rehearsal-4aa7ac7/rehearsal.json` PASS:
authenticated encrypted local restore, typed financial/family reconciliation,
exact fast-forward, nine Chrome checks, restart/memory persistence, injected
worker crash, source rollback and nine after-rollback browser checks. The failure
child deliberately records FAIL with rollback PASS; the parent is PASS. The
older failed 874639f sandbox and all recovery evidence remain preserved. Test
servers on 8140/8150/8160 were closed. These are synthetic fixture-bound results,
not live-backup, real-account or device-loss acceptance.

Fresh portable package at `artifacts/releases/post-audit-4aa7ac7-28624710` PASS:
**35 packaged native checks including seven Chrome flows**, actual local Ollama,
encrypted memory, owner/deletion isolation, launcher, worker/scheduler, outage and
restart checks. Desktop Travel and mobile assistant screenshots were reviewed.
No ignored files existed under the packaged project-data directories; the bundle
inspector passed all 10,322 files. A second clean assembly in
`post-audit-4aa7ac7-repeat-fa68edd5` produced **identical paths and bytes for all
10,322 files**, including both executable hashes. This is same-host/same-SDK
repeatability; independent clean-PC installation is NOT_RUN.

The clean Python 3.12.10 SDK matched all 151 planned application packages; pip
and those packages were unchanged when five declared build-tool dependencies
were added. Pip check passed. The package directory contains hash-pinned inputs
for 156 distributions (154 wheels / two source archives), plus the bootstrap pip
version. Source-archive build-backend provenance is an additional independent
replay consideration. The 468,439,826-byte portable ZIP passed every entry's size
and SHA-256 comparison. It is an application archive, not a financial-data backup.
See [Windows package evidence](WINDOWS_PACKAGE.md).

M16 and M17 implementation are complete locally. M18 clean dependency/security
validation and M19 same-host portable/repeat-build acceptance PASS. M20 local
engine and M21 same-host rehearsal PASS; installer/clean-PC, normal-account,
independent archive/key/device-loss recovery, remote CI and branch protection
remain NOT_RUN. No new waiver or production authorization exists. The backup
adapter's default native-layout proof does not establish coverage of custom
external media/configuration paths; review coverage before any live operation.
Production ACL repair and dependency/runtime promotion remain separately gated.
The latest read-only check still could not reach `127.0.0.1:8000`; no startup,
shutdown, private DB access or repair was attempted.

Next: obtain the required installer/clean-PC environment and scoped CI/human
acceptance approvals, or continue the next independent confirmed roadmap item on
the development branch. Preserve the frozen source, all backups and the cancelled
key-dialog decision. Do not repeat completed P0/M16/M17/full local gates.

### Implementation checkpoint before the full gate — 2026-10-16

The clean SDK at `artifacts/post-audit/m18-clean-resolver-be31990d/venv`
passed **792 backend / 40 Chrome / 34 source-native/Ollama checks**, zero final
failures/skips, at exact source `874639f142f224255c6704d9c32409f79bb0bb73`.
The initial full browser failure, interrupted retry and later successful retry
remain recorded; the intermittent Banking error was not reproduced in the
40-test diagnostic run or completed normal retry. Its cause is unconfirmed.
The Travel preference loading/save race was independently reproduced and fixed.
Source/privacy, dependency policy and migration checks passed. Evidence:
`artifacts/release-gates/post-audit-clean-874639f/release.json`.

That source's actual M21 promotion, nine browser checks, local restore and restart
persistence passed, but worker-crash rollback was **BLOCKED/native_writer_running**.
Preserve `F:/ALFRED_DEV/post-audit-rehearsal-874639f/rehearsal.json` and its archives.
Recorded PIDs can remain alive briefly after clean shutdown or be reused; the
backup guard incorrectly treated them as proof of a writer. The correction uses
the existing supervisor/worker OS locks and SQLite write reservations throughout
capture. Active writers still block. Native shutdown now waits for both locks
after the stopped status is published and keeps its bounded failure result.

Reproductions: `writer-barrier-repro-4e872736` (14 tests, three errors) and
`shutdown-lock-repro-65f45f6e` (two tests, three failed subtest/assertion results),
under `artifacts/post-audit`. The backup-only correction passed 100 focused tests;
the complete shutdown/recovery correction passed **66 focused tests, zero skips
or failures** (`shutdown-recovery-fixed-4daa6f27/receipt.json`). These overlap and
are not summed. Changed implementation is in `alfred_native.py` and
`scripts/release_recovery.py`, with native/recovery regressions. No migration,
dependency, financial-value or production change. AST graph updated locally.

**Readiness at that checkpoint was BLOCKED.** The following work was pending then
and the verified local candidate above supersedes that pending state: a new pinned
full gate and actual M21 rehearsal before fresh packaging. M19 tools are staged;
Inno Setup is unavailable. Separate-PC/installer, normal-account, independent
device-loss recovery and remote CI acceptance remain unverified; no waiver is
inherited. A read-only check on 2026-10-15 found port 8000 unreachable; no service
action was taken. Production source/operator files remained unchanged.

### Earlier frozen critical-fix evidence

**Frozen source: b162c8fb2c43b357e840c3a298d06ffa4bed3251.**
753 backend tests, 37 Chrome tests and 34 source-native/Ollama checks PASS,
zero failures/skips. Actual M21 exact promotion, nine browser checks, restart/
encrypted memory persistence, independent local restore, typed financial/family
reconciliation, injected worker crash and source rollback PASS. Evidence:
artifacts/release-gates/post-audit-critical-b162c8f/release.json and
F:/ALFRED_DEV/post-audit-rehearsal-b162c8f/rehearsal.json. The failure-injection
child report deliberately records FAIL with rollback PASS; the parent rehearsal
is PASS. No database was overwritten by source rollback. All recovery assets
and failed earlier evidence remain. Screenshots reviewed at the preceding
3a46e1c equivalent UI gate; current Chrome gate also PASS.

At that frozen source M20 technical decision was PASS; production promotion
remained BLOCKED and unauthorized. The latest correction above needs its own gate.
Off-device copy/key/device-loss restore, fresh package, normal account, separate
PC, installer, remote Git/CI and branch protection are NOT_RUN. Source-native
checks are not a frozen executable proof. The M15 HDD waiver is not inherited.
P0 fixes and Django 6.0.9 are development-only; live ACL repair/deployment need
separate authorization. Newer M16 source progress is recorded below.

M16/T09 request retention is now implemented in development: configurable 7-day
non-network/90-day network history, current UTC quota windows preserved, active
attempts deferred, bounded oldest-first batches, dry-run CLI and shared 15-minute
source/native scheduling. Saved plans/evidence, owners, expenses, balances, cache
results and provider state are not cleanup targets. Full backups retain telemetry;
post-start canonical reconciliation excludes only the expiring request table.
**156 focused Travel/worker/recovery/promotion tests PASS, zero skips; system and
migration drift PASS** (artifacts/post-audit/m16-integration-a065eaeb/receipt.json).
These overlap prior tests and are not added to 753. This extension is after the
frozen critical candidate; its full combined/package gate has not run.
M16 retention and selective-refresh implementation is now COMPLETE in isolated
development. Category-scoped jobs reuse unrelated fresh/expired caches without
network calls, preserve provenance and quota/lease guards, prioritize the latest
web topic and selected location, and supersede older incompatible jobs. Date
edits invalidate candidate/itinerary forecasts, offers, quote snapshots and old
research banners while retaining independent route/place evidence. Same-length
date shifts retain edited days/allowances; changed duration requires schedule and
budget review. Plan/session changes are atomic on invalidation failure.
**196 targeted backend tests / 5 Chrome workflows PASS, zero failures/skips;
system and migration drift PASS.** Receipts:
artifacts/post-audit/m16-verified-d421da86/receipt.json and
artifacts/post-audit/m16-final-chrome-56feb12f/receipt.json.
Desktop/mobile screenshots were reviewed; changed-dates-no-old-forecast.png
shows the corrected date warning. No migration or dependency was added.
Initial reproduced failures and two corrected synthetic fixture failures are
retained in selective-refresh-repro-072cd2a5, date-invalidation-repro-28a7f490,
m16-selective-integration-8ecbf0b8 and m16-final-contract-3f61f4cd. The latter
rollback assertion needed a DB reload after save_plan's confirmed-state write;
safe class/frame diagnosis is in m16-rollback-diagnostic-865c4715. The initial
Chrome pass also exposed an old banner claim, corrected before final acceptance.
Counts overlap earlier checks and are never added together. Exact source pin and
limited gate scope: artifacts/release-gates/post-audit-m16-selective/release.json.
Full combined/native/package release gates are NOT_RUN for this newer source.
Next scoped unit after M16 was M17; its completed implementation is recorded below.
Implementation commit d66ce9904e560ade110ccf41be210eedc6f7b7e8 also passed exact
source/privacy/dependency/migration preflight and nine targeted retention tests
(artifacts/release-gates/post-audit-m16-d66ce99/release.json). Its full backend,
browser and native gates correctly remain NOT_RUN; the targeted success is not
transferred into a release PASS.

M17 cleanup is COMPLETE in development. The unrouted self-improve package
(missing patch generator, eager GPT-2 pipelines and production-root scanner),
SelfImproveAPI and orphan Google speech/gTTS voice prototype were retired from
source/package module inventory. Their preserved M15 history is linked from the
audit/matrix; no working AI Council or voice feature is claimed. Supported hybrid
reasoning, encrypted memory, registry and consented training remain.
Legacy interactive Gmail/Outlook setup, plaintext CWD token writer, unreachable
Gmail transport and counter-only fake auto-import method were removed. Existing
encrypted EmailConnection models and historical token/recovery files are untouched.
The IMAP portfolio service retains inline attachment parsing; standalone refetch
is explicitly unsupported. Each import gets its own connection, with a deterministic
two-owner concurrency regression. Connection/scan/cleanup failures use existing
safe diagnostic references/classification, never raw server/credential contents;
logout is attempted even after close fails.
**114 focused backend tests PASS, zero skips/failures; system/drift PASS**:
artifacts/post-audit/m17-integration-2bf509e2/receipt.json. This includes seven new
retirement/privacy/isolation checks, supported mail/ML/training/reasoning, finance,
auth and source-native boundary checks. Six original failures are retained in
m17-repro-d0730c23; the intermediate six-test pass is m17-fixed-240a62d7.
Pinned source/privacy/targeted scope:
artifacts/release-gates/post-audit-m17-cleanup/release.json.
No migration/dependency/provider activation; new full/native/package gates NOT_RUN.
Real mail/account/provider acceptance is still pending. No production remediation
or deployment is inferred. Next: M18 clean dependency reproducibility, then M19
fresh native package; reuse constraints/package tooling and do not repeat P0/M15.

Exact implementation pins: M16 3344ce21588dcaf41eb7655579cd978142c5fee2;
M17 86947a62e78359a5a62a51dacbcbbe2d3a3f484e. Both source/privacy/dependency/
migration preflights and targeted CLI runs passed; full newer-source release
gates remain NOT_RUN. M16/M17 documentation checks passed for 12 changed documents,
986 local links and seven archived-source links verified against preserved Git
blobs (artifacts/post-audit/m16-m17-doc-links-8971b1d4/receipt.json).

M18 is IN PROGRESS. Nine unused direct OAuth/voice SDK requirements were removed
after caller/import verification; supported ML/OCR/financial packages and the
historical Windows constraint snapshot remain. A fresh disposable resolver passed
with 151 packages/no conflicts/no retired direct requirements:
artifacts/post-audit/m18-clean-resolver-be31990d/receipt.json. Django startup and
URL checks also passed with retired SDK imports blocked
(artifacts/post-audit/m18-no-retired-sdks-eaa4689f/receipt.json). Resolution is not
an installed-runtime proof. The subsequent clean installation PASS exactly matched
all 151 planned packages; pip check, isolated Django 6.0.9, system/drift PASS with
no baseline fallback (m18-clean-resolver-be31990d/installation-receipt.json).
No production SDK changed.

The pinned 5f6bb76 clean-SDK full gate passed **792 backend tests/zero skips**,
then failed Chrome (38 executed, one error in quick-ideas/preferences). Correct
fail-fast left native/Ollama NOT_RUN; it is not a release PASS:
artifacts/release-gates/post-audit-clean-5f6bb76/release.json. The isolated original
test passed, but a deterministic delayed-read reproduction proved that an old
initial GET could erase a successful preference save from the UI while the DB
retained it (preferences-read-stages-cf247671/diagnostic.json). Both new loading/
outage regressions failed before correction (preferences-loading-repro-1010ed2d).
Travel preferences now use a disabled fieldset until loading completes, serialize
saves, expose aria-busy/status and retain disabled privacy controls after a failed
initial read. Both script callers use v2 assets. APIs/auth/CSRF are unchanged.
**Seven clean-SDK Chrome workflows PASS, zero skips/failures**, including delayed
GET/PATCH and load failure; mobile/error screenshots reviewed; JS syntax PASS:
artifacts/post-audit/preferences-loading-fixed-45eabf1a/receipt.json.
The corrected 874639f candidate received the combined and failed rollback results
recorded above; its later shutdown/recovery correction needs a new gate.
M19 PyInstaller 6.22.3 and declared tool wheels are staged
with hashes at artifacts/post-audit/m19-build-tools-3b6aacd1/receipt.json; not
installed during validation. Inno Setup is unavailable in checked PATH/standard/
registered locations, as already documented historically. Fresh portable package,
installer lifecycle and external/real-account recovery acceptance remain pending.

### Earlier development evidence (preserved; current result above supersedes pending actions)

Latest pinned integration: **3a46e1cb24234c586a40be446501a83c48cce2ea — 751 backend,
37 Chrome and 34 source-native/Ollama checks PASS; zero failures/skips**. Isolated
pip check PASS (shared baseline libraries, not clean-install/package proof).
Evidence: artifacts/release-gates/post-audit-final-3a46e1c/release.json. Synthetic
dashboard/mobile Travel screenshots reviewed. Overall promotion remains BLOCKED.
Actual M21 in F:/ALFRED_DEV/post-audit-rehearsal-3a46e1c passed exact promotion,
nine browser checks, financial preservation and memory restart persistence, then
failed before worker-crash injection because its nested evidence directory did
not exist. Reproduced FileNotFoundError; sandbox approval now creates/verifies
that private directory before writing. 33 focused acceptance/promotion/recovery
tests PASS (artifacts/post-audit/m21-output-directory-2f27f838/receipt.json).
All failed evidence/backups remain; complete actual rollback acceptance is pending.

P0 temporary-file follow-up: uploads and both isolated OCR paths now create
private parent directories before opening document files. Tightening a file ACL
after creation alone cannot revoke an already-open read handle. The creation-time
regression reproduced all three gaps (temp-parent-repro-ee45ea20). Streamed files
retain Django's Windows-safe temporary wrapper; the first attempt using Python's
different sharing mode failed and is preserved (private-temp-parent-efce6af0).
Corrected **115 focused storage/upload/document/loan/finance tests PASS**, zero
skips (artifacts/post-audit/private-temp-fixed-900cdd22/receipt.json). Temporary
directories close with their files; OCR uses private scoped input and safe
classified errors, without raw cleanup paths. No production ACL/file change.

| Unit | Development status | Evidence / remaining acceptance |
| --- | --- | --- |
| P0-B profile money | Implemented: finite, bounded cent validation at API/form/model/ORM and Career scenario inputs; existing Float SQL schema/API numeric contract preserved | 47 combined focused tests PASS, zero skips; migration drift PASS; production not remediated |
| P0-C private media | Implemented: source/debug and native use the same owner-filtered handler; safe missing/permission response, public static assets separate | Same 47-test gate includes anonymous/invalid session/foreign owner/traversal/deletion/source/native tests; packaged/live acceptance pending |
| P0-A Windows storage | Implemented: native and source/debug SQLite/config/cache checks, private retained/streamed uploads, memory/parser/recovery protection; pinned quiesced repair/rollback | Native unit: 117 focused PASS, 11 overlapping CLI PASS, 18 native PASS. Source extension: 89 focused PASS, system/drift PASS. Production ACL repair remains approval-gated |
| P0-D M20 gates | Reused/merged existing 0052410 engine: ignored target file collisions fail before mutation; quoted JSON credentials fail with redacted findings | Both original failures reproduced; 70 focused gate/recovery/promotion/acceptance tests PASS; 13 overlapping incomplete-run/privacy tests PASS |
| AWS / replacement | AWS runtime provider removed; provisioning rejects before prompts/writes; historical flags report disabled. Old protocol is network-free test quarantine only | 86 focused memory/sync/UI tests PASS; 2 final decommission tests and SyntaxWarning-as-error compile PASS; neutral encryption/sync unchanged; R2 is an unimplemented candidate |
| M18 Django security patch | Development requirements and Windows constraints pinned to 6.0.9 | Separate development venv: 227 focused security/finance/upload/document tests PASS, zero skips; system/drift PASS; fresh browser/native/package gates pending |

Changed money/media files: apps/users/money.py, models.py, serializers.py, forms.py;
apps/career/serializers.py; alfred_ai/urls.py, native_views.py; new boundary/profile
tests. Test receipt: artifacts/post-audit/money-media-3570b592/receipt.json (local,
synthetic). First money test attempt exposed a test transaction/savepoint issue;
the fixture was corrected without weakening validation. Historical failed receipt
is preserved. No migration, financial record conversion or balance change.

Storage files: alfred_private_storage.py; alfred_native.py; local_config.py;
memory_key.py; bounded_parser.py; document_extraction.py; statement_import.py;
backup/verification/recovery scripts and synthetic permission fixtures.
Evidence: artifacts/post-audit/storage-final-f320dc9c/receipt.json (117 tests and
WAL/config/media backup fixture); storage-cli-0dc1fcd2/receipt.json (11 tests);
storage-native-final-7e6dbb9c/receipt.json (18 actual native checks). Earlier native
attempt reached 16 checks then refused inherited restored-directory permissions;
the guard now accepts exact owner/SYSTEM inheritance only from a verified private
ancestor. Its failed receipt is preserved. No source/debug database encryption,
portable-key verification or production ACL remediation is claimed.

M20 integration preserves its prior history and both recovery-verifier changes:
private scratch protection plus caller-selected scratch roots. Recovery fixtures
now create private directories before seeding synthetic data; the initial mixed
branch failure is retained under m20-focused-7e820d51. Fixed receipts:
artifacts/post-audit/m20-corrected-67461836/receipt.json and
m20-incomplete-d8fd4607/receipt.json. Zero/skipped successful runner output now
reports NOT_RUN and blocks readiness; an actual failing runner remains FAIL.
The source scanner retains exact path/value-hash exemptions for six reviewed
public synthetic identifiers, never a blanket test-file exception. New P0
regressions are included in the standard release backend gate. M20 full pinned
integration and actual M21 native rehearsal are still pending; production approval,
off-device/key recovery, real-account and external CI gates are not filled by tests.

M20 integration commit: 6045904824a86413396eac16d5b16d9464dcd2fa. Its actual
pinned preflight source/privacy/dependency/migration scope PASS is saved at
artifacts/release-gates/post-audit-m20-6045904/release.json. Overall readiness is
correctly BLOCKED on unexecuted technical/operational gates and approval.

Django 6.0.9 is the compatible 6.0 security patch dated 2026-10-06; it addresses
language/header parsing denial of service and additional scoped security fixes.
No framework major upgrade or schema change is included.
[Official release notes](https://docs.djangoproject.com/en/6.0/releases/6.0.9/).
Receipt: artifacts/post-audit/django609-focused-4084887b/receipt.json. The isolated
.venv supplies its own Django while sharing other baseline libraries read-only;
this is not a clean full dependency installation or reproducible package proof.
Production's interpreter and requirements remain unchanged. Broader dependency
maintenance and M19/clean-PC acceptance remain open.

AWS decommission changes: memory_cloud.py, memory API/status and sync command,
configure_memory_cloud.py, synthetic-only proof script and test fixture. No stored
profile/key is removed or rotated. Active provider documentation and the existing
master prompt/roadmap carry the explicit override; the 143 audit rows/history are
preserved. Receipts: artifacts/post-audit/aws-off-9cadde31/receipt.json (86 tests)
and aws-final-582984f8/receipt.json (two overlapping tests plus strict syntax check).
The documented regex warning was fixed in the quarantined fixture using raw
patterns; no AWS transport is imported by application runtime.

Non-AWS choice: R2 implementation candidate after official atomic CAS, token,
security/pricing/limits review. No adapter/account is activated. Private bucket
configuration proof and least-privilege verification must be resolved before an
implementation can claim readiness; no checkbox replaces that proof. Alternatives
and exact constraints are in the [provider register](ALFRED_EXTERNAL_INTEGRATIONS.md#non-aws-intelligence-storage-decision).
Real cloud, real OpenAI and device-loss recovery remain unaccepted/OFF.

Pinned 3b73d78916b4c5f545e8148ec0abcaee143855cd combined attempt:
**736 backend PASS / zero skips; 34 native/Ollama checks PASS; 36 of 37 Chrome
tests PASS, one Travel quick-ideas timeout.** Overall gate correctly FAIL, not
release-ready. The isolated failing browser test reran PASS without source changes
(travel-browser-debug-7812ac83); a whole browser retry is required, not a claimed
fix. Evidence: artifacts/release-gates/post-audit-integrated-3b73d78/release.json.
Loan/investment monetary screenshots reviewed; their captures were intentional
successful evidence, not additional browser failures.

Source storage extension closes a reproduced part of P0-A: ordinary source/debug
SQLite, retained media and streamed temporary uploads inherited broad fixture
permissions. Synthetic receipt: source-storage-repro-final-84402574. New checks
run before source SQLite/cache use or configuration reads; PrivateFileSystemStorage
and PrivateTemporaryUploadHandler protect data before payload writes. Static
assets stay separate. Existing unsafe directories/files fail for approved repair;
none are automatically changed. Receipt: artifacts/post-audit/source-storage-final-62f32718/receipt.json
(89 PASS / zero skips); system/drift PASS in source-storage-fixed-12c75b59.
The first upload fixture run failed because its intentionally shared media/temp
directory was broad; the disposable fixture is now protected before seeding.
No money, schema, provider, key or production change is included.

8978fe1 combined attempt retained: 744 backend executed, 26 failures/28 errors
from pre-existing broad shared media fixtures; 37 Chrome executed with one different
intermittent navigation error; 34 native/Ollama checks PASS. Overall FAIL remains.
The guard was not weakened. Corrected release environments now select a fresh
ALFRED_MEDIA_ROOT; source startup protects it before preview/document generation.
The shared M14F temp/media fixture is private before seeding. Standalone browser
runs use the same stripped, disposable environment instead of inheriting operator
DB/media/cloud settings. 150 focused document/loan/upload/financial tests PASS
(artifacts/post-audit/media-isolation-fixed-20c05611/receipt.json); 22 overlapping
runner/isolation/fail-fast tests PASS (runner-final-67f8460e). Backend/browser
failure stops subsequent expensive gates and leaves unexecuted gates NOT_RUN.

Pinned e4c66471e34a4eae14eb90a1bae3ce13577a5925 passed **747 backend / 37 Chrome /
34 native-Ollama checks**, zero failures/skips. Source/privacy/configuration/drift
PASS. Receipt: artifacts/release-gates/post-audit-isolated-e4c6647/release.json.
Actual M21 sandbox F:/ALFRED_DEV/post-audit-rehearsal-e4c6647 independently backed
up/restored synthetic data, booted the baseline and exercised fast-forward. It
then failed operator_file_changed_after_promotion because clean tracked checkpoint
source changes were incorrectly hashed as operator overlays. Authorized synthetic
source rollback PASS; data/configuration and all evidence/backups preserved.
This is a real M21 failure, not COMPLETE or real-account acceptance.

Correction: hash protected operator files only when the candidate does not change
them; clean tracked source advances normally, while dirty overlapping operator
edits and ignored-file collisions still block. CLI main/imports share GateError
identity so fixed errors stay actionable. 58 focused M20/promotion tests PASS
(artifacts/post-audit/m21-operator-fix-d24c0908/receipt.json); three overlapping
actual CLI boundary tests PASS (m21-cli-final-18f0f3fd). New candidate requires
fresh combined validation and a new disposable M21 rehearsal.

Pinned f79690a8c42eab6b2ae3182445af5002a87da6a8 retry executed 750 backend tests,
zero skips, with one error; browser/native correctly remained NOT_RUN. Evidence:
artifacts/release-gates/post-audit-m21-resume-f79690a/release.json. The earlier
post-audit-m21-f79690a attempt was interrupted before a final receipt, not PASS.
The redactor omitted setup/subtest failure headers; its reproduced regression
now retains test/class identifiers without parameter values or exception content.
15 runner tests PASS (failure-log-fix-49532b0a); 27 overlapping source/acceptance
tests PASS (m21-three-debug-296f6a15). These targeted results do not clear the
combined failure. Preserve all receipts; repeat the pinned combined gate, identify
any repeated error, then perform the new disposable M21 rehearsal.

The safe failure-header correction is committed at 3a46e1c. Its full rerun passed
as recorded above; the earlier one-error run did not reproduce, and is retained.
Next action: finish the private temporary-parent P0 follow-up under focused tests,
pin the corrected candidate and repeat actual M21 acceptance. No production action.
Specialized audit/runbooks and
historical results below remain reference material, not fresh acceptance.

**Current status — 2026-10-15:** M14/M15 consolidated source is deployed and GitHub master matches 3932f391aa4eed7b3200ad3b034f7991435e01e4. Dated release results are 619 backend/15 Chrome/35 native (overlapping packaged scope); this audit independently ran 86 focused tests, zero skips, plus isolated system/drift checks. Normal-account, real-provider, clean-PC and device-loss acceptance remain incomplete. Port 8000 did not respond during the audit; no service action was taken. M20 is unfinished separate development; M16–M19/M21 are not declared complete.

Use the [authoritative feature matrix](PROJECT_STATUS.md), [completion roadmap](PROJECT_STATUS.md) and [acceptance plan](ALFRED_END_TO_END_ACCEPTANCE.md). The earlier progress narrative below is historical module detail, not proof of current production availability or comprehensive AI accuracy.

Final read-only observation: /health/live/ returned 200 on a runserver listener;
/health/native/ returned 404. No audit restart occurred. Actual DB/worker/native
readiness remains unconfirmed; the initial unavailable observation is historical.

The [completion audit](COMPLETION_AUDIT.md) records the current verification
results and remaining local/LAN runtime work. The sections below describe
implemented capabilities, not a guarantee of complete real-data coverage.

The [29 September travel release continuation](TRAVEL_RELEASE_VERIFICATION_20260929.md)
records the 1.1.0 preview packaging, current travel tests and local upgrade evidence.

The [28 September continuation](WINDOWS_TRAY_VERIFICATION_20260928.md) records
the current tray, branding, website, attribution and cleanup work.

The [27 September release verification](WINDOWS_PACKAGE_VERIFICATION_20260927.md)
records the previous installer/uninstaller, 407 passing backend tests and nine
passing Chrome workflows. All six installer lifecycle checks passed. The same
native executables passed the
[26 September runtime checks](WINDOWS_PACKAGE_VERIFICATION_20260926.md), including
23 packaged checks and a 24-user load test. Overnight attempts interrupted by
host restarts are retained separately. The supervisor restarts verification
after Windows sign-in; use its Status action for the current attempt and expected
finish. Completed overnight acceptance remains pending; 16 focused tests
passed for the observation and supervisor logic.

The active Windows runtime is [Waitress + Huey + SQLite](NATIVE_WINDOWS.md),
with a double-click launcher, persistent task queue, shared local cache and
standalone installer build. The [earlier recovery proof](NATIVE_RECOVERY_PROOF.md)
records the original SQLite snapshot/restore. Current native verification also
exercises real HTTP, worker execution, retries, restart and an isolated restore.
Docker/PostgreSQL/Redis/Celery remain an optional, separately unverified runtime.
The BIOS virtualization issue does not block native Windows operation.
The [native verification report](NATIVE_WINDOWS_VERIFICATION.md) records the
passing full suite, Chrome workflows, packaged OCR, worker/recovery tests and
preservation of the existing account data.

The [18 September hardening report](NATIVE_HARDENING_VERIFICATION.md) adds
durable job claims/recovery, post-reboot retention proof, 12 concurrent-user
checks, mobile and automated accessibility coverage, and project cleanup.
The separate-PC test, real overnight outcomes and independently checked model
accuracy remain open; the report links the fresh verification branch/CI run.

The [sample-user acceptance audit](USER_DATA_ACCEPTANCE.md) records an isolated
signup/API scenario, independently reconciled money totals, correction tests,
and browser checks of the finance pages. It also documents the calculation,
cache, validation and wording defects found and fixed in that pass.

## Completed So Far

### Dashboards and UI

- finance dashboards wired across major sections
- dedicated sign-up and sign-in entry points are now available for users
- expense financial-flow charts now switch between monthly, quarterly, and yearly aggregation
- centralized `/documents/` upload hub for statements, loan PDFs, vehicle files, service bills, resumes, and credit reports
- centralized `/documents/` upload hub now also includes diagnostics, low-confidence review queues, all-scope retry controls, and linked delete behavior for document-derived data
- multi-file upload handling across the document hub, expenses, loans, career, credit-report, and vehicle-service pages
- dedicated vehicle-service dashboard
- mobility dashboard for travel plans, logs, gallery, and heat map
- rebuilt/fixed behavioral page empty-state and duplicate-insight handling
- roadmap and completion tracking moved into a separate superuser-only project-details dashboard instead of the main dashboard
- project-details is now a live superuser operations console with internal-clock timestamps, evidence watchlists, ticket-routing counts, report-library rollups, and adaptive learning progress
- project-details learning progress now refreshes live through a dedicated JSON endpoint instead of only on full page loads
- project-details in-progress progress bars now bind to named learning tracks instead of sorted positions, preventing progress drift as module maturity changes
- live-refresh pages now use interaction guards and selective DOM updates so active forms and dropdowns are not torn down every second
- browser interaction coverage now has a dedicated Selenium runner, a CI browser workflow, separate local Chrome/Edge and CI Chrome `browser_regression_summary.json` proof records, and failure artifacts for screenshots, page HTML, metadata, and browser logs where supported
- heavy finance, mobility, bike-service, and career dashboard reads now use cache-aware materialized payloads keyed to data revisions
- investment summary, allocation, and growth reads now also use cache-aware materialized payloads keyed to portfolio revision
- deterministic staging traffic now exercises all 21 registered materialized cache namespaces and records hit/miss, TTL, generation latency, stale regeneration, revision, and invalidation proof without marking production cache maturity complete
- Project Details selects readiness checks for the active runtime; native Windows checks use Huey, while Celery worker/beat requirements apply to the optional Compose runtime
- the shared `tests/` package is now discoverable by default so the normal `manage.py test` command runs the suite instead of silently skipping it
- supported ML models now persist training state, run history, quality estimates, and freshness windows in the database
- supported ML models can train on the scheduled nightly cycle when consent, data and runtime gates pass; the native Windows runtime disables startup training
- project status now treats local/LAN hosting as the only active operating path; provider-specific deployment leftovers have been removed from tracked source, IDE metadata, artifacts, and local cached evidence

### Vehicle and Mobility

- upload-first vehicle documents
- service-log import from service bills and work notes
- manual service logging fallback
- imported and manual service logs are now summarized together so long-term vehicle history stays usable
- issue/fault reporting with probable cause, suggestion, and projected cost
- condition snapshots with score and condition assessment
- parts-and-performance impact guidance based on service history, condition state, and open issues
- structured service-log and vehicle-document payloads now use centralized merge helpers so partial updates do not drop nested parsed data
- multiple saved vehicle profiles with primary-vehicle behavior
- travel advisor with weather, offbeat suggestions, stay-budget guidance, and vehicle-readiness context
- the vehicle catalog now includes broader official manufacturer coverage and model guidance across Royal Enfield, Suzuki, Honda, TVS, Bajaj, Yamaha, Ather, Tata, Mahindra, Kia, and NEXA-backed entries
- the service dashboard now attaches model-specific maintenance highlights with proof links where the catalog has official references
- the official vehicle catalog now filters model choices by selected vehicle type before the user picks a catalog entry

### Data Verification

- document relevance checks against selected vehicle profiles
- source-aware evidence cache for external data
- freshness tracking and stale cleanup rules for external intelligence
- circuit-breaker-backed stale fallback when verified sources repeatedly fail
- scheduled background refresh for verified external evidence
- foreclosure documents are now checked against the selected loan before a close action is allowed
- chart paths were audited to keep live API-backed data or empty states instead of user-facing demo/report widgets
- document parsers now share a layered extraction engine for PDF text, layout, table flattening, repaired-PDF fallback, and OCR retries
- parser-learning memory now adapts statement, loan-document, loan-closure-document, investment-document, recruiter/JD-document, credit-report, vehicle-document, and resume confidence from repeated uploads, accepted corrections, and retry outcomes
- operational diagnostics now persist document-processing failures, metadata-only saves, retry outcomes, and client-side visualization issues with timestamps and payload context
- recommendation and tax advisory outputs now expose freshness-backed evidence blocks and explicit grounding notes instead of opaque summaries
- investment guidance now exposes verified market and macro proof, freshness metadata, and materialized portfolio payloads
- relationship alignment now exposes factors, grounding notes, and freshness-backed proof instead of a fixed placeholder score
- verified external job feeds now filter blocked cloud-provider skill tokens before storing career evidence, and prior matching local cached job-evidence rows were purged

### Risk and Career

- career projection now uses macro context instead of a fixed placeholder growth rate
- career now shows dated risk-taking windows for job switches, promotion asks, skill upgrades, and side-income moves
- risk outlook now blends user-entered risk snapshots with macro context, market signals, financial pressure, behavioral pressure, and vehicle readiness
- related risk news is now consolidated under Risk Radar instead of being split across multiple module views
- resume uploads are parsed into role/skills/experience signals across broader formats including html, rtf, odt, and image-based CV uploads
- resume parser learning memory is now stored per user so parser adaptation does not leak across users
- pasted job links are analyzed for fit score, missing skills, and market risk
- recruiter mail and JD intake can now be parsed into the same career-fit pipeline, including optional attachment extraction
- study recommendations are now generated from experience stage, latest skill gaps, and live opening signals
- compensation benchmark summaries are now derived when salary-bearing evidence exists in job pages or recruiter/JD intake
- public job parsing now has deeper adapters for JSON-LD pages plus Greenhouse and Lever style openings
- layoff news and suggested openings are pulled from live configured internet sources with evidence
- scanned/image CV uploads now fall into review state instead of breaking the upload flow when OCR is unavailable on the server
- credit score surfaces now distinguish internal estimates from official bureau pulls instead of saving fake bureau pulls as real scores
- relationship alignment is now grounded in partner inputs, user cash-flow pressure, verified planning context, and a bounded optional relationship-model blend

### Expense Import Integrity

- statement intake now supports bank, credit-card, loan, investment, and other statement kinds
- parser status, confidence, and extracted payload are retained even when transaction extraction is incomplete
- account-scoped transaction fingerprints now reduce duplicate statement imports
- same-account repeated uploads are skipped more reliably
- similar transactions on different bank accounts are preserved instead of being deduped incorrectly
- mixed-overlap statement imports now keep new rows even when duplicate rows share the same reference and amount
- malformed or truncated statement PDFs now degrade to a stored review item instead of crashing the import flow
- structurally broken statement PDFs that still contain page objects can now be rebuilt to salvage metadata before they fall back to review
- structurally broken statement PDFs can now also fall through an isolated OCR worker to recover holder/account/period metadata even when the in-process OCR runtime is unhealthy
- metadata-only statement uploads now remain visible in the expenses workspace and central document hub with parser notes and recovered header details
- low-confidence statement uploads now queue deeper background retries instead of staying permanently dead-ended after the first pass
- repaired broken bank PDFs can now import partial OCR-preview transactions immediately, keep page-progress metadata on the upload, and continue deeper retries in the background for the remaining pages
- accepted corrections on partial or metadata-only statements now force a deeper retry window so OCR-recoverable uploads can populate expenses after review instead of only saving header fixes
- imported loan-like statement entries are now matched against the active loan book with confidence and review flags
- assets and liabilities are now surfaced in the expense intelligence view, including vehicle classification based on usage and utility

### Loans And Support Workflow

- active loans can now be consolidated into a new loan record while source loans are marked prepaid
- loan foreclosure now requires an uploaded closure or no-due document
- loan PDF imports now expose detected document type and parse confidence for sanction letters, statements, and repayment schedules
- uploaded loan PDFs are now saved as first-class import records, even when the parse is weak and only a review item can be created
- manual user ticket creation is no longer part of the normal user flow
- Alfred can auto-create summarized tickets when loan matching is low-confidence or a closure document is rejected
- low and medium severity tickets are now auto-handled by ALFRED, while high severity is escalated to superuser developers
- reports and ticket-routing visibility are now superuser-only
- the central document hub now exposes retry controls for statement, loan, vehicle, resume, and credit-report items instead of statement-only retry
- the central document hub now also supports review, correction, retry, and parser-learning feedback for loan-closure, investment-import, and recruiter/JD intake documents
- accepted corrections for invoice-style vehicle documents now update linked service-record fields such as service date, workshop, odometer, cost, and work summary instead of stopping at the document shell
- the document hub and expense intake now keep recent upload stacks scrollable and capped to the latest 10 visible cards per panel so the page height stays stable as history grows
- unresolved retries now create internal retry tickets keyed to the retry count, so ALFRED can auto-handle lower-severity parsing failures and escalate exhausted cases to developers
- parser-confidence calibration is now a trainable ML path that learns from parser outcome history instead of relying only on static confidence heuristics
- relationship-model training is now a safe, bounded path that only activates when enough scored partner profiles exist

## Pending acceptance

- Clean second-PC installation and reboot acceptance. Installer, host-reboot retention and backup/restore checks have passed on the development PC.
- Full overnight scheduled refresh, cleanup and eligible-training outcomes. The September 18 report was interrupted after 4.1344 hours; it is not an active or passing observation.
- More independently checked documents and model outcomes, with enough consenting data to pass quality and freshness gates. The September 25 comparison passed 68 checked fields across three private documents.
- Manual screen-reader testing and heavier real usage. Nine Chrome workflows and a 24-user/480-write synthetic load check passed; the three newly found dropdown-label issues are fixed and included in packaged verification.
- A real Windows sign-in check. Current-user startup registration succeeded on September 25 and remains registered.

See the [September 25 continuation](ACCEPTANCE_20260925.md),
[standalone package guide](WINDOWS_PACKAGE.md) and
[completion audit](COMPLETION_AUDIT.md) for acceptance conditions and dated
evidence. The earlier Windows/Chrome CI proof is dated September 18; current
continuation checks are local.

## Optional extensions

- LAN access and live email/bureau integrations, with the required account access and consent.
- More vehicle catalog models, job sources and geography coverage, informed by real usage.
- Additional model families and richer career/market/risk guidance after current models have sufficient validation evidence.

The [future scope](FUTURE_SCOPE.md) records broader product ideas. Public/cloud
deployment requires a separate explicit decision and is outside current scope.

## Risks Remaining

- browser-only issues can still exist where no driver-backed Selenium pass was recorded; normal test runs still skip browser tests unless `ALFRED_RUN_BROWSER_TESTS=true`, and full UI maturity still needs repeated no-skip browser summaries from both local and CI jobs
- selective fragment refresh now prevents most interaction resets, but any remaining page that still swaps whole DOM blocks in-browser could regress until it gets the same treatment
- some external sources are authoritative APIs, but market data still relies on Yahoo Finance
- multiple-vehicle support is structurally improved, but some naming remains bike-centric in code paths for backward compatibility
- job-link parsing is robust for many public pages, but some portals can still block direct fetches or hide content behind script/runtime layers
- project-details is now dynamic from live operational data, but it is still not generated from a formal release registry
- large-data hardening has deterministic staging proof for all registered cache namespaces, but production maturity still requires shared-cache telemetry under realistic concurrency and payload volume
- public-production readiness remains inactive and decision-gated; native Waitress/Huey/SQLite with a shared disk cache is the active Windows path, and Docker/PostgreSQL/Redis/Celery is an optional alternative
- balance-sheet vehicle classification is heuristic and should still be reviewed against real ownership/use patterns where the financial treatment matters
- auto-training is now safe and stateful, but several modules still remain heuristic, placeholder, or data-poor and should not be treated as fully learned systems yet
- parser adaptation is materially stronger now, but "all document types without fail" is still not a truthful guarantee for arbitrary or severely degraded files

</details>
