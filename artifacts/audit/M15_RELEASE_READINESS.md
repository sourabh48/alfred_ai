# M15 hybrid intelligence development acceptance

## Latest corrected packaged review - 2026-10-12

Original frozen 03ab0aecdecda72dcb4db7866c46821e7c4264bf remains unchanged.
Separate corrected build: f6c686ed67362bf3d777271d33bae4388b9b3cbc; subsequent
eb22c0e changes a browser test only. Actual updated gate: 232 backend PASS,
6 development Chrome PASS, 30 packaged native checks PASS including four packaged
browser flows, and launcher/progress/tray/stop PASS. Zero final failures/skips.
No new migration; system/drift PASS. 10,892 fresh bundle files inspected, no private
runtime paths, M15 assets match source. Binary/portable hashes and final checkpoint
SHA are in the external m15-package-final-manifest.json under isolated-tests.
See M15_PACKAGED_ACCEPTANCE_20261012.md for findings, source/migration/configuration,
scope/limitations, precise evidence and rollback. Original review candidate needed
the closure-conflict and Windows status replacement corrections; they were made
only in a separate hardening branch/worktree and independently tested.

M15 PRODUCTION RELEASE READY remains NO: independent key/archive recovery PENDING
and real provider/IAM/cost/retention approval/acceptance outstanding. No real OpenAI,
cloud upload, key export, cancelled passphrase dialog, stable merge or live change.
Generated narrative remains a hypothesis; independent canonical source fields are
financial authority. Broader document ingestion and currency/citation improvements
remain separate. The following original 223-test checkpoint is historical evidence,
not the current combined count.

2026-10-12. Development worktree F:/ALFRED_DEV/m15 only.
Tested implementation: 4aac9c91c972c047304726b0219736f61ca1402d.
Following checkpoint commit changes documentation only; its SHA and source archive
hash are recorded in F:/ALFRED_DEV/isolated-tests/m15-hybrid-manifest.json.

## Actual final gate

| Gate | Actual result | Evidence under F:/ALFRED_DEV/isolated-tests |
| --- | --- | --- |
| Combined related backend | 223 PASS, 122.787s, zero failures/skips | m15-hybrid-combined.log/.ps1 |
| Actual Chrome workflows | 6 PASS, 71.941s, zero failures/skips | m15-hybrid-chrome.log; m15-hybrid-chrome/browser_regression_summary.json |
| Actual native source/Chrome drill | 19 PASS, run 93f9d6d45d | m15-hybrid-native-runtime.log; native report copied into final manifest evidence |
| Native configuration/system/migration drift | PASS; no new migration | m15-hybrid-native-config-final.log |
| Real local Ollama encrypted save/reopen/recovery/retrieval/reasoning | PASS; all-minilm + qwen3.5:4b; owned source; 256 output-token cap; 25.391s with concurrent gates; zero cloud calls | m15-hybrid-restart-final.log/.py |
| Synthetic relevance calibration | 6 positive + 6 unrelated negative questions; recall@3=1; abstention=1 at 0.20 | m15-hybrid-calibration.json/.py |
| Source diff/AST graph | PASS; 8388 nodes, 21980 edges; no paid semantic labeling | m15-hybrid-graphify.log |

Counts are from single actual runs, not sums of earlier overlapping gates. Focused
runs (108 quality, 57 reasoning, 77 application and 62 model-failure tests) overlap
the combined gate. Native checks include one real Chrome/native page check; this
is not added to the six focused Chrome workflow count. The native drill covers
workers/retries/crash recovery, ownership, HTTP/static/UI, CSRF-authenticated writes,
restart persistence and disposable database/media/queue backup restoration.
No packaged executable/installer or real-account/private-data acceptance was run.
Initial failed synthetic fixture/calibration/offscreen-click evidence is preserved.

## Scope validated

- Atomic exact deduplication preserves ownership, distinct evidence, sensitivity
  and JSON types. Candidate hypotheses remain separate from checked memories;
  corrections, consolidation, feedback, conflicts and deleted-memory protection
  use the existing encrypted journal/revocation/checkpoint engine.
- Existing S3 signed synthetic fixtures, least-privilege configuration, encrypted
  immutable snapshots/CAS, startup/minute/shutdown lifecycle, durable retry state,
  tamper/rollback checks, ownership and deletion propagation pass the combined gate.
- Existing Insights adds local-first conversation and explicit checked memory save.
  Grounding uses owned memory statements, existing canonical Finance metrics with
  evidence states, owned Travel preferences and verified owned Loan closure facts.
  Generated text cannot dispatch tools, change balances or become verified memory
  automatically. Raw OCR/filesystem/parser payloads are not prompt context.
- Existing Settings supports correction/retention/delete/reset plus local sync
  status, sync consent and owner cloud-reasoning policy/budgets. Status reads never
  contact providers or return keys. Text rendering and page-exit cleanup protect
  against hostile model HTML and stale browser context.
- Optional OpenAI is disabled by default. Public general fallback requires explicit
  per-request consent plus existing provider authorization, owner policy, filtering
  and durable caps. Private/domain reasoning stays local. Embedding outages visibly
  remove memory grounding; only a consented public query can fall back without any
  memories. Corrupt storage/unexpected failures remain operational errors.

Existing API GET contracts are preserved with additive safe fields. No new Django
model, migration, dependency, financial calculation or parallel assistant is added.
Arbitrary document ingestion/search is outside this bounded integration; document
knowledge currently uses verified Loan closure evidence or owner-verified memories.
The small relevance fixture is not a universal retrieval-quality guarantee.

## Candidate and remaining acceptance

SOURCE INTEGRATION GATE = PASS
M15 PRODUCTION RELEASE READY = NO
M15 LIVE DEPLOYMENT = NOT AUTHORIZED / NOT PERFORMED

Prepare a local immutable source candidate only after the gate above. Its local
release branch/archive/checkpoint SHA and hash belong in the external manifest.
No remote push, stable merge, installer promotion or live migration is performed.

1. Real storage selection/authorization, restricted IAM/sibling-prefix denial,
   bucket controls/ownership, retention/replication and cost acceptance remain
   PENDING. Owner keys and latest trusted checkpoint must be independently
   recoverable before private cloud use. Mock/wire proofs do not prove real IAM.
2. Off-device recovery and a separately recoverable decryption key remain PENDING.
   Existing backups are preserved. The cancelled sealing/passphrase workflow is
   not restarted, and encryption is not weakened.
3. Real paid OpenAI remains disabled/unapproved. If selected, separately approve
   the restricted project key, current pricing/budget and public-only use before
   real acceptance. Private reasoning continues through Ollama.
4. Document scope and model/relevance calibration must be accepted for the intended
   deployment. Real-account acceptance and packaged runtime promotion remain separate.

Remote/stable master independently verified at
30e0b3f75e785f639897ad36c19090c6a4e8675f. Stable operator changes remain preserved.
No live source/private DB, live tokens, recovery keys or original backups changed.
Historical backups/offline recipients may retain deleted data; no irreversible
erasure is promised.
