---
name: alfred-finance-correctness
description: Change or review ALFRED monetary calculations, loan posting, financial baselines, tax arithmetic, or money-storage migrations.
---

# ALFRED finance correctness

- Orient the affected flow through `AGENTS.md` and a scoped graph query. Read its model, boundary helper, shared service, serializer and existing tests before editing.
- Reuse `apps/loans/money.py` for Loan currency: finite Decimal cents, HALF_UP and the existing per-field bound. Other money domains are being migrated separately; do not silently convert unrelated fields. A virtual aggregate may exceed a stored field's bound, while any stored result must validate before writes.
- Preserve raw Expense/document evidence, original ownership and parent linkage. Unknown/null balances differ from explicit zero. Rates, confidence and measurements are not currency.
- Use `apps/expenses/services/financial_intelligence.py::resolve_canonical_financial_baseline` for canonical finance totals. Keep observed, reported, derived and unavailable evidence distinct; avoid counting debt, assets or payments twice.
- Preserve finalized settlement authority and review idempotence. Allocation must conserve transaction totals and component totals in cents. Reject invalid external amounts before any mutation and keep related writes atomic.
- Follow the existing snapshot/migration pattern for conversion evidence, database aliases and rollback guards; do not repair legacy register/history discrepancies without an explicit scope decision.
- Test meaningful rounding, null/zero, ownership, aggregate bounds and repeat/rollback behavior in isolated data. Keep API money numeric where the existing contract requires it. Consult the applicable `docs/MASTER_M13*_VERIFICATION_*.md` for current guarantees and limits.
