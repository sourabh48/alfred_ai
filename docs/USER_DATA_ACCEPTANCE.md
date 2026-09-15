# Sample-user data acceptance audit

Date: 16 September 2026. Code baseline: `a20435e`, plus the current working tree.

## Decision

**The project is not fully accepted yet.** The local stack, recovery, fresh CI
browser execution, broader real documents, and real model outcomes still need
evidence. The [completion audit](COMPLETION_AUDIT.md) separates these open items
from implemented functionality. The sample below tests application correctness;
it does not certify model accuracy or replace testing with real users.

## Test account and inputs

The repeatable scenario signs up `acceptance_demo` (Asha Demo), then creates its
records through authenticated application APIs. Each test uses a temporary test
database; the normal user database is not seeded. Test passwords are fixtures,
not live account credentials. The databases are removed after the run.

| Input | Synthetic value |
| --- | ---: |
| Salary, each of three recorded months | INR 80,000 |
| Declared housing cost and actual rent each month | INR 20,000 |
| Active personal loan EMI | INR 10,000/month |
| Entered outstanding loan balance | INR 100,000 |
| Latest entered savings-account balance | INR 150,000 |
| Investment cost / current entered value | INR 100,000 / 110,000 |
| Monthly investment contribution | INR 5,000 |
| Current flexible budget | INR 30,000 |
| Groceries + utilities in each earlier month | INR 5,000 + 3,000 |
| Groceries + utilities in latest month | INR 6,000 + 4,000 |
| Latest-month card payment | INR 2,000 |
| Own-account transfer in / out | INR 10,000 / 10,000 |
| Unidentified debit awaiting review | INR 60,000 |

There are 20 transaction records, one bank account, one loan, one investment and
one budget. Dates follow the test month's calendar. External market/career
evidence uses explicit offline fixtures; the local arithmetic is not mocked.
The entered bank balance is a snapshot, not a balance rebuilt from this partial
transaction history. A linked transaction's closing balance can update it;
ordinary manual expenses do not imply a complete bank ledger.

## Independent reconciliation

| Output | Expected and verified |
| --- | ---: |
| Latest-month income | INR 80,000 |
| Direct living expenses, including rent | INR 30,000 |
| Confirmed outflow: 30,000 + 10,000 + 5,000 + 2,000 | INR 47,000 |
| Recorded cash left: 80,000 - 47,000 | INR 33,000 |
| Three-month income / confirmed outflow | INR 240,000 / 123,000 |
| Cash retained as a share of all recorded income | 48.75%, displayed as 48.8% |
| Fixed obligations: housing + loan EMI | INR 30,000/month |
| Flexible living spend this month | INR 10,000 |
| Flexible budget remaining: 30,000 - 10,000 | INR 20,000 |
| Average flexible spend: (8,000 + 8,000 + 10,000) / 3 | INR 8,666.67/month |
| Estimated capacity before investments/card payments | INR 41,333.33/month |
| Estimated recurring living outflow | INR 38,666.67/month |
| Cash runway: 150,000 / 38,666.67 | 3.88 months |
| Assets: bank balance + entered investment value | INR 260,000 |
| Liabilities | INR 100,000 |
| Net worth: 260,000 - 100,000 | INR 160,000 |
| Unrealized investment gain | INR 10,000 |

Transfers do not become income or spending. The INR 60,000 unidentified debit is
shown as excluded pending review. Actual available money may be lower; the
dashboard explicitly warns about this and withholds its health score until
review is complete. These totals are confirmed-record totals, not a bank balance.

## Defects found and corrected

1. **Rent was deducted twice.** Before correction, average variable spend was
   INR 28,666.67 and estimated savings capacity INR 21,333.33. Housing already
   reserved in fixed costs is now excluded once per calendar month. Split rent
   payments share the allowance; excess rent and undeclared rent still count.
2. **Budget summary, categories and daily guidance disagreed.** Transfers,
   investments, settlements and review items inflated flexible spending to
   INR 117,000. All budget paths now use the same living-spend definition.
   Category history uses monthly totals rather than average transaction size,
   allocations follow the selected plan, and the table includes every category.
3. **The newest saved plan could belong to the wrong month.** Plan selection
   now uses its calendar month. A zero budget remains zero, and malformed months,
   negative amounts and non-finite amounts are rejected.
4. **Forecast windows drifted by using 30-day months.** Forecast labels now use
   calendar months and the canonical recent-spend average. Missing history does
   not become zero-cost observed months. Estimates are explicitly labelled.
5. **Edits left stale cached totals.** Successful authenticated API changes
   invalidate derived user and consent-linked family views. A generation token
   prevents an older in-flight response from repopulating a usable stale cache.
   Background/admin writes still rely on their revision/TTL contracts.
6. **Account and loan references lacked ownership validation.** Another user's
   bank account or consolidation loan now fails validation; self-consolidation
   also fails. Cross-user detail reads return 404.
7. **A minimal expense could fail with a NULL payment mode.** Missing inferred
   fields now preserve model defaults or existing values.
8. **Timeframes and estimate labels were misleading.** The dashboard now names
   its latest recorded month and labels all-history ratios. Monthly charts
   include card and investment outflows. Empty accounts show missing history;
   zero recorded assets/debt no longer produce a critical negative-net-worth
   message. Investment gains and growth assumptions have clearer explanations.

## User-understanding checks

Real Edge pages were checked for the expected amounts and explanations on
Dashboard, Budgets, Loans and Investments. Additional browser cases cover an
empty account and older history. The default browser suite also retains the
three document/login/upload/vehicle workflows.

- Amounts use INR formatting and readable category names.
- The reporting month is visible, including when it is older than this month.
- Living expenses, total cash outflow, flexible spending and net worth have
  distinct labels and explanations.
- Transfers and review exclusions are explained; a pending debit does not
  silently support a reassuring health score.
- Budget forecasts are planning estimates, not trained-model predictions.
- Recorded investment values are not presented as live market prices.

This is a developer readability review with automated browser assertions and
screenshots. Human usability testing, accessibility testing with assistive
technology, and complete phone-size coverage remain unverified. Career, risk,
relationship, vehicle and investment recommendations retain heuristic/data
limits; the arithmetic check does not validate those predictions.

## Evidence and repeatable commands

Set `ALFRED_AUTO_TRAIN_ON_STARTUP=false` before running verification.

```powershell
$env:ALFRED_ACCEPTANCE_REPORT='artifacts/verification/user-data-after.json'
.\.venv\Scripts\python.exe manage.py test tests.test_user_data_acceptance --noinput
.\.venv\Scripts\python.exe scripts/run_browser_regressions.py --browser Edge --require-browser --proof-label local-edge
```

- Scenario: `tests/user_acceptance_scenario.py`.
- Arithmetic, edits, validation and isolation: `tests/test_user_data_acceptance.py`.
- Actual page rendering and chart values: `tests/test_user_data_browser.py`.
- Before/after payloads: `artifacts/verification/user-data-before.json` and
  `artifacts/verification/user-data-after.json`.
- Full backend log: `artifacts/verification/user-data-full-suite.log`.
- Browser log: `artifacts/verification/user-data-browser-final.log`.
- Browser summary: `artifacts/browser/browser_regression_summary.local-edge.json`.
- Screenshots and visible text: `artifacts/browser/user-data/`.

Final verification: **373 non-browser tests passed** (379 discovered, six browser
cases deliberately skipped), and **all six Edge browser tests passed separately
with zero skips**. Django checks, migration drift and changed JavaScript syntax
checks also passed. Generated evidence is ignored by Git. See the completion
audit for outstanding operational acceptance.
