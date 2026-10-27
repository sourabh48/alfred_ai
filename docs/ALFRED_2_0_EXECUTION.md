# ALFRED 2.0 execution

Updated 2026-10-27. Canonical development: `development/alfred-integrated` in
`F:/ALFRED_DEV/post-audit`. Recovery source `4b012a2`; clean and synchronized.
The 143 requirements and their acceptance remain in PROJECT_STATUS; the 13
extension IDs below are the existing requirements ledger, not 13 new baseline
capabilities. Coordination rows add no requirements. Baseline75/143; extensions0/13.

## Current checkpoint

- MODE NEXT recovered84902b7; CI40491012266 finished FAILURE: native1435 exactly
  two restart-fixture failures,Linux portable SUCCESS,Selenium CANCELLED30m.
  Prior40485342191 Linux upload failure is superseded by exact84902b7 Linux PASS.
  Both default/file-backed cold-process fixes2 PASS each; existing races2 PASS;
  upload helper1 actual Chrome PASS. Selenium45m measured budget reviewed; no
  coverage/protection/cancellation reduction. Fresh exact-head CI remains required.
- B1 private saved-itinerary PDF LOCAL_VERIFIED: owner/CSRF/revision protected,
  no external calls or financial/private attachment export. Retains per-stop
  source dates/unknowns. Focused47 PASS incl9 PDF cases; final layout/page-limit2
  overlapping PASS;3 unique Chrome workflows PASS;4 global1440/390 light/dark Axe
  audits zero violations; native runtime review CLEAN,fixtures summary-only.
  JS/migration drift PASS; AST Graphify11490/32022/521. Evidence in artifacts/
  travel-export-20261027 and ci-repair-ac05515/travel-export-*.json. Source/privacy,
  commit/push/new-CI closure tracked in EXECUTION_STATE; no full-story promotion.

Verified implementation source **a0b1fdc2e8a8813bf0ee9d7d6fde4142a2733b53**; clean source/history privacy,
dependency/migration preflight PASS,zero findings. Final tracker-only HEAD is bound
by source-checkpoint/release.json,push.json and ci.json in the export artifact
directory. Fresh CI remains pending; source acceptance is not release approval.

## Persistent remaining Travel phases (owner instruction2026-10-27)

- PhaseB/TRAVEL2-004: B1 private saved-itinerary PDF LOCAL_VERIFIED/CI_PENDING; B2 validated
  waypoint/route GPX QUEUED; B3 timezone-correct ICS QUEUED; B4 combined UI/privacy/
  independent parser/Chrome/Axe acceptance QUEUED. Reuse current Travel/document
  helpers; explicit owner export only; no fabricated route,booking or amount.
- PhaseC/TRAVEL2-005: UNBLOCKED for read-only development. C1 canonical Decimal
  affordability,C2 explainable what-if UI,C3 future-date savings,C4 reconciliation/
  privacy tests QUEUED. Verified same-currency amounts only,no inferred INR/FX,
  no double count or canonical writes; incomplete data cannot receive certified
  Affordable. FIN-15 migration remains separately approval-gated.
- PhaseD integrated acceptance: D1 end-to-end backend/browser,D2 persistence/
  restart/offline,D3 security/owner/accessibility,D4 native Windows/regressions,
  D5 exact-head CI/independent review,D6 roadmap/completion,D7 production-readiness
  report without deployment QUEUED. Keep independent screen-reader,real-account
  and production acceptance explicitly pending. No new IDs/count inflation.

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
  source-checkpoint/release.json, push.json and ci.json in the organizer artifacts
  bind the final checkpoint HEAD's preflight/push/new exact-head CI.
- Packing verified source6817fa863e95c34e93a9cae121100024f55d8ff7 clean source/
  history privacy/dependency/migration preflight PASS,zero findings. This final
  checkpoint changes only three trackers; passing runtime evidence is reused.
  artifacts/travel-packing-20261027/{source-checkpoint/release.json,push.json,ci.json}
  bind final checkpoint candidate/ref/CI closure. No master/deployment action.
- Reminder sourcea799b31ec59ace8806460345c6f3de78c7274476 clean source/history
  privacy,dependency/migration preflight PASS,zero findings. This final checkpoint
  changes only three trackers; runtime evidence is reused. Reminder artifacts
  source-checkpoint/release.json,push.json and ci.json bind final candidate/ref/CI.
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
| TRAVEL2-004 — private PDF/GPX/ICS exports | Owned trip/evidence/map structures | Explicit validated source-preserving export | TRAVEL-04/17, owner export consent | P2 /2–3 slices | Correct coordinates/timezones/escaping; preserve expiry/unknowns; no public sharing | File parsers and malformed inputs; desktop export | Existing Travel evidence; extension pending | B1 PDF LOCAL_VERIFIED; source/push/CI closure in EXECUTION_STATE. B2 GPX next; B3 ICS/B4 integrated acceptance queued |
| TRAVEL2-005 — reserve/goal-aware affordability | Canonical baseline and Decimal trip allowances | C1 read-only arithmetic,C2 explainable what-if UI,C3 savings scenarios,C4 reconciliation/privacy | FIN-05/06/07 evidence; FIN-15 migration stays gated | P1 /4 bounded slices | Verified same-currency only,no inferred INR/FX,double counting or canonical writes; incomplete data never certified Affordable | Decimal edge/cutoff/owner/reconciliation and desktop explanation | Owner2026-10-27 read-only approval; existing finance receipts,extension pending | UNBLOCKED read-only; select after PhaseB; migration/financial writes remain gated |
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
