# M14 security release readiness - 2026-10-11

Status: M14E and M14F source COMPLETE; broad security release NOT READY;
no live release authorized. FINAL requested M14 regression integration PASS.
M14F implementation: `895ce13ee86bf5fddbd1332f5326389b7a3b7c5c`.
M14E implementation: `8cecd65748d333f7487bf008a835854a4ac10e50`.
Live source remains `a9d096ea55839269fe6fce14d4f11ea2cbf05336`.
The private database has not been accessed or changed by this development work.
Recovery and restoration assets remain preserved.

M14E adds shared streamed multipart limits, native transport caps, bounded local
document extraction, temporary-storage checks/cleanup, and safe resource errors.
It creates no Django migration or dependency. See
[upload configuration](../../docs/UPLOAD_RESOURCE_LIMITS.md) for defaults,
endpoint coverage, transport framing, Windows limits and platform caveats.

Final gate: **198 backend tests passed, 0 failures/skips**, including **31 M14E
regressions** (243.503 seconds). **3 Chrome workflows passed, 0 skips**
(55.666 seconds); driver-backed summary confirms success. Django system checks
passed; isolated `makemigrations --check --dry-run` reported no changes.
AST-only graph update passed (7,760 nodes / 20,264 edges).

Evidence is preserved outside source in `F:\ALFRED_DEV\isolated-tests`:
`m14e-release-gate.log`, `m14e-release-chrome.log`,
`m14e-release-chrome/browser_regression_summary.json`,
`m14e-migration-drift.log`, and `m14e-final-graphify.log`.

The final gate combines upload/resource, statement/financial identity, retries,
uploader compatibility, Family permissions/invitation concurrency/errors,
authentication/password/CSRF, Career HTTP and cleanup-redaction regressions.
Chrome uses only synthetic local fixtures and isolated database/media storage;
the new PDF reimport workflow compares fingerprints, references, amounts and
account balances after both imports. Historical live reconciliation is not
repeated or claimed as a new result.

M14F now protects loan import/payoff errors, historical import/closure serializers,
review/resolve/retry responses, loan operational-log responses, nested settlement
diagnostics and cached foreclosure watchlists. New parser failures retain only
safe messages/codes/references; logs retain class/reference/stage without
exception text. New loan cleanup metadata is filtered before persistence.
Historical forensic data and document files are not rewritten. Normal owned loan
fields, statuses, links, corrections, settlement amounts and balances remain.
No M14F migration, dependency, monetary calculation or ownership change.
See [loan diagnostic boundary](../../docs/LOAN_DIAGNOSTIC_PRIVACY.md).

M14F validation: 19 focused regressions pass; final focused cleanup/retry gate
36 passed, 0 failures/skips, 19.551 seconds. Affected backend gate: 192 passed,
0 failures/skips, 112.330 seconds (before the final cleanup-metadata filter,
covered by the final 36 and combined gate). Chrome: 4 passed, 0 skipped,
51.461 seconds; driver-backed success true. System checks and migration drift
pass. AST-only update: 7,804 nodes / 20,474 edges, no API/semantic extraction.

Remaining reported release issues (not cleared by this scoped M14F work):

2026-10-11 scoped follow-up: dispositions are now authoritative in
[M14_RETAINED_BLOCKER_DISPOSITIONS.md](M14_RETAINED_BLOCKER_DISPOSITIONS.md).
Other HTTP adapters are resolved (41 passing tests); token rotation and global
abuse protection remain release-blocking until their own gates. Raw local-vault
and Travel telemetry retention are explicitly deferred with configuration and
ownership safeguards, evidence requirements and concrete follow-up milestones.
The older list below records the state at M14F completion.

- Other reported direct HTTP callers have not yet been verified after the
  completed Career SSRF fix. Do not treat them as cleared.
- Raw document-retention policy and integration-token fallback re-encryption
  remain separate unresolved security items. Signing-key rotation is complete.
- Global login/other expensive-endpoint abuse limits remain outside the
  completed M14D account-scoped Family invitation milestone.
- M14G's consent-reset migration is tested development source, not a live
  permission to change private records. Any eventual promotion needs separate
  migration-plan, fresh-backup and reconciliation review plus authorization.

The user's current checkpoint names M14F as the remaining verified blocker;
the previous readiness report also carries the separate reported issues above.
This work resolves M14F without declaring those unverified entries safe. Their
release scope must be explicitly resolved or deferred before broad readiness
can be YES. Completed M14 milestones are not reopened and no broad audit ran.
FINAL combined gate on application HEAD 895ce13:
**297 backend tests passed, 0 failures/skips, 243.888 seconds**, including all
**19 M14F** and **31 M14E** regressions and both family.0004 forward/rollback/replay
rehearsal methods. **10 Chrome workflows passed, 0 failures/skips, 113.447
seconds**; driver_backed_success=true (runner elapsed 124.453 seconds).
This is an actual single combined backend run and a single combined browser run;
earlier overlapping totals are not added. No full repository suite was run.

Backend coverage: Loan/import/payoff/serializer compatibility, password validation,
session-only API auth and CSRF, Career exception disclosure and pinned HTTPS,
Family directional financial opt-in/revocation/Growth exceptions, invitation
synchronized thread/process throttles, streamed multipart/native/parser resource
limits, cleanup/retry integrity, document extraction/uploader/statement identity.
Chrome covers the four Loan workflows, three Family workflows and three shared
upload/login/import workflows. All SQLite/media/limiter data are synthetic and
isolated. The migration rehearsal does not apply anything to the live database.
System/config checks and migration-drift checks PASS; no model changes detected.

Evidence: F:\ALFRED_DEV\isolated-tests\m14-final-backend.log,
m14-final-chrome.log, m14-final-chrome/browser_regression_summary.json,
m14f-system-check.log, m14f-drift-check.log and m14f-graphify-complete.log.
M14F/combined source is committed separately from this final evidence update.

Promotion is prepared only in [the hold plan](M14_CONTROLLED_PROMOTION_PLAN.md).
Source comparison adds only `family.0004_financial_sharing_opt_in`; M14F adds
no migration. No live migration table/private database was read. The plan
requires a fresh verified backup, consent-impact rehearsal, explicit live
authorization, rollback and real-account acceptance. No promotion performed.

Next action: resolve the retained release scope. No scope response was received
while the requested gates ran, so the previous reported blockers remain.
M14 DEVELOPMENT is not marked COMPLETE until release readiness is PASS; M15
has not started. The named completed M14 milestones and M14F are COMPLETE.
Do not rewrite historical live data or start M15 before readiness is PASS.
Travel T09 remains behind these P0 issues. Historical Docker classification is
deferred recovery housekeeping and does not block development.

Local Ollama Codex was attempted for a static configuration-only documentation
draft, in an empty read-only working directory. The local service was unavailable;
the owned stalled CLI was stopped. No private data, credentials or runtime DB
were provided. Hosted Codex completed source/security work and operator docs;
no successful local documentation result is claimed. Local Ollama availability
should be checked before the next routine-model task.

A broad security release is not ready until verified blockers are resolved.
Do not deploy or apply migrations without explicit authorization. Do not delete
recovery databases, backups, private repositories or historical Docker assets.
