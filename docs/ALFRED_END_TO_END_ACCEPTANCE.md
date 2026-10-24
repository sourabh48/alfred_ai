# ALFRED end-to-end product acceptance

Baseline: 3932f391aa4eed7b3200ad3b034f7991435e01e4, audited 2026-10-15. Current normal-account acceptance is PENDING. This plan does not authorize production actions, password changes, provider calls, data corrections or deployment.

Use the [feature matrix](PROJECT_STATUS.md), [provider register](ALFRED_EXTERNAL_INTEGRATIONS.md) and [roadmap](PROJECT_STATUS.md). Record PASS/FAIL/PENDING/NOT_RUN with date, exact source/package SHA, environment and observed evidence for each line. Synthetic and real results remain separate.

## Environments and approvals

| Environment | Allowed data/actions | Required evidence |
| --- | --- | --- |
| Isolated automated tests | Synthetic users, disposable SQLite/media/queues, mock providers | Exact labels/counts/failures/skips and redacted receipts |
| Packaged synthetic runtime | New package from exact SHA; isolated config/keys; loopback | Static/assets, browser screenshots, native lifecycle and restart |
| Clean second PC | Synthetic data, separate installed runtime | Install/upgrade/uninstall/sign-in/offline and preserved state |
| Normal live user | Existing account, normal sign-in; read-only UI unless action explicitly authorized | Actual observed screens, session/family visibility and canonical summaries |
| Real provider | Approved account, least privilege, capped synthetic requests | Actual contract/account scope, costs, authenticity/conflicts/retry/retention |
| Disaster recovery | Approved off-device archive plus separately recoverable protected key | Decrypt-and-restore on independent context, manifest, DB integrity/reconciliation |

Do not request a password in chat. If login fails, diagnose safe hash/backend behavior and offer the supported recovery workflow; credentials can change only after explicit authorization. Never create a replacement user to hide missing records.

## Normal-account checklist

All items are currently **PENDING**, regardless of historical HTTP 200 or synthetic Chrome success.

| Area | Operator action | Acceptance |
| --- | --- | --- |
| Login/logout/session | Sign in normally, idle warning, logout, browser-close behavior and revoked session | Correct account; no password disclosure or residual private page access |
| Dashboard | Compare income/outflow/obligations/cash/savings/net worth to trusted records | Canonical source values, clear measured/estimated/unavailable status |
| Expenses/Banking | Accounts, filters, statement history, transfer legs and corrections | Expected history; no duplicates or unexplained balance/fingerprint changes |
| Loans | EMI, principal, payment review, closure evidence and liabilities | Verified/inferred states distinguished; no phantom active EMI or double posting |
| Investments | Portfolio/current source values, projection assumptions and provenance | No stale quote displayed live or guaranteed return claim |
| Family | Relationships, directional sharing OFF unless explicitly opted in, revoke | No visibility without consent; relationships preserved |
| Travel | Saved plans, preferences, itinerary/map, provider unavailable/freshness labels | No invented availability; expected user history |
| Documents/media | Owned file access, correction/retry/delete state, foreign-ID rejection | No paths/raw diagnostic disclosure; correct permissions |
| Assistant/Ollama | Installed model status, grounded question, source cards, outage/retry/draft | No unsupported monetary prose or silent paid fallback |
| Memory | Save/review/correct/delete/reset/retention, restart retrieval | Encrypted owner-only store; no deleted-memory resurrection |
| Themes/mobile/accessibility | Light/dark, keyboard/focus/forms, 360px viewport, screen-reader statuses | Usable without clipped controls or color-only meaning |
| Provider settings | OpenAI and real sync OFF, clear consent/budget/config status | No keys in browser, synthetic success not presented as real provider |

Live delete/reset or financial corrections are not implied by an acceptance checklist. Demonstrate destructive controls in synthetic environments or obtain specific owner authorization.

## Deterministic finance gate

Seed an independent synthetic ledger through authenticated APIs, including rent, income, investment contributions, card/debt payments, transfer pairs, unclassified debits, multiple accounts and loans. Compare independently calculated Decimal expected values with baseline/loan/investment outputs.

Check zero/large/rounding/negative/invalid/nonfinite values; no accepted NaN/Infinity or overflow. Verify financial identities/fingerprints and ownership, partial-import account snapshot semantics, closure settlement components and no duplicate liability. For future currency schema, verify recorded codes, unknown history, same-currency totals and explicit FX date/rate/provenance; never reinterpret legacy data silently.

For migrations: snapshot/rehearse forward, replay/idempotence and supported reverse; schema rollback is blocked where writes make it unsafe. Use protected disposable copies, never destructive test migrations on the live DB.

## AI/document/model gate

- Verify local model/digest, vectors, limits, inference outage, no cloud model metadata and offline startup.
- Save owner-verified synthetic facts with provenance/sensitivity; retrieve in a fresh session/restart; validate relevance, abstention, dedupe, corrections, conflicts, expiry/reset/tombstones/checkpoints.
- Prove other owner/family accounts cannot retrieve personal memory or source documents.
- Verify direct media access in source/debug as well as native profiles. Baseline
  source DEBUG routing served a synthetic file anonymously; native owner handling
  must be reused before attaching private files to that profile.
- Finance tool results remain canonical, with structurally controlled values/currency; contradictory model prose is suppressed.
- Current document scope is verified closure fields and owned memories. Test stale/deleted/conflicting evidence, citations, injection and missing-evidence abstention. Broader Q&A requires a separate ingestion/evidence acceptance corpus.
- Persistent chat history is NOT_IMPLEMENTED at baseline; do not infer it from TravelMessage or a screenshot.
- For trained predictions, require sufficient genuine consenting labels, chronological holdout, leakage checks, baselines, confidence calibration, freshness and drift. A registry flag or fallback score does not prove accuracy.

## Provider acceptance

OpenAI/S3 real activation is currently **BLOCKED_APPROVAL**. Rail/bureau/live inventory can also require contracts. Use the register to distinguish each.

OpenAI tests require current approved model/prices, public synthetic query, exact request/response validation, measured tokens/reservations/caps, timeout/error redaction and no automatic paid retry. Private memory/financial uploads remain forbidden.

S3 tests require dedicated private account/bucket/prefix, owner headers/IAM/private ownership/SSE and authenticated ciphertext, startup/periodic/shutdown/offline retry, lost acknowledgements/partial download, corruption/version/owner mismatch, concurrent updates, tombstones/pruning and trusted checkpoint restoration. No raw DB/WAL/SHM sync.

Travel acceptance requires approved endpoints/keys/contracts, actual freshness/expiry, live-vs-cached-vs-estimated labels, provider budgets and rights. Validate bike restrictions separately; a car route or research result is not verified road legality, booking availability or permits.

## Native and release gate

Build a fresh package from pinned candidate SHA using existing package tooling; verify manifest/artifact hashes and scan contents for private DBs, keys, media and operator config. Test launcher/tray/server/worker/scheduler, static/offline fonts, login/CSRF, UI routes/themes/mobile, model-outage and restart persistence.

On a clean PC: install, launch, restart/sign-in, approved upgrade preserving private state, uninstall preserving documented data, repair/reinstall and offline prerequisites. No reuse of old build evidence for a changed source.

M20 must reject candidate substitution, dirty/diverged sources, ignored operator collisions, unexpected migrations/dependencies, credential exposure, missing/failed backup, financial changes and absent/scoped/stale approval. Historical M15 recovery waiver cannot silently apply.

M21 must execute a disposable end-to-end promotion, interruption/fault recovery and authorized rollback. Source-only rollback never blindly restores a stale DB over later writes; preserve evidence and schema compatibility.

## Recovery gate

Four statuses must remain distinct:

1. LOCAL_BACKUP_VERIFIED: consistent approved backup, authenticated decryption and independent disposable restore, file manifest/inventory, SQLite integrity/FK and canonical reconciliation.
2. OFF_DEVICE_COPY_VERIFIED: verified copied volumes/files/hashes from the actual destination.
3. PORTABLE_KEY_VERIFIED: genuinely usable without the old Windows profile; key retained separately and protected.
4. INDEPENDENT_DEVICE_LOSS_RESTORE_VERIFIED: complete decryption/restoration with off-device material in independent context.

A DPAPI blob copy does not establish stage 3. Hashes alone do not establish stage 1 or 4. Current HDD copy is user reported and stage 3/4 remain unverified under the release-specific M15 waiver. Do not restart cancelled sealing dialogs, export plaintext keys, delete old backups or invent storage destinations.

## Evidence receipt and completion

Each receipt contains release identifier/SHA, environment, data classification, exact test/check, result/count/skips, safe artifact hashes/paths, observed limitation and operator/approval scope. Never include credentials, private financial figures or raw exception/document text in a public report.

FULL ALFRED PRODUCT COMPLETE requires every confirmed in-scope feature's technical and applicable real acceptance, no unexplained financial/privacy issue, accepted recovery/package/release process and explicit decisions for optional/unknown requirements. Open providers/AI hypotheses/heuristics remain labelled honestly.

Current completion decision: **NOT COMPLETE**. No new real-account, real-provider, clean-PC, installer or device-loss PASS is claimed by this audit.
