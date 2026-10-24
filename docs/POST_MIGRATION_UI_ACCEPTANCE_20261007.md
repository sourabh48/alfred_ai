> Historical operator evidence, preserved during consolidation on 2026-10-21. Current state and instructions: [PROJECT_STATUS.md](PROJECT_STATUS.md). Dated deployment/acceptance claims below are not current release approval.

# Post-migration real-account acceptance — 2026-10-07

Application: http://127.0.0.1:8000/ . Deployed source:
`a9d096ea55839269fe6fce14d4f11ea2cbf05336`. M13C and M13D are already applied.

No connected browser surface is available to this agent. Every screen below is
PENDING until actually checked by the operator. Database readability and health
checks do not constitute UI acceptance. Keep credentials, figures, screenshots,
document contents and personal transaction descriptions on this computer.

Use the existing account. Navigate and filter only; do not save edits, create,
delete, import, reprocess, reset, refresh provider data or trigger background jobs.
Record PASS, FAIL or PENDING and a short sanitized reason for failures.

| Check | Read-only acceptance step | Result |
| --- | --- | --- |
| Existing-user login/session | Sign in privately; reload and open another tab. Confirm the same account remains signed in. | PENDING |
| Dashboard/finance summaries | Open the dashboard. Compare observed balances with local verified evidence; distinguish planning estimates, missing values and actual zero. | PENDING |
| Expenses | Open list and an existing transaction; check category, direction, currency, cents, null/zero balance and date/category/account filtering. No Decimal strings, object text, NaN or truncation. | PENDING |
| Bank accounts/transfers | Inspect existing accounts, balances and transaction history; verify transfer legs and account totals against local evidence. | PENDING |
| Investments/projections | Inspect existing holdings, invested/current values and SIP; check currency cents and projection display/assumptions. | PENDING |
| Loans | Inspect existing loans, outstanding balances, EMI and verification labels; compare locally with the verified snapshot. | PENDING |
| Budgets/monthly summaries | Open budgets and an existing monthly summary. Compare the same month/account/direction/category, respecting transfer exclusions and other displayed scope. | PENDING |
| Travel | Open existing trip history, the saved plan and trip details. Confirm saved content loads without editing or generating new research. | PENDING |
| Documents/media | Open an existing owned upload or trip photo through ALFRED. Verify actual authorized download/rendering; file presence alone is insufficient. | PENDING |
| Console/network | During these checks, inspect browser developer tools for console errors and failed ALFRED requests. Report only sanitized error classes/statuses and screen names. | PENDING |

Local comparison evidence (private; do not upload or paste its contents):

- `F:\ALFRED_RECOVERY\post-migration-acceptance-20261007\financial-comparison.private.json`
  contains current verified records and reconciled monthly expense groups; details remain private.
- `F:\ALFRED_RECOVERY\post-migration-acceptance-20261007\acceptance-verified-snapshot.sqlite3`
  is a consistent, read-only comparison snapshot matching the prior verified snapshot.
- Dashboard aggregates must use the application's canonical finance definitions;
  raw monthly groups are grouped by user/account/month/direction/category and are
  not an independently asserted dashboard total. Compare like-for-like scopes.

Automated closure checks: integrity PASS, both migration records unchanged,
scoped financial/Travel/document records unchanged, no financial mismatches or duplicate fingerprints, and referenced media locally
readable, native readiness 5/5, four health endpoints HTTP 200, worker/scheduler
healthy, zero interrupted claims/queued/scheduled jobs. Private config/media/model
hashes, protected pre-migration backup and encrypted recovery archive remain intact.
These results support storage/runtime recovery, while the ten UI results remain PENDING.

After checking, report only each check's status and sanitized blockers. Historical
Docker recovery and manual UI acceptance must be closed before new high-risk work.
