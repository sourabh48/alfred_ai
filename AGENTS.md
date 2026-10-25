# Local Hosting Guidance

## Codex execution protocol

- Start with `docs/EXECUTION_STATE.md`, `git status -sb` and actual HEAD. Read
  relevant `docs/ALFRED_2_0_REQUIREMENTS.md` and queued task scope before editing.
- `continue`: resume the current incomplete step; if finished, report
  READY_FOR_NEXT and stop. Never select another task automatically.
- `next`: finish/checkpoint or explicitly defer the current task, then select one
  eligible task from `docs/EXECUTION_QUEUE.md`; stop when completed or blocked.
- `status`: read-only Git/PR/task/baseline/extensions/blocker report; no mutations.
- Follow phases IMPLEMENTED_NOT_ACCEPTED → PARTIALLY_IMPLEMENTED → BLOCKED
  (approval/external) → NOT_IMPLEMENTED, module-by-module. Skip only actual
  blockers; document later-phase prerequisite exceptions. Do not repeat verified work.
- PROJECT_STATUS owns exactly 143 original IDs and evidence; requirements own
  intent, the queue owns selection, EXECUTION_STATE owns the compact checkpoint.
  New 2.0 stories have a separate ledger. Never inflate verification from source presence.
- Persist weighted progress/evidence/refs/dirty work/next command after milestones
  and before interruption. Preserve uncertain/uncommitted work and staging choices.
- Run `scripts/project_execution.py --check` with the configured SDK after tracker
  changes; use `--write` only for its generated views. Do not regenerate unrelated docs.
- No production, Pages/protection change, unapproved merge, private history/upload,
  paid/new credentials, currency/valuation change, privileged runtime change,
  destructive operation or security/AI weakening without explicit approval.
  Private knowledge Git sync stays disabled. Source acceptance is not release approval.

- ALFRED is a local or LAN-hosted application in this repository.
- Do not add cloud deployment wiring, cloud credentials, or cloud-specific
  runtime templates without an explicit new decision.
- Keep runtime secrets in untracked local environment files such as
  `config/local.env`.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
