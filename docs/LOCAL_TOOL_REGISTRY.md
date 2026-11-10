# Local assistant tools

The registry in `apps/ml_engine/services/assistant_tools.py` wraps the existing
`hybrid_intelligence` source adapters. It neither calculates new financial values
nor replaces domain services. The assistant's source selection and its post-inference
revalidation both pass through the registry. The existing memory path remains separate.

| Tool | Existing source scope |
| --- | --- |
| finance.baseline | finance |
| finance.record | financial_records; expense, budget, loan, investment or baseline |
| finance.statement | bank_statements |
| documents.financial_records | financial_document; up to three reviewed records |
| documents.loan_closure | documents; verified owned closure evidence |
| travel.preferences | travel; saved owned preferences |
| career.applications | career; recorded application progress, page-only |

Authenticated `GET /api/ai/tools/` returns input/output JSON schemas and each tool's
owner, authentication/authorization, consent, sensitivity, network, timeout, cache,
side-effect and audit declarations. It accepts no query parameters and cannot
register or execute tools. Responses are private/no-store and contain no owner data.
Input schemas come from the same strict DRF fields used for validation. Existing
domain services still verify ownership, selections, source signatures and revisions.

The server's source-selection facade asserts consent only for the source requested
by the authenticated question or owned citation. Models and document text cannot
select new tools, pass a different owner, register code or enable remote providers.
Tool outputs remain untrusted evidence under the existing inference/citation policy.

The five-second deadline is cooperative: the registry checks before the adapter and
rejects late results after validation. It does not forcibly stop SQLite or file reads.
The JSON result cap is 128 KiB; the existing model-context budget remains smaller.
Audit logs contain the fixed tool name, outcome and elapsed time, without owner IDs,
arguments, results, document names or exception text. No additional result cache,
canonical writes, worker, dependency, database schema or credentials were introduced.

This is a bounded local registry, not an MCP transport or autonomous planner.
Career progress reuses the existing application tracker for follow-up dates. Counts
cover up to 300 most recently updated owned opportunities, with the omitted count
and at most three recent details shown explicitly. Stages are recorded reports,
not verified submissions or employer replies. Missing/malformed dates remain
unresolved. The source is re-read before acceptance and is never sent to a model,
provider or transcript store. No profile is created by this tool; salary, contacts,
resume/JD text and private job URLs are excluded.

Career job discovery/matching, broader Travel/research operations and approved MCP servers remain
outside this implementation. Server configuration/disclosure approvals are unchanged.
