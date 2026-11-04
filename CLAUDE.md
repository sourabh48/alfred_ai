# ALFRED — Claude Code instructions

@AGENTS.md

`AGENTS.md` stays the shared source of truth. The notes below only add Claude Code specifics.

## Start of work

- Read `docs/EXECUTION_STATE.md`, then check `git status -sb` and the actual HEAD.
- Follow the `next`, `continue` and `status` rules in `AGENTS.md`. Never select a task automatically.
- Treat documentation and earlier reports as claims. Verify them against source and exact-HEAD CI.

## Non-negotiable constraints

- Offline-first Windows desktop: Django, Python, SQLite, Waitress, Huey and local Ollama.
- No cloud database and no unauthorized transmission of private data.
- Canonical financial calculations use Decimal. Strict owner isolation, authentication and privacy always apply.
- Preserve existing financial records and signing and encryption keys.
- No silent money writes, trading, bookings or production changes.
- No automatic master merge, Pages publishing or deployment.
- Never touch the owner's personal runtime or its data. Use synthetic, isolated fixtures for testing.
- Track 143 original requirements and 13 extensions separately.
- Implemented is not accepted. Merged is not accepted. A green check applies only to its exact HEAD.

## Claude Code tooling

- Domain guidance is on demand in `.claude/skills/`. Start with `alfred-project-context`.
- Read-only audit roles are in `.claude/agents/`. Use them only when isolation helps. They are unrelated to the runtime Development Council in `scripts/development_council.py`.
- Inventory, disabled hooks and owner approvals are in `docs/CLAUDE_TOOLING_MIGRATION.md`.
- Graphify host limit: Windows Application Control blocks `graphify.exe`, and calling Graphify can refresh installed skill copies. Until the owner resolves this, skip the `graphify query` step in `AGENTS.md` and use Grep and Read. Do not run `graphify update`.
