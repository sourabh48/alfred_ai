# Windows reinstall checklist

This checklist covers preparation before complete PC cleanup. `F:\ALFRED` is the actual checkout. The current plan has no reliable retained local disk: follow `WINDOWS_ENCRYPTED_RECOVERY.md` and do not wipe until both permanent source and the separate PRIVATE encrypted GitHub recovery repository are verified.

## Before reinstall

- [ ] All intended source, migrations, templates, static assets, tests, dependencies, CI, scripts and project-local skills are committed.
- [ ] Git working tree is clean or every remaining item is understood; `git status` and `git diff --check` pass.
- [ ] Latest branch commit is pushed; `git ls-remote origin refs/heads/codex/native-runtime-hardening-20260918` equals `git rev-parse HEAD`.
- [ ] Current tracked tree has no real secrets, private documents, databases, tokens, profiles, logs or runtime backups.
- [ ] No required source exists only on the old Windows installation; an isolated source/dependency rebuild has passed.
- [ ] Temporary staging is outside source; the Desktop handoff bundle has been copied to the retained pendrive. Private runtime data remains AES-256/header-encrypted; permanent source remains source-only. A Desktop-only copy will be erased.
- [ ] ALFRED writers are stopped cleanly; both `F:\ALFRED` and `%LOCALAPPDATA%\ALFRED` private state are backed up.
- [ ] Any historical Docker/WSL data is accounted for; an inactive Compose configuration is not proof its former data never existed.
- [ ] Private local config and original native secret keys are included; do not replace keys for an existing database.
- [ ] Internal detailed manifest is encrypted; safe public manifest and every archive-part SHA256 are complete. Original/copied databases pass integrity checks.
- [ ] The actual pendrive copy passes hashes, interactive archive decryption/test, extraction, all internal file hashes and SQLite checks. If choosing the optional GitHub method instead, require PRIVATE visibility, complete LFS upload and a fresh remote download passing the same checks.
- [ ] Strong archive password is recoverable OFF this PC and was never placed in chat, Git, scripts, arguments or logs.
- [ ] Independent password manager/secret source is accessible without this Windows installation. Do not put secret values into Git.
- [ ] GitHub sign-in/2FA/recovery or SSH-key recovery is available independently. Active CLI authentication on this machine is insufficient.
- [ ] Agent tools and their versions, global/project paths and reinstall verification commands are documented in `artifacts/reinstall/AGENT_TOOLS_REINSTALL.md`.
- [ ] Windows installation media and required drivers are available independently.
- [ ] Target cleanup disks are known; the verified backup pendrive is safely ejected/disconnected before wiping and is not reformatted into installation media. Keep it until post-Windows data/source/native recovery is proven. For the optional GitHub method, retain its remote repository until recovery and later explicit deletion confirmation.
- [ ] `artifacts/reinstall/PRE_REINSTALL_FINAL_STATUS.md` explicitly reports a completed gate and `SAFE TO REINSTALL WINDOWS = YES`.

Useful final read-only commands:

```powershell
git status
git diff --check
git rev-parse HEAD
git ls-remote origin refs/heads/codex/native-runtime-hardening-20260918
```

The plaintext staging script requires an explicit destination outside Git. Follow its quiescence instructions. Local staging and the Desktop bundle are temporary; only verification from the retained pendrive (or optional remote backup) proves the selected recovery path.

## After reinstall

Use `docs/WINDOWS_ENCRYPTED_RECOVERY.md` and `docs/WINDOWS_SETUP.md`. No post-Windows restore steps are executed during this preparation task.
