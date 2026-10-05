# Ollama and Codex after ALFRED recovery

Recorded 2026-10-06. This is a later setup plan, not an installation performed before the wipe. First restore and verify ALFRED using [the encrypted recovery guide](../../docs/WINDOWS_ENCRYPTED_RECOVERY.md). Keep the temporary remote backup until all restore gates pass and the user explicitly confirms its deletion.

```text
ALFRED development
        |
      Codex
        |
   +----+----------------+
   |                     |
Ollama local         Hosted Codex
   |                     |
routine work        difficult/high-risk work
```

| Local Ollama through Codex | Hosted Codex |
|---|---|
| Code navigation, documentation, test generation | Financial calculations, loan and net-worth semantics, tax engine |
| Small bug fixes, boilerplate, simple refactors | Database migrations, authentication, security, SSRF |
| CSS/templates, logging, routine cleanup | Encryption/key rotation, family privacy, concurrency |
| Low-risk Travel/UI work | Native-runtime failures, architecture changes, release-critical debugging |

Choose the hosted route at the start when a task touches the right column. Both routes follow `AGENTS.md`, the project-local ALFRED skills, monetary/privacy rules and existing verification gates. Use synthetic test data and keep private runtime data and secrets out of prompts and source commits. ALFRED remains a local/LAN application.

## Later installation and verification

1. Complete source/private-data recovery and verify finance records, media, Travel and native runtime first.
2. Reinstall the tools listed in [AGENT_TOOLS_REINSTALL.md](AGENT_TOOLS_REINSTALL.md). Recheck CLI versions and supported flags after reinstall.
3. Consult [HARDWARE_BASELINE.md](HARDWARE_BASELINE.md), install the appropriate driver, and verify the current official Ollama hardware/backend requirements. The recorded RX 6700 XT memory is not a promise of acceleration. Select a compatible coding model only after checking usable RAM/VRAM, context requirements and actual tool use.
4. Install Ollama and obtain the selected model at that time. Check `ollama --version` and `ollama list`, then run a small disposable coding task and its tests before allowing edits to ALFRED.
5. From the source Git root, start one provider intentionally. The current CLI supports these later command templates:

```powershell
# Local provider: replace the placeholder with an installed, validated model name.
codex.cmd --oss --local-provider ollama --model 'REPLACE_WITH_VALIDATED_MODEL'

# Hosted provider: use normal interactive authentication and the hosted configuration.
codex.cmd
```

The local command explicitly chooses Ollama for that session. Keep normal Codex configured for the hosted provider; do not silently change the shared default or build an automatic routing service. [OpenAI's OSS/local-provider documentation](https://learn.chatgpt.com/docs/config-file/config-advanced#oss-mode-local-providers) confirms `--oss` and `--local-provider`. The current IDE Codex 0.159.3 help also exposes both flags; verify them again against the reinstalled CLI. No model or provider configuration was installed by this document.

## Repeated local failure

If the local session repeats the same failure twice, or encounters a high-risk domain, stop its active work cleanly. Inspect the working tree, preserve useful changes, and update `artifacts/audit/CODEX_CONTINUATION_STATE.md` with the task, current branch/HEAD, changed files, exact failing tests, observed failure and next action. Do not include secrets or private test data.

Start hosted Codex from that checkpoint and continue the same task. Review the existing diff before editing, rerun only checks justified by changes or unresolved failures, and retain completed verification. Do not reset the task, discard the useful diff or loop through the same local attempt indefinitely. This handoff also applies to historically compromised signing-key rotation after restoration.
