# ALFRED agent tooling before Windows reinstall

Inventory date: 2026-10-06. Repository root: `F:\ALFRED` on this machine; `alfred_ai/` is its Python package. Versions were rechecked for the final pre-wipe checkpoint. This records the current installation and later reinstall commands. No tool installation, authentication restoration or post-Windows application restore was performed as part of this inventory.

## Current machine installation

| Tool | Observed version | Actual location / scope | Verification performed before reinstall |
|---|---|---|---|
| Codex used by this IDE | CLI 0.159.3; ACP adapter directory 2.1.1 | `%LOCALAPPDATA%\JetBrains\PyCharm2026.2\acp-agents\codex-acp\2.1.1\node_modules`; IDE-managed | `codex.cmd --version` |
| Separate Codex npm installation | CLI 0.160.0 | `%APPDATA%\npm\node_modules\@openai\codex`; user-global | Explicit `%APPDATA%\npm\codex.cmd --version` |
| Claude Code | 2.1.289 | `%APPDATA%\npm\node_modules\@anthropic-ai\claude-code`; user-global | `claude.cmd --version` |
| Graphify (`graphifyy`) | 0.9.76 | `%APPDATA%\uv\tools\graphifyy`; launcher `%USERPROFILE%\.local\bin\graphify.exe`; isolated user tool | `graphify --version` and scoped query against the current project graph |
| uv | 0.12.23 | WinGet installation of `astral-sh.uv` | `uv --version` |
| gstack | 1.91.22.0; source commit `f97aefe654fbe265a3c978d34865b5aa493e7453` | Source `%USERPROFILE%\gstack`; generated user Codex skills `%USERPROFILE%\.codex\skills\gstack*` | `./setup --status` in Git Bash: global Codex install current, experimental tier; 20 router section links resolve |
| Ponytail | 4.13.0 | Codex user plugin cache `%USERPROFILE%\.codex\plugins\cache\ponytail\ponytail\4.13.0` | Both plugin manifests inspected; `codex.cmd plugin --help` confirms plugin commands exist |
| skills CLI | 1.7.0 | npm `npx` cache, not a project dependency or global executable | Cached CLI run with `node <cached skills path> --version` |
| Node / npm | Node 24.13.0 / npm 11.6.2 | IDE-managed runtime `%LOCALAPPDATA%\JetBrains\PyCharm2026.2\acp-agents\.runtimes\node\24.13.0` | `node --version`, `npm.cmd --version` |
| Bun | 1.4.2 | `%USERPROFILE%\.bun\bin\bun.exe`; user-global | `bun --version` |

PowerShell's current execution policy blocks npm-generated `.ps1` shims. The `.cmd` launchers worked without changing that policy. The IDE's PATH currently selects its Codex 0.159.3 before the separate npm 0.160.0 install; these are two installations, not conflicting reported versions.

Node/npm/Bun are agent-tool prerequisites here, not ALFRED's Django application dependency mechanism. Reinstall an independent Node LTS runtime for terminal tools rather than relying on an IDE's internal runtime path. No Java requirement was identified for these tools or the application. gstack's optional native CSO capability has additional C++ prerequisites; it is not needed to launch ALFRED.

## Project-local files to preserve in Git

- `AGENTS.md`: local/LAN hosting, secret handling and Graphify workflow.
- `.agents/skills/alfred-project-context/SKILL.md`
- `.agents/skills/alfred-finance-correctness/SKILL.md`
- `.agents/skills/alfred-travel-engineering/SKILL.md`
- `.agents/skills/alfred-security-review/SKILL.md`
- `.agents/skills/alfred-release-gate/SKILL.md`
- The existing 11 canonical upstream skill folders under `.agents/skills/`, including `project-context-ingestion`, their supporting resources/licenses, and `skills-lock.json` (public source names and content hashes).
- `.codex/skills/graphify/`: existing project-local Graphify instructions/references and version marker 0.9.76.
- `.codex/hooks.json`: existing relative `graphify hook-check` command; no embedded credential or machine path.

The five ALFRED-specific definitions were created during the earlier pre-wipe preparation using the agreed current engineering rules and are now committed. They are concise instruction-only skills; cloning the project preserves them without an installer. Current Codex discovers repository `.agents/skills` automatically. [Official skill discovery documentation](https://learn.chatgpt.com/docs/build-skills).

The upstream `project-context-ingestion`, integration, observability, performance, migration, transaction and test-builder skills explicitly target Kotlin/Spring. They are preserved reusable definitions, not instructions to install Java or convert this Django project. Use `alfred-project-context` for ALFRED orientation.

## Machine state excluded from Git

`F:\ALFRED\.claude\skills\*` currently consists of Windows directory junctions with absolute targets in `F:\ALFRED\.agents\skills`. They are disposable host aliases; preserve their canonical targets, not the junctions. Recreate Claude discovery after reinstall if needed using the command below.

Do not commit or wholesale copy `%USERPROFILE%\.codex`, `%USERPROFILE%\.claude`, `%USERPROFILE%\.gstack`, `%APPDATA%\npm`, npm caches, uv tool environments, Bun binaries, IDE agent runtimes, plugin caches, browser profiles or agent conversation/session history. Reinstall public tools and sign in again. Authentication/configuration may contain private material and belongs only in a separately protected private backup if the user chooses to preserve it. This inventory never reads or records token values.

`graphify-out/` is generated project graph/cache state, including old-machine interpreter/root pointers. It is regenerated from source; it is not required to build ALFRED. The earlier temporary Graphify helper installation and its recorded temp path are not restore dependencies. Keep Graphify separate from `.venv` because its dependency versions can differ from application requirements.

## Later reinstall commands (documentation only)

These commands are for the later tooling restore task. Review upstream instructions again when performing it; no command in this section was executed now. Install Git for Windows/Git Bash and a supported Node LTS first; skills CLI 1.7.0 requires Node >=22.20.0 and current gstack requires Bun >=1.4.0. Install Bun using its [official Windows instructions](https://bun.sh/docs/installation). Keep agent tools outside the ALFRED application venv.

### Codex and Claude Code

For the same terminal package versions observed here:

```powershell
npm.cmd install -g @openai/codex@0.160.0
npm.cmd install -g @anthropic-ai/claude-code@2.1.289
codex.cmd --version
claude.cmd --version
```

Use the same install commands with `@latest` when deliberately updating. The npm installation methods are documented by [OpenAI](https://learn.chatgpt.com/docs/codex/cli) and [Anthropic](https://code.claude.com/docs/en/setup#install-with-npm). Current native installers are alternatives; use one installation method intentionally. Reinstall the IDE and its Codex integration separately if that interface is wanted; let the IDE manage its adapter rather than copying old `AppData` binaries. Sign in through each tool's normal interactive flow later; do not transfer secrets into the repository.

### Graphify

Install uv from its [official installation instructions](https://docs.astral.sh/uv/getting-started/installation/) (Windows supports `winget install --id astral-sh.uv -e`). Then:

```powershell
uv tool install graphifyy==0.9.76
graphify --version
graphify update . --no-cluster
graphify query 'ALFRED local runtime' --budget 800
```

Run the last two commands from the cloned Git root, with a fresh terminal after adding the tool launcher directory to PATH if needed. `update` is the project's AST-only code refresh, with no API key/model call; private runtime documents must remain outside the source scan. To deliberately update the CLI later use `uv tool upgrade graphifyy`, reviewing any skill change first. The existing project skill is already preserved; `graphify install` is available if registering skills for another host is needed. [Graphify's upstream install/usage instructions](https://github.com/Graphify-Labs/graphify).

### gstack

Use Git Bash, not PowerShell, for these upstream shell commands. Clone outside ALFRED:

```bash
git clone https://github.com/garrytan/gstack.git ~/gstack
cd ~/gstack
git checkout f97aefe654fbe265a3c978d34865b5aa493e7453
./setup --host codex
./setup --status
```

The pinned commit reproduces the recorded source. For a deliberate newer install, use the current upstream branch and rerun `./setup --host codex`; `/gstack-upgrade` is its registered update workflow. `--host claude` can be added later if Claude skills are wanted; this machine's recorded gstack install targets Codex only. Browser skills also need Node and Bun on PATH on Windows. [Upstream Windows and host setup instructions](https://github.com/garrytan/gstack#other-ai-agents).

### Ponytail

```powershell
codex.cmd plugin marketplace add DietrichGebert/ponytail
codex.cmd plugin add ponytail@ponytail
codex.cmd plugin list
```

Later, review/trust the plugin's lifecycle hooks in `/hooks` and start a new thread. Check the installed plugin version; the command installs the marketplace version available then and does not guarantee 4.13.0. Claude Code's alternative is two separate interactive prompts, `/plugin marketplace add DietrichGebert/ponytail` then `/plugin install ponytail@ponytail`. [Ponytail's upstream instructions](https://github.com/DietrichGebert/ponytail#install).

### skills CLI and repository skills

The CLI can be used without a global install:

```powershell
npx.cmd --yes skills@1.7.0 --version
npx.cmd --yes skills@1.7.0 list
```

The canonical repository skills already arrive with Git. To make the five ALFRED definitions discoverable by Claude Code later, from the repository root:

```powershell
npx.cmd --yes skills@1.7.0 add ./.agents/skills --skill alfred-project-context alfred-finance-correctness alfred-travel-engineering alfred-security-review alfred-release-gate --agent claude-code --copy
```

This creates host-local copies/aliases; do not replace the canonical versioned definitions or commit machine aliases. To reinstall the existing upstream `project-context-ingestion` independently, use `npx.cmd --yes skills@1.7.0 add JetBrains/skills --skill project-context-ingestion --agent codex --global`. It is optional and Kotlin-specific. Review updates rather than automatically overwriting the project's preserved skill files. [skills CLI commands](https://github.com/vercel-labs/skills).

## Pre-reinstall verification and limits

Tool versions and public upstream install commands were checked. Graphify executes on the existing graph; gstack's read-only status verifies its current generated routing. The gstack source checkout and Ponytail cached checkout have no working-tree changes to preserve. All five ALFRED definitions passed Codex's bundled skill validator and the PowerShell check below. A read-only `skills@1.7.0 add ./.agents/skills --list` discovers all 16 canonical project skills, including the five new ALFRED definitions. The source Git verification must include their canonical files, not old-machine junctions.

In a clean checkout, this check uses only PowerShell:

```powershell
$alfredSkills = 'alfred-project-context','alfred-finance-correctness','alfred-travel-engineering','alfred-security-review','alfred-release-gate'
foreach ($skill in $alfredSkills) {
    $skillPath = Join-Path '.agents/skills' "$skill/SKILL.md"
    if (-not (Test-Path -LiteralPath $skillPath -PathType Leaf)) { throw "Missing project skill: $skill" }
    if (-not (Select-String -LiteralPath $skillPath -Pattern "^name: $skill$" -Quiet)) { throw "Invalid project skill name: $skill" }
    Get-FileHash -LiteralPath $skillPath -Algorithm SHA256
}
```

No fresh Windows reinstall or tool reinstall is claimed. Tools require their public distribution sources and, for provider-backed sessions, the user's account/access recovery. Global conversation history and plugin caches are not required to rebuild or resume ALFRED from its versioned checkpoint. A general `setup_agent_tools.ps1` was intentionally omitted: host-specific installers, interactive sign-in and hook trust should remain explicit instead of a script silently changing every tool installation.

Ollama is deferred until ALFRED has been restored and verified. See [HARDWARE_BASELINE.md](HARDWARE_BASELINE.md) and [OLLAMA_CODEX_HYBRID_PLAN.md](OLLAMA_CODEX_HYBRID_PLAN.md); no model installation is part of this pre-wipe inventory.
