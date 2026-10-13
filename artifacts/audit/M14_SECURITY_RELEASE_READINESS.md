# M14 security release readiness - 2026-10-11

Stable integration update: local master merged frozen 6050234 at ffe2b7c and
added the native source-worker cwd regression correction at d84a5e5. Actual
updated source gate: 357 backend / 12 Chrome / 19 native checks passed, zero
failures/skips. A fresh DPAPI-restored private snapshot proves exactly family.0004
pending, forward/rollback/replay and finance/family hash reconciliation PASS.
Final integrated HEAD is recorded in the external stable-integration manifest;
following documentation changes do not change the tested application tree.
Live promotion remains AWAITING APPROVAL; no installed source/database/config/
token/service change. Current-user encrypted backup and source restore verified;
M15 remains isolated. See the updated existing controlled promotion plan.

M14 DEVELOPMENT = COMPLETE
M14 RELEASE READY = YES
FINAL M14 INTEGRATION = PASS
LIVE SOURCE MODIFIED = NO
LIVE DATABASE MODIFIED = NO

This is the local/native M14 source release candidate. Live promotion, private
migration, token rotation and real-account acceptance require separate explicit
authorization. No broad audit or completed M14D/E/F/G/H redo was performed.

Validated source/test candidate: 495a184c7a44bfe169978f8e0c018f8a286fb208.
Stable source (Git-only verification): a9d096ea55839269fe6fce14d4f11ea2cbf05336.
The following evidence-only commit freezes HEAD on release/m14-20261011. Exact
final HEAD/full range are in F:/ALFRED_DEV/isolated-tests/m14-promotion-manifest.json.
All application/test changes were committed before the gate; the freeze commit
changes documentation only. M15 is isolated from this release candidate.

## Retained blockers resolved or explicitly deferred

Four retained issue groups were found in the previous authoritative report:

| Item | Final disposition | Evidence |
| --- | --- | --- |
| Other outbound HTTP callers | RESOLVED | 7bb5086: twelve Investment/Verified Intelligence adapters reuse pinned public HTTPS, no redirects, public-only DNS, streamed caps and MIME/timeouts; safe class/reference failures. Six new regressions; related 41 passed. |
| Raw document retention | DEFERRED | Protected local owner vault and extraction-only option; native private-media/retained-review tests and release configuration pass. No historical purge. Concrete M15 vault/privacy and Travel T09 follow-ups with risk, mitigation, owner and required evidence. |
| Email token fallback re-encryption | RESOLVED in source | 64d21f3: count-only dry-run and atomic verified apply, primary-only re-read, mixed keys/legacy/nulls, rollback/conflicts/idempotence, no secret output. Seven new tests; related 18 passed. No live rotation/key removal. |
| Login/expensive-endpoint abuse | RESOLVED | cf799d4: shared atomic persistent reservations, username/IP/account/global budgets, all login paths/signup/API/processing, 429/Retry-After before writes, safe fail-closed 503. Existing Family budgets/auth/CSRF/M14E limits retained. Twelve new tests; related 55 and Chrome 2 passed. |

family.0004 consent reset was already resolved in development; forward/rollback/
replay rehearsals pass again in the final gate. It is an authorized-promotion
prerequisite, not an unresolved source blocker. No release-blocking item remains.
Full classification and all required deferral fields are recorded in
[M14_RETAINED_BLOCKER_DISPOSITIONS.md](M14_RETAINED_BLOCKER_DISPOSITIONS.md).
Retention proof is committed separately at 495a184.

## Actual updated combined gate

On candidate 495a184, one combined backend run: **356 passed, 0 failures, 0 skips,
354.594 seconds**. One combined Chrome run: **12 passed, 0 failures, 0 skips,
138.356 seconds** (runner 148.546 s); driver_backed_success=true.
These are actual new results, not sums of the earlier overlapping gates.

Coverage: passwords, session-only API authentication/CSRF; Career/Family Growth
safe errors; Family opt-in/revocation and consent migration; invitations and
shared reservation threads/processes; M14E streamed/parser/native limits; M14F
current/historical loan diagnostics, persistence/log filtering; loan/import/
payoff/serializer/financial identity compatibility; all retained blocker fixes;
retention source deletion, retries/manual correction and native owner-only media.
Chrome covers the prior ten affected workflows plus login-limit recovery and
Investment compatibility. All fixtures/databases/media/limiter data are synthetic.

Native configuration proof PASS: DEBUG=false, authenticated private media,
explicit source deletion option, session auth/CSRF, positive limits, absolute
persistent protection directories. Django checks PASS; isolated native migration
check reports no changes. AST-only graph update PASS: 7892 nodes / 20678 edges.
No migration/dependency created by these blocker fixes; source comparison adds
only the previously tested family.0004 relative to stable. No live migration
table/private database/config/tokens/keys/backups were read or modified.

Evidence under F:/ALFRED_DEV/isolated-tests:
- m14-blockers-combined-backend.log
- m14-blockers-combined-browser.log
- m14-blockers-chrome/browser_regression_summary.json
- m14-native-config-proof-final.log
- m14-blockers-final-graph.log
- m14-http-before.log / m14-http-after.log
- m14-token-focused.log / m14-token-integration.log
- m14-abuse-before.log / m14-abuse-focused-final.log / m14-abuse-related-final.log
- m14-abuse-fixture-recheck.log / m14-blockers-chrome-verified.log

Initial synthetic fixture failures were corrected and their logs preserved;
zero unresolved failure remains. Earlier 297/10 M14F baseline is preserved in
Git history and prior evidence. No full-repository/installer/clean-PC or live
provider/real-account acceptance is claimed by this security source gate.

## Frozen promotion and M15

[Controlled promotion plan](M14_CONTROLLED_PROMOTION_PLAN.md) includes exact
source range/final HEAD, source and protected DB/config/media backups, fresh-copy
migration rehearsal, historical sharing OFF impact, verified token rotation,
configuration/privacy checks, rollback, runtime smoke and real-account acceptance.
No promotion, private migration, token mutation or key retirement was performed.

M15 DEVELOPMENT READY = YES. Start ALFRED Persistent Intelligence & Memory Engine
on codex/m15-persistent-memory-20261011 in F:/ALFRED_DEV/m15, from the frozen M14
HEAD. First local vertical slice only: verified structured memory/provenance/
sensitivity, local Ollama embedding, semantic retrieval in a fresh session,
owner isolation, append-only encrypted event, restart/restore/retrieve.
Cloud reasoning stays optional/privacy-gated; no cloud sync or broad autonomous
learning until the local slice is stable. Frozen M14 receives no M15 commits.
