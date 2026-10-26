# ALFRED 2.0

A privacy-first Windows application connecting personal finance, documents,
wealth, investment research, career, travel and local intelligence. ALFRED runs
locally or on your LAN using **Django + Waitress + Huey + SQLite**. Ollama is the
default AI route; encrypted memory and reviewed evidence supplement canonical
calculations. Planned 2.0 upgrades reuse this application rather than separate apps.

## Current verified status

Generated from the [canonical inventory and PR checkpoint](docs/PROJECT_STATUS.md).
Counts describe accepted scopes, not universal accuracy or production readiness.

<!-- BEGIN STATUS DASHBOARD -->
**Baseline: 75/143 (52.4%) verified.**

IMPLEMENTED_NOT_ACCEPTED: 24 | PARTIALLY_IMPLEMENTED: 26 | BLOCKED_APPROVAL: 5 | BLOCKED_EXTERNAL: 3 | NOT_IMPLEMENTED: 10 | COMPLETE_VERIFIED: 75

PR/CI: PR #16 READY/open, unmerged. Recovery HEAD 06873da exact-head run 40286766839 PASS: Windows native, Selenium, Linux. INV-05 changes require their own pushed-head CI; no transferred green claim. READY_TO_MERGE: NO — independent reviews 0, protection GET 403, Pages authorization absent. AGENTS requires manual owner merge. No merge/publication or protection bypass.

Extensions: **0/13 accepted**; separate source-bound story ledger.
<!-- END STATUS DASHBOARD -->

[Current task and exact resume](docs/EXECUTION_STATE.md) ·
[Requirements](docs/ALFRED_2_0_REQUIREMENTS.md) ·
[Dependency queue](docs/EXECUTION_QUEUE.md) ·
[143-capability evidence](docs/PROJECT_STATUS.md) ·
[Acceptance gates](docs/ALFRED_END_TO_END_ACCEPTANCE.md)

Implemented, verified, configured-provider, real-account, native/packaged and
production acceptance are separate states. A pushed branch is not a merged PR;
a merge is not deployment authorization. No current production health is claimed.

## Features and coordinated upgrades

- **Finance and Wealth 2.0:** canonical income/expenses/loans/net worth, budgets,
  reconciliation and source-grounded planning; expand goals, reserves, snapshots,
  look-through and reviewable proposals. Preserve Decimal precision. Currency/FX/
  valuation policy remains unapproved; never infer denomination from location.
- **Career 2.0:** owned resume/JD/recruiter workflows, skill gaps, configurable
  Bengaluru/Java/Spring Boot/AWS search interests, job/application outcomes,
  interview preparation and evidence-labelled salary/career scenarios. No implicit sending.
- **Travel 2.0:** conversational discovery, private plans, day/stop editing,
  motorcycle/pillion budgets, maps and dated evidence. Expand routed detours,
  independently supported restrictions, organizers/reminders and exports. Car
  routing never proves motorcycle legality; links do not establish bookings/permits.
- **Investment 2.0:** owned portfolios, imports, evidence and scenarios; expand
  fundamentals/valuation, risk challenge, watchlists and goal-aware research.
  Suggestions are uncertain; no automatic stock trading or unapproved market feed.
- **Shared intelligence:** owner-isolated documents/citations, encrypted learning
  candidates and reviewed packs, local models, quality/readiness checks, bounded
  jobs, offline recovery and explicit confirmation. Private Git sync stays disabled.

Aurelio is reference-only; TREK ideas are independently implemented; TradingAgents
reuse requires component/license/dependency checks. Career Ops repository identity
is unresolved. See requirements for exact scope, exclusions and approval decisions.

## Install and develop

For users: [Windows installation](docs/INSTALLATION.md), [package guide](docs/WINDOWS_PACKAGE.md)
and [native runtime/recovery](docs/NATIVE_WINDOWS.md). Existing downloadable previews
are historical artifacts; they do not contain every current development feature.
Never promote a package or modify production based only on this README.

For developers: [development setup](docs/DEVELOPMENT.md), [repository map](docs/REPOSITORY.md),
[Travel providers](docs/TRAVEL_PROVIDERS.md) and [project instructions](AGENTS.md).
Keep secrets in ignored `config/local.env`; use the configured Python SDK and
isolated synthetic test data. No cloud deployment wiring or AWS runtime activation.

Check generated inventory views with the configured SDK:

```powershell
python scripts/project_execution.py --check
```

Use `--write` only after intentional tracker/requirements changes. The script is
network-free; it does not verify product behavior or activate integrations.

## Exact Codex commands

- **`continue`** — read EXECUTION_STATE, verify Git/HEAD, recover the current task
  and its incomplete step. Reuse valid evidence. If finished, report READY_FOR_NEXT
  and wait; do not start another task.
- **`next`** — checkpoint or explicitly defer the current task, select the next
  eligible queue item in phase/module order, execute that one task, then stop.
- **`status`** — read-only report of refs, PR/CI, task progress, baseline/modules,
  extensions, remaining categories and approval decisions. No source mutations.

Before interruption, record exact tests/artifacts, refs, changed/dirty files,
blockers and the next command in EXECUTION_STATE. Never reset, clean, force-push,
automatically stash or overwrite uncertain work. Master/Pages publishing and
production require the documented approvals; do not bypass missing reviews or 403s.

## Historical evidence

The dated reports and original Git history remain intact. They establish only
what was tested then, not the acceptance of the current development branch.
[README at the prior checkpoint](https://github.com/sourabh48/alfred_ai/blob/5af834c/README.md)
retains the earlier distribution/setup record.

<details>
<summary>Recorded 2026-09-26 through 2026-10-15 release evidence</summary>

### Historical verification receipts

**Recorded Windows verification, 26–29 September 2026.** These are completed
checks within the scope of the linked reports, not a claim of universal accuracy.

| Check | Recorded result |
| --- | --- |
| Then-current launcher and tray | Real Windows icon registered and removed correctly; offline guide present |
| Then-current packaged native runtime | **23 checks passed** on 28 September |
| Then-current concurrent local usage | **24 users, 480 writes, zero errors** |
| Then-current installed upgrade | **1.0.1 → 1.1.0 passed**, existing records retained and uninstaller present |
| Backend regression suite | **466 passed**; 11 browser cases skipped and checked separately |
| Chrome browser workflows | **11 passed**, zero skips, including travel planning |
| Full installer lifecycle | **6 passed** on the previous release; current full uninstall acceptance remains open |
| Observation and supervisor logic | **16 focused tests passed** |
| Tray/native/launcher logic | **16 focused tests passed** after branding changes |
| OCR, backup/restore, mobile layouts and automated accessibility | Passed within the documented test scope |

[Travel preview release verification](docs/TRAVEL_RELEASE_VERIFICATION_20260929.md) ·
[Previous tray and release verification](docs/WINDOWS_TRAY_VERIFICATION_20260928.md) ·
[Previous release verification](docs/WINDOWS_PACKAGE_VERIFICATION_20260927.md) ·
[Native runtime evidence](docs/WINDOWS_PACKAGE_VERIFICATION_20260926.md) ·
[Completion audit](docs/COMPLETION_AUDIT.md)

Still open: installation and reboot on a clean second Windows PC, a completed
continuous observation of scheduled jobs, manual screen-reader testing, heavier
real usage, and accuracy checks against independently reviewed documents and
outcomes. Model fitting alone does not establish accuracy. Optional LAN access
and live email/bureau integrations require their own configuration and validation.

The checkout includes [verification startup controls](docs/NATIVE_WINDOWS.md#verification-across-windows-sign-ins)
that retain interrupted reports and begin a fresh observation after sign-in.
Starting an observation does not count as passing it.


</details>
