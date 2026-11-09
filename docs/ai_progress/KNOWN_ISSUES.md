# Known issues and gates

- **USE-02 bounded repair accepted locally:** bank statements now stage previews
  before canonical writes, including retries. Source0f35605 and evidence are indexed.
  Loan review is also accepted locally at88c1df8; other modules still need their own confirmation work. Next is investments.
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

- Loan review limits:100 rows/2 MiB structured extraction,10 per page,24-hour
  draft/30-minute token. Edited drafts cannot be overwritten by retry; re-upload
  the retained original if an edited draft expires. No balance overwrite/closure
  or currency inference; unsupported/missing terms require owner correction.
- Four loan Axe audits have no automated violations, but gradient contrast remains
  manually unverified. Source package, real owner acceptance and independent review
  are still outstanding. No current installer was built or replaced in this slice.

- Fixed atc2d1517: removing legacy loan sources no longer deletes canonical loans.
  Investment upload/retry/correction still contain automatic holding writes; next
  selected scope is their review/confirmation. This is source tracing, not accepted
  investment usability. Investment source removal also needs preservation review.
