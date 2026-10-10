# M15 first local memory slice

Branch: codex/m15-persistent-memory-20261011 in F:/ALFRED_DEV/m15.
Frozen M14 release: 6050234e6da66d38d558be1976371e9d541f0319 on
release/m14-20261011. M15 files do not belong to that release candidate.

This slice is an internal engine plus a synthetic operator proof. Existing
parser learning memory records represent training feedback, not confirmed facts;
the financial brain is unchanged. No UI/API route, automatic document ingestion,
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

SQLite stores the local derived memory index and an append-only event table.
Each confirmed memory and its Fernet-encrypted event commit in one transaction,
with full synchronous durability. SQL triggers reject event UPDATE/DELETE.
Fernet journal keys are generated once in journal.key, fsynced and retained;
missing/unreadable recovery keys never get replaced when encrypted events exist.
Backup verified.sqlite3 consistently (account for WAL/SHM) plus journal.key in a
protected recovery set. A key stored beside the vault is not zero-knowledge.

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

The local index currently contains plaintext structured records/embeddings.
Use an owner-protected OS directory and protected/encrypted backups; this phase
uses synthetic memories only. Before exposing a UI/API or using private accounts,
integrate account reset/deletion and retention lifecycle (including append-only
tombstone/key retirement design), actual-session/controller authorization, vault
encryption/ACL acceptance and explicit consent. Do not represent this engine
proof as a private-account or complete M15 release acceptance.

## Synthetic two-process proof

With the configured Python interpreter, first use a new empty proof directory:

```powershell
& 'F:/ALFRED/alfred_ai/.venv/Scripts/python.exe' scripts/verify_local_memory_slice.py --phase save --proof-dir F:/ALFRED_DEV/isolated-tests/m15-memory-new-proof
& 'F:/ALFRED/alfred_ai/.venv/Scripts/python.exe' scripts/verify_local_memory_slice.py --phase restore --proof-dir F:/ALFRED_DEV/isolated-tests/m15-memory-new-proof
```

Save refuses to overwrite an existing non-empty directory. Restore requires the
synthetic proof marker and removes only its disposable derived memory index to
prove encrypted event recovery. It prints counts/status only, never memory text
or key material. Production callers use the service, not this synthetic harness.

Validated 2026-10-11: 25 backend tests passed, 0 failures/skips, 14.489 s,
including 16 new memory/embedding cases and existing brain/authentication tests.
System checks pass. Two actual Python processes using local Ollama generated
384-dimensional vectors, retrieved the same memory after restart, rebuilt its
index from the encrypted event and preserved provenance/sensitivity/ownership;
semantic score 0.518286 for the synthetic paraphrased travel query. Cloud calls 0.
Installed local model digest:
1b226e2802dbb772b5fc32a58f103ca1804ef7501331012de126ab22f67475ef (45,960,996 bytes).
AST-only graph update passed: 7944 nodes / 20827 edges. No new Django migration,
dependency, live source/database/config/key/token change or private input.
Initial Windows fixture handles were explicitly closed; corrected tests pass.
Proofs/logs remain under F:/ALFRED_DEV/isolated-tests (m15-memory-release-slice.log,
m15-memory-final-save.log, m15-memory-verified-restore.log, m15-memory-graph.log).
