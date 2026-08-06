from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from difflib import SequenceMatcher
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from apps.expenses.models import Expense
from apps.loans.models import Loan, LoanClosureDocument, LoanForeclosureSnapshot, LoanPaymentHistory


FULL_MATCH_TOLERANCE_FLOOR = 600.0
PARTIAL_MATCH_RATIO = 0.4
RECONCILIATION_WINDOW_DAYS = 45
SETTLEMENT_COMPONENT_FIELDS = (
    "principal_paid",
    "interest_paid",
    "charges_paid",
    "penalties_paid",
    "tax_paid",
)
SETTLEMENT_FALLBACK_FIELD = "principal_paid"


@dataclass
class LoanLinkResult:
    loan: Loan | None
    confidence: float
    notes: str


@dataclass
class ForeclosureProcessingResult:
    loan: Loan
    closure_document: LoanClosureDocument
    snapshot: LoanForeclosureSnapshot
    confirmed: bool
    message: str


class LoanForeclosureService:
    def process_document(
        self,
        *,
        user,
        selected_loan: Loan,
        closure_file,
        parsed: dict,
        requested_closure_amount: float | None = None,
        requested_closure_date: str | None = None,
    ) -> ForeclosureProcessingResult:
        payload = dict(parsed.get("payload") or {})
        if requested_closure_amount:
            payload["total_amount_payable"] = float(requested_closure_amount)
            payload["closure_amount"] = float(requested_closure_amount)
        if requested_closure_date:
            payload["effective_closure_date"] = requested_closure_date
            payload["closure_date"] = requested_closure_date

        link = self.link_document_to_loan(user=user, payload=payload, preferred_loan=selected_loan)
        if link.loan is None:
            raise ValueError("The uploaded foreclosure document could not be linked to an active loan with enough confidence.")
        if link.loan.id != selected_loan.id:
            raise ValueError(
                f"The uploaded foreclosure document appears to belong to loan #{link.loan.id}, not the currently selected loan."
            )

        verified, verification_note = self._verify_selected_loan(selected_loan, parsed, link)
        closure_amount = float(payload.get("total_amount_payable") or payload.get("closure_amount") or selected_loan.remaining_balance or 0)
        closure_date = _parse_date(payload.get("effective_closure_date") or payload.get("closure_date"))

        with transaction.atomic():
            closure_file.seek(0)
            closure_document = LoanClosureDocument.objects.create(
                loan=selected_loan,
                uploaded_file=closure_file,
                file_name=closure_file.name,
                extracted_text=parsed.get("extracted_text") or "",
                extracted_payload={
                    **payload,
                    "parser_notes": parsed.get("parser_notes", ""),
                    "linkage_notes": link.notes,
                },
                parser_status=str(parsed.get("parser_status") or "needs_review"),
                parse_confidence=float(parsed.get("confidence") or 0),
                verification_status="verified" if verified else "rejected",
                verification_notes=verification_note,
                closure_amount=closure_amount,
                closure_date=closure_date,
            )
            snapshot = LoanForeclosureSnapshot.objects.create(
                **self._snapshot_defaults(
                    loan=selected_loan,
                    closure_document=closure_document,
                    payload=payload,
                    classification_confidence=float(parsed.get("confidence") or 0),
                    linkage_confidence=link.confidence,
                    linkage_notes=link.notes,
                )
            )

            if verified:
                self._mark_foreclosure_pending(selected_loan, snapshot)
                confirmed = self.reconcile_snapshot(snapshot)
            else:
                confirmed = False

            closure_document.refresh_from_db()
            snapshot.refresh_from_db()
            selected_loan.refresh_from_db()

        message = (
            f"Foreclosure payment was reconciled for {selected_loan.lender or 'this loan'}, and the loan is now marked foreclosed."
            if confirmed
            else (
                f"Foreclosure letter saved for {selected_loan.lender or 'this loan'}. "
                "The loan remains in liabilities until Alfred finds a full closure-payment match from statements."
                if verified
                else verification_note
            )
        )
        return ForeclosureProcessingResult(
            loan=selected_loan,
            closure_document=closure_document,
            snapshot=snapshot,
            confirmed=confirmed,
            message=message,
        )

    def sync_snapshot_from_document(self, closure_document: LoanClosureDocument) -> LoanForeclosureSnapshot:
        payload = dict(closure_document.extracted_payload or {})
        link = self.link_document_to_loan(
            user=closure_document.loan.user,
            payload=payload,
            preferred_loan=closure_document.loan,
        )
        defaults = self._snapshot_defaults(
            loan=closure_document.loan,
            closure_document=closure_document,
            payload=payload,
            classification_confidence=float(closure_document.parse_confidence or 0),
            linkage_confidence=link.confidence,
            linkage_notes=link.notes,
        )
        snapshot, created = LoanForeclosureSnapshot.objects.get_or_create(
            closure_document=closure_document,
            defaults=defaults,
        )
        if not created:
            for key, value in defaults.items():
                if key in {"matched_emi_transaction_ids", "matched_closure_transaction_ids", "reconciliation_status", "reconciliation_confidence", "matched_payment_total", "reconciliation_notes", "audit_payload"}:
                    continue
                setattr(snapshot, key, value)
            snapshot.audit_payload = {
                **dict(snapshot.audit_payload or {}),
                "document_payload": payload,
                "parser_status": closure_document.parser_status,
            }
            snapshot.save()
        return snapshot

    def link_document_to_loan(self, *, user, payload: dict, preferred_loan: Loan | None = None) -> LoanLinkResult:
        candidates = list(
            Loan.objects.filter(user=user)
            .exclude(status__in=["foreclosed", "closed", "prepaid"])
            .order_by("-updated_at", "-id")
        )
        if preferred_loan and preferred_loan in candidates:
            candidates.remove(preferred_loan)
            candidates.insert(0, preferred_loan)

        best_loan = None
        best_score = 0.0
        best_notes = "No reliable deterministic loan linkage was found."
        for loan in candidates:
            score, notes = self._link_score(loan, payload, user=user, preferred_loan=preferred_loan)
            if score > best_score:
                best_loan = loan
                best_score = score
                best_notes = notes

        return LoanLinkResult(
            loan=best_loan if best_score >= 42 else None,
            confidence=round(min(best_score, 100.0), 1),
            notes=best_notes,
        )

    def reconcile_pending_foreclosures(self, *, user, expenses: Iterable[Expense] | None = None) -> list[LoanForeclosureSnapshot]:
        snapshots = list(
            LoanForeclosureSnapshot.objects.select_related("loan", "closure_document")
            .filter(loan__user=user, loan__status="foreclosure_pending")
            .order_by("-updated_at", "-id")
        )
        resolved: list[LoanForeclosureSnapshot] = []
        for snapshot in snapshots:
            if self.reconcile_snapshot(snapshot, expenses=expenses):
                snapshot.refresh_from_db()
                resolved.append(snapshot)
        return resolved

    def reconcile_snapshot(self, snapshot: LoanForeclosureSnapshot, *, expenses: Iterable[Expense] | None = None) -> bool:
        loan = snapshot.loan
        expected = float(snapshot.total_amount_payable or loan.remaining_balance or 0)
        candidate_expenses = list(expenses) if expenses is not None else list(self._expense_queryset_for_snapshot(snapshot))

        emi_candidates: list[Expense] = []
        closure_candidates: list[tuple[list[Expense], float, str]] = []
        for expense in candidate_expenses:
            relevance_score, relevance_note = self._expense_relevance_score(expense, loan, snapshot)
            if relevance_score < 20:
                continue
            if self._looks_like_emi(expense, loan):
                emi_candidates.append(expense)
            closure_match = self._closure_match_for_expense(expense, expected=expected, relevance_score=relevance_score)
            if closure_match:
                closure_candidates.append(([expense], *closure_match))

        closure_candidates.extend(
            self._aggregate_same_day_candidates(candidate_expenses, loan=loan, snapshot=snapshot, expected=expected)
        )
        closure_candidates.extend(
            self._aggregate_split_payment_candidates(candidate_expenses, loan=loan, snapshot=snapshot, expected=expected)
        )
        closure_candidates.sort(key=lambda item: item[1], reverse=True)

        emi_ids = [expense.id for expense in sorted(emi_candidates, key=lambda item: (item.transaction_date, item.id), reverse=True)[:12]]
        best_group, best_score, best_note = (closure_candidates[0] if closure_candidates else ([], 0.0, "No closure payment candidate matched the document total yet."))
        matched_total = round(sum(item.amount for item in best_group), 2) if best_group else 0.0
        full_tolerance = max(expected * 0.015, FULL_MATCH_TOLERANCE_FLOOR) if expected else FULL_MATCH_TOLERANCE_FLOOR
        partial_floor = expected * PARTIAL_MATCH_RATIO if expected else 0.0

        if not best_group:
            status = "unmatched"
            confidence = 0.0
            notes = "No loan-linked debit matched the foreclosure amount yet."
        elif expected and abs(matched_total - expected) <= full_tolerance:
            status = "full_match"
            confidence = min(0.97, 0.62 + (best_score / 140))
            notes = best_note
        elif expected and matched_total >= partial_floor and matched_total < max(expected - full_tolerance, 0):
            status = "partial_match"
            confidence = min(0.84, 0.45 + (best_score / 180))
            notes = f"{best_note} Matched debit total is below the document payable amount."
        else:
            status = "mismatch"
            confidence = min(0.76, 0.35 + (best_score / 200))
            notes = f"{best_note} Amount mismatch against the document payable total."

        snapshot.matched_emi_transaction_ids = emi_ids
        snapshot.matched_closure_transaction_ids = [expense.id for expense in best_group]
        snapshot.matched_payment_total = matched_total
        snapshot.reconciliation_status = status
        snapshot.reconciliation_confidence = round(confidence, 3)
        snapshot.reconciliation_notes = notes
        settlement_allocation = self._build_settlement_allocation(
            snapshot,
            matched_expenses=best_group,
            matched_total=matched_total,
            status=status,
            confidence=round(confidence, 3),
        )
        snapshot.audit_payload = {
            **dict(snapshot.audit_payload or {}),
            "last_reconciled_at": timezone.now().isoformat(),
            "expected_total_amount": expected,
            "settlement_allocation": settlement_allocation,
        }
        snapshot.save(
            update_fields=[
                "matched_emi_transaction_ids",
                "matched_closure_transaction_ids",
                "matched_payment_total",
                "reconciliation_status",
                "reconciliation_confidence",
                "reconciliation_notes",
                "audit_payload",
                "updated_at",
            ]
        )

        if status == "full_match":
            self._finalize_foreclosure(
                loan,
                snapshot,
                best_group,
                settlement_allocation=settlement_allocation,
            )
            return True

        self._mark_foreclosure_pending(loan, snapshot)
        return False

    def _verify_selected_loan(self, loan: Loan, parsed: dict, link: LoanLinkResult) -> tuple[bool, str]:
        from apps.loans.services.loan_closure_parser import loan_closure_parser

        verified, base_note = loan_closure_parser.verify_document(loan, parsed)
        if not verified:
            return False, base_note
        if link.loan is None:
            return False, "The document looked like a closure letter, but Alfred could not link it to the selected loan deterministically."
        if link.loan.id != loan.id:
            return False, f"The document linked more strongly to loan #{link.loan.id} than the selected loan."
        return True, f"{base_note} {link.notes}".strip()

    def _snapshot_defaults(
        self,
        *,
        loan: Loan,
        closure_document: LoanClosureDocument,
        payload: dict,
        classification_confidence: float,
        linkage_confidence: float,
        linkage_notes: str,
    ) -> dict:
        return {
            "loan": loan,
            "closure_document": closure_document,
            "document_type": str(payload.get("document_type") or "other")[:40],
            "lender_name": str(payload.get("lender_name") or loan.lender or "")[:120],
            "borrower_name": str(payload.get("borrower_name") or _borrower_name(loan.user) or "")[:180],
            "loan_account_number": str(payload.get("loan_account_number") or loan.loan_account_number or "")[:64],
            "statement_date": _parse_date(payload.get("statement_date")),
            "effective_closure_date": _parse_date(payload.get("effective_closure_date") or payload.get("closure_date")),
            "due_by_date": _parse_date(payload.get("due_by_date")),
            "outstanding_principal": float(payload.get("outstanding_principal") or 0),
            "accrued_interest": float(payload.get("accrued_interest") or 0),
            "foreclosure_charges": float(payload.get("foreclosure_charges") or 0),
            "taxes_gst": float(payload.get("taxes_gst") or 0),
            "overdue_charges": float(payload.get("overdue_charges") or 0),
            "total_amount_payable": float(payload.get("total_amount_payable") or payload.get("closure_amount") or closure_document.closure_amount or 0),
            "classification_confidence": classification_confidence,
            "linkage_confidence": linkage_confidence,
            "linkage_notes": linkage_notes,
            "reconciliation_status": "unmatched",
            "reconciliation_confidence": 0,
            "matched_payment_total": 0,
            "matched_emi_transaction_ids": [],
            "matched_closure_transaction_ids": [],
            "reconciliation_notes": "",
            "audit_payload": {
                "document_payload": payload,
                "parser_status": closure_document.parser_status,
            },
        }

    def _link_score(self, loan: Loan, payload: dict, *, user, preferred_loan: Loan | None = None) -> tuple[float, str]:
        score = 0.0
        notes: list[str] = []
        document_account = _normalize_reference(payload.get("loan_account_number"))
        loan_account = _normalize_reference(loan.loan_account_number)
        if document_account and loan_account:
            if document_account == loan_account:
                score += 72
                notes.append("Exact loan account number match.")
            elif document_account[-6:] and document_account[-6:] == loan_account[-6:]:
                score += 58
                notes.append("Last six digits of the loan account matched.")

        document_lender = str(payload.get("lender_name") or "").upper()
        loan_lender = str(loan.lender or "").upper()
        lender_tokens = [token for token in loan_lender.replace("&", " ").split() if len(token) > 2]
        lender_hits = [token for token in lender_tokens if token in document_lender]
        if lender_hits:
            score += min(22, 8 * len(lender_hits))
            notes.append(f"Lender tokens matched: {', '.join(lender_hits[:3])}.")

        borrower_text = str(payload.get("borrower_name") or "").upper()
        user_name = _borrower_name(user).upper()
        if borrower_text and user_name:
            borrower_similarity = SequenceMatcher(None, borrower_text, user_name).ratio()
            if borrower_similarity >= 0.72:
                score += 12
                notes.append("Borrower name aligns with the account holder.")

        payable = float(payload.get("total_amount_payable") or 0)
        balance = float(loan.remaining_balance or loan.principal or 0)
        if payable and balance:
            delta_ratio = abs(payable - balance) / max(balance, 1)
            if delta_ratio <= 0.05:
                score += 14
                notes.append("Document payable amount is close to the tracked remaining balance.")
            elif delta_ratio <= 0.12:
                score += 8
                notes.append("Document payable amount is within the loose remaining-balance tolerance.")

        if preferred_loan and loan.id == preferred_loan.id:
            score += 6
            notes.append("User-selected loan was treated as the preferred deterministic target.")

        return score, " ".join(notes) if notes else "Only weak foreclosure-link signals were available."

    def _expense_queryset_for_snapshot(self, snapshot: LoanForeclosureSnapshot):
        loan = snapshot.loan
        reference_dates = [item for item in [snapshot.statement_date, snapshot.effective_closure_date, snapshot.due_by_date, loan.closed_on] if item]
        anchor = min(reference_dates) if reference_dates else timezone.localdate()
        start_date = anchor - timedelta(days=RECONCILIATION_WINDOW_DAYS)
        end_date = max(reference_dates) + timedelta(days=RECONCILIATION_WINDOW_DAYS) if reference_dates else timezone.localdate() + timedelta(days=RECONCILIATION_WINDOW_DAYS)
        return Expense.objects.filter(
            user=loan.user,
            direction="debit",
            transaction_date__gte=start_date,
            transaction_date__lte=end_date,
        ).order_by("transaction_date", "id")

    def _expense_relevance_score(self, expense: Expense, loan: Loan, snapshot: LoanForeclosureSnapshot) -> tuple[float, str]:
        text = " ".join(
            part for part in [
                expense.description,
                expense.raw_description,
                expense.external_reference,
                expense.company_name,
                expense.merchant,
                expense.counterparty,
            ]
            if part
        ).upper()
        score = 0.0
        notes: list[str] = []
        loan_account = _normalize_reference(loan.loan_account_number)
        if loan_account and loan_account[-6:] and loan_account[-6:] in text:
            score += 38
            notes.append("Statement narration contains the loan account suffix.")

        lender_tokens = [token for token in str(loan.lender or "").upper().replace("&", " ").split() if len(token) > 2]
        hits = [token for token in lender_tokens if token in text]
        if hits:
            score += min(26, 8 * len(hits))
            notes.append(f"Lender tokens matched: {', '.join(hits[:3])}.")

        if expense.classification == "loan" or expense.category == "loan":
            score += 18
            notes.append("Expense is already classified as a loan repayment.")
        if expense.linked_loan_payments.filter(loan=loan).exists():
            score += 24
            notes.append("Expense was already linked to this loan.")
        elif expense.linked_loan_payments.exclude(loan=loan).exists():
            score -= 24
            notes.append("Expense is already linked to a different loan.")

        if any(keyword in text for keyword in ["FORECLOSURE", "PRE CLOSURE", "CLOSURE", "NO DUE", "FULL AND FINAL"]):
            score += 18
            notes.append("Narration contains closure wording.")

        return score, " ".join(notes) if notes else "Only a weak narrative match was found."

    def _closure_match_for_expense(self, expense: Expense, *, expected: float, relevance_score: float) -> tuple[float, str] | None:
        if relevance_score < 20 or expected <= 0:
            return None
        tolerance = max(expected * 0.015, FULL_MATCH_TOLERANCE_FLOOR)
        delta = abs(float(expense.amount or 0) - expected)
        if delta <= tolerance:
            return relevance_score + 42, "A single debit amount matched the foreclosure payable total closely."
        if float(expense.amount or 0) >= expected * PARTIAL_MATCH_RATIO:
            return relevance_score + 18, "A sizable debit aligned with the foreclosure window but did not fully match the payable amount."
        return None

    def _aggregate_same_day_candidates(self, expenses: list[Expense], *, loan: Loan, snapshot: LoanForeclosureSnapshot, expected: float) -> list[tuple[list[Expense], float, str]]:
        if expected <= 0:
            return []
        grouped: dict[date, list[Expense]] = {}
        for expense in expenses:
            score, _ = self._expense_relevance_score(expense, loan, snapshot)
            if score < 20:
                continue
            grouped.setdefault(expense.transaction_date, []).append(expense)

        candidates = []
        tolerance = max(expected * 0.015, FULL_MATCH_TOLERANCE_FLOOR)
        for _, items in grouped.items():
            if len(items) < 2:
                continue
            total = sum(item.amount for item in items)
            if abs(total - expected) <= tolerance:
                base_score = sum(self._expense_relevance_score(item, loan, snapshot)[0] for item in items) / len(items)
                candidates.append((items, base_score + 36, "A same-day group of debits matched the document payable total."))
        return candidates

    def _aggregate_split_payment_candidates(
        self,
        expenses: list[Expense],
        *,
        loan: Loan,
        snapshot: LoanForeclosureSnapshot,
        expected: float,
    ) -> list[tuple[list[Expense], float, str]]:
        if expected <= 0:
            return []
        relevant_expenses = []
        for expense in expenses:
            score, _ = self._expense_relevance_score(expense, loan, snapshot)
            if score >= 20:
                relevant_expenses.append((expense, score))
        if len(relevant_expenses) < 2:
            return []

        tolerance = max(expected * 0.015, FULL_MATCH_TOLERANCE_FLOOR)
        candidates: list[tuple[list[Expense], float, str]] = []
        seen_groups: set[tuple[int, ...]] = set()
        max_group_size = min(3, len(relevant_expenses))
        max_split_span_days = 7

        for start_index in range(len(relevant_expenses)):
            for group_size in range(2, max_group_size + 1):
                end_index = start_index + group_size
                if end_index > len(relevant_expenses):
                    break
                window = relevant_expenses[start_index:end_index]
                grouped_expenses = [item[0] for item in window]
                if (grouped_expenses[-1].transaction_date - grouped_expenses[0].transaction_date).days > max_split_span_days:
                    continue
                key = tuple(expense.id for expense in grouped_expenses)
                if key in seen_groups:
                    continue
                total = round(sum(expense.amount for expense in grouped_expenses), 2)
                if abs(total - expected) > tolerance:
                    continue
                base_score = sum(score for _, score in window) / len(window)
                candidates.append(
                    (
                        grouped_expenses,
                        base_score + 32,
                        "A short sequence of related debits matched the foreclosure payable total as a split payment.",
                    )
                )
                seen_groups.add(key)
        return candidates

    def _looks_like_emi(self, expense: Expense, loan: Loan) -> bool:
        if not loan.emi:
            return False
        delta = abs(float(expense.amount or 0) - float(loan.emi or 0))
        return delta <= max(float(loan.emi or 0) * 0.05, 150)

    def _mark_foreclosure_pending(self, loan: Loan, snapshot: LoanForeclosureSnapshot) -> None:
        loan.status = "foreclosure_pending"
        loan.is_active = False
        update_fields = ["status", "is_active", "updated_at"]

        pending_balance = loan.remaining_balance
        if pending_balance is None or float(pending_balance) <= 0:
            pending_balance = (
                snapshot.total_amount_payable
                or snapshot.outstanding_principal
                or loan.principal
                or 0
            )
        pending_balance = round(float(pending_balance or 0), 2)
        if loan.remaining_balance != pending_balance:
            loan.remaining_balance = pending_balance
            update_fields.append("remaining_balance")

        if loan.closed_on is not None:
            loan.closed_on = None
            update_fields.append("closed_on")
        loan.save(update_fields=update_fields)

    def _finalize_foreclosure(
        self,
        loan: Loan,
        snapshot: LoanForeclosureSnapshot,
        matched_expenses: list[Expense],
        *,
        settlement_allocation: dict,
    ) -> None:
        payment_total = round(sum(item.amount for item in matched_expenses), 2)
        closure_date = max((item.transaction_date for item in matched_expenses), default=snapshot.effective_closure_date or timezone.localdate())
        loan.status = "foreclosed"
        loan.is_active = False
        loan.closed_on = closure_date
        loan.remaining_balance = 0
        loan.closure_reason = "foreclosed"
        loan.last_payment_date = closure_date
        loan.total_paid = float(loan.total_paid or 0) + payment_total
        loan.save(
            update_fields=[
                "status",
                "is_active",
                "closed_on",
                "remaining_balance",
                "closure_reason",
                "last_payment_date",
                "total_paid",
                "updated_at",
            ]
        )

        expense_allocations = {
            item["expense_id"]: item
            for item in settlement_allocation.get("expense_allocations") or []
        }
        created_payment_ids: list[int] = []
        preserved_history: list[dict] = []
        for expense in matched_expenses:
            existing = LoanPaymentHistory.objects.filter(loan=loan, expense_reference=expense).first()
            if existing is not None:
                preserved_history.append(
                    {
                        "expense_id": expense.id,
                        "payment_history_id": existing.id,
                        "reason": "Existing linked payment history was preserved and not overwritten.",
                    }
                )
                continue
            allocation = dict(expense_allocations.get(expense.id) or self._build_zero_component_map())
            payment = LoanPaymentHistory.objects.create(
                loan=loan,
                payment_date=expense.transaction_date,
                amount=expense.amount,
                principal_component=float(allocation.get("principal_paid") or 0),
                interest_component=float(allocation.get("interest_paid") or 0),
                principal_paid=float(allocation.get("principal_paid") or 0),
                interest_paid=float(allocation.get("interest_paid") or 0),
                charges_paid=float(allocation.get("charges_paid") or 0),
                penalties_paid=float(allocation.get("penalties_paid") or 0),
                tax_paid=float(allocation.get("tax_paid") or 0),
                remaining_balance=float(allocation.get("remaining_balance_after_payment") or 0),
                is_auto_detected=True,
                detection_confidence=round(snapshot.reconciliation_confidence * 100, 1),
                detection_reason="Reconciled foreclosure payment from document and statement match.",
                matched_reference=(expense.external_reference or "")[:120],
                match_status="matched",
                loan_effect_applied=True,
                expense_reference=expense,
            )
            created_payment_ids.append(payment.id)

        snapshot.audit_payload = {
            **dict(snapshot.audit_payload or {}),
            "settlement_allocation": settlement_allocation,
            "settlement_posting": {
                "finalized_at": timezone.now().isoformat(),
                "created_payment_history_ids": created_payment_ids,
                "preserved_existing_payment_history": preserved_history,
                "loan_state_after_reconciliation": {
                    "status": loan.status,
                    "is_active": loan.is_active,
                    "remaining_balance": round(float(loan.remaining_balance or 0), 2),
                    "closed_on": loan.closed_on.isoformat() if loan.closed_on else "",
                    "total_paid": round(float(loan.total_paid or 0), 2),
                },
            },
        }
        snapshot.save(update_fields=["audit_payload", "updated_at"])

    def _build_settlement_allocation(
        self,
        snapshot: LoanForeclosureSnapshot,
        *,
        matched_expenses: list[Expense],
        matched_total: float,
        status: str,
        confidence: float,
    ) -> dict:
        document_basis = self._document_component_basis(snapshot)
        matched_total = round(float(matched_total or 0), 2)
        expected_total = round(float(document_basis["expected_total"] or 0), 2)
        base_payload = {
            "allocation_status": "pending_unmatched",
            "allocation_method": "unallocated",
            "confidence": round(float(confidence or 0), 3),
            "expected_total": expected_total,
            "payment_total": matched_total,
            "payment_gap": round(expected_total - matched_total, 2),
            "raw_document_total": round(float(document_basis["raw_document_total"] or 0), 2),
            "document_normalization": document_basis["document_normalization"],
            "document_components": document_basis["document_components"],
            "allocated_components": self._build_zero_component_map(),
            "expense_allocations": [],
            "notes": document_basis["notes"],
        }
        if status == "full_match":
            allocated_components = _proportional_money_split(
                matched_total,
                document_basis["document_components"],
                fallback_key=SETTLEMENT_FALLBACK_FIELD,
            )
            return {
                **base_payload,
                "allocation_status": "finalized",
                "allocation_method": "document_components",
                "allocated_components": allocated_components,
                "expense_allocations": self._split_components_across_expenses(
                    matched_expenses,
                    allocated_components,
                    snapshot=snapshot,
                    finalized=True,
                ),
                "notes": " ".join(
                    filter(
                        None,
                        [
                            document_basis["notes"],
                            "Closure payment was allocated deterministically from the foreclosure document fields.",
                        ],
                    )
                ).strip(),
            }
        if status == "partial_match":
            allocated_components = _proportional_money_split(
                matched_total,
                document_basis["document_components"],
                fallback_key=SETTLEMENT_FALLBACK_FIELD,
            )
            return {
                **base_payload,
                "allocation_status": "provisional_partial",
                "allocation_method": "proportional_to_matched_payment",
                "allocated_components": allocated_components,
                "expense_allocations": self._split_components_across_expenses(
                    matched_expenses,
                    allocated_components,
                    snapshot=snapshot,
                    finalized=False,
                ),
                "notes": " ".join(
                    filter(
                        None,
                        [
                            document_basis["notes"],
                            "Matched payment was below the document payable total, so the settlement split was allocated proportionally and kept provisional.",
                        ],
                    )
                ).strip(),
            }
        if status == "mismatch":
            return {
                **base_payload,
                "allocation_status": "mismatch_unallocated",
                "notes": " ".join(
                    filter(
                        None,
                        [
                            document_basis["notes"],
                            "Candidate payment mismatched the document payable total, so no settlement posting was created.",
                        ],
                    )
                ).strip(),
            }
        return {
            **base_payload,
            "notes": " ".join(
                filter(
                    None,
                    [
                        document_basis["notes"],
                        "No statement payment matched the foreclosure document yet.",
                    ],
                )
            ).strip(),
        }

    def _document_component_basis(self, snapshot: LoanForeclosureSnapshot) -> dict:
        document_components = {
            "principal_paid": round(max(float(snapshot.outstanding_principal or 0), 0), 2),
            "interest_paid": round(max(float(snapshot.accrued_interest or 0), 0), 2),
            "charges_paid": round(max(float(snapshot.foreclosure_charges or 0), 0), 2),
            "penalties_paid": round(max(float(snapshot.overdue_charges or 0), 0), 2),
            "tax_paid": round(max(float(snapshot.taxes_gst or 0), 0), 2),
        }
        raw_total = round(sum(document_components.values()), 2)
        expected_total = round(float(snapshot.total_amount_payable or raw_total or 0), 2)
        normalization = "exact"
        notes = ""
        if expected_total <= 0 and raw_total > 0:
            expected_total = raw_total
            notes = "Structured foreclosure components were used because the document payable total was missing."
        elif raw_total <= 0 and expected_total > 0:
            normalization = "principal_only_fallback"
            document_components = {
                "principal_paid": expected_total,
                "interest_paid": 0.0,
                "charges_paid": 0.0,
                "penalties_paid": 0.0,
                "tax_paid": 0.0,
            }
            raw_total = expected_total
            notes = "Structured foreclosure components were missing, so the document payable total was treated as principal deterministically."
        elif raw_total > 0 and abs(raw_total - expected_total) >= 0.01:
            normalization = "scaled_to_payable_total"
            document_components = _proportional_money_split(
                expected_total,
                document_components,
                fallback_key=SETTLEMENT_FALLBACK_FIELD,
            )
            notes = "Structured component values were scaled to the document payable total for deterministic settlement accounting."
        return {
            "expected_total": expected_total,
            "raw_document_total": raw_total,
            "document_components": document_components,
            "document_normalization": normalization,
            "notes": notes,
        }

    def _split_components_across_expenses(
        self,
        matched_expenses: list[Expense],
        allocated_components: dict,
        *,
        snapshot: LoanForeclosureSnapshot,
        finalized: bool,
    ) -> list[dict]:
        ordered_expenses = sorted(matched_expenses, key=lambda item: (item.transaction_date, item.id))
        if not ordered_expenses:
            return []
        weights = {expense.id: round(float(expense.amount or 0), 2) for expense in ordered_expenses}
        component_splits = {
            field: _proportional_money_split(
                float(allocated_components.get(field) or 0),
                weights,
                fallback_key=ordered_expenses[0].id,
            )
            for field in SETTLEMENT_COMPONENT_FIELDS
        }
        running_balance = round(max(float(snapshot.outstanding_principal or allocated_components.get("principal_paid") or 0), 0), 2)
        allocations: list[dict] = []
        for index, expense in enumerate(ordered_expenses):
            allocation = {
                field: round(float(component_splits[field].get(expense.id, 0) or 0), 2)
                for field in SETTLEMENT_COMPONENT_FIELDS
            }
            delta = round(float(expense.amount or 0) - sum(allocation.values()), 2)
            if abs(delta) >= 0.01:
                allocation = _absorb_rounding_delta(allocation, delta)
            running_balance = round(max(running_balance - float(allocation.get("principal_paid") or 0), 0), 2)
            allocations.append(
                {
                    "expense_id": expense.id,
                    "payment_date": expense.transaction_date.isoformat(),
                    "amount": round(float(expense.amount or 0), 2),
                    "matched_reference": (expense.external_reference or "")[:120],
                    **allocation,
                    "remaining_balance_after_payment": 0.0 if finalized and index == len(ordered_expenses) - 1 else running_balance,
                }
            )
        return allocations

    def _build_zero_component_map(self) -> dict:
        return {field: 0.0 for field in SETTLEMENT_COMPONENT_FIELDS}

def _proportional_money_split(total: float, weights: dict, *, fallback_key) -> dict:
    keys = list(weights.keys())
    if not keys:
        return {}
    normalized_weights = {key: max(float(value or 0), 0.0) for key, value in weights.items()}
    total_cents = int(round(max(float(total or 0), 0.0) * 100))
    if total_cents <= 0:
        return {key: 0.0 for key in keys}
    weight_sum = sum(normalized_weights.values())
    if weight_sum <= 0:
        return {
            key: round(float(total or 0), 2) if key == fallback_key else 0.0
            for key in keys
        }
    positions = {key: index for index, key in enumerate(keys)}
    exact_allocations = {
        key: (total_cents * normalized_weights[key]) / weight_sum
        for key in keys
    }
    cents_allocations = {key: int(exact_allocations[key]) for key in keys}
    remaining_cents = total_cents - sum(cents_allocations.values())
    ranked_keys = sorted(
        keys,
        key=lambda key: (exact_allocations[key] - cents_allocations[key], normalized_weights[key], -positions[key]),
        reverse=True,
    )
    for index in range(remaining_cents):
        cents_allocations[ranked_keys[index % len(ranked_keys)]] += 1
    return {key: round(cents_allocations[key] / 100, 2) for key in keys}


def _absorb_rounding_delta(components: dict, delta: float) -> dict:
    adjusted = {key: round(float(value or 0), 2) for key, value in components.items()}
    if abs(delta) < 0.01:
        return adjusted
    ranked_fields = sorted(
        SETTLEMENT_COMPONENT_FIELDS,
        key=lambda field: (adjusted.get(field, 0.0), field == SETTLEMENT_FALLBACK_FIELD),
        reverse=True,
    )
    if delta > 0:
        target = ranked_fields[0]
        adjusted[target] = round(adjusted.get(target, 0.0) + delta, 2)
        return adjusted
    remaining = round(abs(delta), 2)
    for field in ranked_fields:
        available = round(adjusted.get(field, 0.0), 2)
        if available <= 0:
            continue
        reduction = min(available, remaining)
        adjusted[field] = round(available - reduction, 2)
        remaining = round(remaining - reduction, 2)
        if remaining <= 0:
            break
    return adjusted


def _normalize_reference(value: str | None) -> str:
    return "".join(char for char in str(value or "").upper() if char.isalnum())


def _borrower_name(user) -> str:
    full_name = " ".join(part for part in [getattr(user, "first_name", ""), getattr(user, "last_name", "")] if part).strip()
    return full_name or getattr(user, "username", "")


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


loan_foreclosure_service = LoanForeclosureService()
