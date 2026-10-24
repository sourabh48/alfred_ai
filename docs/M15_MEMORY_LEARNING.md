# M15 local memory review pipeline

**Integrated status — 2026-10-15:** Candidate/review/provenance/conflict/feedback/evaluation code is included in deployed M15. Synthetic quality evaluation does not certify genuine model accuracy or broad autonomous learning. Hypotheses never become canonical financial facts; corrections/deletion retain owner boundaries. [Matrix](PROJECT_STATUS.md) and [acceptance](ALFRED_END_TO_END_ACCEPTANCE.md).

2026-10-11, isolated M15 source only. No deployment or financial-record change.

`/api/ai/memories/learning/` uses the existing session, CSRF, owner, abuse and
no-store controls. GET returns the owner's encrypted local candidates. POST
supports extract, verify, correct, consolidate, reembed and evaluate. Unknown
fields, including owner overrides, are rejected.

Extraction selects up to eight supplied statements, records source references,
sensitivity, confidence 0.5 and `unverified_candidate`. It makes no model call
and never asserts that extracted text is true. Exact repeated candidates are
deduplicated. Candidates have per-record encryption keys and never enter
retrieval or cloud snapshots. Explicit `verified: true` is required to promote
a candidate; provenance retains its source, candidate ID and verification.

Correction/consolidation creates one newly embedded verified memory and revokes
the superseded keys in the same SQLite transaction. Sensitivity cannot be
lowered through consolidation. Failed embeddings preserve the originals;
concurrent reset prevents late resurrection. Re-embedding changes one memory.
Sync applies only changed encrypted index records. Evaluation accepts owned,
verified expected IDs and reports recall@3 and mean reciprocal rank without
persisting queries. Generated hypotheses are never verified ground truth.

Discarded candidates never enter the sync journal, including tombstone metadata.
Candidate expiry, delete/reset, account revocation and journal recovery share
the existing retention/key-revocation controls. Current-replica revocation does
not erase historical backups. Cloud reasoning cannot make memories authoritative
financial facts; finance remains in canonical Django models and authorized
application workflows.

Initial focused gate: 79 tests PASS, 23.567 seconds, zero failures/skips, including 11
new learning regressions and existing sync/runtime/privacy/memory suites.
Evidence: F:/ALFRED_DEV/isolated-tests/m15-learning-focused.log.
The candidate-discard follow-up passed 45 memory/privacy/learning regressions,
9.159 seconds. Final combined gate: 169 backend/3 Chrome PASS, zero failures/skips,
including verification/correction refreshing the real Settings page and escaping
synthetic markup. Synthetic data and embedding fixtures only. Full M15 remains in development.

## Owner corrections and retrieval quality (2026-10-12)

Exact verified saves now deduplicate atomically by owner, content, provenance and
sensitivity. Concurrent identical saves share one ID/event; different evidence,
sensitivity or owners remain separate. This never merges contradictory memories
or resurrects deleted keys. Explicit correction/re-embedding bypass deduplication.
Retrieval and evaluation accept an optional finite cosine `min_score` in [-1,1].
Existing retrieval is unchanged when it is omitted; scores are not confidence
probabilities. Hybrid reasoning uses a separately configured relevance cutoff.

Settings now offers a correction form for each owned memory. The owner writes a
replacement statement and explicitly confirms it. This replaces the whole memory
body; original source history and sensitivity are preserved. The existing atomic
replacement/re-embedding/revocation pipeline handles the save. No automatic edits,
financial writes, cloud calls, new storage tables or dependencies were added.

Stale corrections, competing promotions and changed-content verification retries
return safe HTTP 409 with a reference and exception classification in redacted logs.
The committed winner remains intact. Identical verification retries keep the same
ID without adding an event or embedding again. Browser conflicts preserve the draft
and require the owner to refresh and review; they never automatically retry an edit.

Evaluation keeps the existing `cases` contract (1-20 bounded queries) and now
accepts `expected_id: null` when the owner expects no memory to match. A non-null
ID must still be an active verified memory of the requesting owner. Reports contain
aggregate counts, recall@3, reciprocal rank and top-1 accuracy for positive cases;
false-positive and abstention rates measure negative cases. Metrics with no applicable
cases are null. Positive-only recall/MRR remain compatible. No queries, returned
memory bodies, individual-case results or evaluation history are persisted or echoed.

The current nearest-memory retriever has no calibrated relevance cutoff. Returning
any memory on a no-match case counts as a false positive, even at a low similarity
score. These metrics measure retrieval against owner labels, not factual truth or
model confidence. AI hypotheses remain unverified. Corrections/additions/deletions
during evaluation invalidate the report with 409 rather than mixing memory versions.

Settings supports one transient quality check at a time, with an owned expected-match
selector. Successful mutations/refresh clear the check; page exit clears memories,
drafts, the question and report. Late evaluation responses cannot repopulate them.
Encrypted memory retention, family exclusion and historical-backup limitations remain
unchanged. Use synthetic fixtures until separately approved private acceptance.

## Recovery verifier boundary

The existing Desktop `ALFRED_OFFDEVICE_TRANSFER_20261011/VERIFY_TRANSFER.ps1`
counts files below `archive/` and compares every manifest-listed non-key file's
existence, size and SHA-256. Key records are skipped without `-KeyPath`; supplying
it only checks a listed key's size/hash. The current manifest has no key records,
so it verifies no decryption key, even with that option. It does not authenticate
the manifest, reject unlisted files outside `archive/`, decrypt or restore archives,
check SQLite, establish Windows-profile independence or confirm external placement
and secure archive/key separation. The public Desktop README documents this boundary.

Off-device archives and a separately recoverable key remain PENDING. Existing local
restore receipts do not establish either requirement. All archives and original keys
remain preserved; the passphrase workflow stays cancelled. No new passphrase is needed
for this development milestone, and encryption was not changed.
