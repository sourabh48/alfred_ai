# Codex / Claude handoff

Status: CODEX_ACTIVE. Claude has not been launched. This is not final-review readiness.

Read AGENTS.md, CLAUDE.md, docs/EXECUTION_STATE.md, STATE.json and the execution
board, then inspect actual HEAD, status and staged diff. Canonical trackers govern
scope; this directory only coordinates continuity.

Only Codex currently owns this worktree. Do not start another writer while its
execution is active. An explicitly configured independent task requires a separate
worktree. Before taking over, the user must end the previous writer and update
the active-agent record. Preserve staged choices and the unrelated existing
`alfred_ai/services/materialized_cache.py` edit.

Current bounded task: USE-02 statement preview/confirmation. Trace upload,
manual retry, scheduled retry and document-correction callers before edits.
Do not permit background parsing to create transactions, accounts, balances or
loan postings without a server-bound reviewed confirmation.

No authorized Claude launch/orchestration has been invoked or confirmed. At an
actual handoff checkpoint Codex will record CODEX_TO_CLAUDE_READY with exact
source/test/dirty state. The continuation instruction will be:

> In F:\ALFRED\alfred_ai, resume from docs/ai_progress/HANDOFF.md and STATE.json.
> Verify no other agent is writing this worktree. Read AGENTS.md, CLAUDE.md and
> docs/EXECUTION_STATE.md; verify actual branch/HEAD/status and source receipts.
> Preserve the existing cache edit. Continue the recorded incomplete USE-02 scope,
> test with isolated synthetic data, commit only reviewed scope and checkpoint.
> Do not start 3.0, touch owner data, publish or claim release/final-review readiness.

The CLAUDE.md Graphify host note is historical: normal Graphify query/update
succeeded during this execution. Recheck normally; never bypass application control
or install Graphify into ALFRED's application environment.
