---
name: alfred-release-gate
description: Prepare or evaluate an explicitly requested ALFRED local Windows release, packaging gate, clean-source push, or pre-reinstall readiness checkpoint.
---

# ALFRED release gate

- Read `AGENTS.md`, current continuation state and the release/checkpoint documents relevant to the requested action. Inspect branch, HEAD, intended diff and remote before changing Git or packaging state.
- Preserve local/LAN hosting. Use current `docs/NATIVE_WINDOWS.md`, build scripts and CI as the source of launch/build commands; do not add cloud deployment wiring.
- Verify no required source, migrations, templates, static source, tests or reusable project skills exist only locally. Exclude operator secrets/data, generated binaries, caches and browser profiles from source commits.
- Run Django system checks and migration-drift checks in isolated local-runtime configuration. Run relevant tests, and the complete backend/appropriate browser or packaging gate when required by the release scope. Record exact counts, skips, failures and evidence; never infer success from an earlier source state.
- Commit/push, installer promotion and live data migrations require authorization for that action. A release-preparation request alone does not imply every external or irreversible action.
- For pre-Windows preparation, use `docs/WINDOWS_REINSTALL_CHECKLIST.md` and `artifacts/reinstall/`; verify the separate private backup and remote HEAD. Do not execute post-reinstall restoration steps. Say Windows is safe to reinstall only when every documented readiness condition is met.
