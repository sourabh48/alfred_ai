# M20/M21 implementation checkpoint

Branch: feature/m20-release-gates. Base: 3932f391aa4eed7b3200ad3b034f7991435e01e4.
Current HEAD: use `git rev-parse HEAD`; exact verified commit is recorded externally
after each commit to avoid a self-referential SHA.

M15 production and GitHub master remain at the base. Production operator changes,
private data, configuration, service and backups are outside this worktree.

## Existing meaning and prerequisites

M20 is the existing CI/governance milestone (master triggers, backend/native/browser/
drift/privacy gates, branch protection and actual CI evidence). M21 is release and
clean-PC/build/upgrade/reboot/reinstall/accessibility acceptance. The requested
automation extends these meanings, not substitutes synthetic checks for human or
separate-machine acceptance. M16-19 are separate open backlog items, not declared
prerequisites; they remain open. No dependency pruning or Travel changes here.

## Implementation matrix

| Feature | Exists | Missing | Implementation | Test | Status |
| --- | --- | --- | --- | --- | --- |
| Pinned Git/source/dependency/migration inventory | Manual release receipts | Reusable gate | scripts/release_gate.py | tests/test_release_gate.py | 12 focused tests PASS |
| Deterministic decisions and scoped waivers | Manual reports | Machine report, fail closed | release_gate.py | Missing/failed/waived gates | Included in 12 PASS |
| Backend/browser/native regression runners | Django, run_browser_regressions, verify_native_runtime | Isolation/orchestration/CI triggers | release_validation.py reuses house runners | Runner/privacy suite included in 20 PASS | Implemented; actual combined runs pending |
| Financial snapshot/reconciliation | rehearse_money_migrations | Release wrapper | Reuse copy_database/read_database/database_digests | Pending | NOT_RUN |
| Local backup/file/SQLite verification | backup_before_windows_reinstall, verify_private_recovery | Explicit single-runtime encrypted wrapper | Reuse SQLite API and verifier; no broad-root scanner | Pending | NOT_RUN |
| Privacy/source scan | Manual Git history review, package inspector | Reusable redacted scan | Pinned source/history checks, redacted logs, stripped child env | History secrets/private paths/unsafe log tests | Included in 20 PASS |
| Controlled promotion | native start/stop, manual FF and rollback | Pinned approval/resumable rehearsal | Thin wrapper; dry run default | Pending | NOT_RUN |
| M21 failure/rollback acceptance | Native synthetic/recovery house drill | Release engine rehearsal | Disposable Git/runtime only | Pending | NOT_RUN |
| Remote CI / branch protection | One PR/manual workflow | Actual remote evidence/protection | Master trigger and engine backend integration proposed locally | Local review; publication NOT authorized | NOT_RUN remotely |
| Real-account / separate-PC / installer | Existing acceptance docs/kit | Actual human/device evidence | Keep human checklist | Not inferable locally | PENDING |

## Restrictions and recovery

M15 external-recovery waiver is historical, release-specific and not inherited.
HDD copy is user reported; device-loss recovery remains unverified. No key dialogs,
plaintext key export, backup deletion, real cloud/OpenAI calls or production changes.
New worktree has no private local.env or database. Its PyCharm module is not mapped;
use the existing verified project Python 3.12 SDK without installing dependencies.

## Resume

Last verified unit: 12 unittest tests PASS (21.545s), zero failures/skips, using
F:/ALFRED/alfred_ai/.venv/Scripts/python.exe -B -m unittest tests.test_release_gate
from this worktree. This covers exact pins, dirty/advanced/diverged candidates,
dependency/migration declarations, explicit incomplete gates and waiver isolation.
Files: scripts/release_gate.py, tests/test_release_gate.py, this checkpoint.

Second unit: 20 focused tests PASS (42.399s), zero failures/skips. Prior 12 are
included, not added. Changed files: release_gate.py, release_validation.py,
test_release_gate.py, test_release_validation.py, browser-regression.yml,
docs/RELEASE_GATES.md and this checkpoint. Requested command scope has its own
exit result: preflight may return 0 while the explicit overall release remains
BLOCKED; status/full readiness still fails closed. Targeted tests do not fill the
full backend gate. First committed foundation: f8bba80e461a5bb4a99a8b9f3c0452be20ed82e0.

Next implement recovery gates and promotion rehearsal. Run actual pinned preflight
after this unit is committed, then the selected validation gate. GitHub Actions
read-only evidence is external: isolated-tests/m20-baseline-remote-ci-detail-20261015.json.
It identifies the successful M15 run as GitHub Pages, not backend/native/browser CI.
No M20 remote workflow execution/protection evidence exists until separately
authorized publication/settings work. Keep those gates NOT_RUN.
