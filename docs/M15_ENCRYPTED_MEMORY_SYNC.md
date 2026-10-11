# M15 encrypted synchronization: synthetic provider slice

Worktree F:/ALFRED_DEV/m15, branch codex/m15-persistent-memory-20261011.
M14 remains installed at 30e0b3f75e785f639897ad36c19090c6a4e8675f.
This implementation never synchronizes the live SQLite database, WAL or SHM.
No real cloud adapter, cloud credential, private upload or OpenAI request is enabled.

## Protocol

MemorySynchronizer accepts the existing encrypted MemoryStore and a provider with
head, download and publish methods. The supplied MockCloudProvider is a local,
ACL-private ciphertext-only SQLite mock, using atomic compare-and-swap publishing
and immutable SHA-256-addressed snapshot objects. A real provider must enforce
authenticated owner authorization independently, bounded reads/deadlines, atomic
CAS and immutable objects. A remote object namespace is not authorization.

Synchronization is OFF until explicit authenticated owner consent. Each owner has
a separate Fernet synchronization key, protected locally with current-user DPAPI.
Missing keys are refused; encrypted metadata alone prevents replacing a missing
local master key. Synthetic fresh-vault proofs explicitly provision the protected
owner key. Keys are never downloaded from the provider or printed. Cross-device
key recovery is a separate prerequisite; DPAPI files alone are not portable.

Snapshots contain already-encrypted immutable memory records, owner/reset generation,
retention and revocations, then receive authenticated outer encryption. Per-record
decryption keys are held only in the encrypted mutable current-head manifest,
never in immutable snapshot objects. The mock replaces this manifest with SQLite
secure_delete, and removes revoked record keys from it on the next successful tick.
Content, provenance, vectors and retry state remain encrypted on disk.

Save/delete/reset/retention queue synchronization atomically with local changes.
The encrypted owner state retains pending status, revision/hash acknowledgement,
bounded exponential retry/backoff and conflict status across restart. No query,
memory text, raw exception, key or sensitive path is logged. Failed requests use
existing safe class/reference logging; offline errors preserve pending local data.
A lost successful publish response acknowledges the existing version without
publishing another identical logical snapshot. Consent/budget changes made during
network operations are preserved; consent withdrawal prevents importing a download.

Downloads authenticate owner, schema, revision, object hash, key manifest, each
record, provenance, sensitivity and finite embedding before replacing local state.
Remembered high-water revisions reject rollback; parent chains detect forks.
Verification is bounded to 128 ancestors/64 MiB, a 32 MiB snapshot, a 128 KiB head,
512 live memories and 4096 retained events/revocations. Larger gaps fail closed
and need a trusted newer checkpoint. Recovered events also obey the local cap.

Conflicts preserve local edits and require explicit confirmed recovery. Deterministic
merge retains disjoint immutable memories, unions revocations, uses the newer reset
generation and the shorter retention policy. Authenticated remote revocations apply
even during an edit conflict. Reset prevents an offline older generation from
restoring old memories; retention expiry queues removal of remote record keys.
Family grants never grant memory or synchronization access.

## Limits of deletion and recovery

Revocation covers current local keys/indexes and the next verified current replica.
Immutable objects retain ciphertext. A provider retaining old head versions or a
previous recipient/backup retaining old keys can retain prior content. No global
erasure or ability to make recipients forget is claimed. A real adapter must avoid
versioned key manifests and supply tested retention/revocation reconciliation.
Restore old backups only after reconciling current revocations and reset generations.
An entirely fresh device without a trusted high-water checkpoint cannot detect an
unseen historical provider rollback. Preserve a separately protected recovery key
and checkpoint before using a real provider or private memories.

## Synthetic two-process Ollama proof

Run with the configured project interpreter and a new empty proof directory:

```powershell
& 'F:/ALFRED/alfred_ai/.venv/Scripts/python.exe' scripts/verify_memory_sync_slice.py --phase save --proof-dir F:/ALFRED_DEV/isolated-tests/m15-sync-new-proof
& 'F:/ALFRED/alfred_ai/.venv/Scripts/python.exe' scripts/verify_memory_sync_slice.py --phase restore --proof-dir F:/ALFRED_DEV/isolated-tests/m15-sync-new-proof
```

The save process refuses existing data. The restore process downloads encrypted
objects into a fresh vault with an explicitly provisioned synthetic protected key,
authenticates them, restores its encrypted journal and queries real local Ollama.
It copies no SQLite files and outputs only safe synthetic status/counts.
Proof F:/ALFRED_DEV/isolated-tests/m15-sync-ollama-proof-20261011-closure passed in
two independent processes: same memory ID, 384 dimensions, score 0.518286,
provenance/sensitivity/ownership preserved, external cloud calls zero.

Protocol regression cases include encrypted disks/queue, offline restart/backoff,
consent, deletion/reset/retention, immutable versions, CAS races, conflict recovery,
tampering/forks/rollback, missing keys, download bounds, lost responses, concurrent
budget updates and consent withdrawal. Runtime integration and optional mock
reasoning are the next separate commit; no unfinished M15 source belongs in master.
