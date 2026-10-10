# Controlled M14 promotion plan — prepared, not executed

Development checkout: `F:\ALFRED_DEV\m13c`.
Stable checkout: `F:\ALFRED\alfred_ai`.
Stable source baseline, rechecked through Git only:
`a9d096ea55839269fe6fce14d4f11ea2cbf05336`.
Validated M14F implementation: `895ce13ee86bf5fddbd1332f5326389b7a3b7c5c`.
Final application/test candidate:
`495a184c7a44bfe169978f8e0c018f8a286fb208`.
Exact validated source range:
`a9d096ea55839269fe6fce14d4f11ea2cbf05336..495a184c7a44bfe169978f8e0c018f8a286fb208`.
HTTP, token rotation and abuse source commits are 7bb5086, 64d21f3 and cf799d4.
The following evidence-only commit records the final gates. Its final development
HEAD/full promotion range are frozen in `F:\ALFRED_DEV\isolated-tests\m14-promotion-manifest.json`
and branch `release/m14-20261011`; no M15 commit belongs to this candidate.
Verify that manifest and both actual Git HEADs before authorizing any promotion.

This is a controlled plan, not live authorization. Release readiness requires the
new combined gate and the documented retention disposition. No live source,
database, configuration, credential or backup has been modified. M15 starts in
its own worktree after freeze and does not wait for live deployment.

1. Before any live action, require explicit authorization for source promotion
   and the private-database migration/token rotation. Confirm a clean stable source baseline,
   final development HEAD, local/LAN configuration, and successful combined M14
   proof. Preserve untracked operator files; never copy development SQLite,
   uploads, limiter stores, test credentials, caches or registry into stable.
2. Stop stable server, workers and scheduled writers under the approved
   maintenance window. Create a fresh consistent encrypted SQLite recovery
   backup, including media and local configuration/keys needed for recovery.
   Account for WAL/SHM state; verify hashes, integrity and a disposable restore.
   Preserve the original recovery archive and earlier backups unchanged. Record
   a verified source Git bundle/archive at the stable baseline plus a protected
   backup of untracked operator files before fast-forward. Verify a disposable
   source restore as well as the DB/config/media recovery set.
   baseline loan/document/account counts and balances locally, without private
   values in Git or hosted diagnostics. Keep public/LAN access closed through
   acceptance so rollback cannot discard later user writes.
3. Only after authorization, apply the frozen source range by an ordinary
   fast-forward, preserving untracked `config/local.env` and operator assets.
   Run local system/config checks and inspect the actual live migration plan.
   Source comparison identifies exactly one added migration:
   `family.0004_financial_sharing_opt_in`, dependent on `family.0003`.
   M14F creates no migration. The live migration table was not read during
   preparation; any unexpected pending migration is a stop condition.
4. Rehearse `family.0004` on a disposable fresh backup copy before applying it
   live. It preserves links/dependents/financial records, adds directional member
   consent, changes defaults to OFF, and disables ambiguous historical sharing
   grants. Users must explicitly opt in again for each direction. Reverse/replay
   deliberately keeps permissions OFF. This privacy change needs real-account
   acceptance; it does not change loan balances or financial calculations.
5. After the approved migration, start only the local testable stable service.
   Before exposing it, rehearse and explicitly authorize email-token rotation
   as described in docs/EMAIL_TOKEN_ROTATION.md: new primary, temporary fallback
   reads, count-only dry-run, atomic apply, primary-only re-read verification,
   zero remaining fallback/legacy/invalid counts. Keep old recovery keys/backups;
   remove runtime fallback only after token and other signing-key consumers are
   verified. No live rotation or fallback removal has been performed here.
   Validate native_settings: DEBUG=false, private owner-checked media, session
   auth/CSRF, positive limits and absolute persistent protection directories.
   Select the source-retention mode explicitly (extraction-only recommended);
   never run an automatic historical source purge. Preserve limiter stores on
   upgrade; do not replace them with development caches or reset quotas.
   Smoke-test login/password validation, session-only API authentication and
   authenticated-write CSRF; Career and Family safe failure messages; family
   invitation throttling/expiry and opt-in/revocation; upload-size rejection then
   a valid synthetic import; safe loan parser failure, historical payload
   filtering, document access, successful import/reimport and payoff evidence.
   Check status codes, correlation references and class-only logs.
   Check login/signup/API/expensive 429/Retry-After and valid recovery, invitation
   quotas, transport private/redirect refusal and safe provider fallback using
   synthetic fixtures. Check backend evidence, native configuration/migration
   drift and the 12-workflow Chrome driver-backed summary before acceptance.
   Reconcile pre/post counts and monetary balances locally. Do not use private documents
   in automated regression tests.
6. Real-account acceptance must confirm existing loan/import history loads,
   retained documents open, balances/deduplication remain unchanged, historical
   diagnostic content is absent from normal APIs, and family sharing is OFF
   until the owner explicitly grants it. Confirm optional provider/privacy
   settings and normal restart behavior. Open LAN access only after acceptance.
7. Rollback: stop all writers/access; preserve the failed candidate and its
   diagnostics separately. Restore the prior source baseline without destructive
   reset/clean commands. Prefer retaining OFF consent on any compatible rollback;
   reversing `family.0004` must not resurrect historical grants. If a full DB
   restore is necessary, use the verified fresh pre-promotion backup in the closed
   maintenance window, reconcile counts/balances, and inspect consent before
   restoring access. The older baseline lacks these security protections, so
   keep LAN access closed until safe recovery is accepted. Do not restore over
   later accepted user writes; reconcile them separately if the window was opened.
   Token rollback requires the pre-rotation DB and its compatible key set;
   restoring source alone does not restore token encryption keys. Preserve
   current limiter histories, revoke exposed credentials separately if needed,
   and keep LAN closed until recovery is accepted. No balance/schema overwrite
   after acceptance is authorized by this plan.

After M14 readiness PASS, M15's first verified-local-memory/Ollama/retrieval/
encrypted-journal/restart slice starts on `codex/m15-persistent-memory-20261011`
in `F:\ALFRED_DEV\m15`, branched from the frozen manifest HEAD.
A future sync abstraction must keep runtime local; cloud deployment wiring,
credentials or cloud-specific runtime templates require a separate decision
under AGENTS.md. This local/LAN release adds no cloud wiring or secrets.
