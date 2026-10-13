# M15 consolidated release candidate

Dedicated worktree: F:/ALFRED_DEV/m15-integrated.
Branch: release/m15-integrated-20261014, created at actual stable M14
30e0b3f75e785f639897ad36c19090c6a4e8675f, then fast-forwarded to the complete
75b6f50b4cb8561b2e1423d02516d8176f512316 UI candidate. No cherry-picks, source
conflicts, duplicate merges or feature exclusions were needed. Frozen original
03ab0ae, hardening 081e30e and UI 75b6f50 branches remain unchanged.

Ancestry checks prove stable M14, original hybrid, trusted checkpoint 14ab9de,
hardening 081e30e and previous packaged source 5596635 are all incorporated.
The UI source/portable archive SHA-256 values match their trusted manifests.
5596635 and 75b6f50 have identical application/static/packaging/dependency trees;
they differ in documentation and a native test assertion. Those older binaries
and counts are historical evidence only. This candidate receives a new build
and actual combined gate in its own worktree.

## Integration coverage matrix

| Retained capability | Implementation / focused gate |
| --- | --- |
| M14 passwords, session-only authentication, CSRF | test_password_security, test_api_session_security, test_auth_pages |
| Directional Family consent, ownership, invitation concurrency | test_family_account_links, test_family_consent_migration, test_family_invitation_atomic/throttling, test_family_api_errors |
| Upload/resource limits, safe parsing/diagnostics, deduplication | test_upload_limits, test_loan_diagnostics, test_document_retry_integrity, test_expense_money_identity |
| Pinned safe HTTPS, timeout/destination guards, abuse budgets | test_travel_http, test_remaining_public_http, test_career_job_http, test_global_abuse_limits |
| Retention and token rotation safeguards | test_upload_privacy_retention, test_retention_release_boundary, test_token_rotation; live rotation remains excluded |
| Canonical financial Decimal calculations and legacy APIs | test_financial_baseline_alignment, test_expense_money_runtime, test_loan_money_runtime/related_money_runtime/foreclosure_money/money_field, test_investment_money |
| Local Ollama embedding, inference, relevance and abstention | test_persistent_memory, test_hybrid_intelligence; real local packaged --memory drill |
| Encrypted indexes, keys, journal, owner isolation, revocation | test_memory_privacy, test_memory_checkpoint, test_memory_sync, test_user_data_reset |
| Learning, deduplication, verified facts versus hypotheses, corrections/conflicts | test_memory_learning, test_hybrid_intelligence, test_intelligence_ui |
| Encrypted S3-compatible adapter, immutable snapshots, retries, deletion propagation | test_memory_cloud, test_memory_sync_runtime, test_memory_sync; synthetic providers only |
| Optional OpenAI consent, privacy and budget limits | test_memory_reasoning, test_hybrid_intelligence; real access disabled |
| Conversation, citations and bounded document grounding | test_document_grounding_acceptance, test_intelligence_ui; owner memories and verified loan closure evidence only |
| Financial narrative suppression and exact source cards | test_intelligence_currency; currencies absent in records remain NOT RECORDED |
| UI-A/B/C/D/E, memory management, Finance/Banking, Loans, Investments and Travel | 14 scoped development Chrome workflows and fresh packaged browser checks |
| Windows workers, scheduler, start/stop, status replacement retry and persistence | test_native_runtime/launcher/tray/observation; fresh executable and launcher drills |

No completed feature is missing from the integrated source. Saved conversation
history, comprehensive financial-document ingestion and explicit currency storage
were never part of the validated implementation. Currency persistence remains a
separately scoped schema follow-up. Legacy screens retain their documented INR
convention; AI source cards preserve canonical Decimal strings without inventing
currency metadata. No canonical balances, transactions or loans are modified.

New acceptance checks use an absent local model in the disposable packaged
runtime, without stopping the installed Ollama service or enabling cloud access.
They verify safe 503, visible outage, unchanged draft/retry and no cloud usage.
Travel screenshots wait for loaded plans and completed entrance animation.

The first combined backend gate passed 619 tests (509.525s). The first 14-workflow
Chrome gate passed 13 and timed out at Travel's next itinerary action. Evidence and
the first d518c54 package are preserved. A deterministic delayed-response regression
reproduced enabled suggestion buttons while the preceding action was still busy.
Those controls now stay disabled through response/list rendering, are re-enabled on
success/failure, and the browser waits for enabled controls. The new regression and
original saved-trip/mobile workflow both pass (2 tests, 24.241s). The corrected
source must receive the final combined gate and a second, fresh package; the first
package is not promotable.

## Gate and immutable evidence

Initial state: validation IN PROGRESS. Do not reuse 308/14/32 as new proof.
Run all selected M14/M15/financial suites once, plus development Chrome, native
configuration/system/migration checks and a new package from this branch's
committed source. Actual counts, build/review SHAs, hashes and evidence are recorded
below after the gate and in the external integrated-release manifest.

Corrected source 13ca4b4 final backend: 619 PASS, 470.416s. Development Chrome:
15 PASS, 173.812s; no failures/skips. System/native configuration/drift PASS.
Fresh r2 bundle: 10,895 inspected files; changed assets match and no private paths.
Initial packaged drill reached 13 checks, then its rapid scripted request burst
correctly hit the production per-account 429 limit during memory correction;
the visible draft was preserved. Positive --memory fixtures now explicitly use
bounded account budgets (512 API / 64 expensive), isolated to the synthetic test
process/data directory. Production settings and the 619-test limiter regressions
remain unchanged. This is not a rate-limit bypass in application source.
The launcher completed its own proof and stopped cleanly, but failed to write
the summary because this fresh worktree lacked artifacts/ops. The house verifier
now creates the parent directory. A new native/launcher run is required before
claiming packaged acceptance. The native drill also verifies grounded local
reasoning after recovery from the deliberately missing model, with cloud disabled.
These post-build changes affect host acceptance scripts only, not packaged runtime.
Keep first-run logs/proofs/screenshots; never add partial checks to the final count.

## Recovery and main-folder promotion boundary

Live master remains 30e0b3f75e785f639897ad36c19090c6a4e8675f. Its operator edits
in the continuation/promotion documents and skills-lock.json, and untracked
deployment/restoration reports, remain untouched. origin/master was refreshed
and equals this M14 SHA; ordinary fast-forward ancestry to M15 passes. Source
push and live deployment remain separate, explicitly unauthorized operations.

The existing Desktop VERIFY_TRANSFER.ps1 passed staged material count, size and
SHA-256 checks. It has 15 entries, nine archive entries, zero key entries; -KeyPath
therefore cannot establish independent key recovery. It performs no archive
authentication/decryption, restoration, SQLite check, external-device test or
manifest authenticity check. Existing post-M14 receipts prove 9,694 protected
files and three independently transaction-consistent SQLite snapshots restored
on this device, with integrity/foreign keys PASS. They explicitly do not prove
cross-database quiescence or an independently retained key after profile loss.

Independent off-device archive AND separate recovery key restore remains PENDING.
Cancelled passphrase/sealing dialogs stay cancelled. Preserve all recovery
material; do not weaken encryption, regenerate/export keys or upload private data.
See docs/M15_RECOVERY_ACCEPTANCE.md for the existing simple manual alternative:
a specifically approved existing password manager or protected offline key device,
separate from approved archive storage, followed by an independent disposable
restore. No destination or export is invented by this preparation.

This missing recovery proof BLOCKS live promotion. Local source consolidation
and packaged validation proceed safely; approval will be requested only after
mandatory recovery/acceptance gates are satisfied. This is not deployment consent.

Read-only current-runtime observation: port 8000 is a loopback Django runserver
process, with no native health route. The recorded native supervisor and worker
PIDs have exited; runtime.json is historical. The exact owning runserver console,
working directory/data configuration and any independent writers must be confirmed
before promotion. Do not infer a healthy current native worker from stale state.
No live process was stopped, restarted, reconfigured or modified during preparation.

## Controlled deployment procedure to execute only after explicit approval

1. Pin the final integrated release SHA, verify clean integrated source and current
   stable/remote ancestry, review the tracked privacy-safe diff, and preserve frozen
   M14/M15 archives. Stop on any new stable or remote commit; never force/reset it.
2. Preserve operator tracked patches and untracked files in the encrypted recovery
   inventory. Only the known colliding tracked documents may be temporarily restored
   to their M14 versions after backup/approval to permit fast-forward; reapply and
   review the operator changes afterward. Never blanket reset, clean or stash private
   untracked files. Do not overwrite config, encryption keys, media, models or jobs.
3. Establish a closed maintenance window. Identify the ACTUAL runserver owner and
   gracefully stop its owning console (Ctrl+C or its operator Stop control), including
   autoreloader parents and any independent workers/writers. Require port 8000 closed;
   the native stop command alone cannot stop this current development server. For an
   actual native instance use the configured SDK and alfred_native.py stop --data-dir
   F:/ALFRED/restored-runtime from the stable folder. Verify all matching writers exit;
   do not blanket-kill processes. Preserve pending work and limiter histories.
4. Create a NEW F:/ALFRED_BACKUPS/m15-prepromotion-<timestamp> recovery set. Capture
   each SQLite database using SQLite's backup API after quiescence (application,
   jobs and durable cache), not copies of active SQLite/WAL/SHM files. Inventory
   durable config/keys/media/models/jobs/protection state and source/operator patches.
   Encrypt using the approved existing portable scheme without rotating its key.
   Keep all older backups. Authenticate, hash, restore into a separate disposable
   directory, verify all inventory entries, SQLite integrity/FKs, finance/family
   reconciliation and pending-job recovery. Require the independent archive/key
   restoration evidence as well; the 12 October snapshot is not a fresh backup.
5. Ordinary source fast-forward to the exact integrated SHA only. Dependency diff
   and added migration diff are empty. M13C/M13D and family.0004 remain intact;
   family.0004 is already applied and must NOT be replayed or change current consent.
   On a disposable fresh private-copy rehearsal, require an empty migration plan;
   any unexpected pending migration stops promotion. No live token re-encryption.
6. Preserve native.env/local.env and keys. Keep ALFRED_MEMORY_CLOUD_AUTHORIZED=false,
   ALFRED_MEMORY_OPENAI_AUTHORIZED=false, ALFRED_MEMORY_SYNC_PROVIDER empty and
   ALFRED_MEMORY_MOCK_REASONING=false. Local models all-minilm:latest and qwen3.5:4b
   provide embedding/inference; unavailable models show safe outage with no automatic
   cloud fallback. New encrypted memory lives under the selected runtime data folder.
7. If the actual launch entry uses a packaged executable, back up its entire bundle
   and replace it with the verified integrated bundle only after authorization.
   Updating Git alone does not update an existing executable. A source-based native
   launch uses the existing SDK and exact stable-folder source. Retain the M14 bundle.
8. Run system/native configuration and read-only migration checks in the approved
   runtime environment. Reconcile finance/family counts and monetary hashes locally;
   do not put private values in Git or diagnostics. Restart only when these pass:
   alfred_native.py start --data-dir F:/ALFRED/restored-runtime --no-browser.
   Check native HTTP/worker/scheduler health, imports/documents and session/CSRF.
9. Normal real-account browser acceptance: Dashboard totals, Expenses/Banking,
   Investments, Loans/EMI, Family relationships/consent, Travel history/plans,
   retained documents, assistant/source cards, memory correction/deletion, local
   model availability, cloud-disabled settings and logout/restart. User signs in
   normally; do not request passwords or create replacement accounts. Keep network
   access closed until acceptance; estimate 15-30 minutes with rehearsal complete,
   extending the window if backup/reconciliation takes longer.
10. Any unexplained failure: stop writers, preserve diagnostics and ALL post-backup
    writes, restore the exact M14 source/bundle/config from the verified recovery
    set into a separate recovery location before replacement. M15 adds no database
    migration, so compatible data can usually remain. If data restore is necessary,
    require verified reconciliation and do not discard later accepted writes.
    Preserve M15 vault/journal/revocations/checkpoints/keys even on M14 source rollback;
    do not revive deleted memories or financial sharing. Recheck native health before
    reopening access. Source rollback alone does not recover encryption keys.

GitHub: after separate explicit authorization and a fresh origin/master ancestry
check, use an ordinary pinned-SHA push to refs/heads/master and independently verify
the remote SHA. No push occurs during preparation. Preserve legitimate newer commits.

## Separately scoped follow-up: explicit currency persistence

ISSUE: canonical financial models lack explicit currency metadata. OWNER: ALFRED
maintainer. OUTSIDE THIS RELEASE: design per-record/account currency ownership,
authoritative code sources and an approved reversible migration/backfill. Unknown
historical currency must remain unknown; an INR display convention is not proof
for backfilling records. Preserve all Decimal values, balances and import identity.
REQUIRED EVIDENCE: forward/rollback rehearsal, unknown/multiple-currency and owner
isolation fixtures, unchanged financial totals and legacy INR/API compatibility.
No schema change or live backfill is authorized or performed in this integration.

Regular release rule: Completed -> Tested -> Integrated -> Packaged -> Approved ->
Promoted. This worktree is the single M15 release source; earlier worktrees remain
preserved provenance, not independent unfinished releases to deploy separately.
