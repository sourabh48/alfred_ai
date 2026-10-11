# M13C Investment currency storage

Development checkout: `F:\ALFRED_DEV\m13c`, branch
`codex/investment-money-m13c-20261006`, based on `5687a82`.
The restored application continues to use `F:\ALFRED\alfred_ai` and
`F:\ALFRED\restored-runtime`. No M13C migration has run on an operator database.

## Implemented scope

- Only Investment `invested_amount`, `monthly_sip`, and `current_value` become
  Decimal fields with 14 digits, two decimal places, finite bounded input and
  HALF_UP normalization. The stored absolute limit is `999999999999.99`.
- Migration 0004 retains original float representations and normalized cents
  in owned snapshots before altering fields. All legacy amounts are validated
  before capture. Explicit application uses the selected database alias and
  stamps an apply marker. Reverse migration restores only unchanged fields of
  applied snapshots with matching ownership; edits and new records survive.
- Ordinary ORM writes and API/document boundaries normalize currency. Numeric
  JSON remains numeric. Virtual totals do not inherit the per-field bound.
  Arbitrary raw SQL and database arithmetic expressions are not validated by
  the Python field helper.
- Summary weighting, allocation, portfolio mix, canonical investment assets,
  net-worth output, voice output and recommendation profiles accept Decimal
  register values. Existing tax deductions already accumulate via Decimal and
  cap the result before their numeric output boundary.
- Correction and retry persistence keeps extracted source evidence and
  accepted correction text. Invalid currency aborts related writes; the PDF
  holdings loop is atomic. Retry extraction's missing/placeholder zero cannot
  erase an existing amount; explicit zero corrections can. Review output uses
  the linked register's explicit zero instead of an obsolete payload value.
- Owned data reset removes retained Investment snapshots, including orphans,
  while preserving other users' evidence.
- Rates, confidence, provider NAV, raw portfolio evidence and Expense/BankAccount
  storage remain unchanged. Projection still starts at recorded month zero,
  returns months 0..12, adds SIP at the beginning of each future month, divides
  the entered annual rate by 1200, and invalidates its cache by local month.

## Validation

All tests use disposable databases and distinct recovery validation directories,
with auto-training disabled and local-memory caches. The verified restoration
Python environment is reused without installing or modifying dependencies.
PyCharm reports that this external checkout is outside its configured modules;
the explicitly verified interpreter is used instead.

- Migration drift: no changes detected.
- Initial focused run: 81 tests passed; a subsequent money-only run passed 10.
  Later PDF atomicity and apply-marker/changed-owner checks are included in the
  final backend gate.
- Final backend: 709 tests run, 692 passed, 17 browser skips; exit 0,
  1145.507 seconds. This includes the final 12 Investment money tests.
- Investment-specific Chrome workflow: one passed, 73.086 seconds, exit 0.
- Final AST-only code index: 7,398 nodes / 19,142 edges, exit 0; no semantic
  extraction, clustering or model calls. There are 26 unclassified files and
  35 symbol-free source warnings; this is not a complete semantic audit.
- Full serial Chrome gate: all 18 workflows passed, no skips, exit 0,
  168.596 seconds. Its proof summary confirms driver-backed success and includes
  the Investment workflow added after backend discovery.
- Whitespace check passed. All required M13C development gates passed.
- The initial concurrent full Chrome attempt ended with a Windows Python fatal
  exception `0xc000070a` during test-user password creation. It produced no test
  result and left an orphaned headless driver holding the output pipe. The
  verified test-driver process tree was closed and its failure log/summary
  retained. The full browser retry runs after backend completion on separate
  disposable storage; no application workaround was added for this crash.

Evidence logs are under `F:\ALFRED_RECOVERY\m13c-*.log`, with browser summaries
and failure artifacts in the respective `m13c-*-proof` directories.
The separate Investment browser workflow checks form correction, half-cent
rounding, original evidence and numeric register API output.

## Continuation

After final gates, continue the dedicated Expense/BankAccount stage. First trace
normalization through import fingerprints, deduplication, bank syncing and Loan
detection; preserve raw evidence and linkage. Do not replace unrelated FloatFields
or migrate the restored private databases as part of development validation.

Restoration acceptance limits remain in `WINDOWS_RESTORATION_VERIFIED_20261006.md`:
real-account sign-in and private finance/Travel/media UI acceptance require local
confirmation; preserved historical data and the Docker VHDX still need classification.
The Desktop backup and pristine database copies remain retained.
