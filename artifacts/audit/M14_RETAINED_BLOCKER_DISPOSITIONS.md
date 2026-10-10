# M14 retained blockers: scoped resolution

Authoritative scope: M14_SECURITY_RELEASE_READINESS.md at development HEAD
97c06fada2572c7c4c08f383abd6a124173dadc3. No new broad audit.

| Retained item | Classification | Concrete boundary |
| --- | --- | --- |
| Other direct HTTP callers | RELEASE-BLOCKING | Investment AMFI/news and Verified Intelligence provider adapters bypassed pinned public HTTPS, redirect and response limits. Reuse public_http; focused reproduction and compatibility gate required. |
| Raw upload retention | DEFERRABLE subject to release configuration | Local source documents support review/retry and forensic recovery. Existing extraction-only deletion is configurable; production/native configuration requests it. No historical deletion is authorized. Details below. |
| Integration token fallback re-encryption | RELEASE-BLOCKING | EmailConnection OAuth access/refresh values use MultiFernet with SECRET_KEY_FALLBACKS; fallback reads alone do not permit verified old-key retirement. Add dry-run/transactional verified rotation; no live token writes. |
| Global login / expensive-endpoint limits | RELEASE-BLOCKING | Family invitation quotas cover only that operation. Protect all login entry points and authenticated expensive operations with the existing atomic diskcache pattern; preserve auth/CSRF and per-account isolation. |
| family.0004 consent reset | ALREADY RESOLVED in development | Forward/rollback/replay tests passed in the combined 297 gate. Deployment still requires fresh backup, disposable rehearsal, consent reconciliation and explicit authorization. This is a promotion prerequisite, not an unresolved source flaw. |

## Explicit retention deferral

ISSUE: Raw-document lifetime in the owner's local vault is not time bounded;
TravelProviderRequest telemetry also has no bounded retention job.

CURRENT RISK: Host disk growth and more sensitive material recoverable by an
attacker who already controls the owner's machine/backups. Retained sources may
be needed for pending review/retry. Extracted financial records remain canonical.

EXISTING MITIGATION: Extraction-only deletion is available for all seven source
families through ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION; native and local
environment examples set true. Private native media is ownership checked. Release
configuration must use DEBUG=false and native private media, without an external
public media server. M14E bounds each upload and parser; normal API ownership and
CSRF remain enforced. Recovery backups are protected and preserved.

WHY IT DOES NOT BLOCK M14: An automatic historical purge would destroy retry or
forensic evidence without addressing a new API authorization flaw. The local/LAN
release has an extraction-only option and authenticated native source access;
it introduces no cloud document storage. The protected vault remains an owner
decision. Default/debug configuration is not approved for a LAN release.

FOLLOW-UP MILESTONE: M15 cloud synchronization hardening: explicit per-owner
retention/vault policy and encryption before any document synchronization.
Travel T09: configurable telemetry cleanup preserving current-month quotas,
active requests and evidence/history. Do not implement the whole T09 now.

OWNER: ALFRED maintainer (Codex implementation; Sourabh release acceptance).

REQUIRED TEST/EVIDENCE: Extraction-only cleanup across source families, missing
source retry/manual-correction preservation, ownership-checked native media;
promotion config validation. Before retention cleanup: deterministic dry-run,
active/review exclusions, restart/idempotence tests and quota preservation.

## HTTP resolution

Twelve remaining adapter methods now use the existing pinned public HTTPS
transport. GET query parameters, JSON/RSS/text/HTML parsing and stale/circuit
fallbacks remain; redirects, private DNS destinations, compression, wrong MIME,
timeouts and streamed response limits are enforced centrally. AMFI latest/history
caps are 8/16 MB; HTML and RSS caps are 2 MB; JSON retains the shared 4 MB cap.
New provider failures store/log only a safe message and reference/class.

Evidence: m14-http-before.log reproduces the bypass without external requests;
m14-http-after.log: 41 tests passed, 0 failures/skips, 11.585 seconds, including
6 new regressions plus existing transport, Career and advisory/integration tests.
No dependency, schema, financial calculation or live data change.

## Token re-encryption resolution

HTTP implementation commit: 7bb5086ac1046382f4abb84fc0e6c1ad647304b7.
Email OAuth tokens remain encrypted under the existing key derivation. The new
reencrypt_email_tokens command defaults to count-only dry-run; --apply verifies
all values under primary-only decryption within one atomic transaction. Fallback
reads remain until independently authorized verification/retirement. Invalid
tokens, verification errors and concurrent write conflicts roll back all writes;
current-primary values and repeated runs remain unchanged. No secret output,
new dependency, schema migration or live rotation. Operator procedure:
[EMAIL_TOKEN_ROTATION.md](../../docs/EMAIL_TOKEN_ROTATION.md).
Seven focused tests passed (0.041 s); related security gate: 18 passed,
0 failures/skips, 11.529 s (m14-token-focused.log, m14-token-integration.log).
The source workflow blocker is resolved; applying it to private tokens remains
an explicitly authorized promotion operation, with keys/backups retained.

## Abuse-limit resolution

Token implementation commit: 64d21f37607b1a765c0ea7ca746216c3cb014c69.
Shared atomic non-evicting diskcache reservations now protect all login entry
points, signup, authenticated APIs and expensive operations, with independent
account/IP and global quotas. Existing invitation scopes/budgets remain intact;
no duplicate invitation throttle. Rejection precedes view execution, returns
429/Retry-After, and makes no application mutation. Store failures fail closed
503 with safe class/reference logging. Authentication/ownership/CSRF and M14E
resource limits remain independent. See [ABUSE_PROTECTION.md](../../docs/ABUSE_PROTECTION.md).
The pre-fix login regression failed across all three entry points. Final focused
12 tests passed (12.335 s); related security gate 55 passed, 0 failures/skips,
79.462 s. Chrome login recovery and Investment compatibility: 2 passed,
0 failures/skips, 16.940 s, driver-backed success true. Initial fixture failures
and corrected logs remain in isolated-tests; no unresolved failure remains.
No migration, dependency, live source/database/config/key change. Final combined
M14 gate is still required before marking development complete.
