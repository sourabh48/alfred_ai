# Windows reinstall checklist

This checklist covers preparation before reinstalling Windows. Do not format a volume containing the repository or private backup. `F:\ALFRED` is the actual checkout.

## Before reinstall

- [ ] All intended source, migrations, templates, static assets, tests, dependencies, CI, scripts and project-local skills are committed.
- [ ] Git working tree is clean or every remaining item is understood; `git status` and `git diff --check` pass.
- [ ] Latest branch commit is pushed; `git ls-remote origin refs/heads/codex/native-runtime-hardening-20260918` equals `git rev-parse HEAD`.
- [ ] Current tracked tree has no real secrets, private documents, databases, tokens, profiles, logs or runtime backups.
- [ ] No required source exists only on the old Windows installation; an isolated source/dependency rebuild has passed.
- [ ] Backup destination is chosen and confirmed untouched by the reinstall. E/F/G are on the same physical SATA disk; C is a separate NVMe disk. Confirm disk identity before formatting.
- [ ] ALFRED writers are stopped cleanly; both `F:\ALFRED` and `%LOCALAPPDATA%\ALFRED` private state are backed up.
- [ ] Any historical Docker/WSL data is accounted for; an inactive Compose configuration is not proof its former data never existed.
- [ ] Private local config and original native secret keys are included; do not replace keys for an existing database.
- [ ] Timestamped backup manifest exists; each SHA256 is independently checked and copied databases pass integrity checks. Backup is readable from the untouched destination.
- [ ] Independent password manager/secret source is accessible without this Windows installation. Do not put secret values into Git.
- [ ] GitHub sign-in/2FA/recovery or SSH-key recovery is available independently. Active CLI authentication on this machine is insufficient.
- [ ] Agent tools and their versions, global/project paths and reinstall verification commands are documented in `artifacts/reinstall/AGENT_TOOLS_REINSTALL.md`.
- [ ] Windows installation media and required drivers are available independently.
- [ ] `artifacts/reinstall/PRE_REINSTALL_FINAL_STATUS.md` explicitly reports a completed gate and `SAFE TO REINSTALL WINDOWS = YES`.

Useful final read-only commands:

```powershell
git status
git diff --check
git rev-parse HEAD
git ls-remote origin refs/heads/codex/native-runtime-hardening-20260918
```

The backup script requires an explicit destination. Follow its documented quiescence instructions; never use the repository or a directory beneath it as the backup destination.

## After reinstall

Use the separate post-reinstall prompt and `docs/WINDOWS_SETUP.md`. No post-Windows restore steps are executed during this preparation task.
