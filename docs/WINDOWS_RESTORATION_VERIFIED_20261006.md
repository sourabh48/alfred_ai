> Historical operator evidence, preserved during consolidation on 2026-10-21. Current state and instructions: [PROJECT_STATUS.md](PROJECT_STATUS.md). Dated deployment/acceptance claims below are not current release approval.

# Windows restoration verification — 2026-10-06

Permanent source: sourabh48/alfred_ai, branch codex/native-runtime-hardening-20260918,
HEAD 5687a82ecb43702e90822f19e958b164dfe4cfdd. Requested checkpoint
6afeb10f8d724d007f787d9001280bc96af67f59 exists and is an ancestor.
Archive-bound checkpoint 5bf9cbe3e4c0c609e5fff5adf135ebcdc6a213b4 also exists.
No source reset, new application reconstruction, release, commit or push.

## Recovery evidence

The retained Desktop bundle was inventoried. Its single encrypted volume is
67,915,749 bytes; both hash manifests agree with its SHA256 and the bundled
7-Zip hash matches. Password was entered only at native local masked prompts.
Archive test/extraction passed; all 51,617 private-file hashes and all 17 SQLite
quick_check checks passed. Original backup files remain untouched.

Runtime mappings: source data F:\ALFRED\restored-runtime; source code
F:\ALFRED\alfred_ai; second profile %LOCALAPPDATA%\ALFRED. Historical profiles
remain separate under ALFRED_RECOVERED_HISTORY. The verified 96 MiB Docker
VHDX is retained offline under ALFRED_RECOVERED_DOCKER; its contents and
historical relevance have not been inspected or declared unnecessary.

All copied-file hashes and all 17 working SQLite checks passed. Pristine main
DBs are retained under F:\ALFRED_RECOVERY\before-migration, with the full
verified extraction retained separately. Existing settings/source conflicts
were avoided by choosing a separate restored source data root.

Both profiles passed native configuration checks, migration-plan review and
migration-drift checks. Reviewed loans 0013–0015 and mobility 0010–0012 were
applied to working copies only. Existing user-data table row counts were
preserved; new Django content types/permissions are expected migration metadata.
Both working databases passed quick_check after migration.

Both profiles started and stopped cleanly, one at a time. The source profile
was restarted and serves http://127.0.0.1:8000/. Login page HTTP 200/password
form verified. Actual existing-account login awaits operator confirmation;
at least one source-profile password value is unrecognized by Django. Password
values were neither displayed nor replaced. Finance/Travel/media completeness
is proved against the private manifest and retained row counts, not yet by
operator UI acceptance. No synthetic user data was substituted for recovery.

All retained email tokens in both active profiles were readable. Source-profile
key rotation/re-encryption was rehearsed on a separate DB/config copy, then
performed with the runtime stopped and a fresh private rollback checkpoint.
New key and re-encrypted tokens were verified; compromised fallback was retired
from source native.env. Second profile had no compromised active/fallback key.
No pending family invites existed. Old sessions/signatures may require login.
Historical signing keys remain only with their preserved recovery snapshots;
no key or credential values were printed. Historical Docker recovery and Git
history remediation remain separate work.

## Fresh-environment validation

Python 3.12.10 x64, new .venv, repository requirements installed. pip check,
Django check, isolated showmigrations and makemigrations --check --dry-run
passed. Focused native/recovery suite: 26 passed. Full backend: 697 run,
680 passed, 17 disabled-browser skips, 691.962 s, exit 0. Separate Chrome
regressions: all 17 passed, 114.915 s, exit 0. Application tests used isolated
SQLite/locmem settings and no real operator environment or helper PYTHONPATH.
Logs/result files are in the recovery coordination workspace, not public Git.

## Agent tools and hybrid

Git for Windows, standalone Node LTS 24.19.0, Codex 0.160.0, Claude Code
2.1.289, uv 0.12.23, Bun 1.4.2, Graphify 0.9.76 and Ponytail 4.13.0 installed.
gstack 1.91.22.0 pinned f97aefe654fbe265a3c978d34865b5aa493e7453; global
Codex routing current (20 links resolve). Chromium bootstrap repaired. Optional
CSO helper remains unavailable without the Windows C++ build toolchain.
Ponytail hooks are installed but were not automatically trusted.
Five ALFRED Claude skill copies were installed; canonical repository skills
remain preserved. The installer added their public hashes to skills-lock.json.
Graphify code-only/no-cluster refresh passed (7,340 extracted nodes/18,991
edges; query graph includes document nodes). No semantic model/API calls.

Ollama 0.35.1 installed. qwen3.5:4b digest verified; alfred-routine variant uses
65,536 context. Ollama reported the loaded model's full 5,350,904,298-byte
allocation in GPU memory. Hosted Codex authentication and real coding smoke
passed. ollama launch codex provider/coding smoke passed; separately configured
local Codex coding smoke also passed. Generated JS was checked with Node.

F:\ALFRED_TOOLS contains Codex-Local, Codex-Cloud, Codex-Smart and Start-ALFRED
PowerShell scripts plus .cmd launchers. Local configuration is separate from
hosted configuration. Smart routing forces finance/security/auth/encryption/
migration work to hosted Codex; unknown scope defaults to cloud. Keyword
routing is a conservative heuristic, not a security boundary. Persistent
Windows execution policy was not changed. No private runtime data entered
coding prompts. Browser/tool session credentials were not copied into Git.

## Continuation

Scoped M13C graph query and Investment model/serializer/view orientation resumed.
The three Investment register amounts remain FloatField; no M13C implementation
or real-data M13C migration is claimed. Next: bounded Decimal cents for
invested_amount, monthly_sip and current_value, retained-original/apply-marker/
owned rollback pattern, numeric API output and Decimal/rate-safe callers.
Preserve M12C projection semantics, rate/confidence/raw evidence, ownership,
nullable/zero behavior, document correction/retry and user reset. Expense/bank
fingerprint normalization remains a later separate phase. No full audit redo.

Remaining acceptance: operator login and real finance/Travel/media UI checks;
classify historical Docker data; optional current frozen-package rebuild;
Ponytail hook trust via normal interactive review; optional gstack CSO build
prerequisites; Claude interactive sign-in when needed. Keep Desktop backup and
all recovery checkpoints. No deletion is authorized; any later deletion needs
explicit approval and a separate verified ongoing backup first.

## Current post-migration recovery status - 2026-10-07

This section supersedes earlier pre-M13C continuation text. Live source remains
HEAD a9d096ea55839269fe6fce14d4f11ea2cbf05336. Both investments.0004 and
expenses.0005 Decimal migrations remain APPLIED LIVE. No migration, engineering
implementation, financial-record write or cleanup occurred during acceptance.

Read-only consistent snapshot SHA256:
02e42ebd7d0d0a55d097191d51489919f7b56c35d268e4b664f67a653630c267,
identical to the prior verified post-migration snapshot. Integrity PASS,
foreign-key violations 0, 69 total tables (68 application tables plus
sqlite_sequence). All 24 scoped financial/Travel/document tables unchanged:
Financial registers, statement identities, transfer legs and monthly groups reconcile with zero mismatches or duplicate fingerprints. Saved Travel and referenced media remain locally readable.
Private config/media/model hashes unchanged. Protected pre-migration backup
and Desktop encrypted recovery archive retain verified hashes. All preserved.

Native readiness 5/5 PASS, four health endpoints HTTP 200, worker/scheduler
healthy, no interrupted claims/queued/scheduled jobs. ALFRED remains running
at http://127.0.0.1:8000/ without an acceptance-phase restart. Actual local
configured Codex and hosted Codex neutral-response smoke PASS. Finance/migration
routing HOSTED and README routing LOCAL. Ollama uses its existing installation;
no private data included in coding prompts and persistent execution policy unchanged.

Historical Docker classification COMPLETE for the verified inventory. Sole
historical VHDX is Docker bootstrap Linux data; no reachable ALFRED/database/
PostgreSQL/volume payload identified. The initially UNKNOWN inode 12 is empty
ext4 orphan bookkeeping, confirmed by superblock and all 35 blocks. Restored
copy REGENERABLE; identical pristine backup RECOVERED and retained. Each is
100663296 bytes (96 MiB), combined standalone storage 192 MiB. Wider recovery
archive and rollback SQLite remain REQUIRED. Docker/WSL unnecessary for current
native ALFRED or its verified recovery. No install, writable original mount or
deletion. Detailed HISTORICAL_DOCKER_CLASSIFICATION.md is in private evidence.

Every real-account screen and console/network acceptance item remains PENDING:
no connected browser surface is available. Storage readability does not prove
UI acceptance. Checklist: docs/POST_MIGRATION_UI_ACCEPTANCE_20261007.md in live
checkout. Report only statuses and sanitized blockers, keeping credentials,
financial figures, screenshots and document contents local. Operator checklist
completion request sent; no verification yet received. Recovery closure PENDING.

Evidence: F:\ALFRED_RECOVERY\post-migration-acceptance-20261007,
RECOVERY_CLOSURE_REPORT.md, closure-readonly-checks.json, source-verification.json,
hybrid-smoke-result.json and offline ext4 evidence. Initial checker used application
table count against the historical total including sqlite_sequence; fixed count
convention, no data/schema mismatch. First script/log/snapshot preserved.

IMPORTANT CURRENT development HEAD: 6001a4ece2ab37ffba956625cba7b16c59fa5cac
already contains the completed focused M14A Career HTTP fix. It was not promoted;
live remains a9d096e. Do not repeat M14A, M13C/D or completed broad audits.
Prior live baseline: backend 718 passed / 19 disabled-browser skips; Chrome 19
passed. Completed suites not rerun. The existing development 17-test M14A gate
is prior evidence. No high-risk modification began during recovery acceptance.

Exact next action: operator completes the ten local read-only UI checks, compares
figures locally and reports only PASS/FAIL/PENDING plus sanitized blockers.
After acceptance, next provisional engineering task from CURRENT development
checkpoint is M14B signup/password-change password-validator enforcement,
using hosted Codex. If already enforced, advance to M14C/D as recorded.
Keep every backup and recovery asset. No cleanup is authorized.
