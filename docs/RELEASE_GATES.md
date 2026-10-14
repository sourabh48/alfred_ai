# Local release gates (M20/M21)

Development: `feature/m20-release-gates`, isolated from the running installation.
Use the existing project Python 3.12 interpreter in these PowerShell examples.
No new dependency, hosting service or provider credential is required.

```powershell
$python = 'F:\ALFRED\alfred_ai\.venv\Scripts\python.exe'
$candidate = git rev-parse HEAD
$baseline = '3932f391aa4eed7b3200ad3b034f7991435e01e4'
& $python scripts/release_gate.py preflight --release-id m20-local --candidate $candidate --baseline $baseline --output artifacts/release-gates/m20-local
& $python scripts/release_gate.py validate --output artifacts/release-gates/m20-local --profile targeted --test-label tests.test_release_gate --test-label tests.test_release_validation
& $python scripts/release_gate.py validate --output artifacts/release-gates/m20-local --profile backend
& $python scripts/release_gate.py validate --output artifacts/release-gates/m20-local --profile browser
& $python scripts/release_gate.py validate --output artifacts/release-gates/m20-local --profile native --with-ollama
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
recovery. The old M15 waiver is not inherited. Promotion remains unimplemented and
blocked in this unit; no command deploys, migrates or pushes.
