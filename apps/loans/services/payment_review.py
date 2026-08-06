from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.loans.models import Loan, LoanPaymentHistory
from apps.reports.services import operational_logging_service


VALID_REVIEW_DECISIONS = {"accept", "reject"}


def serialize_payment_review(payment: LoanPaymentHistory) -> dict:
    expense = payment.expense_reference
    loan = payment.loan
    return {
        "id": payment.id,
        "loan_id": payment.loan_id,
        "loan": {
            "id": loan.id,
            "lender": loan.lender,
            "loan_account_number": loan.loan_account_number,
            "loan_type": loan.loan_type,
            "remaining_balance": round(float(loan.remaining_balance or 0), 2) if loan.remaining_balance is not None else None,
            "total_paid": round(float(loan.total_paid or 0), 2),
            "last_payment_date": loan.last_payment_date.isoformat() if loan.last_payment_date else "",
        },
        "payment_date": payment.payment_date.isoformat(),
        "amount": round(float(payment.amount or 0), 2),
        "principal_component": round(float(payment.principal_component or 0), 2),
        "interest_component": round(float(payment.interest_component or 0), 2),
        "principal_paid": round(float(payment.principal_paid or 0), 2),
        "interest_paid": round(float(payment.interest_paid or 0), 2),
        "charges_paid": round(float(payment.charges_paid or 0), 2),
        "penalties_paid": round(float(payment.penalties_paid or 0), 2),
        "tax_paid": round(float(payment.tax_paid or 0), 2),
        "remaining_balance": round(float(payment.remaining_balance or 0), 2) if payment.remaining_balance is not None else None,
        "match_status": payment.match_status,
        "loan_effect_applied": payment.loan_effect_applied,
        "is_auto_detected": payment.is_auto_detected,
        "detection_confidence": round(float(payment.detection_confidence or 0), 2),
        "detection_reason": payment.detection_reason,
        "matched_reference": payment.matched_reference,
        "expense_reference_id": payment.expense_reference_id,
        "expense": {
            "id": expense.id,
            "merchant": expense.merchant,
            "description": expense.description,
            "raw_description": expense.raw_description,
            "amount": round(float(expense.amount or 0), 2),
            "transaction_date": expense.transaction_date.isoformat(),
            "classification": expense.classification,
            "category": expense.category,
            "direction": expense.direction,
            "external_reference": expense.external_reference,
        }
        if expense
        else None,
    }


@transaction.atomic
def review_loan_payment_match(
    *,
    user,
    payment_id: int,
    decision: str,
    reviewer=None,
    notes: str = "",
) -> LoanPaymentHistory:
    decision = (decision or "").strip().lower()
    if decision not in VALID_REVIEW_DECISIONS:
        raise ValueError("decision must be accept or reject")

    payment = (
        LoanPaymentHistory.objects.select_for_update()
        .select_related("loan", "expense_reference")
        .filter(id=payment_id, loan__user=user)
        .first()
    )
    if payment is None:
        raise LoanPaymentHistory.DoesNotExist("Loan payment review row not found.")
    if payment.match_status != "review":
        raise ValueError("Only loan payments with match_status=review can be accepted or rejected.")

    if decision == "accept":
        if not payment.loan_effect_applied:
            _apply_payment_to_loan(payment.loan, payment)
            payment.loan_effect_applied = True
        payment.match_status = "matched"
        _append_review_note(payment, "Accepted", notes)
        event_type = "loan_payment_review_accepted"
        message = "Loan payment review row accepted and eligible for calculation confidence."
    else:
        if payment.loan_effect_applied:
            _reverse_payment_from_loan(payment.loan, payment)
            payment.loan_effect_applied = False
        payment.match_status = "rejected"
        _append_review_note(payment, "Rejected", notes)
        event_type = "loan_payment_review_rejected"
        message = "Loan payment review row rejected and excluded from calculation confidence."

    payment.save(update_fields=["match_status", "loan_effect_applied", "detection_reason"])
    operational_logging_service.log(
        user=user,
        module="loans",
        category="api",
        scope="loan_payment_review",
        event_type=event_type,
        severity="info",
        document_id=payment.id,
        file_name="",
        message=message,
        payload={
            "payment_id": payment.id,
            "loan_id": payment.loan_id,
            "decision": decision,
            "reviewer_id": getattr(reviewer, "id", None),
            "notes": notes,
            "loan_effect_applied": payment.loan_effect_applied,
            "expense_reference_id": payment.expense_reference_id,
        },
    )
    return payment


def _append_review_note(payment: LoanPaymentHistory, label: str, notes: str) -> None:
    cleaned = " ".join(str(notes or "").split())
    suffix = f"{label} on {timezone.now().date().isoformat()}"
    if cleaned:
        suffix = f"{suffix}: {cleaned}"
    base = payment.detection_reason or ""
    merged = f"{base} | {suffix}" if base else suffix
    payment.detection_reason = merged[:255]


def _apply_payment_to_loan(loan: Loan, payment: LoanPaymentHistory) -> None:
    principal_paid = _principal_paid(payment)
    loan.last_payment_date = max(
        [value for value in [loan.last_payment_date, payment.payment_date] if value],
        default=payment.payment_date,
    )
    loan.total_paid = round(float(loan.total_paid or 0) + float(payment.amount or 0), 2)
    if payment.remaining_balance is not None:
        loan.remaining_balance = max(round(float(payment.remaining_balance or 0), 2), 0)
    else:
        current_balance = float(loan.remaining_balance if loan.remaining_balance is not None else loan.principal or 0)
        loan.remaining_balance = max(round(current_balance - principal_paid, 2), 0)

    if loan.remaining_balance <= 100:
        loan.is_active = False
        loan.status = "closed"
        loan.closed_on = payment.payment_date
        loan.remaining_balance = 0

    loan.save(
        update_fields=[
            "last_payment_date",
            "total_paid",
            "remaining_balance",
            "is_active",
            "status",
            "closed_on",
            "updated_at",
        ]
    )


def _reverse_payment_from_loan(loan: Loan, payment: LoanPaymentHistory) -> None:
    principal_paid = _principal_paid(payment)
    current_balance = float(loan.remaining_balance if loan.remaining_balance is not None else 0)
    loan.remaining_balance = round(max(current_balance + principal_paid, 0), 2)
    loan.total_paid = round(max(float(loan.total_paid or 0) - float(payment.amount or 0), 0), 2)
    latest_applied = (
        LoanPaymentHistory.objects.filter(loan=loan, loan_effect_applied=True, match_status="matched")
        .exclude(id=payment.id)
        .order_by("-payment_date", "-id")
        .first()
    )
    loan.last_payment_date = latest_applied.payment_date if latest_applied else None
    if loan.status in {"closed", "prepaid"} and loan.remaining_balance > 100:
        loan.status = "active"
        loan.is_active = True
        loan.closed_on = None
    loan.save(
        update_fields=[
            "last_payment_date",
            "total_paid",
            "remaining_balance",
            "is_active",
            "status",
            "closed_on",
            "updated_at",
        ]
    )


def _principal_paid(payment: LoanPaymentHistory) -> float:
    return round(float(payment.principal_paid or payment.principal_component or 0), 2)
