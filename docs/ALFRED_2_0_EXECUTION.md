# ALFRED 2.0 execution

Updated 2026-10-27. Canonical development: `development/alfred-integrated` in
`F:/ALFRED_DEV/post-audit`. Recovery source `4b012a2`; clean and synchronized.
The 143 requirements and their acceptance remain in PROJECT_STATUS; the 13
extension IDs below are the existing requirements ledger, not 13 new baseline
capabilities. Coordination rows add no requirements. Baseline75/143; extensions0/13.

## Current checkpoint

- Selected: TRAVEL2-001, IMPLEMENTING. Extend the existing owned session/plan JSON,
  manual multi-stop API, Decimal allowances and desktop UI; no replacement planner.
- PR16 is OPEN at4b012a2, reopened by explicit owner request. This supersedes the
  older no-open-PR checkpoint. Head CI40394951006 PASS all3 jobs; PR CI40414777100
  IN_PROGRESS at recovery;0 reviews/approvals. Receipts:
  `artifacts/travel-discovery-20261027/pr16-validation.json`. No eligible scoped
  merge: PR16 contains the cumulative development diff; complete cumulative review,
  newest PR checks, compatibility/security/privacy/rollback and Pages authorization
  are not all established. Masterc47fed9/frozen4aa7ac70 stay untouched.
- Implementation present: new `travel/editor.py`, existing planner API/session
  JSON and desktop controls. Seven unique backend workflows accepted across initial
  five passes and two read-time-aging assertion repairs; native pointer workflow
  and stale-draft/lost-response retry each passed. Full-story acceptance is pending.
- Initial native review found stop-render markers, legacy-ID collisions, LAN UUID,
  missing safety/source panels and legacy revision gaps; repairs are implemented
  with targeted regressions. No external AI review/disclosure. Failed receipts kept.
- NEXT ACTION: finish current integration runs `travel-editor-backend-batch` and
  `travel-editor-browser-final`, repair only actual failures, run desktop Axe and
  source/privacy/migration gates, final native review, then commit/push verified
  source. Backend test cache isolation was corrected after synthetic429 interference;
  rerun affected integration once. Receipts in artifacts/ci-repair-ac05515 and
  artifacts/travel-editor-20261027. No source acceptance or extension promotion yet.
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
| CAREER2-002 — reviewable application workflow | Recruiter/JD/discovery/geography and owned documents | Source-backed drafts and attachment/revision review | CAREER-04/07, DOC-06, AI-15 | P2 /2–4 slices | Stale proposals/attachments rejected; no implicit sending | API owner/CSRF/stale/retry; Chrome review | Career Discovery/Geography receipts; extension pending | QUEUED; preserve no-send boundary |
| TRAVEL2-001 — desktop itinerary editing/undo | Manual stops, dated days, estimates, chat edits, save/reopen | Pointer and keyboard reorder, activity CRUD, stable IDs, undo/history, stale/idempotent updates, safe invalidation | TRAVEL-03 accepted; TRAVEL-04 bounded manual slice | P1 /2–3 slices | Full bounded edit/reorder/undo/save/reopen flow; unrelated data preserved; conflicts visible; no stale route/cost claim | New editor backend; existing multi-stop/continuation; actual Chrome drag/keyboard; accessibility/privacy | Pending; recovery source4b012a2 and existing multi-stop receipts | IMPLEMENTING; complete backend then desktop acceptance |
| TRAVEL2-002 — private booking/document organizer | Owned trip plans and general corpus | Explicit attachment/link/expiry/revocation review | TRAVEL-04, DOC-06 | P2 /2–3 slices | Owner-only originals and source dates; no inferred availability or booking writes | API ownership/path/expiry; desktop attach/revoke; privacy | DOC-06 accepted; extension pending | QUEUED; next independent Travel task after editor |
| TRAVEL2-003 — packing/reminders | Static packing and trip dates | Durable owner opt-in checklist/reminder lifecycle | TRAVEL-04; local durable queue | P2 /2 slices | Idempotent completion/timezone/cancel/offline behavior; no external sending | Backend lifecycle/timezones; Chrome opt-in/reopen | Existing itinerary packing; extension pending | QUEUED; reuse queue/settings after organizer |
| TRAVEL2-004 — private PDF/GPX/ICS exports | Owned trip/evidence/map structures | Explicit validated source-preserving export | TRAVEL-04/17, owner export consent | P2 /2–3 slices | Correct coordinates/timezones/escaping; preserve expiry/unknowns; no public sharing | File parsers and malformed inputs; desktop export | Existing Travel evidence; extension pending | QUEUED; inspect available export helpers first |
| TRAVEL2-005 — reserve/goal-aware affordability | Canonical baseline and Decimal trip allowances | Approved reserve/goal/scenario contract and explanations | FIN-05/06/07/15, FIN-CURRENCY | P1 /3 slices | Canonical reconciliation; no reserve double count or unapproved currency inference | Decimal edge/cutoff/owner tests; desktop explanation | Existing finance/Travel cost receipts; extension pending | BLOCKED_APPROVAL; obtain concrete contract decisions before implementation |
| INVEST2-001 — analyst/bull/bear/valuation/risk packet | Owned portfolio, AMFI/Yahoo evidence and local routing | Compatible pinned TradingAgents graph adapter and independent challenge | INV-04, AI-15/16, source/dependency/provider clearance | P2 /4–6 slices | Dated sourced arguments/unknowns; bounded tools; no private disclosure/orders | Isolated compatibility; point-in-time/leakage/cancel; desktop review | UPSTREAM_REFERENCE_MATRIX T pin; engine adoption pending | QUEUED; test component isolation, do not bulk-install conflicting dependencies |
| INVEST2-002 — watchlist thesis/decision versions | Holdings and local review alerts | Owned research/watchlist histories separate from positions | INV-01/07; non-monetary scope first | P2 /2–3 slices | Instrument identity, stale thesis detection and explicit decisions; zero holdings writes | API history/owner/freshness; Chrome reopen | Existing investment/alert evidence; extension pending | QUEUED; select independent non-monetary scope after higher priorities |
| WEALTH2-001 — fund look-through/overlap | Canonical portfolio and dated market evidence | Shared source-dated company/sector/country/currency exposure and opaque portions | INV-01/04, FIN-15, approved instrument/source policy | P2 /3–4 slices | Reconciled weights; unknown exposure explicit; no invented price/FX | Deterministic overlap/completeness/owner; desktop drill-down | Aurelio reference map; extension pending | QUEUED; inspect approved source availability |
| WEALTH2-002 — fingerprinted proposal cards | Existing reviewed-source and confirmation patterns | Shared stale-safe cross-module proposal confirmation | FIN-12, DOC-06, AI-12 | P2 /3 slices | Dependency changes reject stale proposal; only approved confirmation acts | Fingerprints/replay/owner/CSRF; Chrome correction | Canonical contracts map; extension pending | QUEUED; no financial write without approved contract |
| WEALTH2-003 — snapshot reconciliation | Canonical net worth, expenses, loans and investments | Dated institution/asset anchors, post-anchor events/dividend/recurring provenance | FIN-03/11/12/15, INV-01, currency policy | P1 /3–5 slices | Strict cutoff, transfer/null/dividend identity; no historical rewrite | Decimal cutoff/double-count/replay; desktop provenance | Finance baseline evidence; extension pending | BLOCKED_APPROVAL for monetary policy; prepare approved read-only scope |
| WEALTH2-004 — public analyst/private challenger | Existing owner/evidence/local routing boundaries | Distinct minimal public-research and confidential local-context packets | AI-04/12, DOC-06, consent policy | P2 /2–3 slices | Adversarial leakage/role/source/owner tests; no implicit cloud disclosure | Packet contracts/malicious sources; desktop consent | Integration architecture; extension pending | QUEUED; use local synthetic packets first |
| CORE (coordination) — canonical financial intelligence | Canonical Decimal baseline/projections and accepted FIN-05 | Reserve/goal/currency/snapshot contracts once approved; shared adapters | FIN-06/07/15, FIN-CURRENCY | P1 /contract-specific | One canonical arithmetic path; read-only scenarios never actual money | Existing financial baseline/money/reconciliation suites | Baseline ID receipts own acceptance | BLOCKED_APPROVAL for missing contracts; no duplicate finance engine |
| LOCAL (coordination) — Ollama intelligence | Existing local provider/registry, deadlines and evaluation | Genuine quality evidence and demonstrated bounded delegation, where useful | AI-15→16→12; authorized cohorts | P1 /evidence-dependent | Local default, bounded cancellation, source-grounded abstention; no invented calibration | Existing model/cohort/privacy/timeout suites; optional isolated synthetic smoke | AI-15/16 receipts; broad quality pending | PARTIAL; no model activation/promotion as a shortcut |
| DESKTOP/RELEASE (coordination) — integration and release | Django desktop UI, Chrome/Axe, release/privacy/native gates | Per-slice desktop acceptance and separately authorized cumulative release | Domain acceptance, reviews, CI, rollback, Pages authorization | P1 /per slice | Owner/session/CSRF, keyboard/pointer, source/financial/privacy regression; exact newest HEAD; explicit release approval | Focused backend/Chrome/Axe, JS, migration, privacy; package only when selected | PR16 and per-source receipts | ACTIVE validation; never treat development integration as deployment |

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
