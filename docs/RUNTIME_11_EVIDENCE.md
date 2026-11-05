# RUNTIME-11 evidence — 2026-11-04

Status: IMPLEMENTED_NOT_ACCEPTED. Baseline 75/143 and extensions 0/13 are unchanged. The owner formally accepted the
residual risk below on 2026-11-05. The advisory stays open and visible while the scanner reports it.

Which commit each result belongs to:

| Commit | Change | Results that apply |
|---|---|---|
| `d2a9601` | First mitigation, earlier package | Results kept below for history, marked with that commit |
| `297e180` | Last product change, and the source of the current package | Scan, drills, local AI, journeys, Chrome, backend, package, installer |

`0b42291`, `e46f4f9` and `297e180` changed product code after the review (see Independent review). `7bb90e9` and
`b1fcc92` are test-only. The final commit adds only this evidence and tracker text. A green check applies only to its
exact commit, so exact-head CI still decides.

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
- Other pickle paths, outside diskcache:
  - `joblib.load` in `apps/ml_engine/inference_adapters/` and `apps/ml_engine/loaders/model_loader.py`.
  - Huey payloads in `artifacts/native/jobs.sqlite3`.
  - Backups restore both `ml_models` and that queue file.
  - `torch.load` uses `weights_only=True`.
  - Since `0b42291`, startup refuses a queue file (`jobs.sqlite3`, `-wal`, `-shm`) or any model file that is not
    private. It does not repair them. See the review below for what this leaves.

## Independent review

A separate read-only reviewer, not the author, reviewed `d2a9601` and then the fixes. It covered diskcache JSON
integrity, the permission check race, multi-process creation, Huey and joblib pickle reachability and restored backups.

Findings on `d2a9601`:

- F1, Medium: the Huey queue and model files had no permission refusal, though both are read through pickle or joblib.
  Fixed in `0b42291`.
- F2, Low: a forged rate-limit row could raise on a huge number or block as long as a far-future time says. Fixed in
  `0b42291` and `e46f4f9`.
- F3, Low, residual: diskcache Settings rows can set cache attributes. Not fixed.
- F4, Low, residual: restore accepts any key (`scripts/release_recovery.py:260`); a crafted backup with its own key
  passes verification and is then unpickled. Not fixed.
- F5, Low, residual: during the 30-second recheck window a junction or re-created folder also passes.

Second pass on `e46f4f9` found two defects, both fixed in `297e180` with a test that fails on the old code:

- D1: forged times slightly ahead of now still blocked forever. Times ahead of now are now ignored.
- D2: SQLite creates and removes `-wal` and `-shm` while the startup check runs, which could refuse a healthy start. A
  failed check is now repeated once, and a file that vanished passes.

Residual after both passes, accepted by the owner on 2026-11-05 (OWNER_DECISION: "Accept the risk"):

- R1: the queue and model check runs at startup only. A file loosened while running is refused at the next start.
- R2: absolute `artifact_path` rows in the database are not checked (`training/quality.py:30`,
  `inference_adapters/artifacts.py:13`, `projection_engine.py:200`).
- R3: `-journal` is not checked; Huey uses WAL by default.
- R4: scripts that skip the launcher's configuration skip the queue folder check.
- One loose model file stops the app. This fails closed.
- Moving the clock back more than one window gives one fresh quota. That needs administrator rights.
- Anyone who can already write the private folders can still deny service.

The reviewer could not read the installed package sources, so diskcache Settings mechanics and Huey startup order were
reviewed from ALFRED code only.

## Compatibility, on `d2a9601`

- Cryptography: a fixture made by 43.0.3 opens under 50.0.2, 14/14 from source and 14/14 from the packaged app.
- Old models: sentence model, scikit-learn models and torch weights load with the same results. A file holding Python
  objects is refused.
- Local AI with Ollama: 19/20. The other test is STALE_EVIDENCE, not a defect. Its held-out benchmark hashes all of
  `persistent_memory.py`, frozen 2026-10-19. Later changes there are vault tables, pruning and journal recovery, not
  scoring, and they predate RUNTIME-11. The hash was not edited. A new independent held-out set is needed to clear it.
- Local AI on `297e180`: 13/20. The stale benchmark above fails as before. Six canonical tests time out: Ollama updated
  itself to 0.40.14 on 2026-11-03, after the last passing run. It now loads models without memory mapping, and ALFRED
  asks for a fresh load on every call, so each chat call passed the 30-second client limit (Ollama logged 500 at 30 s).
  Embedding calls all answered. The timeout was not raised; this needs a decision on the Ollama setup, not a code change
  here. Packaged memory drill on `297e180` with Ollama running: 35/35.
- Drills: runtime 22, memory 34, backup, recovery and travel all pass.
- Packaged: extended 23, memory 35, launcher, statement parsing and OCR 13/13.
- Journeys: 89/89 and 13/13. A third set is 199/201. Its two failures are the Reports page answering 403 by design, and
  they count as console errors.

## Regression

- Chrome on `297e180`: 156/156, shard accounting complete. Earlier: 156/156 on `b1fcc92` and `338ad27`.
- Backend on `297e180`: 2,526 run, 0 failures, 176 skipped. Through `SafeDisk`: the same counts.
- Since `b1fcc92` the browser tests run Chrome and Edge with reduced motion. Fades read as empty text and smooth
  scrolling misplaced clicks, failing a different test each run. The trade-off: animations and smooth scrolling are no
  longer exercised by these tests. The app's own reduced-motion rule is what now runs.
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

Built from `297e180` with the existing signed Inno Setup, on disposable folders and synthetic data. The owner's installed
ALFRED was not modified.

- `ALFRED-Setup.exe`: 449,202,204 bytes, SHA-256 `d520994d87468620f09d2809efa8cbc61cbc5f1bc0d90405625277174d79a925`.
- `ALFRED-Windows-x64.zip`: 501,961,984 bytes, SHA-256 `6cb1cf3162733c3387f325176b912f17edff918c9e516b90ec356e9be5273253`.
- Statement parsing and OCR from the packaged app: 13/13. Launcher: pass.
- Smart App Control blocked the new unsigned `ALFRED.exe` and `ALFRED-Setup.exe` (`WinError 4551`) in the extended
  drill, the installer verifier and the lifecycle test, so those did not run on `297e180`. It was not bypassed.
- Last full installer results, on `d2a9601`: verifier 6/6 and lifecycle 37/37: failed install, refused and interrupted
  upgrade, upgrade while running, rollback keeping later writes, uninstall keeping data, and reinstall. On `7bb90e9`,
  the same package code as `297e180` except the D1 and D2 fixes: extended 23, memory 35, crypto 14/14,
  verifier 6/6, lifecycle 37/37.
- Finding: an upgrade interrupted by a locked file does not restore files already replaced, so the app will not start until
  Setup runs again. Data was unchanged, and rerunning Setup repaired it.
- Finding: the installer is not code-signed. Windows Smart App Control blocked builds `4e140df` and `297e180`, and
  allowed `d2a9601` and `7bb90e9`. Other users may see the block. Only Inno Setup itself is signed. The owner decided on
  2026-11-04 not to buy a code-signing certificate, so the installers stay unsigned.
- Operator databases had identical SHA-256 hashes, `integrity_check` ok and no foreign-key errors, before and after.

PENDING: separate-user installation and a clean PC.

## Recheck on master — 2026-11-05

- The RUNTIME-11 branch is on master through PR #21 (`7ab0572`, then `0defab2`). Master `ca4d66a` contains `297e180`
  and passed all 14 CI checks on that exact SHA, so the exact-head CI item is met for that commit.
- Advisories: OSV queried for the 152 installed packages, the 168 Windows pins and the 145 Linux pins. Only `diskcache`
  5.6.3 is reported (GHSA-w8v5-vhqr-4h9v, the same issue as PYSEC-2026-2447 / CVE-2025-69872). The pip-audit download
  was refused on this PC, so OSV was queried directly with package names and versions only.
- `pip check` is clean. Every installed package matches its Windows pin exactly. Five installed packages had no pin:
  PyInstaller (pinned in `requirements-build.txt`) and its four dependencies. A rebuild could therefore pull newer
  PyInstaller hooks. They are now pinned in `requirements-build.txt` to the installed versions, with a contract test.
- The Docker image could not install its requirements: `requirements.txt` names `constraints/windows-py312.txt` next to
  itself, but the Dockerfile copied only `linux-py312.txt` into `/app/`, so pip stopped ("Could not open constraint
  file", reproduced locally). It now copies `constraints/` whole; the Windows pins all carry a `win32` marker and stay
  inactive on Linux. Docker is not installed here, so no image was built: the Linux install itself is unverified.
- Local evidence: `F:\ALFRED\dev-evidence\post-audit\runtime-11-20261105` (freeze and OSV results, not in Git).

## Acceptance

RUNTIME-11 stays unaccepted. The independent review is done and its defects are fixed. Exact-head CI passed on master
`ca4d66a`; the 2026-11-05 pin and Docker fix needs its own CI run. The owner accepted the residual risk above on 2026-11-05. Still needed: a fresh independent AI held-out benchmark, installer runs on
`297e180` where Smart App Control allows them, separate-user installation and a clean PC. Installer signing stays
declined by the owner.
