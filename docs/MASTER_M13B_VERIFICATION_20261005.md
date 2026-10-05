# Master M13B verification: related Loan currency

Task date: 2026-10-05. Status: implementation and verification complete.

This implements the scope in [MASTER_M13B_PLAN_20261005.md](MASTER_M13B_PLAN_20261005.md): nine `LoanPaymentHistory` currency fields, `LoanClosureDocument.closure_amount`, and seven `LoanForeclosureSnapshot` currency fields. Together with M13A, all 24 Loan-domain currency fields use the existing `LoanMoneyField` boundary: finite Decimal cents, HALF_UP, +/-999,999,999,999.99 per stored field. Confidence, rates and other measurements retain their existing types. API currency remains numeric JSON.

## Storage and evidence

Migration `0015_related_loan_money_decimal` freezes migration 0014's conversion policy. It validates all three legacy models before capture, retains original float text/null and normalized cents, and records original source, owner, Loan and relevant parent identities. Application is atomic, database-alias-aware and marked once. Reverse restores unchanged cells only under the original linkage and ownership; edits, null/zero transitions, new rows and deleted records are preserved. Owner reset removes retained snapshots even after source deletion.

The migration does not repair Loan register totals or historical allocations. A runnable reconciliation case retains two original `1.005` payments, normalizes their total to `2.02`, and reports the `0.01` difference from the existing `2.01` register. Raw Expense and document amounts remain evidence. SQLite's numeric storage/SQL aggregates still have limitations; actual per-field ORM retrieval is checked, and runtime history sums use Decimal values before output conversion. Virtual totals may exceed a field maximum; amounts persisted into a bounded field must validate and roll back atomically.

## Runtime behavior

Foreclosure matching and allocation use Decimal/integer cents. Deterministic remainder allocation spends each transaction's remaining cent capacity, conserving both transaction totals and all five component totals within the newly computed allocation. Partial matches stay provisional, mismatches stay unallocated, existing linked history is preserved, and finalized reconciliation is repeat-safe. Preserved history may retain component amounts different from the new allocation; its audit records identify the preserved rows. JSON audit values come from the same calculations. The obsolete residual-adjustment helper was removed.

For an unfinalized settlement, explicit accepted/requested zero stays zero and cannot infer a balance-sized closure. A parser's default zero for missing evidence retains the prior fallback. Requests use the existing accepted-correction evidence to distinguish the cases without overwriting raw parsed amounts. Document correction rejects malformed/non-finite/out-of-range/boolean currency with HTTP 400; document and snapshot synchronization share an atomic boundary. After finalization, corrections can update document/snapshot evidence but do not reallocate or reverse the posted audit/history/register; settlement undo is outside this stage.

Review of a payment already referenced by a finalized settlement is rejected before writes. Unrelated reviews can change evidence disposition while leaving the settled register authoritative; apply/reverse/history sync cannot replace the finalized balance, total or lifecycle. This fixes a reproduced loss: reviewing preserved unapplied history after a `3000.13` settlement previously produced `3000.03` on acceptance or `1000.01` on rejection and changed `foreclosed` to `closed`.

Payment detection/review, canonical component/home totals, tax history and document retry use the new money boundary. Unknown balances remain distinct from zero. Owned API access and legacy component fallback remain supported. Affected Loan and financial cache revisions were advanced.

## Verification

All application runs use the PyCharm-configured `F:\ALFRED\.venv\Scripts\python.exe` (Python 3.12.2), with environment preflight before every invocation. Tests use local runtime, disabled startup training, disposable SQLite data and locmem cache. No operator `config/local.env` or runtime database is loaded.

| Gate | Result | Local evidence |
|---|---|---|
| Related/register migration and verification | 36 passed, zero skips, 63.381 s, exit 0 | `artifacts/m13b-related-money-migration-final-20261005.log` |
| Money field and register/runtime boundaries | 27 passed, zero skips, 0.295 s, exit 0 | `artifacts/m13b-money-boundary-20261005.log` |
| Foreclosure cents, zero/evidence and existing lifecycle | 19 passed, zero skips, 6.478 s, exit 0 | `artifacts/m13b-foreclosure-zero-lifecycle-targeted-20261005.log` |
| Final adjacent runtime/API gate | 62 passed, zero skips, 2.987 s, exit 0 | `artifacts/m13b-adjacent-runtime-final-20261005.log` and result JSON |
| Deterministic Career parser fixtures | 5 passed, zero skips, 3.797 s, exit 0; runtime URL validation unchanged | `artifacts/m13b-career-dns-targeted-20261005.log` |
| Initial complete backend | 688 run / 669 passed / 17 browser skips / 2 errors, 746.737 s, exit 1; Career fixture DNS failures | `artifacts/m13b-backend-final-20261005.log` and result JSON |
| Final complete backend rerun | 688 run / 671 passed / 17 browser skips / zero failures/errors, 641.053 s, exit 0 | `artifacts/m13b-backend-verified-20261005.log` and result JSON |
| Chrome closure correction and canonical page totals | 2 passed, zero skips, 31.147 s, exit 0 | `artifacts/m13b-loan-browser-20261005.log`, `artifacts/browser-related-loan-money-20261005/browser_regression_summary.json` |
| Closure screenshot refinement | 1 passed, zero skips, 8.844 s, exit 0; screenshot inspected | `artifacts/m13b-closure-browser-final-20261005.log`, `artifacts/browser-related-loan-money-final-20261005/browser_regression_summary.json` |
| Django system check | No issues, exit 0 | `artifacts/m13b-system-check-20261005.log` |
| Model/migration drift | No changes, exit 0 | `artifacts/m13b-migration-drift-20261005.log` |
| Whitespace | Exit 0; ordinary CRLF conversion warnings only | `artifacts/m13b-final-diff-check-20261005.log` and result JSON |
| Final Graphify refresh after Career fixture/helper docstring edits | Exit 0; 7,220 nodes / 18,817 edges; AST-only, no clustering/model calls | `artifacts/m13b-graphify-update-complete-20261005.log` and result JSON |

The migration gate covers actual nondefault SQLite alias capture/application/reversal, source deletion, owner reset, idempotence, reversal guards and explicit child/register reconciliation. Runtime checks cover cent conservation, large virtual aggregates, bounded-write rollback, invalid correction atomicity, numeric JSON, ownership, nullable balances, raw evidence, cache refresh and finalized settlement review. Chrome exercises the actual closure correction form with `2.675`, preserving the input evidence while document/snapshot storage becomes `2.68`, and the existing dashboard/budget/Loan/investment totals workflow.

Earlier attempts are retained separately: the first migration run failed five zero-representation fixture assertions (`0` versus stored legacy float `0.0`); expected fixture text was corrected, migration source unchanged. The initial 59-test adjacent gate passed before the added transaction/finalized-review coverage and is historical evidence only. The isolated read-only settlement reproducer is `artifacts/m13b-lifecycle-readonly-reproducer-20261005.log`. The initial complete backend gate failed two pre-existing Career parser fixtures: page-fetch responses were mocked, but URL validation still performed real DNS for Ashby/Workday hosts. That run is not passing gate evidence. Only those fixtures in `tests/test_career_recruiter_and_evidence.py` were changed to supply a deterministic public resolver address alongside the mocked response; production URL validation still runs. The whole five-test module passed, and the final complete backend rerun uses the corrected fixture state.

## Limits and next stage

No operator database migration, commit, push, installer rebuild or release promotion occurred. PostgreSQL upgrade/rollback on real data is not claimed. Other monetary domains remain open under M13; M14 security remediation and later Travel work remain in the master backlog. Final graph coverage is AST-only: 24 unsupported files were skipped and 33 code files yielded no symbols. The isolated helper path remains recorded in `artifacts/m13-graphify-tool-path-20261005.txt`; its PYTHONPATH is confined to the separate Graphify process.

The scoped next stage is M13C: `Investment.invested_amount`, `monthly_sip` and `current_value`. Preserve annual return rates, confidence and raw portfolio evidence. Its adjacent slice must cover numeric serializers, Decimal/rate arithmetic, canonical asset/tax totals, correction/retry persistence and owner-reset snapshots. Expense/BankAccount currency is a later dedicated stage because normalization also changes import fingerprints, deduplication, bank syncing and Loan detection. Read-only scope evidence: `artifacts/m13c-storage-scope-graph-query-20261005.log`.
