# Master M13B plan: Loan payment and foreclosure currency

Task date: 2026-10-05. Status: implemented and verified; see [MASTER_M13B_VERIFICATION_20261005.md](MASTER_M13B_VERIFICATION_20261005.md).

This document records the M13B scope after the Loan register stage in [MASTER_M13A_VERIFICATION_20261005.md](MASTER_M13A_VERIFICATION_20261005.md). It began as a read-only source review and implementation plan; the user authorized implementation on the next continuation. Actual results and limitations are recorded in the M13B verification note. Its final full gate passed 671 backend tests with 17 browser skips, plus two distinct Chrome workflows separately. The earlier M13A gate remains historical evidence for its own state.

## Proposed storage boundary

Convert these 17 currency fields in `apps/loans/models.py` together with their necessary arithmetic and output boundaries:

| Model | Fields | Count |
|---|---|---|
| `LoanPaymentHistory` | `amount`, `principal_component`, `interest_component`, `principal_paid`, `interest_paid`, `charges_paid`, `penalties_paid`, `tax_paid`, `remaining_balance` | 9 |
| `LoanClosureDocument` | `closure_amount` | 1 |
| `LoanForeclosureSnapshot` | `outstanding_principal`, `accrued_interest`, `foreclosure_charges`, `taxes_gst`, `overdue_charges`, `total_amount_payable`, `matched_payment_total` | 7 |

`LoanPaymentHistory.remaining_balance` is nullable: preserve unknown balance separately from explicit zero. The other currency fields retain their existing required/default behavior. Reuse the supported per-field cents boundary and HALF_UP policy established for the Loan register: finite values within +/-999,999,999,999.99, with 14 digits including two decimal places. Preserve signed legacy values during migration; business validation remains a separate concern.

Keep `detection_confidence`, `parse_confidence`, `classification_confidence`, `linkage_confidence`, and `reconciliation_confidence` as confidence measures. Interest rates, matching ratios, scores, dates, flags, IDs, and other measurements are outside this currency cutover. Expense storage and other financial domains remain separate M13 stages. Keep original extracted payloads and source expenses as evidence rather than rewriting them into normalized money.

SQLite retains its numeric-storage and SQL-aggregate limitations. Per-field ORM round trips must be verified. Virtual sums can exceed an individual field's limit; do not apply the storage bound again to aggregate calculations. A sum that will be persisted into a bounded field still requires validation and an atomic failure path.

## Runtime and output boundary

`apps/loans/services/loan_foreclosure_service.py` requires the main arithmetic cutover. Normalize document/default/request amounts, matched payments, component totals, payment gaps and balances to Decimal cents. Replace monetary float operations in `_document_component_basis`, `_build_settlement_allocation`, `_split_components_across_expenses`, `_proportional_money_split`, and `_absorb_rounding_delta`. Preserve matching ratios and score formulas separately.

The current proportional split calculates cents with `int(round(float(total) * 100))` and uses float weights and remainders. Use exact cents and Decimal weights, preserve deterministic remainder ordering, and conserve both component totals and each transaction's allocated amount. Keep partial allocations provisional, mismatches unallocated, and existing linked payment history intact. Finalized allocation, history posting and register updates must agree and remain repeat-safe.

Update these adjacent boundaries as necessary:

- `loan_intelligence.py` and `payment_review.py`: store Decimal history values and use them directly for accept/reject/sync arithmetic, preserving verification guards and nullable balances.
- `loan_closure_parser.py` and `alfred_ai/services/document_review.py`: normalize extracted, corrected and retried currency at persistence boundaries; preserve raw evidence and distinguish explicit zero from missing values where a request supplies that distinction.
- `payment_history_access.py`: retain owned queries and support for legacy principal/interest component columns while returning the new field types correctly.
- `apps/expenses/services/financial_intelligence.py`: sum payment components and home-ownership repayment/cost totals in Decimal before formatting the canonical payload. Preserve legacy component fallback semantics and review exclusions.
- `apps/ml_engine/services/tax_optimizer.py`: sum the relevant principal/interest history in Decimal, then cross the existing numeric analysis/output boundary without changing tax policy.

Keep API currency as JSON numbers. `LoanClosureDocumentSerializer` and `LoanForeclosureSnapshotSerializer` will otherwise inherit DRF's default Decimal-to-string behavior after the model change. `serialize_payment_review`, nested loan snapshots, foreclosure watchlists, canonical summaries and document review responses need explicit numeric output conversion. Bump affected cache schema markers once the final output contract is implemented.

`LoanForeclosureSnapshot.audit_payload` contains expected/payment totals, gaps, raw document totals, normalized components, expense allocations and posted loan state. Build these amounts from the same cent-exact calculation and convert deliberately to JSON-safe values at the persistence boundary; do not place raw Decimal objects in a default JSONField. Preserve existing audit and extracted evidence. Document any new audit schema or fixed-cent text representation and verify consumers together.

## Migration, retained snapshots and rollback

The next migration must depend on `0014_loan_money_decimal` and freeze its conversion policy rather than calling a future runtime helper. Capture and validate every legacy source row before altering or normalizing currency fields. Reject invalid/non-finite/out-of-range data with the source model, row and field identified; do not replace it with zero.

Retain ancillary snapshots separately from the Loan register snapshots. Identify them uniquely by source model and original row ID, with original owner, original loan identity, relevant parent identities, round-trippable source float text/null, normalized two-place text/null, policy and `applied_at`. Live source links should use `SET_NULL` so evidence survives source-row deletion; owner deletion/data reset must remove that owner's retained evidence while preserving other owners' snapshots.

Derive ownership from the linked Loan. For a foreclosure snapshot, validate that its Loan and closure document's Loan agree. Do not silently repair ownership or parent links as part of a currency migration. Apply only pending snapshots in the correct database alias and transaction, under matching source identity, owner and loan linkage. Mark application once; repeated capture/application must preserve original evidence and later edits.

Reverse after restoring FloatFields. Restore source precision only for cells whose current normalized value still matches the retained snapshot and whose identity, owner and linkage still match. Preserve changed values, null/zero transitions, newly created rows and current nonmonetary history. Do not recreate deleted records.

Reconcile per-row and aggregate before/after results for all three models. Individually rounding legacy child rows can change a sum relative to an already-normalized Loan register total. Report that difference with retained evidence; do not automatically repair the register or overwrite allocation history during the migration.

## Focused verification required before completion

- Migration tests: all 17 fields, positive/negative half cents, SQLite supported bounds, null versus zero, frozen policy, rejection rollback, retained evidence after source deletion, owner reset, alias handling, repeat application, reverse preservation of edits/new rows, unchanged relationships/lifecycle/history and explicit aggregate reconciliation.
- ORM boundary tests: create, bulk create, partial save and queryset update; malformed, boolean and non-finite rejection; invalid writes preserve prior records; supported maxima survive actual SQLite retrieval.
- Allocation tests: one cent among three weights, stable ties, zero/missing component fallback, component scaling, five-component conservation, multiple/split transactions, residual-cent absorption, partial/mismatch states, existing history preservation and repeat reconciliation without duplicate posting.
- Runtime/API tests: exact accept/reject/sync totals, nullable history balance, verification guards, owned access, numeric JSON and JSON-safe audit output, legacy component fallback, cache refresh and virtual totals above the per-field limit.

Update the two half-cent cases in `tests/test_loan_money_runtime.py` for the new history-storage contract: normalized history is cents while source Expense evidence remains unchanged. Broaden the gate with `tests.test_loan_lifecycle_and_reports`, `tests.test_financial_relationships`, document review/retry integrity and tax policy tests. Run checks and migration drift detection using the configured interpreter and isolated test data. No operator database migration or release promotion is part of this plan.
