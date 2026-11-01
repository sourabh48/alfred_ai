# RUNTIME-11 evidence — 2026-11-01

Status: IMPLEMENTED_NOT_ACCEPTED. Baseline 75/143 and extensions 0/13 are unchanged. The residual risk below is
documented, not formally accepted. That needs a separate owner decision.

Which commit each result belongs to:

| Commit | Change | Results that apply |
|---|---|---|
| `d2a9601` | Last product change, and the source of the package | Scan, drills, local AI, journeys, backend, package, installer |
| `338ad27` | Test-only, from `d2a9601` | Chrome, CI preflight |

The final commit adds only this evidence and tracker text. The diff from `d2a9601` to `338ad27` is
`tests/test_user_data_browser.py` only, and tests are not packaged. A green check applies only to its exact commit, so
exact-head CI still decides.

## Dependencies

- Before: 276 advisories in 30 packages. After: 1 advisory in 1 package, in 147 packages scanned including pip.
- `pip check` is clean and no migrations are needed.
- Open: `diskcache` 5.6.3, PYSEC-2026-2447 / CVE-2025-69872. It has no upstream fix and the scanner still reports it.
- `pip-audit` cannot look up `torch 2.15.0+cpu`, so OSV was queried for `torch 2.15.0`: no advisories.
- Line-by-line matrix, local and not in Git: `artifacts/runtime-11-20261101/RUNTIME-11-advisory-matrix.csv`.

## What was done about diskcache

- Only `diskcache/core.py` uses pickle. ALFRED reaches diskcache in two places: the Django cache in native settings and
  the throttling store. `apps/mobility` imports only its `Timeout`.
- `alfred_ai/safe_cache.py` replaces its serializer. Values are typed JSON text and keys must be text or numbers. A row in
  pickle mode, a pickled key, or a file name diskcache would not write is never opened. Reads treat it as a miss. Throttling
  reads use the strict form, which reports it.
- Throttling keeps its atomic rolling window in a new `json-v1` folder. An unreadable record fails closed for its window,
  then is reset so the limit recovers.
- Old pickled rows are not migrated or read. They stay on disk in the old folders because deleting them is the owner's
  decision.

Measured on `d2a9601`:

- Five stores written by the running app had value mode 1 and raw keys throughout, with no pickled sample.
- 19 pickled rows planted across those stores did not run. Health stayed 200, login answered 429 then 302, and pages
  answered 200, or 429 for a planted limit, which is the fail-closed result.

## Folder permissions

- Cache, throttling and invitation folders must be private to the current account, SYSTEM and Administrators, and owned by
  one of them. This includes locations set in configuration. A shard or database file loosened later is also refused.
- A new folder is created private. An existing folder that is not private is refused, not repaired, and startup stops with
  `ImproperlyConfigured`.
- A store nested inside a non-private external parent is refused. Keep configured stores as siblings, as the defaults are.
- Startup always checks. While running, a process rechecks a throttling store at most every 30 seconds, so a folder loosened
  meanwhile is refused up to 30 seconds later. Checking on every request took simultaneous requests from about 7 ms to
  93 ms; this brings them back to about 9 ms.

Tests are in `tests/test_safe_cache.py`: malicious serialized values, keys and files, insecure and foreign-owned folders,
configured external paths, the recheck window, corruption, concurrent limits across threads and processes, expiry and
restart.

## Remaining reachable paths and residual risk

These stay open after the mitigation:

- Anyone who can already write to these private folders can still forge JSON values, change cache settings or deny service.
  The mitigation removes code execution through pickle, not that.
- A folder could be changed between the permission check and its use, for up to 30 seconds on a throttling store.
- The storage lock covers one process, so separate processes creating the same new store at the same moment could collide.
  Rate limits run only in the web process.
- `Cache.pull`, `peek` and `peekitem` loop on a planted row. ALFRED does not call them, and a test holds that true.
- Other pickle paths, outside diskcache and not changed here:
  - `joblib.load` in `apps/ml_engine/inference_adapters/` and `apps/ml_engine/loaders/model_loader.py`.
  - Huey payloads in `artifacts/native/jobs.sqlite3`.
  - Backups restore both `ml_models` and that queue file.
  - `torch.load` uses `weights_only=True`.
- No independent security review was done on this mitigation, only a self-review by the same AI harness.

## Compatibility, on `d2a9601`

- Cryptography: a fixture made by 43.0.3 opens under 50.0.2, 14/14 from source and 14/14 from the packaged app.
- Old models: sentence model, scikit-learn models and torch weights load with the same results. A file holding Python
  objects is refused.
- Local AI with Ollama: 19/20. The other test is STALE_EVIDENCE, not a defect. Its held-out benchmark hashes all of
  `persistent_memory.py`, frozen 2026-10-19. Later changes there are vault tables, pruning and journal recovery, not
  scoring, and they predate RUNTIME-11. The hash was not edited. A new independent held-out set is needed to clear it.
- Drills: runtime 22, memory 34, backup, recovery and travel all pass.
- Packaged: extended 23, memory 35, launcher, statement parsing and OCR 13/13.
- Journeys: 89/89 and 13/13. A third set is 199/201. Its two failures are the Reports page answering 403 by design, and
  they count as console errors.

## Regression

- Chrome on `338ad27`: 156/156, shard accounting complete.
- Backend on `d2a9601`: 2,521 run, 0 failures, 176 skipped. Through `SafeDisk`: the same counts.
- Chrome runs on earlier commits failed one or two tests each, a different set each time. No product change was needed for
  them apart from the 30-second recheck above:
  - Lost session: the live server shares one in-memory SQLite connection between threads, which the real runtime does not,
    and a page's burst of requests could empty a session read. `tests/test_user_data_browser.py` now takes requests one at
    a time, except in the four tests that hold a request open. This failure also occurred at `904a6e6`, before the
    mitigation: the reminder journey failed 2 of 6 runs there, by lost session or by the rate limit below.
  - API budget: the reminder journeys spent 102 to 121 of the 120-per-minute budget, depending on machine speed. They now
    run without that budget. `tests/test_global_abuse_limits.py` still covers the limit.
  - Reading during a redraw or fade: the Yahoo evidence and two Career tests now wait.
  - Removed cookie restored by a late response: four auth-loss tests now end the session itself.
- Taking requests one at a time reduces concurrency coverage in that test class, so concurrency rests on the drills and on
  this probe: the real packaged app, at `4e140df`, was sent 120 requests in bursts of 10 with one session. 119 answered 200
  and one 429 at the budget limit, with no session lost.

## Package and installer

Built from `d2a9601` with the existing signed Inno Setup, on disposable folders and synthetic data. The owner's installed
ALFRED was not modified.

- `ALFRED-Setup.exe`: 449,204,998 bytes, SHA-256 `d725f6470fccdb83bb56d53df09b0b19186a3393683b835225e8591e42b95d99`.
- `ALFRED-Windows-x64.zip`: 501,959,474 bytes, SHA-256 `1c9ca18ac56999da9b602acc2d116c719aabf2f825158b280c2a794d17ededea`.
- Installer verifier 6/6 and lifecycle 37/37: failed install, refused and interrupted upgrade, upgrade while running,
  rollback keeping later writes, uninstall keeping data, and reinstall.
- Finding: an upgrade interrupted by a locked file does not restore files already replaced, so the app will not start until
  Setup runs again. Data was unchanged, and rerunning Setup repaired it.
- Finding: the installer is not code-signed. Windows Smart App Control blocked an earlier build (`4e140df`) twice, then
  allowed the same file on a later attempt, and it allowed the `d2a9601` build first time. Other users may see the block.
  Only Inno Setup itself is signed.
- Operator databases had identical SHA-256 hashes, `integrity_check` ok and no foreign-key errors, before and after.

PENDING: separate-user installation and a clean PC.

## Acceptance

RUNTIME-11 stays unaccepted. Still needed: exact-head CI, an independent review, and the owner's decision on the residual
risk.
