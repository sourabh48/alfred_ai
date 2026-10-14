# M15 recovery acceptance: existing material and manual alternative

**Current recovery status — 2026-10-15:** Local independent pre-M15 restoration was verified; HDD copying is user reported and independently recoverable off-device archive/key restore remains UNVERIFIED under an explicit M15-only deployment waiver. Cancelled sealing dialogs stay cancelled; no plaintext key workaround or new export is authorized. Hash verification/current-profile DPAPI does not prove device-loss recovery. Use [four-stage acceptance](ALFRED_END_TO_END_ACCEPTANCE.md).

## Historical preparation record — 2026-10-12

2026-10-12. Preparation only; no key export, new seal/passphrase dialog, rotation,
restore of live data, backup overwrite or deletion. Off-device recovery PENDING.

Desktop transfer root:
C:/Users/soura/Desktop/ALFRED_OFFDEVICE_TRANSFER_20261011.
Its existing VERIFY_TRANSFER.ps1 passed counts/sizes/SHA256 again. The manifest
has 15 non-key material entries and no key records. Supplying -KeyPath therefore
would still not verify a key. The verifier does not authenticate/decrypt an
archive, restore files, check SQLite, prove external storage or protect the
manifest against replacement. Keep the separately trusted hash receipts.

| Material | Existing evidence | Device-loss recovery |
| --- | --- | --- |
| Original 2026-10-06 portable 7z AES256 archive with encrypted headers | Historical local hash/extraction receipts; preserved unchanged | Format is portable with its existing established secret; current off-device secret availability/restore not verified. Do not prompt for it now. Predates M14. |
| M14 prepromotion encrypted supplement | Fresh-process on-device authenticated restore: 9,691 files, three SQLite databases, hashes/integrity PASS | Portable archive format; separately retained key and actual external copy not verified. |
| Post-M14 2026-10-12 supplement | Fresh-process on-device authenticated in-memory restore: 9,694 files, three SQLite databases, integrity/FKs PASS; family.0004 applied | Same missing independent archive/key copy. SHA256 17558ef52538d9cc4bf750a78a937f9cd8083ce6eb8ff89f767e6d8f901679d7. |
| M15 journal/sync owner keys | Current-user DPAPI protects local keys; synthetic encrypted journal/checkpoint recovery passed | DPAPI files alone are not portable after Windows-profile loss. Independent owner key and latest trusted high-water checkpoint are required before private cloud recovery. |

The current-independent-verification.json receipt explicitly records dpapi_used
false for the M14 supplement decryption and sealed_key_used false. That proves
portable encryption/fresh-process local restoration, not retention of the key
outside this device or an independent Windows-installation restore. Keep those
claims distinct. Existing M14 recovery material is not a backup of future M15
private memory keys. Historical copies can retain deleted data until retention
expires or the corresponding recoverable keys are securely retired.

## Simple manual alternative requiring a separate approval

Use an existing trusted password manager with independently tested account/vault
recovery, or an already protected offline key device. The user must approve the
specific destination and secure input method first. Do not invent a cloud service,
create a replacement recovery key or save a new plaintext key file.

After that approval, the operator retains the EXISTING required recovery secrets
as separate encrypted vault items. Any authorized local transfer helper must pass
key bytes directly in memory through the approved manager's secure local interface;
no chat, shell arguments, transcript, logs, clipboard history or plaintext file.
Normal unlocking/recovery of the already chosen manager is user-controlled; the
cancelled ALFRED passphrase/sealing dialog is not restarted. Do not implement or
run an exporter until the manager/device and safe input mechanism are chosen.

Copy encrypted archives and trusted verification receipts to the separately
approved archive device/destination. Keep the password-manager/offline-key recovery
material separate. From the ACTUAL copied archive root run the existing verifier
without any key/passphrase argument; this proves only copied hashes.

Then, in a disposable independent Windows profile/device, use only the external
archive and separately recoverable key (not this profile, local originals, staging
or sync caches) to authenticate and restore. Require the complete expected inventory,
all file hashes and SQLite integrity/foreign keys. For M15 also import the SAME
canonical identity and latest trusted checkpoint, reconcile current revocations,
and verify Ollama retrieval with no deleted-memory resurrection. Retain a safe
receipt with hashes/counts/status only, never secret/key/private document content.

Until this independent test passes, INDEPENDENT RECOVERY = PENDING and
M15 PRIVATE RECOVERY READINESS = BLOCKED. Preserve every original backup and all
later writes; never restore over the live database. No Windows wipe is approved.
