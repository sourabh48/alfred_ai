---
name: alfred-security-review
description: Perform a requested, scoped security or privacy review of ALFRED endpoints, document ingestion, provider calls, runtime configuration, or repository contents.
---

# ALFRED security review

- Establish the requested scope through `AGENTS.md`, a scoped graph query and the relevant current backlog item. Do not expand ordinary feature work into an unsolicited full security audit.
- ALFRED contains private financial documents and Travel data. Report only redacted findings, variable names and safe metadata; never print credentials, tokens, private transaction content or uploaded documents.
- Trace the shared trust boundary and every caller before proposing a fix. Check owner scoping, authentication/CSRF, validation, URL/DNS restrictions and atomic error behavior where those controls are involved.
- Review current local/LAN defaults and actual runtime paths. Keep real configuration, databases, uploads, private model data, browser profiles and backups out of Git; safe examples must contain placeholders only.
- Distinguish a confirmed exploit or exposed secret from a heuristic match. Removing a secret from current files does not remove Git history; flag rotation/history work separately without rewriting history on your own.
- Preserve existing URL/provider security checks in production when making tests deterministic. Leave a minimal runnable regression for an actionable security fix, using isolated synthetic data.
