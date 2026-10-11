# Pre-reinstall source verification — 2026-10-05

These checks ran before reinstalling Windows, using an isolated source copy and a newly created Python 3.12 venv. They used synthetic/disposable data. No operator database migration, private-data restore, actual private backup or release promotion was performed.

| Check | Result |
|---|---|
| Fresh dependency install from requirements/Windows constraints | Passed; compatible Protobuf 6.33.6 replaces the original environment's incompatible 7.34.1 constraint |
| Fresh `python -m pip check` | Passed, no broken requirements |
| `python manage.py check` | Passed, zero issues |
| `python manage.py makemigrations --check --dry-run` | Passed, no changes detected |
| Final `python manage.py test --noinput --verbosity 1` | 693 run, 676 passed, 17 browser skips; zero failures/errors; 661.580 s framework time, 675.828 s process time; exit 0 |
| Final Chrome browser runner, all default labels, `--require-browser` | 17 passed, zero skips/failures/errors; 116.734 s framework time, 128.156 s process time; exit 0 |
| Final native source runtime `--browser --extended` | Passed; 201.609 s process time, exit 0; HTTP/auth, worker/retry/crash recovery, restart persistence, synthetic backup recovery, concurrent users, responsive layouts and automated accessibility |
| Fresh bootstrap `-MigrateFresh` on an empty synthetic profile | Passed, 28.891 s; no operator migration |
| Bootstrap rerun on that synthetic profile | Passed, 10.453 s; native key, local config and database SHA256 unchanged |
| Backup script synthetic check using its default interpreter option | Ten named checks passed, exit 0, 10.985 s; operator_data_accessed=false |
| Focused persisted-key/config/native/readiness/setup regression | 28 passed in 5.345 s |
| Focused Travel browser regression after fixture repair | Three passed in 30.559 s; final full browser gate also passed |
| Project-local ALFRED skills | Five pass bundled validator; all 16 canonical repository skills are discovered |
| Final Graphify AST update | Passed; generated graph remains ignored; no API/model call |
| Final staged diff whitespace check | Passed after removing upstream reference-document whitespace |

## Audit conclusions

The final intended tree has no tracked private/runtime database, real environment file, PDF upload, private key, native executable, runtime archive, media directory or machine-specific Claude junction. Required source, migrations, tests, assets, dependency definitions, CI, scripts, canonical skills and safe examples are included. No source-file deletion or `git rm --cached` was necessary.

The final current-source Gitleaks scan returns five alerts: four public motorcycle catalogue identifiers and the known-key SHA256 fingerprint used to reject an exposed historical default. All five are reviewed non-credentials. Raw scanner reports and inventory logs remain outside Git. A blind private-value comparison separately discovered the active historical signing fallback; its plaintext has been removed from current source, but public history/older packages remain exposed. Rotation must preserve encrypted-data recovery and follow a verified backup. No history rewrite or private-key change was performed.

## Earlier attempts

The first dependency snapshot could not resolve Protobuf 7.34.1 with Google's `<7` dependency requirements; the restorable snapshot fixes this. An initial 690-test gate had two readiness failures because the validation runner incorrectly inherited eager-Celery flags into production-contract subprocesses. The corrected final runner removes those flags. The first full Chrome gate had one native-click scrolling race in the Travel fixture; the fixture now resets its viewport and removes smooth scrolling for native clicks. These earlier failures are superseded by the final passing gates above.

The original running/development environment was not upgraded; its existing Protobuf dependency conflicts remain documented. Historical engineering and manual/live-provider/release acceptance limitations remain in the master backlog and are not a new whole-project audit.

## Outstanding pre-format gate

The actual private backup is still pending the user's confirmed untouched destination and graceful runtime shutdown. Independent GitHub/SSH recovery, secret recovery and Windows installation-media readiness also require confirmation. Under the user's final push gate, push/remote HEAD equality waits for the verified private backup. The generated `PRE_REINSTALL_FINAL_STATUS.md` records the actual final local and remote SHA after all local commits and read-only checks.

`SAFE TO REINSTALL WINDOWS = NO`
