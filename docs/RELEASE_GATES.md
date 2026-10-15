# Local release gates (M20/M21)

Existing engine from `feature/m20-release-gates` / 0052410 is integrated into
`fix/post-audit-critical-20261015`. See [current status](PROJECT_STATUS.md) for
fresh evidence. Select the isolated development Python 3.12 interpreter; do not
install updates into the running production environment.

```powershell
$python = '.\.venv\Scripts\python.exe'
$candidate = git rev-parse HEAD
$baseline = '3932f391aa4eed7b3200ad3b034f7991435e01e4'
& $python scripts/release_gate.py preflight --release-id m20-local --candidate $candidate --baseline $baseline --output artifacts/release-gates/m20-local
& $python scripts/release_gate.py validate --output artifacts/release-gates/m20-local --profile targeted --test-label tests.test_release_gate --test-label tests.test_release_validation
& $python scripts/release_gate.py validate --output artifacts/release-gates/m20-local --profile backend
& $python scripts/release_gate.py validate --output artifacts/release-gates/m20-local --profile browser
& $python scripts/release_gate.py validate --output artifacts/release-gates/m20-local --profile native --with-ollama
& $python scripts/release_gate.py validate --output artifacts/release-gates/m20-local --profile packaged --bundle $freshBundle --package-manifest $freshPackageManifest --with-ollama
& $python scripts/release_gate.py status --output artifacts/release-gates/m20-local
```

Preflight requires a full exact candidate SHA at a clean checkout, including
untracked source. It inventories the baseline range and blocks undeclared
dependency/migration changes. Declare reviewed paths explicitly with
`--expected-dependency` / `--expected-migration`; this does not apply migrations.
The manifest preserves this policy for subsequent validation runs.

Optional `--target-repo` checks the target's exact baseline and records hashes of
protected operator files. Unknown edits or operator edits overlapping the release
diff block, rather than being stashed, deleted or overwritten automatically.
Candidate additions that collide with existing ignored files also fail this gate;
Git's ordinary fast-forward can overwrite such files despite a clean status.
Credential scanning includes quoted JSON access/refresh tokens and client secrets.
Only exact reviewed public fixture path/value hashes are exempted. Successful
runners with zero/skipped required tests report NOT_RUN, never PASS; failed
runners remain FAIL.

Exit codes: 0 requested command scope passed, 1 failed, 2 blocked/incomplete.
Preflight/targeted PASS is **not** full release readiness. Both the JSON and
Markdown report separately show technical, operational and approval status.
`status` returns nonzero until every required release gate is satisfied or an
explicitly scoped operational waiver is valid. A technical failure is not waivable.

Profiles reuse the established combined M14/M15 backend labels, the existing
Chrome runner and the native synthetic runtime drill. Targeted tests do not fill
the complete backend gate. Zero/skipped tests cannot pass a release suite.
Child environments remove operator secrets, force disposable SQLite and disable
real OpenAI and cloud sync. Diagnostic logs keep test names/counts and omit raw
tracebacks, exception messages, OCR text, paths and model/user payloads.
Every run has a new log identity and retains previous results. Explicit retries
can replace a failed gate only with new passing evidence. Package validation
requires the exact clean source receipt, both executable hashes and the existing
bundle inspector before invoking native/Chrome acceptance. No supplied package
means NOT_RUN; this command never installs a build tool or reuses old proof.

Pinned privacy scanning covers all candidate files and intermediate unpublished
commits. It does not read the live database or working-copy private configuration.
Known synthetic S3/disposable rehearsal identifiers are narrowly classified;
test filenames do not grant a general secret exemption. Findings contain only
codes and hashed references, never the matched credential or private payload.

The existing GitHub workflow now proposes master-push checks and invokes this
engine for backend/source/privacy/drift validation. It uploads redacted summary
artifacts and retains native/browser jobs. This branch is not published: actual
M20 remote CI and required-check/branch-protection evidence remain NOT_RUN.
The successful M15 GitHub Pages run is unrelated to backend/native/browser CI.

## Backup and independent local restore

The one-runtime wrapper reuses native locks, the SQLite backup mechanism, the
private manifest verifier and the Windows vault ACL/key-protection helpers.
It deliberately does not run the older whole-PC scanner or cancelled key dialogs.
It reads an existing Fernet/DPAPI-protected key supplied by path. It never generates,
exports or rotates recovery keys. Synthetic unit fixtures alone create test keys.

```powershell
& $python scripts/release_gate.py backup --output artifacts/release-gates/m20-local --runtime $selectedRuntime --backup-directory $newPrivateBackup --key-file $existingProtectedKey --target-repo $baselineSource
& $python scripts/release_gate.py recovery --output artifacts/release-gates/m20-local --backup-directory $newPrivateBackup --key-file $existingProtectedKey --restore-directory $newDisposableRestore
```

All paths are explicit operator selections; variables above are not guessed real
destinations. The destination must be new, outside runtime/source, without links,
and separate from the existing key. Native/worker locks and SQLite write barriers
must be available. This command will not stop a running service; it rejects writers.
It captures the default native database, queue, configuration, media and existing
encrypted-memory directory, preserving committed WAL rows through SQLite's API.
Custom external storage is not silently assumed covered; review/extend the coverage
manifest before using this default-layout adapter for such a release.

Encrypted payloads use authenticated one-MiB chunks and an authenticated manifest;
archive names contain only chunk indices. A fresh process decrypts and restores into
a new ACL-private location, checks every count/size/hash, SQLite integrity/FKs,
typed row/schema fingerprints, configuration/media and source recovery inventory.
Raw record values and private filenames stay inside the encrypted manifest and
private restore. Detailed public findings/exception contents are never logged.

New private restore/evidence copies are retained locally. After verified success
only this operation's transient capture scratch is removed, with a checked boundary.
No source file, recovery archive or previous backup is deleted or overwritten.
For transfer, select only `recovery.zip` and `backup.json`, never the plaintext
ACL-private disposable verification tree. Keep the key separately protected.

The report records LOCAL_BACKUP_VERIFIED independently of OFF_DEVICE_COPY_VERIFIED,
PORTABLE_KEY_VERIFIED and INDEPENDENT_DEVICE_LOSS_RESTORE_VERIFIED. Raw portable key
format, matching hashes and current-profile DPAPI success do not prove device-loss
recovery. The old M15 waiver is not inherited.

## Controlled promotion

`promote` defaults to a non-mutating dry run. Supply explicit `--target-repo`,
`--runtime` and `--environment rehearsal|production`; an existing manifest pins
the candidate. `--execute` additionally requires an existing key and a new
`--authorization` JSON bound to the exact release, target, runtime, gate-evidence
digest and approved archive digest. Approval must expire within 24 hours. It
does not transfer to another release or environment. The rehearsal runtime must
carry its exact `.alfred-release-rehearsal.json` binding. An injected test service
operator is forbidden for production.

The engine checkpoints each stage, stops through the existing native launcher,
captures a fresh encrypted quiesced backup and independent restore, verifies no
migrations are pending, then performs only `git merge --ff-only <exact SHA>`.
It preserves operator hashes, checks native/worker/scheduler health and compares
canonical data after restart. Schema changes require a separate reviewed migration
procedure; this command never applies a migration or installs a dependency.

Interruption is recorded and requires review before resumption. Completion is
idempotent for that same target/runtime only. If explicitly authorized, failure
recovery preserves a new encrypted diagnostic backup and switches source back to
the baseline without force. It never overwrites a database. Changed data/schema
blocks blind rollback and requires manual reconciliation. Failed rollback is
BLOCKED, never COMPLETE. No release command pushes to GitHub.

Local development tests exercise real Git/SQLite/encryption with simulated service
actions; they are not actual native or real-account acceptance evidence.

## M21 disposable rehearsal

After the pinned backend, Chrome and native/Ollama gates pass:

```powershell
& $python scripts/release_gate.py rehearse --output $releaseEvidence --rehearsal-directory $newPrivateSandbox --port 8150
```

The sandbox must be new and outside the candidate checkout. The command accepts
only the engine's current hashed, successful house-native fixture. It creates a
local source clone at the baseline, a separately encrypted synthetic backup and
restored runtime, then exercises actual native startup, Chrome navigation, exact
promotion, restart/memory persistence, worker crash injection and source rollback.
Only a new synthetic fixture key is generated, profile-protected on Windows; it
cannot decrypt existing backups. No live path is a test target. Failed evidence
and backups remain. Rehearsal authorization is bound to the sandbox and never
authorizes production. Same-host recovery does not fill off-device/key gates.

## Evidence, waivers and approval

`record --evidence <JSON>` accepts operational observations only, bound to this
release ID and candidate SHA. Include `gate`, `status`, `observed_utc`,
`authorized_by`, `authorization_evidence` and `reason`. A PASS requires
`evidence_files` whose hashes are retained. Device-loss restore additionally
requires explicit observations of decryption, SQLite integrity, reconciled
inventory and independence from the original profile. These are labeled operator
attestations; never use synthetic evidence for an actual account/device.

A waiver also requires `decision: YES` and `scope: this_release_only`; it stays
WAIVED_BY_USER. Financial/privacy/source/local-backup/operator/remote-Git gates
cannot be attested or waived. Evidence history is retained. Do not place secrets
in notes or attachments.

`approval-request` with explicit target/runtime/environment writes a bound
`approval-request.json` with PENDING decision and empty author/evidence/expiry.
It never generates authorization. The operator must review the gate report and
provide a separate explicit YES before supplying that file to `promote --execute`.
The production preflight rechecks remote ancestry. A backup from another runtime
cannot authorize shutdown. After promotion, actual human acceptance may remain
BLOCKED; `complete` only records completion after all required observations pass.

Read [the human acceptance checklist](RELEASE_HUMAN_ACCEPTANCE.md). Proposed GitHub
required checks are `native-windows` and `selenium` from Browser Regression.
Enforce them on master only after separately authorized publication, actual remote
CI PASS and explicit repository-settings approval. No command changes protections.
