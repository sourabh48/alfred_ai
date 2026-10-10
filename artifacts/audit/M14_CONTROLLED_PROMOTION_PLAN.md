# Controlled M14 promotion plan — prepared, not executed

Development checkout: `F:\ALFRED_DEV\m13c`.
Stable checkout: `F:\ALFRED\alfred_ai`.
Stable source baseline, rechecked through Git only:
`a9d096ea55839269fe6fce14d4f11ea2cbf05336`.
Validated M14F implementation: `895ce13ee86bf5fddbd1332f5326389b7a3b7c5c`.
Exact application-source range:
`a9d096ea55839269fe6fce14d4f11ea2cbf05336..895ce13ee86bf5fddbd1332f5326389b7a3b7c5c`.
The following documentation commit records the final gates without changing
application source. Its final development HEAD and full promotion range are
frozen after commit in `F:\ALFRED_DEV\isolated-tests\m14-promotion-manifest.json`.
Verify that manifest and both actual Git HEADs before authorizing any promotion.

This is a hold plan. A passing regression gate does not clear the additional
reported blockers retained in M14_SECURITY_RELEASE_READINESS.md. Resolve their
release scope before requesting promotion authorization. No live source,
database, configuration, credential or backup has been modified by M14F.

1. Before any live action, require explicit authorization for source promotion
   and the private-database migration. Confirm a clean stable source baseline,
   final development HEAD, local/LAN configuration, and successful combined M14
   proof. Preserve untracked operator files; never copy development SQLite,
   uploads, limiter stores, test credentials, caches or registry into stable.
2. Stop stable server, workers and scheduled writers under the approved
   maintenance window. Create a fresh consistent encrypted SQLite recovery
   backup, including media and local configuration/keys needed for recovery.
   Account for WAL/SHM state; verify hashes, integrity and a disposable restore.
   Preserve the original recovery archive and earlier backups unchanged. Record
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
   Smoke-test login/password validation, session-only API authentication and
   authenticated-write CSRF; Career and Family safe failure messages; family
   invitation throttling/expiry and opt-in/revocation; upload-size rejection then
   a valid synthetic import; safe loan parser failure, historical payload
   filtering, document access, successful import/reimport and payoff evidence.
   Check status codes, correlation references and class-only logs. Reconcile
   pre/post counts and monetary balances locally. Do not use private documents
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

M15 has not started. Its initial verified-local-memory/Ollama/retrieval/encrypted
journal/restart slice can begin only after M14 release readiness is explicitly
PASS. A future sync abstraction must keep runtime local; cloud deployment wiring,
credentials or cloud-specific runtime templates require a separate decision
under AGENTS.md. This local/LAN release adds no cloud wiring or secrets.
