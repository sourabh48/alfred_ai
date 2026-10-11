# M15 frozen review and corrected packaged acceptance

Original frozen review HEAD: 03ab0aecdecda72dcb4db7866c46821e7c4264bf.
Original branch release/m15-hybrid-review-20261012 and its archive are unchanged.
Original archive SHA256 reverified:
FE495B515008199614F3C72214C1302A8E001F37B42D384AB475B6FED085D47D.

Corrected build/source SHA: f6c686ed67362bf3d777271d33bae4388b9b3cbc.
Separate worktree F:/ALFRED_DEV/m15-hardening, branch
codex/m15-release-hardening-20261012. Following eb22c0e fixes a browser test only;
following checkpoint documentation does not change packaged application code.
Final checkpoint/review SHA and archive hashes are recorded in the external
F:/ALFRED_DEV/isolated-tests/m15-package-final-manifest.json.

## Exact current gate

| Gate | Actual final result | Evidence under F:/ALFRED_DEV/isolated-tests |
| --- | --- | --- |
| Relevant combined backend | 232 PASS, 143.272s, zero failures/skips | m15-package-combined.log/.ps1 |
| Development Chrome | 6 PASS, 66.067s, zero failures/skips | m15-package-source-chrome.log and summary |
| Packaged native executable | 30 PASS, run 786b0b27ee | m15-package-native.log/.ps1; m15-package-native-report.json |
| Packaged Chrome flows | 4 PASS within the native drill | Dashboard/charts/Settings, actual Ollama conversation/citation, verified document abstention/citation, memory correction screenshots |
| Packaged launcher | PASS | m15-package-launcher.log; m15-package-launcher-report.json |
| Package private-path/asset inspection | 10,892 files, 1,228,186,906 bytes; zero private runtime paths; M15 assets match | m15-package-bundle-inspection.json |
| Configuration/system/migration drift | PASS; no new migration | m15-package-config.log |
| Source AST graph refresh | 8429 nodes, 22068 edges, no paid semantic call | m15-package-graphify.log |

These are actual runs, not added earlier counts. Packaged browser observations
are included in the 30 native checks, not 30 additional tests. The preceding
29-check source drill validates test tooling and is not added to packaged counts.
Focused document/native counts overlap the combined backend gate.

Fresh PyInstaller 6.22.3 build from pinned repository requirements/spec, with new
output/work/cache directories; no old application build reused. Build tools were
installed into F:/ALFRED_DEV/build-tools/m15-20261012, not the live SDK. Binary bundle:
F:/ALFRED_DEV/release-candidates/m15-package-20261012-hardening/bundle/ALFRED.
ALFRED.exe SHA256:
1dbcd707ae71fba52a14e206d7e4b225b757a3f3e6ee10c476149af30e58d4a2.
ALFRED Launcher.exe SHA256:
95949f168846e381cce12cf2986f6bda0626d25c39c08dc197f0ff9d90ae1292.
Portable review ZIP CRC/hash/inventory are recorded in m15-package-archive-report.json.
All packaged checks used synthetic isolated data and installed local Ollama only.
Launcher checks observed its progress window, registered/removed tray, offline
guide, graceful stop and operation without system Python on PATH. Native checks
cover bundled OCR, ownership, scheduler/workers/retry/crash recovery, actual local
embeddings/generation, encrypted indexes/journals, corrections, deletion/reset/
retention, offline/default-disabled cloud, restart and encrypted-vault restoration.
Disposable processes stopped. This is same-PC acceptance, not independent-device,
installer lifecycle, private-account or device-loss recovery acceptance.

## Review findings and source changes

1. Competing verified closure amount/date evidence previously allowed inference.
   A focused failure reproduced this. 556f180 adds a minimal same-loan conflict
   guard and checks after inference, with existing safe 409/reference handling.
   Six regressions cover owned minimal references, raw OCR/token/prompt-injection
   exclusion, changed/deleted/unverified evidence, equal independent evidence and
   conflicts introduced during generation. No evidence/financial row is rewritten.
2. Extended native acceptance exposed WinError 5 replacing runtime.json after
   workers drained. A real open-reader regression reproduced it. b7a819f retries
   only PermissionError for at most 1.55s, preserving atomic replacement, old state
   and diagnostic temp evidence. Permanent/unexpected failures still propagate.
3. f6c686e extends the existing native verifier with --memory and makes packaging
   inspection require/digest-check M15 assets. eb22c0e scrolls the actual delete
   button in an older browser test; the header interception was test positioning.
4. 835f00e prepares an uninstalled S3 IAM example, gated synthetic live acceptance,
   local-only diagnostics and a manual approved-manager recovery alternative.
   No new adapter, provider contact, credential or key export is created.

Initial failed regression/source/browser/interrupted-build evidence is preserved.
Only the corrected fresh build is accepted. No unrelated future features are in
this candidate. Frozen original and stable M14 files are not changed.

## Scope and limitations

Document grounding is owned verified memories plus selected owned verified Loan
closure amount/date evidence. Raw OCR, filenames, paths, tokens and extraction
diagnostics do not enter that tool context. Actual packaged Ollama explicitly
declined the unsupported account-number question; synthetic injected raw content
never appeared. This proves the observed case and application boundaries, not
universal prompt-injection resistance or comprehensive financial-document analysis.
Broader ingestion remains a later feature. Generated narrative is a hypothesis:
the observed model appended a dollar currency label despite the UI's INR formatting.
Use the independent canonical source fields for financial facts; narrative currency,
formatting and factual claims are not mechanically validated. Currency/citation
quality improvement belongs on a separate subsequent branch, not this frozen build.

Real S3 provider/account/destination/IAM/cost/retention acceptance remains AWAITING
APPROVAL. Proposed AWS configuration is not selection/authorization. Masked source
management CLI provisioning remains operator-only; no packaged credential UI.
No real cloud object, raw SQLite/WAL/SHM upload or paid OpenAI request occurred.
OpenAI real access stays DISABLED; owner consent/pricing/caps remain required.

Independent recovery remains PENDING. Desktop transfer hashes passed, but the
verifier has no key records and does not decrypt/restore. M14 fresh-process local
receipts prove portable encryption with existing local key, not externally retained
archive/key material. M15 DPAPI keys need a separately recoverable owner key and
latest trusted checkpoint. Packaged restore proof stays within the current profile.
See docs/M15_RECOVERY_ACCEPTANCE.md; no cancelled passphrase dialog was restarted.
Preserve all backups. Historic backups/offline recipients can retain deleted data.

## Integration and migration plan for a later authorized promotion

Stable source base: 30e0b3f75e785f639897ad36c19090c6a4e8675f.
Source diff: that base through corrected build f6c686e, with following test/docs
checkpoint only. Exact file/status/stat reports are retained in the final manifest
evidence. Existing stable operator changes require preserved/reviewed reconciliation
before any merge; they are not silently overwritten by audit-document differences.
No new Django migration; existing M13C/M13D and family.0004 files remain intact.
family.0004 was already applied in verified live M14; do not reverse or reapply it.
Recheck exact live migration history only as part of an authorized deployment gate.

M15 settings default to local processing: computed data-root private-memory-v2,
qwen3.5:4b, all-minilm local embeddings, relevance threshold 0.20, empty real storage
provider, real cloud/OpenAI authorization false. Optional real configuration remains
untracked/encrypted, owner consent required. No cloud-hosting runtime template.
Actual Ollama models must be installed separately; this bundle does not download them.

Before any future promotion: obtain explicit authorization plus independent recovery
PASS; gracefully drain the target writers; capture and restore-verify fresh consistent
canonical DB, jobs, media, configuration, all encryption keys and M15 vault/checkpoint
backups; preserve stable source/operator edits. Promote only a frozen validated SHA.
Run normal-account acceptance without asking for passwords in chat. Reconcile
financial records, family consent/relationships, memory ownership and migration
history before declaring healthy. Do not re-encrypt live tokens as part of this.

Rollback: stop the exact target data-folder installation with the verified native
stop command; preserve post-backup writes and logs. Restore source to saved M14
SHA/configuration after reconciliation. No schema rollback is required. Preserve
M15 vault/journal/keys; M14 does not manage them. Never blindly restore an old memory
head/key set over newer revocations. If DB restoration is necessary, restore to a
new directory, verify integrity/FKs and reconcile later writes/current tombstones
before switching. The synthetic same-profile DB/media/queue/vault restore passed;
an independent private recovery/rollback package is still mandatory before live use.

PACKAGED DEVELOPMENT ACCEPTANCE = PASS
M15 PRODUCTION RELEASE READY = NO
LIVE PROMOTION / STABLE MERGE / REMOTE PUSH = NOT AUTHORIZED / NOT PERFORMED
Next blocker: independent archive/key recovery, then separately authorized provider
acceptance. No live source/private DB/token/recovery-key/backups modified.
