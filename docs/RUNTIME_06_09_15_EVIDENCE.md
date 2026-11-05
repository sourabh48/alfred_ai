# RUNTIME-06, RUNTIME-09 and RUNTIME-15 evidence

Source review on 2026-11-02 from `development/alfred-integrated` at `1d9df25`, on a
PC shared with a running RUNTIME-11 session. Only focused test modules ran. No
Chrome, native drill, package build, full backend suite, Ollama or Docker run
happened, and no real data or permissions were touched. All three items stay
IMPLEMENTED_NOT_ACCEPTED. RUNTIME-11's dependency upgrades are not on this branch,
so recheck these results after it lands.

Focused results, synthetic fixtures only:

| Module | Result |
| --- | --- |
| `tests.test_private_storage` | 12 passed |
| `tests.test_source_storage` | 10 passed |
| `tests.test_local_config` | 14 passed |
| `tests.test_native_runtime` | 20 passed |
| `tests.test_local_stack_ops` | 23 passed |
| `tests.test_production_readiness_contracts` | 15 passed |

## RUNTIME-06: offline startup and local model prerequisites

Verified from source:

- The startup path in `alfred_native.serve` opens no external connection. A new
  test runs its three maintenance commands, on a fresh folder and with a memory
  vault, with connections and name lookups blocked.
- Ollama is called only at the fixed `127.0.0.1:11434`, ALFRED has no model pull,
  and a missing model gives a 503 `local_model_unavailable` from the memory API.
- Templates and stylesheets load no script, style or font from the internet. A new
  test keeps it that way.

Changed:

- The operator guides named no required models, though the tracker refers to
  declared prerequisites. `docs/NATIVE_WINDOWS.md` and the packaged `READ ME.txt`
  now list them, and a test ties those names to the code.
- Removed a stale claim about optional Google fonts; no page uses them.

Depends on RUNTIME-11: on this branch `TransactionClassifierAdapter` can still try
a Hugging Face download when it loads. RUNTIME-11 already sets
`local_files_only=True`, so it is not changed here.

Recheck on master, 2026-11-05: steps 1 to 3 below are done. A clean checkout of
`6743fd9` on drive G: was packaged (ALFRED.exe SHA-256 `5b33a61b…44457`), and
`verify_native_runtime.py --executable … --launcher … --browser --memory` passed
**35/35** against the installed Ollama 0.40.14 with `qwen3.5:4b` and `all-minilm`.
That includes Chrome pages with no internet-loaded files, the missing-model safe 503
with no cloud call, the model-outage draft-and-retry check, and recovery after the
outage. The installed Ollama passes as it is, so the staged runtime does not need to be
adopted. Ollama ran as a test-owned `ollama serve`. Evidence, not in Git:
`F:\ALFRED\dev-evidence\post-audit\runtime-06-20261105`. Still open: step 4, a separate PC.

Still needed for acceptance:

1. Package rebuild, because `READ ME.txt` changed: PyInstaller, then
   `scripts/package_windows_release.py`.
2. `scripts/verify_native_runtime.py --executable dist/ALFRED/ALFRED.exe --browser`
   on the final commit, with Ollama and both models present (the 35 native checks).
3. Chrome check with Ollama stopped: ALFRED starts, the assistant shows the
   unavailable message and the draft is kept.
4. The independent-host kit on a separate PC with the network disconnected after
   the models are installed.
5. The operator decision on adopting the staged Ollama runtime, which stays open.

## RUNTIME-09: filesystem protection of private DB/config

Verified from source and by the tests above:

- New folders get owner and SYSTEM access only; a restricted Windows token is
  really denied; loosened data is refused with no permission change.
- Repair needs a pinned plan, an authorization reference and stopped writers, and
  rollback refuses changed files.
- `config/local.env`, `.env` and SQLite files were checked individually. The native
  signing key was not.

Changed:

- `native_secret_file` now refuses a `config/native.env` that holds wider
  permissions of its own, as `local.env` already did. **Effect on an existing
  install:** ALFRED will not start if that file is loosened, until the authorized
  repair runs. The owner's real file was not inspected.
- Compose backups in `scripts/local_stack_ops.py` held the whole database dump and
  uploads in a folder with the checkout's permissions. That folder and the
  restore-check extraction folder are now private.

Belongs in files this work must not edit:

- `alfred_private_storage.guard_sqlite_storage` does not check `db.sqlite3-wal` and
  `db.sqlite3-shm`, which hold recent private rows. RUNTIME-11's
  `verify_pickle_storage` covers those side files for the job queue only. Apply the
  same check to the main database.
- `safe_path` rejects UNC paths but accepts a mapped network drive such as `Z:`,
  where local permissions may not protect the data. Lower priority.

Not solved by permissions, and needs an owner decision: the SQLite file is still
plaintext on disk, so anyone with disk access outside Windows can read it.

Still needed for acceptance:

1. Owner authorization for a dry-run plan on the real runtime, then a backup, a
   stop and the repair (`docs/NATIVE_WINDOWS.md`).
2. Native drill on the final commit, covering a fresh folder and a restored one.
3. A read attempt from a second, real standard Windows account.
4. Full backend regression after RUNTIME-11 lands, since it changes the same
   storage module.

## RUNTIME-15: local/LAN hosting and optional Docker stack

Verified from source:

- The native listener binds `127.0.0.1` only (new test) and native `ALLOWED_HOSTS`
  is loopback. LAN service exists only through Compose.
- Compose publishes only `web`, on `127.0.0.1` by default (new test). PostgreSQL and
  Redis have no host ports. No cloud wiring exists.

Changed:

- `.dockerignore` used bare names, which Docker matches at the context root only,
  and it omitted `.claude`, generated memory stores and key files. A nested `.env`,
  SQLite file or key, or `ml_models/alfred/memory`, could reach the image, and
  `.claude/worktrees` could carry whole checkouts. It now matches at any depth.
- The web service refuses to start with the published example `DJANGO_SECRET_KEY`.
- `local_stack_ops.py verify` now blocks acceptance on the example secret or
  database password, a wildcard `ALLOWED_HOSTS`, or a bind address that is not
  loopback or private, including `0.0.0.0`. Backups are not blocked by this.
- The example environment no longer trusts forwarded headers from LAN clients.
- `docs/LOCAL_HOSTING.md` now says local AI and private memory need the native
  runtime: Ollama's fixed address is the container itself, and the vault needs
  Windows key protection.

Needs a separate decision, because it cannot be tested without Docker:

- The `Dockerfile` runs as root. Adding a non-root user also needs an ownership
  plan for existing named volumes.
- The image uses a floating `python:3.12-slim` and installs without a Linux
  constraints file, so it is not reproducible. This belongs with RUNTIME-11.
- `test_local_stack_ops` and `test_production_readiness_contracts` are in neither
  `scripts/release_validation.py` nor a workflow. Add them once RUNTIME-11, which
  edits the same line, has landed.
- A LAN connection is plain HTTP, so session cookies are readable on that network.
  This is the documented trusted-LAN limit.

Compose run 2026-11-06 (Docker Desktop 4.98.0, disposable clone of `49d622e` on G:, synthetic settings):

- Steps 1-3 below passed: SVM on, `config --quiet`, `up --build`, no planted private file in the image, user
  `alfred`, `verify` accepted, backup and isolated restore check accepted with synthetic rows.
- Data persisted through `down`/`up`; beat sent jobs and the worker completed them.
- Containers cannot read the Windows zone and fall back to Asia/Kolkata with a warning; the hosting guide now
  says to set `ALFRED_TIME_ZONE`.
- Evidence: `F:\ALFRED\dev-evidence\post-audit\runtime-15-20261106`. Docker was uninstalled afterwards at the
  owner's request.

Still needed for acceptance:

1. Owner enables SVM in the BIOS; virtualization was off when last checked
   (`docs/DOCKER_SETUP_STATUS.md`).
2. `docker compose ... config --quiet`, then `up --build -d`, then inspect the image
   for `.claude`, `.env`, SQLite and key files.
3. `scripts/local_stack_ops.py verify`, `backup` and `restore-check`.
4. A host restart, a request from a second LAN device, and scheduled job outcomes
   over their real schedule.

## All items

After RUNTIME-11 lands, merge this branch and rerun the modules above, then the full
backend and browser regressions on the combined commit.
