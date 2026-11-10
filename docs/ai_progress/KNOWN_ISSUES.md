# Known issues and gates

## Offline overview limits

Bounded record recoveryebbd056 handles existing supported canonical finance,
statement, loan, investment/budget and reviewed-document questions. It supplies
source cards, without a model explanation. It does not repair vault/key errors,
answer unsupported scenarios or activate arbitrary tools/MCP/cloud providers.
Timeouts remain bounded by the existing local deadline. Full USE-04 and release
acceptance remain open. Source-card baseline metadata currency bug selected next.

## Bound actions - remaining scope

The locally accepted savings-goal hardening0ca2168 fixes server binding, expiry,
stale review, replay, cancellation and retry. It does not accept full USE-05.
Only the existing deterministic savings-goal actions are exposed; no external
writes or new actions/MCP servers. Audit deletion invalidates old cards; page
reload requires a new review for unsaved cards. Old clients must reload for IDs.
Owner/manual contrast/independent/CI/package/upgrade acceptance remains open.

- **USE-02 bounded repairs accepted locally:** statements0f35605, loans88c1df8
  and investmentsb42988b stage owned previews before confirmed canonical writes.
  Broader real-document/provider/owner/package acceptance remains separate.
- Statement limits: 2000 rows /8 MiB structured extraction,100 rows/page,24-hour
  extraction lifetime,30-minute confirmation token. Edited previews are protected
  from retry overwrite; re-upload the retained original for an expired edited draft.
- Statement confirmation does not approve automatic loan postings or closures.
  Those require separately reviewed domain actions. No second money engine introduced.
- Source-center hub is partial onboarding: saved/parser counts are not verification;
  knowledge readiness and complete confirmation/correction journeys remain.
- Conversation continuity is bounded general local dialogue only. Saved encrypted
  history still requires its operator/owner gates. Bounded answer stylesb535299,
  revision-bound rename/title searcha173b3e and page-only dialoguec365a38 accepted
  locally. Title search covers titles, not transcript bodies. Page-only local general
  streaming/cancellation0712fa2 is locally accepted; saved-history/domain/cloud
  streaming and broader model routing remain. Bounded final-answer Markdown/tables
  a74995c accepted locally; nested/advanced syntax and code colouring remain.
  Source-backed/financial
  output is buffered for final validation. No full assistant parity claim.
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
  Investment upload/retry/correction now stage owned drafts atb42988b. Existing
  holdings remain unchanged when linked or when their sources are removed.

- Investment review bounds:100 rows/2 MiB structured extraction,10 per page,
 24-hour draft/30-minute confirmation. Existing holding updates use separate edit
  controls. Expired edited drafts need a new source upload; their corrections are
  preserved. Source-currency evidence stays unknown when the PDF did not establish it.
- Manual gradient contrast, real email-provider acceptance, owner runtime/installer,
  complete source-specific onboarding, streaming/tools/actions and2.0 release remain
  open. Current task is READY_FOR_NEXT; no subsequent task was automatically selected.
