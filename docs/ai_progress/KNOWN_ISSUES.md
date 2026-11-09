# Known issues and gates

- **USE-02 bounded repair accepted locally:** bank statements now stage previews
  before canonical writes, including retries. Source0f35605 and evidence are indexed.
  Other module imports still require their own preview/confirmation work; next is loans.
- Statement limits: 2000 rows /8 MiB structured extraction,100 rows/page,24-hour
  extraction lifetime,30-minute confirmation token. Edited previews are protected
  from retry overwrite; re-upload the retained original for an expired edited draft.
- Statement confirmation does not approve automatic loan postings or closures.
  Those require separately reviewed domain actions. No second money engine introduced.
- Source-center hub is partial onboarding: saved/parser counts are not verification;
  knowledge readiness and complete confirmation/correction journeys remain.
- Conversation continuity is bounded general local dialogue only. Streaming,
  cancellation, search/rename, answer budgets and broader model routing remain.
- Existing savings-goal action flow still requires scoped hardening review before extension.
- No application MCP server/source connection is configured. Host tools available
  to Codex do not automatically become tools available inside ALFRED.
- 2.0 exact-head CI, current packaging, owner/independent/separate-PC/accessibility
  acceptance and installation promotion remain open per canonical trackers.
- Alternate runtime databases exist. Selected populated runtime was verified at
  F:/ALFRED/restored-runtime; no owner runtime changes are authorized by tests.
- Existing materialized_cache.py working edit is unrelated and must be preserved.

Resolved checkpoint blocker: repository author identity recovered from existing
Git history; command-scoped identity used for local commits. No global Git config
or remote publication changed.
