# Local/LAN completion audit

Audit started: 15 September 2026. Continued: 16 September 2026 (Asia/Kolkata).
Initial baseline commit: `c31de65`. Sample-user continuation baseline: `a20435e`;
results cover the local working tree.

**Result:** requirements are **not all accepted**. The current working tree
passed **373 non-browser tests and all six Edge workflows**. The sample-user
continuation fixed additional arithmetic, cache, ownership and presentation
defects. Runtime acceptance remains open because
Docker is unavailable; real-data model validation and fresh CI Chrome proof also
remain.

This checklist compares the README, project tracker, architecture and status notes
with implementation and recorded verification. Implementation, test results,
runtime operation and real-data maturity are separate checks. Synthetic fixtures
are regression evidence only. Public deployment and the planned RL learner are
outside this audit.

## Requirements checklist

| Requirement | Implementation at audit start | Verification / remaining work |
| --- | --- | --- |
| Accounts, family sharing and operational access | Implemented | Included in backend suite; browser login covered |
| Statement intake and financial consistency | Implemented | Deduplication/calculation regressions in backend suite; real-page statement correction passes |
| Budgets, daily guidance and financial baseline | Corrected in sample audit | Housing counted once, eligible spending aligned, current-month plan selected, forecast calendar corrected; independent arithmetic and edit tests |
| Sample-user values and readable output | Verified for core finance scenario | Signup plus 20 transactions through APIs; dashboard, budgets, loans, investments, empty and older-history browser checks; see [sample audit](USER_DATA_ACCEPTANCE.md) |
| Account ownership and derived-data refresh | Corrected in sample audit | Foreign account/loan links rejected; edits/deletes refresh cached user and consent-linked family views; in-flight invalidation regression |
| Loan consolidation and foreclosure reconciliation | Implemented | Lifecycle, cross-module calculations and linked retry records covered by regressions |
| Uploaded credit reports and loan synchronization | Implemented | Extraction/synchronization and retry regressions present; live bureau API remains absent |
| Investment PDF and email intake | Implemented | Partial/reordered holding retries preserve values and links; live mailbox requires configured access |
| OCR candidates, overlays and accepted corrections | Implemented | All correction families have backend coverage; statement and vehicle forms have local Edge proof; broader real layouts remain |
| Raw-upload retention and retry behavior | Implemented | Missing/purged original-file cases tested across all seven file scopes; retained corrections remain usable |
| Career, vehicle and advisory evidence | Implemented with heuristic/data limits | Outcome, freshness and failure-recovery contracts covered by regressions; fresh real outcomes still required |
| Supervised ML quality and freshness | Training implemented | Readiness gates enforced and regressions pass; poor expense quality, tiny datasets and proxy targets remain blockers |
| Browser interactions and CI | Runner/workflow implemented | Local Edge suite expanded from three to six workflows; fresh CI Chrome and wider interaction coverage remain |
| Local stack and background jobs | Compose configuration implemented | Configuration fixes and verification helper complete; Docker unavailable, so runtime remains unverified |
| Backup, restore and restart recovery | Instructions exist | Safe backup/isolated-restore helper and 19 unit tests complete; live restore and host restart drill still required |
| Cache performance | All 21 groups have staging proof | Isolated synthetic workload covers 21/21 namespaces; Redis, concurrent load and runtime tuning remain |
| Documentation and completion tracking | Reconciled | README/model claims, local commands, OCR/future scope and tracker next steps updated; percentages remain maturity estimates |

## Remaining requirements and their acceptance conditions

| Priority / area | What is left | Evidence needed to close it |
| --- | --- | --- |
| Local runtime | Docker/Compose unavailable on this host | Start local PostgreSQL, Redis, web, worker and beat; pass `scripts/local_stack_ops.py verify` |
| Recovery | Live backup/restore and host restart persistence untested | Paired backup, successful isolated database/file restore, restart and verify records/files remain |
| LAN operation | A second device has not been tested | Trusted second-device login and API access, with the intended local firewall/bind configuration |
| Scheduled work | Contract tests exist; sustained actual scheduled outcomes are unverified | Observe worker/beat evidence refresh, cleanup and permitted training across scheduled cycles |
| CI and browser breadth | Local Edge proof exists; fresh CI Chrome and wider form/device coverage are missing | Current-change CI Chrome with no skips; extend document-family/forms, phone sizes and accessibility checks |
| Cache/load | Sequential isolated workload covers all 21 namespaces | Shared Redis under concurrent realistic reads/writes, capacity/latency measurements and TTL tuning |
| ML serving maturity | Expense validation failed its quality gate; other sample counts are tiny and some targets are proxies | Sufficient consenting real data, actual outcomes, chronological holdouts and passing quality/freshness gates for each model |
| Document maturity | Arbitrary or severely degraded layouts cannot be guaranteed | More reviewed real documents per family, accepted corrections, false-match and retry evidence |
| Career/vehicle/advisory maturity | Source/geography/catalog gaps and heuristic assumptions remain | More real salary, service-cost, condition and outcome records; healthy sources and calibrated predictions |
| Live integrations | Email/intake adapters tested with fixtures; approved official bureau pulls absent | Configured live account evidence for email, and a separately approved consented bureau integration if required |
| Usability | Developer readability review completed for core finance pages | Task-based testing with actual users and assistive technology; no claim of comprehensive human validation |

Future enhancements are tracked separately in [Future scope](FUTURE_SCOPE.md):
generic vehicle naming, more source/catalog coverage, portfolio/job alerts and a
formal release acceptance registry. Public/cloud hosting and the planned RL
learner remain outside the active local/LAN requirement. No independent signed
requirements specification was present; this audit uses the README, architecture,
status/future-scope documents and live project-tracker definitions.

## Sample-user continuation

The [sample-user audit](USER_DATA_ACCEPTANCE.md) contains the full input and
expected-output table, the defects reproduced before fixing them, the user-facing
explanations and artifact paths. Before the fixes, INR 10,000 of flexible spending
appeared as INR 117,000, rent reduced estimated savings twice, and edited values
remained stale. Current API and browser results reconcile independently across
income, expenses, budget, loan, investment and net-worth views.

The synthetic user is temporary and is not left in the normal user database.
Market/career sources use offline fixtures; arithmetic uses the real services.
Final continuation verification:

- **379 tests in 495.965 seconds; OK (skipped=6)**, exit 0. This is 373 passing
  non-browser tests; the six Selenium cases are deliberately separate.
- **6 Edge tests in 38.885 seconds; OK, zero skips**, exit 0. This includes the
  three earlier document workflows and three new sample-user/readability cases.
- Django system check passed; no migration changes were detected.
- All four changed JavaScript files passed syntax checks; `git diff --check`
  passed.
- Eight new backend acceptance tests cover independent totals, aligned budget
  guidance, month selection/invalid input, edits/deletions, minimal input,
  ownership isolation, housing allowance boundaries and in-flight cache writes.

Logs: `artifacts/verification/user-data-full-suite.log` and
`artifacts/verification/user-data-browser-final.log`. Summary:
`artifacts/verification/completion_audit_summary.json`.

Browser setup initially read animated elements before visible text was ready.
Its waits now require populated text, and teardown drains active Django requests
before removing the temporary user/session data. The final run has no test
errors or session-cleanup exceptions. Navigation can still log harmless client
disconnects (broken pipes).

## Verification log

The sections below preserve the initial audit evidence. The sample-user
continuation uses `artifacts/verification/user-data-full-suite.log` and
`artifacts/verification/user-data-browser-final.log` for its later results.

### Browser and document interaction

The real Edge run passed all three workflows with zero skips: login/statement
upload/vehicle setup/dashboard refresh, statement candidate correction, and
vehicle OCR overlay correction. The latter two now submit through the actual
page buttons and verify that a refresh preserves the same open form and values.

The audit found that `documentCenterRoot` covered only the hero header. Review
forms were outside its interaction guard and were replaced during Save clicks.
The root now contains the whole page, and a background response rechecks the
guard before rendering. Numeric correction fields accept decimal values.
Tests use temporary SQLite file storage to support concurrent browser requests;
instant test scrolling avoids clicking before the page's smooth scroll ends.

```powershell
.\.venv\Scripts\python.exe scripts/run_browser_regressions.py --browser Edge --require-browser --proof-label local-edge
```

Proof: `artifacts/browser/browser_regression_summary.local-edge.json` and
`artifacts/verification/browser-audit-final.log`. Browser runner unit checks: 7 passed,
including required-browser failure when zero tests run. This is local Edge
evidence; a fresh CI Chrome run and wider browser coverage remain open.

### Local operations

The Compose stack now uses the local environment password consistently, binds
to loopback by default, shares persistent model storage between web/worker,
waits for web migrations before worker/beat startup, and checks beat's own
process. Runtime secret files and backups are excluded from the Docker context.

`scripts/local_stack_ops.py` provides read-only verification, a paired database
and file backup with writers paused, and restoration into a generated temporary
database. Its 19 unit tests cover integrity, unsafe archives, service recovery,
and cleanup failures. Actual Docker backup/restore has **not** run.

```powershell
.\.venv\Scripts\python.exe scripts/local_stack_ops.py verify
```

Result: exit 1, **Docker CLI unavailable**. The blocker is recorded in
`artifacts/ops/local_stack_verification.json`. Service health, migrations on
PostgreSQL, real Redis/worker operation, host restart persistence, second-device
LAN access, scheduled job outcomes, and a live isolated restore check remain
unverified. See [Local hosting](LOCAL_HOSTING.md) and
[Backup and restore](BACKUP_AND_RESTORE.md) for repeatable commands.

### Model evidence and limits

Training completion is now separate from inference readiness. Runtime checks
require sufficient samples, quality/confidence, fresh validation and an existing
artifact. Proxy labels used for burnout, behavioral risk, and parser confidence
remain explicit validation blockers. Salary fitting no longer uses its salary
target as an input. Expense windows retain user boundaries and chronological
holdouts, compare against a recent-median baseline, and reject failed artifacts.

The pre-existing registry records expense WAPE `0.9719` and quality `2.81/100`,
so it fails its quality gate. Other recorded datasets have 9–15 rows. Those
historical fits are not proof of reliable predictions. This continuation did
not retrain on the live user database. Synthetic regressions verify behavior;
fresh real outcomes and validation data remain required.

### Application checks

`manage.py check` passed with no issues and
`manage.py makemigrations --check --dry-run` found no model changes.
Both modified JavaScript files passed `node --check`.

Document retry/privacy verification: **43 passed**. The 12 new integrity tests
cover missing/purged sources, saved corrections across document families,
reordered/partial financial rows, zero amounts, and linked-record preservation.
ML/readiness integration verification: **43 passed**, followed by **12 passed**
for the final training-summary and fixture changes. Browser-runner verification:
**7 passed**.

Final full-suite command, with `ALFRED_AUTO_TRAIN_ON_STARTUP=false` and
`ALFRED_RUN_BROWSER_TESTS=false`:

```powershell
.\.venv\Scripts\python.exe manage.py test --noinput --verbosity=2
```

Result: **368 tests in 478.506 seconds; OK (skipped=3)**, exit 0. The three
Selenium tests are intentionally excluded from this run and passed separately
in Edge with zero skips (23.062 seconds). Final backend log:
`artifacts/verification/backend-audit-final.log`. Machine-readable summary:
`artifacts/verification/completion_audit_summary.json`. Final `git diff --check`
also passed. The initial run exposed statement fixtures without source files,
stale documentation assertions, and ML imports during concurrent edits; these
were corrected and the entire suite rerun against the settled code.

### Isolated cache workload

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_local_cache.py
```

Proof: `artifacts/cache/isolated_synthetic_benchmark.json`.

| Measurement | Result |
| --- | --- |
| Data | 3,000 seeded expenses; 3,005 including cross-module fixtures; one synthetic user |
| Requests | Ten repetitions per target; 21/21 materialized namespaces observed |
| Materialization calls | 239 total; 215 hits and 24 misses; 90.0% hit rate |
| TTL coverage | 100% observed |
| Exercise duration | 11.094 seconds, excluding database setup/migrations |
| Average generation latency | 45.6 ms from existing namespace telemetry |
| Isolation | Temporary SQLite/media/model paths, private memory cache, offline evidence fixtures |
| Network / cleanup | Zero attempted network calls; temporary storage removed |

The benchmark also passed with conflicting PostgreSQL/Redis/startup-training
environment settings, confirming that the isolated configuration took effect.
Per-endpoint timings are in the report. These measurements use sequential
Django test-client requests and are affected by other work on the host. They do
not establish real-user latency, concurrent throughput, Redis behavior, or model
accuracy, and are stored separately from runtime production proof.

## Remaining acceptance work

1. Make Docker/Compose available and start the configured local stack, then run
   `scripts/local_stack_ops.py verify`.
2. Capture a paired backup, pass its isolated restore check, and verify data
   persistence after an agreed host restart.
3. Verify access from a second trusted LAN device if LAN access is needed and
   observe worker/beat outcomes across their actual schedules.
4. Obtain fresh CI Chrome proof and expand browser coverage beyond the six
   current workflows; measure Redis and concurrent traffic on the running stack.
5. Collect real validation outcomes and enough samples for ML readiness. Tiny
   fits and proxy labels remain blocked even when fitting completes.

No cloud deployment, live restore, host restart, or production-data retraining
was performed during this continuation.
