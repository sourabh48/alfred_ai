# Codex / Claude handoff

Status: CODEX_TO_CLAUDE_READY. Executing agent was Codex, not Claude.
Codex stops writing after this checkpoint; no Claude agent was launched.
Latest implementation source `c2d1517a364d385c7605ac346d3de86a35734326`.
Resolve the final checkpoint commit with `git log -1 --format=%H -- docs/ai_progress/STATE.json`.

This is a context-continuation handoff, not final-review or release readiness.

Read AGENTS.md, CLAUDE.md, docs/EXECUTION_STATE.md, STATE.json and the execution
board, then inspect actual HEAD, status and staged diff. Canonical trackers govern
scope; this directory only coordinates continuity.

Claim the sole writer role only after verifying this handoff and actual Git state. Preserve `alfred_ai/services/materialized_cache.py` unchanged.

Loan review implementation: `88c1df826aa14fc56247678cabaa175356d62882`.
Follow-up `c2d1517` preserves canonical loans when legacy sources are removed;
86 affected backend and one real Chrome source-deletion journey PASS. Source
preflight PASS at c2d1517; its broader215/native22 evidence belongs to88c1df8.
Upload/retry cannot post loans. Existing matches link only; explicit confirmation
binds the owner/source/draft/dependencies and posts once through canonical services.
215 backend,2 Chrome, native22 PASS. Four Axe audits have zero automated violations;
manual gradient contrast review remains. Clean-source preflight PASS; release blocked.
The source guide is docs/LOAN_IMPORT_REVIEW_GUIDE.md. No migrations/dependencies added.
The original 29 bank-source hashes matched; no bank implementation was rewritten.

Next selected task: USE-02 investment-document preview/confirmation. Query Graphify,
then trace apps/investments views/parsers/corrections and shared document retry.
Use canonical investment money validation. Do not alter owner data or silently
post on extraction. Complete/test/commit/checkpoint this bounded slice and continue
eligible 2.0 usability work. Parent readiness, package, owner and3.0 gates stay open.

Clean validation-only worktrees retained: usability-source-check-0f35605 and
usability-loan-check-88c1df8 under F:/ALFRED_DEV. No parallel coding agent owns them.
All source changes are committed; checkpoint changes are recorded in STATE.json.
The loan validation worktree retains its historical name but is now detached atc2d1517.

The JetBrains-provided Claude CLI is installed, and Claude desktop processes were
already present. Neither establishes an authenticated, authorized unattended write
handoff. No CLI agent or final audit was launched; use this continuation instruction:

> In F:\ALFRED\alfred_ai, resume from docs/ai_progress/HANDOFF.md and STATE.json.
> Verify no other agent is writing this worktree. Read AGENTS.md, CLAUDE.md and
> docs/EXECUTION_STATE.md; verify actual branch/HEAD/status and source receipts.
> Preserve the existing cache edit. Claim the single-writer role and continue the
> recorded USE-02 investment-document preview/confirmation scope,
> test with isolated synthetic data, commit only reviewed scope and checkpoint.
> Do not start 3.0, touch owner data, publish or claim release/final-review readiness.

The CLAUDE.md Graphify host note is historical: normal Graphify query/update
succeeded during this execution. Recheck normally; never bypass application control
or install Graphify into ALFRED's application environment.

Investment trace already completed (no investment source edits):
- apps/investments/views.py::import_investment_pdf calls parse_portfolio_pdf.
- portfolio_intelligence.py::parse_portfolio_document is the existing pure parser;
  parse_portfolio_pdf calls _create_or_update_investment before document persistence.
- Shared document_review.py::_retry_investment_document and
  _apply_investment_correction call _upsert_retry_investments; source deletion can
  also remove orphan holdings. All need reviewed, bound canonical-write controls.
- Reuse InvestmentSerializer, investment_money and document_evidence.capture_import.
  Missing/zero terms and currency require explicit treatment; no duplicate engine.
Do not restart the roadmap, repeat bank/loan acceptance or begin3.0. Source acceptance
is not installed/package/real-account acceptance. No remote CI was dispatched.
