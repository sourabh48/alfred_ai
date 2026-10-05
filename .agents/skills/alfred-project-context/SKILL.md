---
name: alfred-project-context
description: Resume ALFRED engineering work from its recorded checkpoint, or orient a scoped implementation question in this Django project.
---

# ALFRED project context

Paths below are relative to the Git repository root, not the `alfred_ai` Python package.

- Read `AGENTS.md`. For continuation work, read `artifacts/audit/CODEX_CONTINUATION_STATE.md` and the relevant row in `artifacts/audit/ALFRED_DEEP_REVIEW_BACKLOG.md`; inspect branch, HEAD and working tree before editing.
- Use the scoped Graphify query/path/explain workflow in `AGENTS.md` when a graph exists. Read only the files needed for the current question. Do not restart completed phases or turn a bounded request into another whole-project audit.
- ALFRED is a Django monolith: `apps/` holds domains, `alfred_ai/` holds shared settings/views/services, `templates/` and `static/` hold the UI, and `tests/` holds runnable checks. Use `requirements.txt` and current CI for compatibility and test commands.
- Keep hosting local/LAN and secrets in untracked local configuration. Keep test data separate from the operator database and uploads.
- When working through PyCharm tools, obtain the configured Python environment before each Python command. Keep external agent tools out of the application environment.
- Trace existing callers and reuse the current helper before adding code. Record relevant checks and outstanding work in the checkpoint when finishing a continuation phase.
