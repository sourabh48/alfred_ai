# M15 local memory review pipeline

2026-10-11, isolated M15 source only. No deployment or financial-record change.

`/api/ml/memories/learning/` uses the existing session, CSRF, owner, abuse and
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

Candidate expiry, delete/reset, account revocation and journal recovery share
the existing retention/key-revocation controls. Current-replica revocation does
not erase historical backups. Cloud reasoning cannot make memories authoritative
financial facts; finance remains in canonical Django models and authorized
application workflows.

Focused gate: 79 tests PASS, 23.567 seconds, zero failures/skips, including 11
new learning regressions and existing sync/runtime/privacy/memory suites.
Evidence: F:/ALFRED_DEV/isolated-tests/m15-learning-focused.log.
Synthetic data and embedding fixtures only. Full M15 remains in development.
