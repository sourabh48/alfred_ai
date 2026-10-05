# Windows reinstall checklist

This checklist covers preparation before complete PC cleanup. `F:\ALFRED` is the actual checkout. The current plan has no reliable retained local disk: follow `WINDOWS_ENCRYPTED_RECOVERY.md` and do not wipe until both permanent source and the separate PRIVATE encrypted GitHub recovery repository are verified.

## Before reinstall

- [ ] All intended source, migrations, templates, static assets, tests, dependencies, CI, scripts and project-local skills are committed.
- [ ] Git working tree is clean or every remaining item is understood; `git status` and `git diff --check` pass.
- [ ] Latest branch commit is pushed; `git ls-remote origin refs/heads/codex/native-runtime-hardening-20260918` equals `git rev-parse HEAD`.
- [ ] Current tracked tree has no real secrets, private documents, databases, tokens, profiles, logs or runtime backups.
- [ ] No required source exists only on the old Windows installation; an isolated source/dependency rebuild has passed.
- [ ] Temporary staging is outside source; only encrypted archives and safe metadata enter a separate PRIVATE GitHub repository. Permanent source remains source-only.
- [ ] ALFRED writers are stopped cleanly; both `F:\ALFRED` and `%LOCALAPPDATA%\ALFRED` private state are backed up.
- [ ] Any historical Docker/WSL data is accounted for; an inactive Compose configuration is not proof its former data never existed.
- [ ] Private local config and original native secret keys are included; do not replace keys for an existing database.
- [ ] Internal detailed manifest is encrypted; safe public manifest and every archive-part SHA256 are complete. Original/copied databases pass integrity checks.
- [ ] Git LFS upload is complete; a fresh GitHub clone downloads actual content; downloaded hashes, interactive archive decryption/test, extraction and SQLite checks pass.
- [ ] Strong archive password is recoverable OFF this PC and was never placed in chat, Git, scripts, arguments or logs.
- [ ] Independent password manager/secret source is accessible without this Windows installation. Do not put secret values into Git.
- [ ] GitHub sign-in/2FA/recovery or SSH-key recovery is available independently. Active CLI authentication on this machine is insufficient.
- [ ] Agent tools and their versions, global/project paths and reinstall verification commands are documented in `artifacts/reinstall/AGENT_TOOLS_REINSTALL.md`.
- [ ] Windows installation media and required drivers are available independently.
- [ ] Target cleanup disks are known; remote temporary backup will survive until proven post-Windows recovery and later explicit remote-deletion confirmation.
- [ ] `artifacts/reinstall/PRE_REINSTALL_FINAL_STATUS.md` explicitly reports a completed gate and `SAFE TO REINSTALL WINDOWS = YES`.

Useful final read-only commands:

```powershell
git status
git diff --check
git rev-parse HEAD
git ls-remote origin refs/heads/codex/native-runtime-hardening-20260918
```

The plaintext staging script requires an explicit destination outside Git. Follow its quiescence instructions. Local staging is temporary and is not sufficient evidence of remote recovery.

## After reinstall

Use `docs/WINDOWS_ENCRYPTED_RECOVERY.md` and `docs/WINDOWS_SETUP.md`. No post-Windows restore steps are executed during this preparation task.
