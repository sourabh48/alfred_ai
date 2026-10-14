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

Backup, recovery and promotion adapters are the next implementation unit. Until
verified they remain NOT_RUN and block promotion. Existing M15 external-recovery
waivers are not carried forward. No command in this initial unit deploys or pushes.
