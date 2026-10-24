# M15 encrypted synchronization: synthetic provider slice

**Post-audit override, 2026-10-15:** AWS is decommissioned. Its adapter is removed
from development runtime and quarantined in network-free tests; historical
activation flags cannot enable it. Neutral encrypted synchronization remains.
R2 is an unimplemented candidate; no account/contact is approved. Results below
are historical synthetic evidence. See [current status](PROJECT_STATUS.md).

**Integrated status — 2026-10-15:** The synthetic protocol and later AWS wire adapter are incorporated in deployed M15, not proof of real provider activation. Lifecycle/retry/tombstone/checkpoint behavior remains locally/synthetically accepted. Owner key/checkpoint/device-loss acceptance is separate and unverified. Memory sync is not full financial database backup. [Current register](ALFRED_EXTERNAL_INTEGRATIONS.md).

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
Final proof F:/ALFRED_DEV/isolated-tests/m15-sync-ollama-proof-final-20261011 passed in
two independent processes: same memory ID, 384 dimensions, score 0.518286,
provenance/sensitivity/ownership preserved, external cloud calls zero.

Protocol regression cases include encrypted disks/queue, offline restart/backoff,
consent, deletion/reset/retention, immutable versions, CAS races, conflict recovery,
tampering/forks/rollback, missing keys, download bounds, lost responses, concurrent
budget updates and consent withdrawal. Protocol commit:
f29d6d0c49d384c49d99559a85d2dfe959710ae3. No unfinished M15 source belongs in master.

## Runtime and API integration

Both provider settings default OFF: ALFRED_MEMORY_SYNC_MOCK_DIR is empty and
ALFRED_MEMORY_MOCK_REASONING is false. An operator may configure an absolute
isolated mock directory for synthetic development only. There is no selectable
real provider, remote URL or credential in this slice. Mock configuration never
grants owner consent; authenticated POST configure additionally requires enabled
and consent=true. GET returns safe owner status, never paths or encrypted payloads.

| Endpoint under /api/ai/memories/ | Method | Behavior |
| --- | --- | --- |
| sync/ | GET | Configured mock provider; owner status only |
| sync/ | POST | action=configure, sync or recover; confirmed recovery only |
| reason/ | POST | Optional mock reasoning; explicit consent and public query |

Existing session-only auth, CSRF, no-store responses and shared expensive/account/
global limits apply. Clients cannot choose owner, provider, destination, budget or
cloud retrieval through a local endpoint. Invalid requests return 400, auth/CSRF
403, conflicts 409, budgets/throttles 429 with Retry-After and operational failures
503. Logs retain safe class/error reference only.

sync_private_memory performs a bounded rotating batch of at most 16 active users,
checking stored opt-in independently per owner. Startup verifies/downloads before
serving; the native worker ticks every minute with a two-second synchronization
budget. Shutdown drains writers first, then gives synchronization a shared five-
second deadline. The mock observes this deadline for SQLite locks and operations;
directory ACL subprocesses also observe the remaining deadline. Pending work is
durable, so bounded shutdown need not flush every owner. There are no orphaned
background network threads. Inactive/deleted accounts are never uploaded. Missing
provider/vault returns without creating storage or making provider calls.

Optional reasoning is request-driven, using only explicitly public query/context.
The existing retrieval classification gate rejects any personal/sensitive result;
provenance/IDs/owner and vectors are omitted from the provider payload. The mock
returns a fixed synthetic answer and makes no network request. There is no real
OpenAI adapter, API key, paid call or automatic AI memory export.

The encrypted per-owner UTC-day ledger reserves a conservative byte-token bound,
512 output tokens and 256 adapter-overhead tokens before dispatch. Default quota
4096, server-configurable 1-65536. Failures retain reservations; restart/reset
cannot reset a same-day quota. Concurrent sync metadata updates preserve it.
The next day resets the ledger, and rejection occurs before provider dispatch.
A real OpenAI adapter must separately enforce the same token/deadline contract,
validate actual usage/pricing and obtain authorization before being connected.

## Current gate and follow-up

Final combined backend: 108 PASS, 52.439 seconds, no failures/skips, including 35
new protocol/runtime/reasoning regressions and existing memory/privacy/reset/
session/abuse/brain/native/launcher/tray tests. Chrome: two synthetic workflows
cover session/CSRF/consent/encrypted mock sync/reasoning and existing delete/reset/
retention/owner isolation. Native source/Chrome drill: 19 checks PASS, including
actual startup, HTTP, separate worker, retries, crash recovery, restart, queue and
backup restoration. Isolated migration drift: No changes detected. No new Django
migration or dependency, live database/token mutation, backup deletion or Git push.
AST graph refresh: 8146 nodes/21087 edges, no semantic API call.

Evidence stays outside Git: F:/ALFRED_DEV/isolated-tests/m15-sync-combined-release.log,
m15-sync-browser-final.log (two workflows, 16.429 s), m15-sync-native-runtime.log, m15-sync-config.log,
m15-sync-graphify-final.log and m15-sync-manifest.json. The first native test fixture
used an incorrect stop-directory path; correction and explicit closure of the
startup SQLite handle passed the supervisor and actual native drill. Failed
fixture evidence remains in m15-sync-focused-v3.log.
The additional merge-expiry regression confirms that expiry after applying a
merged snapshot remains pending until the remote current manifest loses the key.
Its initial fixture omitted the newly expired remote record; corrected fixture
and final combined gate pass, with the failed attempt retained separately.

MOCK CLOUD VERTICAL SLICE COMPLETE; whole M15 INCOMPLETE. Next is an explicitly
approved real provider adapter with owner credentials, safe transport, key recovery,
trusted checkpoints and manifest-retention tests. Do not enable private cloud
memories or real OpenAI reasoning based only on these synthetic proofs.
