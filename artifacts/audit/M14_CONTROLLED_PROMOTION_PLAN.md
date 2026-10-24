> Historical operator evidence, preserved during consolidation on 2026-10-21. Current state and instructions: [../../docs/PROJECT_STATUS.md](../../docs/PROJECT_STATUS.md). Dated deployment/acceptance claims below are not current release approval.

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
   and the private family-sharing migration. Live token rotation requires its own
   authorization and another verified backup; it is not part of this deployment approval.
   Confirm a preserved stable source baseline,
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
   If a separate email-token rotation is authorized later, first capture its own
   fresh verified backup, then rehearse and authorize email-token rotation
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

## Stable Git integration and deployment approval gate - 2026-10-11

Target stable Git branch: master, tracking origin/master. Remote HEAD refreshed
and unchanged: da74570681165cfa46dd3186f95ee400643c41d6. The remote merge commit
and required M13C/M13D ancestry are preserved by an ordinary local merge.
Merge commit: ffe2b7cfc64cf37e1a0ff90ec89de129269cc356; its tree exactly matched
frozen M14 6050234e6da66d38d558be1976371e9d541f0319.
No remote push/PR or live checkout switch was performed. M15 commits are excluded.

Native integration found and reproduced one source-launcher compatibility defect:
changing cwd to private runtime data prevented Python parser workers importing
the project. d84a5e5b0d0c35a62d9290c1e403629e69ff17c6 fixes the shared OCR command
to prepend the trusted code root, with a real subprocess regression. Parser
budgets/HTTP semantics/frozen-executable invocation remain active. This correction
also belongs to M15 as an independent cherry-pick, never the reverse.

Final validated application/test candidate: d84a5e5b0d0c35a62d9290c1e403629e69ff17c6.
Actual new gate on that source: 357 backend passed, 342.618 s; 12 Chrome passed,
136.881 s; 0 failures/skips. Native source/Chrome verification: 19 checks passed,
including valid PDF import, worker recovery, process restart, durable queue and
DB/media restoration. Earlier runs and corrected test-limiter isolation evidence
are retained outside Git. Repeated tests use fresh dedicated limiter directories;
operator limiter histories are never reset. AST-only graph update passed.
The following documentation-only commit records the final integrated HEAD in
F:/ALFRED_DEV/isolated-tests/m14-stable-integration-manifest.json; its app/test tree
remains identical to the validated candidate. master is then frozen separately
on release/m14-integrated-20261011, freeing master for an authorized live switch.

Installed source baseline remains a9d096ea55839269fe6fce14d4f11ea2cbf05336.
The manifest records both exact origin/master..integrated_HEAD and installed
baseline..integrated_HEAD ranges plus file inventory. Runtime source differences
include M14 password/session/CSRF, safe diagnostics/historical filtering,
financial sharing opt-in, invitation/global abuse controls, upload/parser caps,
central HTTP transport, token rotation tooling and this native-worker correction.
No M15 memory source or private runtime files/secrets are included. M13C/M13D
Decimal migrations are already present and applied in the private snapshot.

Fresh recovery set: F:/ALFRED_BACKUPS/m14-prepromotion-20261011-1645.
SQLite snapshot was captured through a read-only source connection and SQLite's
online backup API (WAL committed data included), integrity/foreign-key checked,
independently restored and hash verified. Current-user DPAPI protects the DB,
configuration/keys, retained media, models, protection histories, native queue,
source bundle and operator-local edits. 9690 protected files are verified.
An independent bundle clone restored source baseline a9d096e. ACL inheritance is
removed; only the current Windows user and SYSTEM receive directory grants.
Disposable plaintext snapshot/rehearsal DBs were removed after verification.
Earlier original/off-PC portable recovery archives remain unchanged. This fresh
DPAPI recovery set depends on the current Windows profile; it is not a portable
Windows-reinstallation backup. Do not change that profile during this promotion.

Exact pending plan, independently inspected on a DPAPI-restored private copy:
family.0004_financial_sharing_opt_in ONLY. Forward, reverse and replay passed;
every finance/user/family table's count and full-row hash remained identical,
except the explicitly excluded financial-consent fields. Relationships remain;
historical grants are OFF in both directions. Integrity and foreign keys passed;
Django system and migration-drift checks passed. No live SQL mutation occurred.
Any actual pending-plan difference at deployment time is a stop condition.

Existing installed checkout edits in CODEX_CONTINUATION_STATE.md, skills-lock.json
and two untracked operator documents are preserved, including protected copies.
Replay was rehearsed on the independently restored source clone: all 193 added
checkpoint lines, local skill-lock edits and both untracked documents survived
a switch to the tested master source; application/template/static/test/script
diff was empty. Prepared checkpoint replay is protected alongside the backup.
Only after approval and rechecking original edits, preserve the checkpoint, restore
that single tracked file to the installed HEAD to permit Git switch, then install
the prepared combined checkpoint after switching. Skill-lock and untracked files
are retained by the normal switch. No private configuration is stashed in Git.
Before any authorized switch, reconcile/replay these documentation/skill edits
without overwriting them. Do not bypass Git refusal or stash private configuration
into Git. Abort if any unexpected application source edit or newer stable commit
appears. Refresh/verify the backup in the quiesced maintenance window if data,
keys/config/media or writer activity has changed since this preparation.

Verified source control commands (prepared, NOT executed on the live runtime):

```powershell
& 'F:/ALFRED/alfred_ai/.venv/Scripts/python.exe' F:/ALFRED/alfred_ai/alfred_native.py stop --data-dir F:/ALFRED/restored-runtime
& 'F:/ALFRED/alfred_ai/.venv/Scripts/python.exe' F:/ALFRED/alfred_ai/alfred_native.py status --data-dir F:/ALFRED/restored-runtime
# After authorization, preserved local edits, fresh backup and exact-plan recheck:
git -C F:/ALFRED/alfred_ai switch master
& 'F:/ALFRED/alfred_ai/.venv/Scripts/python.exe' F:/ALFRED/alfred_ai/alfred_native.py start --data-dir F:/ALFRED/restored-runtime --port 8000 --no-browser
```

Native start applies pending migrations before serving. The exact family-only
plan must therefore be rechecked before that start; this command is a migration
action requiring the user's approval. Stop waits for jobs; a still-running status
is a stop condition. Source-native shutdown/restart was exercised on disposable
profiles, never the installed runtime. Expected maintenance downtime: 15-30 min,
subject to draining active work and real-account acceptance. Keep LAN access closed
until login/CSRF, owner documents, imports/deduplication/balances, safe historical
loan diagnostics, financial sharing OFF/explicit opt-in and restart are accepted.

Rollback is the existing step 7: stop access/writers, preserve candidate evidence,
switch back to the protected a9d096e source and restore the verified DB/config/key/
media/queue set into a new recovery folder if necessary. Preserve/reconcile local
edits and any subsequent writes; never restore over accepted later writes. Keep
family financial consent OFF and LAN closed on the older source. Restore compatible
keys with a restored DB; do not retire fallbacks or rotate tokens as part of this
approval. No source promotion, live migration, token operation or service change
has been executed. Approval question is the user's required Step 5, not inferred:
"Do you authorize promoting M14 to the live ALFRED installation and applying the verified family-sharing migration?"

## Authorized execution receipt - 2026-10-11

The user explicitly authorized the frozen 30e0b3f75e785f639897ad36c19090c6a4e8675f
release and verified family migration. That exact source is installed on master;
only family.0004 was applied. Backup freshness, private-copy rehearsal and live
reconciliation PASS; historical sharing OFF and all other rows/values preserved.
The live loopback service and worker are healthy. Actual HTTP/worker gate 21 PASS;
private-copy authenticated compatibility/media/CSRF/upload gate 21 PASS. Recovery
sets, current keys, configuration, media, jobs and operator edits are preserved.
Profile-independent encrypted current recovery supplement also verified; no token
re-encryption or remote push. See docs/M14_LIVE_DEPLOYMENT_20261011.md and protected
live-deployment-receipt.json. Real-account password/browser acceptance is PENDING;
entire deployment completion is not yet claimed. No M15 code is installed.
