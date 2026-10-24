# M15 first local memory slice

**Integrated status — 2026-10-15:** This guide's original slice below is historical scope. Its encrypted local engine/index/journal, APIs and UI are incorporated in deployed 3932f391 alongside later learning/hybrid/sync adapters. The original statements that no background learning/sync/reasoning was added apply only to that first slice. Real providers stay disabled; current-profile DPAPI is not portable recovery. [Current feature matrix](PROJECT_STATUS.md).

This document records the local baseline. The subsequent opt-in synthetic
encrypted synchronization milestone is documented in
[M15_ENCRYPTED_MEMORY_SYNC.md](M15_ENCRYPTED_MEMORY_SYNC.md).

Branch: codex/m15-persistent-memory-20261011 in F:/ALFRED_DEV/m15.
Frozen M14 release: 6050234e6da66d38d558be1976371e9d541f0319 on
release/m14-20261011. M15 files do not belong to that release candidate.

This slice now includes the engine, authenticated memory lifecycle APIs,
Account Settings delete/reset/retention controls and a synthetic operator proof. Existing
parser learning memory records represent training feedback, not confirmed facts;
the financial brain is unchanged. No automatic document ingestion,
background learning, cloud synchronization or cloud deployment wiring is added.

MemoryStore takes an absolute private directory and an authenticated persisted
application user. Save requires explicit verified=True, a structured non-empty
JSON memory, provenance with a source, and public/personal/sensitive classification
(sensitive by default). Content/provenance are snapshotted before embedding.
Callers must obtain the owner from the authenticated session, never a client-
supplied owner ID. Owner identity includes stable creation time and is hashed;
only that owner's rows/events participate in retrieval and restore.

Local inference uses the fixed 127.0.0.1:11434 Ollama listener and the installed
all-minilm:latest embedding model. Calls carry no proxy/cookie/credential headers,
follow no redirects, limit input to 8192 bytes and response to 256 KiB, and use a
30-second socket timeout. Inputs exceeding the model context fail (truncate=false).
Vectors must be finite/nonzero and bounded to 4096 dimensions. Model digest is
checked before/after inference and persisted; changed/incompatible models fail
instead of mixing vector spaces. Remote-model metadata is refused. The API follows
[Ollama's embedding contract](https://docs.ollama.com/api/embed); the small model is
listed in [Ollama's model library](https://ollama.com/library/all-minilm).

SQLite stores encrypted derived records AND an encrypted append-only event table.
Content, provenance and embeddings use a per-record Fernet key, stored only as
an encrypted wrapping. The master key in journal.key is current-user DPAPI
protected, with UI forbidden and no LOCAL_MACHINE flag. Directory ACLs exclude
inheritance and grant the current Windows user and SYSTEM. The default new vault
is ALFRED_DATA_DIR/artifacts/private-memory-v2; legacy plaintext schemas/keys are
refused and preserved. No private data is automatically migrated or purged.
Each confirmed memory, key wrapping and event commit in one transaction, with
FULL synchronous durability, secure_delete and DELETE rollback journaling;
temporary SQLite rollback data contains ciphertext. SQL triggers reject event
UPDATE/DELETE. No plaintext vector cache or temporary memory text file is created.
Protected journal keys are generated once, fsynced and retained;
missing/unreadable recovery keys never get replaced when encrypted events exist.
Backup verified.sqlite3 consistently plus journal.key in a protected recovery set.
DPAPI is Windows-profile bound, not zero-knowledge or a portable reinstall backup;
it does not protect against a compromised application/Windows user. See
[Microsoft's DPAPI contract](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata).

Restore verifies/decrypts every matching event before replacing only the owner's
derived index. Corrupt/incomplete journals roll back without losing the current
index; repeated restore is idempotent. Restore preserves original memory IDs,
provenance, sensitivity, embedding version and verification timestamp. Cosine
retrieval scans at most 512 memories per owner and returns at most 20 results;
larger memory volumes/vector indexing belong to a later slice.

Cloud-context selection defaults OFF. Even explicit consent permits only public
classified results; personal/sensitive memories are refused. The engine calls no
OpenAI/cloud reasoning endpoint and creates no cloud sync client. Classification
covers content AND provenance. Optional reasoning integration must retain this
gate before transmitting anything; it is not implemented in this slice.

Private-memory storage and lifecycle now pass the Windows synthetic gate below.
No real private-account acceptance or whole-M15 completion is claimed. These APIs
do not accept cloud/owner fields; authenticated session ownership is mandatory and
family financial-sharing consent never grants memory access. Responses use
Cache-Control: no-store, private. No browser storage is used; UI textContent avoids
HTML injection, pagehide clears memory DOM and fresh/restored pages re-fetch current
session data. The existing service worker has no response-caching handler.

Deletion removes the index row and wrapped record key, appending an encrypted
revocation. Current-journal recovery cannot restore deleted/expired data. Reset
revokes all owner keys and increments a generation to reject in-flight old saves;
retrieval re-checks live keys after inference. Other owners remain untouched.
Retention is encrypted per owner, defaults to 30 days, accepts 1-365 days and
expires immediately when shortened. Expiry considers journal records even if the
derived index is missing, runs on access/native startup/daily 03:00 UTC, and can
be invoked with manage.py prune_private_memory. Cleanup is idempotent. Account
data reset and User pre_delete revoke memory first; vault failure stops financial
mutation. Separate SQLite/Django transactions mean an eventual finance failure
keeps memory revoked. Memory retention removes no canonical financial records.
Old backups retain original keys/data and must be separately retired/reconciled
with current revocations before restoring; no global backup/cloud-replica revocation
is implemented. History is bounded at 4096 events before accepting another save;
tested compaction must precede increasing this cap.

| Endpoint under /api/ai/memories/ | Method | Behavior |
| --- | --- | --- |
| root | GET / POST | Owner listing / explicit verified save |
| <id>/ | DELETE | Owner-only revocation; foreign/unknown IDs 404 |
| reset/ | POST | Requires confirm=true; owner reset |
| retention/ | PUT | Validated days; immediate expiry |
| restore/ | POST | Restore only current live owner keys |
| retrieve/ | POST | Local semantic query and optional limit |

Shared session-only auth/CSRF and account/global/expensive limits remain active.
Safe referenced errors return 503 for operational failures, 400 validation,
403 auth/CSRF and 429/Retry-After before mutation. Memory/provenance/paths/keys and
raw exceptions are never logged. Settings provides Delete Memory, confirmed Reset
My Memories and retention controls; existing Remove Account Data includes memories.

## Synthetic two-process proof

With the configured Python interpreter, first use a new empty proof directory:

```powershell
& 'F:/ALFRED/alfred_ai/.venv/Scripts/python.exe' scripts/verify_local_memory_slice.py --phase save --proof-dir F:/ALFRED_DEV/isolated-tests/m15-memory-new-proof
& 'F:/ALFRED/alfred_ai/.venv/Scripts/python.exe' scripts/verify_local_memory_slice.py --phase restore --proof-dir F:/ALFRED_DEV/isolated-tests/m15-memory-new-proof
```

Save refuses to overwrite an existing non-empty directory. Restore requires the
synthetic proof marker, refuses any additional records, and removes only the
matching disposable derived memory row to
prove encrypted event recovery. It prints counts/status only, never memory text
or key material. Production callers use the service, not this synthetic harness.

Initial engine checkpoint 2026-10-11: 26 backend tests passed, 0 failures/skips, 12.544 s,
including 17 new memory/embedding cases and existing brain/authentication tests.
System checks pass. Two actual Python processes using local Ollama generated
384-dimensional vectors, retrieved the same memory after restart, rebuilt its
index from the encrypted event and preserved provenance/sensitivity/ownership;
semantic score 0.518286 for the synthetic paraphrased travel query. Cloud calls 0.
Installed local model digest:
1b226e2802dbb772b5fc32a58f103ca1804ef7501331012de126ab22f67475ef (45,960,996 bytes).
AST-only graph update passed: 7946 nodes / 20834 edges. No new Django migration,
dependency, live source/database/config/key/token change or private input.
Initial Windows fixture handles were explicitly closed; corrected tests pass.
Initial proofs/logs remain under F:/ALFRED_DEV/isolated-tests (m15-memory-guarded-final.log,
m15-memory-final-save.log, m15-memory-guarded-restore.log, m15-memory-guard-graph.log).

Current protected-vault gate: 33 focused privacy/embedding tests PASS; one related
backend gate 91 passed, 149.649 s, 0 failures/skips; Chrome combined 3 passed,
40.208 s, 0 failures/skips (memory lifecycle/XSS and existing family workflows).
Native source/Chrome verification 19 checks PASS, including worker recovery,
imports, restart and backup restore. Native config/system/migration drift PASS;
no Django migration/dependency added. Two real Ollama/Python processes on a new
protected synthetic vault: 384 dimensions, same memory ID after encrypted recovery,
score 0.518286, ownership/provenance/sensitivity PASS, cloud calls 0. Graph AST
update 8026 nodes/20640 edges PASS. CLI-array/scroll/config fixture issues corrected.
Logs: m15-private-focused-final.log, m15-private-combined.log,
m15-private-browser-combined.log, m15-private-native-runtime.log,
m15-private-config-proof-final.log, m15-protected-memory-save.log / restore.log,
m15-private-graph.log. M15 private-account/cloud acceptance remains unperformed.
Only the M14 native compatibility correction is cherry-picked here (80a5d3c);
no M15 memory source is included in the stable master integration.
