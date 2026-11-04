# Claude Code tooling migration

Recorded 2026-10-31 against base `626c5bcf294004b3f238bc66551ec356bcbf89d2` on `development/alfred-integrated`. No ALFRED runtime file changed.

## Before and after

| Area | Before: Codex and legacy | After: Claude Code |
| --- | --- | --- |
| Instructions | `AGENTS.md` | `CLAUDE.md` imports `AGENTS.md` and adds Claude notes |
| ALFRED skills | `.agents/skills` | Same 5 copied to `.claude/skills` |
| Other skills | 11 JetBrains-sourced, Graphify, gstack, Ponytail | 2 security skills, Graphify and 6 Ponytail skills imported. Graphify and Ponytail run only when invoked by name |
| Agents | No agent definitions, only interface metadata | 10 read-only project subagents |
| Hooks | 1 Graphify, 3 Ponytail | None enabled, and no `.claude/settings.json` was created |

## Skills

Format: NAME | TYPE | SOURCE | VERSION | ENTRY POINT | COMPATIBILITY | STATUS

| Name | Type | Source | Version | Entry point | Compatibility | Status |
| --- | --- | --- | --- | --- | --- | --- |
| alfred-project-context | Project | `.agents/skills` | Unversioned | SKILL.md | Yes | RECOVERED, imported unchanged |
| alfred-finance-correctness | Project | `.agents/skills` | Unversioned | SKILL.md | Yes | RECOVERED, imported unchanged |
| alfred-travel-engineering | Project | `.agents/skills` | Unversioned | SKILL.md | Yes | RECOVERED, imported unchanged |
| alfred-security-review | Project | `.agents/skills` | Unversioned | SKILL.md | Yes | RECOVERED, imported unchanged |
| alfred-release-gate | Project | `.agents/skills` | Unversioned | SKILL.md | Yes | RECOVERED, imported unchanged |
| security-best-practices | Third party | `.agents/skills` (JetBrains/skills lock entry; authored by OpenAI) | Unversioned | SKILL.md | Yes | Imported unchanged |
| security-threat-model | Third party | `.agents/skills` (JetBrains/skills lock entry) | Unversioned | SKILL.md | Yes | Imported unchanged |
| graphify | Third party | `.codex/skills` | 0.9.76 | SKILL.md | Partial: CLI blocked on this host | Imported, runs only when invoked by name |
| ponytail, -audit, -debt, -gain, -help, -review | Third party, MIT | Codex plugin cache | 5.3.3 (4.11.0 not present) | SKILL.md | Yes, skills only | Imported, run only when invoked by name |
| gstack and gstack-* (56) | Third party | `~/.codex/skills` | 1.91.22.0 | SKILL.md | Not verified | DISABLED_PENDING_APPROVAL, not imported |
| integration-resilience-engineer, observability-integrator, performance-concurrency-advisor, schema-migration-planner, test-suite-builder, transaction-consistency-designer, project-context-ingestion | Third party | `.agents/skills` | Unversioned | SKILL.md | No: written for Kotlin and Spring | Not imported |
| refactoring-code | Third party | `.agents/skills` | Unversioned | SKILL.md | No: requires Rider | Not imported |
| playwright | Third party | `.agents/skills` | Unversioned | SKILL.md | Not needed: project tests use Selenium, and it depends on playwright-cli | Not imported |
| imagegen, openai-docs, review-agent, skill-installer | Codex system | `~/.codex/skills/.system` | Unversioned | SKILL.md | Codex only | Not imported |
| skill-creator | System | Codex system and Claude synced | Unversioned | SKILL.md | Yes | Existing global Claude entry reused |
| 12 other claude.ai synced skills | User | `~/.claude/skills/synced` | Managed | SKILL.md | Yes | Existing global entries reused |
| aws-security, aws-sdk-python-usage, other Bedrock or AWS skills, web-design-guidelines | Requested | Not found | None | None | None | MISSING, not invented |

No skill was newly created because all 5 ALFRED skills already existed. The legacy checkout's copies are older: its `alfred-project-context` still points to retired audit files. They were left in place and not imported.

Adaptation: the 7 Graphify and Ponytail `SKILL.md` copies gained `disable-model-invocation: true`. This keeps Graphify from trying a blocked CLI and keeps Ponytail's minimal-change rules out of finance and security work unless someone asks for them.

## Agents

| Discovered | Type | Status |
| --- | --- | --- |
| Claude agent definitions | None in repo, legacy or user folders | Nothing to convert |
| `agents/openai.yaml` in 10 `.agents` skills and in gstack skills | Codex interface metadata, not role prompts | Not converted |
| Development Council roles in `scripts/development_council.py` | Runtime system | Kept separate. `alfred_ai/council/` does not exist |

Configured as NEWLY_CREATED in `.claude/agents/`: project-architect, django-backend-reviewer, financial-correctness-auditor, security-privacy-auditor, ai-ml-auditor, investment-wealth-auditor, travel-career-reviewer, windows-release-auditor, test-quality-reviewer and independent-code-reviewer. Each is limited to Read, Grep and Glob, so none can edit files or run commands.

## Hooks

| Hook | Source | Finding | Status |
| --- | --- | --- | --- |
| `graphify hook-check` on PreToolUse Bash | `.codex/hooks.json` | Deliberate no-op. `graphify.exe` is blocked by Windows Application Control, so a direct copy would fail on each match | DISABLED_PENDING_APPROVAL |
| `graphify hook-guard search` | Graphify 0.9.76 | Valid Claude output through the uv tool Python. It tells Claude to run `graphify query` first, which the blocked command cannot do | DISABLED_PENDING_APPROVAL |
| Ponytail session_start | Codex plugin | Injects rules into every session, writes flag files and can prompt for status-line setup | DISABLED_PENDING_APPROVAL |
| Ponytail user_prompt_submit | Codex plugin | Tracks mode on each prompt and writes state | DISABLED_PENDING_APPROVAL |
| Ponytail subagent_start | Codex plugin | Injects rules into every subagent, including audit agents | DISABLED_PENDING_APPROVAL |
| Ponytail claude-band | Claude plugin manifest | Declares no hook events, only a UI module | Not imported |

No pre-tool safety, post-edit, privacy, release, session or checkpoint hook exists in any inspected location. No Git hook is active. Codex's `notify` setting is not a project hook and was left alone. No replacement hook was invented, because `CLAUDE.md` already covers session orientation.

## Verification

A read-only validation script run at this HEAD found 0 problems:

- 14 skills have valid frontmatter, and their references resolve.
- 10 agents have matching names, read-only tools and existing preloaded skills.
- The 7 imported `.agents` skills match their sources byte for byte.
- `.codex/hooks.json`, the Codex Graphify skill and `AGENTS.md` hashes are unchanged.
- Git shows only `.claude/`, `CLAUDE.md` and this file as new. No tracked file changed.
- A scan of the new files found no credential patterns, personal paths or account email.
- `~/.claude/settings.json` is unchanged in keys, and no Ponytail flag file was created.

After the session reloaded the project:

- `CLAUDE.md` and the imported `AGENTS.md` loaded as project instructions.
- All 7 skills that Claude may call were listed, and `alfred-project-context` loaded when invoked.
- All 10 agents were invoked. Each read a repository file, reported its preloaded skills, and reported no tool that can write files or run commands. These are the agents' own reports of their tools, and no write was attempted.

In a separate non-interactive Claude Code process, run on a clean export of only the staged files:

- All 5 ALFRED skills and all 10 agents were discovered.
- Every agent's preloaded skills are present in the export.
- `CLAUDE.md` loaded. The export used a stub `AGENTS.md`, so that import was not retested there.

Not verified:

- The 7 Graphify and Ponytail skills can only be started by a person, so they have not been run.
- A real `git clone` of a commit has not been tested, because nothing is committed.

## Owner approvals

1. Graphify: allow `graphify.exe` under Windows Application Control, or approve a project wrapper. Calling the CLI can also refresh installed skill copies, so approve that behavior too.
2. Ponytail hooks: approve them only if its rules should apply to every session. Installing the plugin from its marketplace also needs approval.
3. gstack: choose any read-only skills to import. Its preamble runs helper scripts, its folder includes telemetry and update helpers, and several skills ship, deploy or import browser cookies.

## Limitations

- `.gitignore` excludes `/.claude/skills/` and was not changed. Only the 5 ALFRED skills are tracked, added with `git add -f`. The security, Graphify and Ponytail copies stay local, so a fresh clone will not have them. A new skill in that folder also needs `git add -f`; edits to tracked skills do not.
- `security-privacy-auditor` preloads only `alfred-security-review`, so every committed agent works from committed skills.
- Skill copies can drift from `.agents/skills`, which remains the source for the ALFRED skills. `skills-lock.json` does not track the Claude copies.
- `AGENTS.md` tells agents to use Graphify first. `CLAUDE.md` overrides that for Claude Code on this host until approval 1 is resolved.
