# M13D Expense and BankAccount currency storage

Development continues in `F:\ALFRED_DEV\m13c` on
`codex/expense-bank-money-m13d-20261006`, from the verified M13C source
commit `4ac6c10`. The original checkout and private restored runtime remain
separate. Hosted Codex performed the migration and financial-correctness work.
Existing M13C implementation and completed audits were retained.

## Scope and guarantees

- Expense `amount` and nullable `closing_balance`, and BankAccount nullable
  `current_balance`, use 14-digit, two-place Decimal fields. Runtime/API/import
  boundaries enforce finite bounded HALF_UP cents, with a stored absolute limit
  of `999999999999.99`. Null balances remain distinct from explicit zero;
  negative balances remain supported. Virtual totals may exceed the field limit.
- `expenses.0005_expense_bank_money_decimal` validates both registers before
  capture, retains original float representations and independently normalized
  cents in owned snapshots, changes fields, then explicitly applies values with
  markers on the selected database alias. An unchanged, applied, still-owned
  field can restore its original precision on reverse. Edits, new rows,
  changed owners and unapplied/orphan evidence are guarded. Reset removes
  owned snapshots, including orphan evidence, without removing another user's.
- Historical transaction fingerprints are unchanged. `transaction_identity`
  retains the original amount/closing-balance representations for the existing
  float-format hash and exact reference-signature algorithms. Reimports and
  changed-closing-balance reference deduplication use this retained amount.
  Metadata edits and resubmitted displayed cents preserve it; a real monetary
  change replaces the affected identity. Identity evidence is private/internal.
- Account balances are converted independently, never recomputed from statement
  rows. Ownership, account/upload links, raw descriptions, external references,
  dates, timestamps, classifications, confidence and extracted payloads are
  retained. Transfer legs remain separate and excluded from direct spend/income.
  Legacy register/history inconsistencies are not repaired by this migration.
- Currency totals use Decimal accumulation and existing numeric JSON contracts.
  Bank aggregation, canonical balance sheets, Loan detection, credit utilization,
  voice and financial-brain callers accept the new register types. Statistical
  ratios and model inputs retain appropriate float boundaries. The financial
  cache version advances. Rates, confidence and other domains are unchanged.
- Invalid statement currency is rejected before any account/upload mutation.
  Expense/account posting and statement persistence are atomic. Python field
  validation does not protect arbitrary raw SQL or database expressions.
- A real Chrome Expense edit exposed a dialog hidden behind its backdrop in
  the scrolling workspace. The dialog now attaches to the body before Bootstrap
  initialization; its asset version advances. The real-click regression passes.

## Validation evidence

All application gates use disposable SQLite databases, separate data directories,
disabled startup auto-training and local-memory caches. The verified PyCharm
Python 3.12.10 environment is reused. External development files are outside
PyCharm's configured module, so preflight uses the original `manage.py` and its
reported interpreter. No runtime environment file or helper PYTHONPATH is loaded.

- Focused final domain/migration/baseline gate: 34 passed, exit 0, 27.728 s.
- Loan/foreclosure compatibility gate after updating the former Expense-float
  assertions: 38 passed, exit 0, 0.905 s. These now check normalized Expense
  cents and the retained source identity; Loan posting behavior is unchanged.
- Synthetic combined M13C/D rehearsal: 1 passed, exit 0, 11.831 s. It verifies
  source preservation, full retained-source restoration on reverse, repeat apply,
  and refusal to reuse evidence directories or target the source runtime.
- Focused Chrome Expense workflow: 1 passed, exit 0, 9.388 s, driver-backed.
  It checks the actual form, exact cents, unchanged fingerprint/evidence,
  changed-balance reference reimport suppression and numeric API output.
  Its screenshot was inspected.
- Migration drift: no changes detected. Whitespace check passed.
- AST-only Graphify update: 7,498 nodes / 19,529 edges, exit 0, no clustering,
  semantic extraction or model calls. 26 unclassified and 35 symbol-free files
  remain documented index limitations.
- Corrected full backend: 737 run / 718 passed / 19 disabled-browser skips,
  zero failures/errors, exit 0, 641.684 s. Log: `m13d-backend-verified.log`.
- Full serial Chrome: 19 passed, no skips, exit 0, 125.521 s; the proof summary
  confirms driver-backed success. Log: `m13d-chrome-verified.log`.

Logs and browser proof stay under `F:\ALFRED_RECOVERY\m13d-*`. The initial resumed
focused gate found two credit-utilization type errors; the corrected focused
gate passed. A new invalid-ORM fixture initially broke its enclosing test
transaction; isolating each expected failure fixed the fixture. The first focused
Chrome attempt reproduced the backdrop bug; the real-click retry passed after
the targeted repair. Failed logs are retained, not counted as passing evidence.
The first full backend attempt ran 737 tests in 652.318 s, with four failures and
19 disabled-browser skips. All four were old Loan-domain assertions expecting
fractional-cent Expense floats; the M13D fixtures now retain their original
source amounts explicitly and assert Decimal storage. The focused 38-test gate
passed, and the corrected full rerun supplies the completion gate.

## Private database rehearsal and live gate

`scripts/rehearse_money_migrations.py` reads source DB/WAL/SHM bytes through file
copies only, checks stable hashes, and opens SQLite exclusively on disposable
copies. It creates a separate fresh pre-migration SQLite backup, checks integrity
and all-table logical equality, rejects unexpected migration plans, applies only
M13C + M13D, reconciles each currency value and owned snapshot, checks every
unrelated column/table and historical fingerprint/reference signature, checks
repeat application, and reverses a second copy to the exact original data.
Detailed hashes and financial totals remain in private evidence outside Git.
Fresh backup verification must also run independently of its creation helper.

The private-copy rehearsal is pending until both full application gates pass.
Neither migration is authorized for the live private database by this development
task. Controlled live migration requires successful reconciliation, an independently
verified fresh backup, stopped writers and explicit live-migration authorization.
Keep all retained recovery backups and pristine historical data.
