# M14 security release readiness - 2026-10-08

Status: M14E source COMPLETE; broad security release NOT READY; no live release authorized.
Validated implementation: `8cecd65748d333f7487bf008a835854a4ac10e50`.
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

Release blockers remain:

- M14F: loan upload fallback stores and returns raw exception text;
  `LoanPDFParser.parse_document` prints it; `LoanImportDocumentSerializer`
  exposes stored payload diagnostics. New cleanup diagnostics are already
  hardened; historical diagnostic filtering and other producers remain open.
- Other reported direct HTTP callers have not yet been verified after the
  completed Career SSRF fix. Do not treat them as cleared.
- Raw document-retention policy and integration-token fallback re-encryption
  remain separate unresolved security items. Signing-key rotation is complete.
- Global login/other expensive-endpoint abuse limits remain outside the
  completed M14D account-scoped Family invitation milestone.
- M14G's consent-reset migration is tested development source, not a live
  permission to change private records. Any eventual promotion needs separate
  migration-plan, fresh-backup and reconciliation review plus authorization.

Next smallest task: hosted M14F loan-upload diagnostics and public historical
payload filtering. Preserve usable review uploads, record ownership, successful
imports and loan-liability confirmation. Do not rewrite historical live data.
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
