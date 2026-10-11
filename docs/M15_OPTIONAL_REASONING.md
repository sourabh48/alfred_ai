# M15 optional public-context cloud reasoning

2026-10-11, isolated source/synthetic HTTP fixtures only. Real paid OpenAI calls:
ZERO. Default `ALFRED_MEMORY_OPENAI_AUTHORIZED=false`. Ollama embeddings and
private-data processing remain local. No M15 deployment or live credential change.

The adapter uses only `https://api.openai.com/v1/responses` through the existing
safe HTTPS transport. A restricted owner project key is encrypted in the private
vault. `configure_memory_reasoning --user <id>` requires a masked interactive
terminal and refuses echo fallback; it neither enables contact nor owner consent.
Keys are never browser fields, command arguments, Git values, diagnostic content
or cloud-sync objects. Each account provisions its own restricted project key.

Real dispatch requires operator authorization, a current UTC-date operator
price review (`ALFRED_MEMORY_OPENAI_PRICING_DATE`), an enabled owner policy and
explicit public-query consent for every request. GET/PUT
`/api/ai/memories/reason/` reads/configures only owner policy and bounded daily
limits; it never returns credentials. Mock reasoning remains explicitly
configured for synthetic development and keeps its existing consent contract.

Only user-verified public retrieval context is permitted. Provenance, owner IDs,
private source references and sensitivity metadata are stripped. Conservative
checks reject financial/sensitive field names, likely account/phone numbers,
tokens, email, paths, monetary amounts and medical context, even when incorrectly
classified public. This filter is an additional guard, not a guarantee of perfect
PII recognition: users must confirm truly public data. Personal/sensitive context
stays local. There is no automatic background export, tool call, file upload,
conversation ID, arbitrary endpoint, cloud embedding or financial mutation.

Requests pin `gpt-4.1-mini-2025-04-14`, standard service tier, `store:false`, no background processing,
no tools and at most 512 output tokens, 64 KiB response, five seconds total.
Typed output, pinned model, status and bounded input/output/total usage are
verified. Replies are labeled `ai_generated_hypothesis`, grounded in
`user_verified_public_context`, with `financial_authority:false`; suggestions
never become verified memories or canonical balances automatically.

Before dispatch, one SQLite transaction rechecks record revocation and reserves
the full conservative JSON-byte input bound plus output allowance and estimated
maximum cost in integer micro-USD. Owner limits cannot exceed operator limits
(default 4096 tokens and 10000 micro-USD/$0.01 daily). Failed calls retain
reservations; reset/restart, changed policies and concurrent requests cannot
erase the day's ledger. The next UTC day resets usage, but real contact stops
until pricing is reviewed again. No billable retry is automatic. Diagnostics
retain only safe classification/reference IDs, never prompts, keys or upstream
error bodies.

As checked against the [official model pricing](https://developers.openai.com/api/docs/models/gpt-4.1-mini),
the reservation uses $0.40/million uncached input tokens and $1.60/million output
tokens, rounding upward and taking no caching discount. Recheck these rates,
project ownership/permissions, provider billing controls and the intended public
task before authorizing paid access. Local estimates limit this adapter's calls;
they do not control unrelated account usage or changed provider pricing.

The [Responses API contract](https://developers.openai.com/api/reference/python/resources/responses/methods/create)
supports the chosen bounded stateless text request. `store:false` does not
promise zero retention: [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data)
describe abuse-monitoring retention and account-specific exceptions. This
milestone makes no zero-data-retention or irreversible-erasure claim.

Focused reasoning/runtime gate: 25 PASS, 8.778 seconds, zero failures/skips.
Eleven new reasoning regressions cover disabled/stale-price contact, public-data
filters, owner consent, atomic concurrent quotas, retained failure reservations,
usage/schema/tool/size rejection, revoked context, encrypted masked provisioning
and session/CSRF/no-store API compatibility. The first malformed-response fixture
hit its deliberately low daily quota; its isolated budget was increased without
weakening production limits. Failed evidence is retained separately.
Final combined: 169 backend and three Chrome PASS, zero failures/skips; system/
migration drift checks PASS. No new Django migration or dependency. The final
standard-tier reservation includes the complete exact request body. Already
authorized in-flight requests cannot be recalled by subsequent memory deletion;
historic/provider copies remain subject to their respective retention controls.
Final combined results and commits are recorded in the continuation checkpoint
and F:/ALFRED_DEV/isolated-tests/m15-cloud-manifest.json.
