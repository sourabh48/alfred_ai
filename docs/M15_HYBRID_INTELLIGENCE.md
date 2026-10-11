# M15 hybrid intelligence

Development only, synthetic acceptance; no live M14 deployment or private uploads.

The existing Insights endpoint now accepts POST questions alongside its unchanged
financial GET contract. Session/CSRF, owner, no-store, safe errors and the existing
expensive-action limits apply. Ollama generates first on the fixed local listener
using an installed model checked before/after inference. Cloud-model metadata,
redirects, tool calls, changed models and malformed/oversized replies are refused.
Generation shares a 30-second deadline, 4096-byte context and 256-output-token cap;
the response is always an AI hypothesis, never an authoritative balance or write.
The stateless bounded request follows the [Ollama chat contract](https://docs.ollama.com/api/chat).

Read-only sources are selected explicitly, never dispatched from generated text:
canonical Finance through resolve_canonical_financial_baseline (with evidence
states preserved), owned Travel preferences, or owned verified Loan closure
evidence. Document OCR/raw payloads/diagnostics are not included. Other document
types are not automatically ingested into memory. Sources appear independently of
model claims. Families never gain memory/tool access through a connected account.
Selected memories are owner-verified statements, with provenance and similarity,
not factual certainty. Oversized memory context is omitted as whole records.
Revocation or changed canonical evidence during inference invalidates the answer.

Optional fallback requires per-request explicit public-query consent, general
scope, local model failure, and the existing approved provider/owner policy. Domain
context stays local. Public payload filters, durable owner token/spending limits,
bounded transport and default-disabled real OpenAI authorization remain in force.
No automatic paid retry or tool execution exists. Withdrawn cloud context is also
rechecked before returning a result; already authorized in-flight calls cannot be
recalled. Queries/answers are not automatically persisted. Owners must explicitly
verify a memory before saving it through the existing encrypted store.

Settings/environment select ALFRED_MEMORY_OLLAMA_MODEL (default qwen3.5:4b) and
ALFRED_MEMORY_RELEVANCE_MIN_SCORE (default 0.20). Legacy retrieval remains unchanged.
All-minilm synthetic calibration: 6 positive/6 negative questions, recall@3 and
negative abstention both 1.0 at 0.20; positive top scores 0.229-0.619, negatives
-0.048-0.117. A 0.30 cutoff missed a held-out positive. This small fixture does not
establish universal relevance; repeat evaluation when changing the embedding model
or memory domain. Cosine scores are not confidence probabilities.

Focused reasoning gate: 57 PASS, including 13 new hybrid regressions. Local actual
qwen3.5:4b synthetic generation PASS in 9.437s with 96 output tokens and zero cloud
calls. Full UI/combined/native gates follow in the continuation checkpoint.

Existing S3/CAS/queue/lifecycle/tombstone/checkpoint implementation is reused.
Real connection still needs separate provider selection, least-privilege IAM/cost
acceptance and separately recoverable owner keys/checkpoints. Off-device recovery
and independent keys remain PENDING. The passphrase workflow stays cancelled.
