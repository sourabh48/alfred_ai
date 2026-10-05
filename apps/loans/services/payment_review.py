from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.loans.models import Loan, LoanPaymentHistory
from apps.loans.money import loan_money, loan_money_float
from apps.reports.services import operational_logging_service


VALID_REVIEW_DECISIONS = {"accept", "reject"}
SUBSCRIPTION_FALSE_POSITIVE_KEYWORDS = (
    "GOOGLE PLAY",
    "PLAYSTORE",
    "GOOGLE INDIA DIGITAL",
    "NETFLIX",
    "SPOTIFY",
    "YOUTUBE",
    "SUBSCRIPTION",
    "MEMBERSHIP",
)


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
            "remaining_balance": loan_money_float(loan.remaining_balance) if loan.remaining_balance is not None else None,
            "total_paid": loan_money_float(loan.total_paid),
            "last_payment_date": loan.last_payment_date.isoformat() if loan.last_payment_date else "",
        },
        "payment_date": payment.payment_date.isoformat(),
        "amount": loan_money_float(payment.amount),
        "principal_component": loan_money_float(payment.principal_component),
        "interest_component": loan_money_float(payment.interest_component),
        "principal_paid": loan_money_float(payment.principal_paid),
        "interest_paid": loan_money_float(payment.interest_paid),
        "charges_paid": loan_money_float(payment.charges_paid),
        "penalties_paid": loan_money_float(payment.penalties_paid),
        "tax_paid": loan_money_float(payment.tax_paid),
        "remaining_balance": loan_money_float(payment.remaining_balance) if payment.remaining_balance is not None else None,
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
    settled_payment_ids = _finalized_settlement_payment_ids(payment.loan)
    if settled_payment_ids is not None and payment.id in settled_payment_ids:
        raise ValueError("Payments in a finalized foreclosure settlement cannot be accepted or rejected through payment review.")

    if decision == "accept":
        if not payment.loan.is_confirmed:
            raise ValueError("Confirm the loan terms and current balance before accepting payment matches.")
        if settled_payment_ids is not None or _predates_verified_balance(payment):
            # A verified balance or finalized settlement supersedes this allocation.
            # Retain the evidence row without applying it again to that balance.
            payment.loan_effect_applied = False
        elif not payment.loan_effect_applied:
            _apply_payment_to_loan(payment.loan, payment)
            payment.loan_effect_applied = True
        payment.match_status = "matched"
        _append_review_note(payment, "Accepted", notes)
        event_type = "loan_payment_review_accepted"
        message = "Loan payment review row accepted and eligible for calculation confidence."
    else:
        if payment.loan_effect_applied and settled_payment_ids is None and not _predates_verified_balance(payment):
            _reverse_payment_from_loan(payment.loan, payment)
        payment.loan_effect_applied = False
        payment.match_status = "rejected"
        _append_review_note(payment, "Rejected", notes)
        event_type = "loan_payment_review_rejected"
        message = "Loan payment review row rejected and excluded from calculation confidence."

    payment.save(update_fields=["match_status", "loan_effect_applied", "detection_reason"])
    _sync_loan_from_applied_matches(payment.loan)
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


@transaction.atomic
def reject_subscription_false_positive_match(
    *,
    payment_id: int,
    user=None,
    reviewer=None,
    notes: str = "",
) -> LoanPaymentHistory:
    queryset = (
        LoanPaymentHistory.objects.select_for_update()
        .select_related("loan", "expense_reference")
        .filter(id=payment_id)
    )
    if user is not None:
        queryset = queryset.filter(loan__user=user)
    payment = queryset.first()
    if payment is None:
        raise LoanPaymentHistory.DoesNotExist("Loan payment row not found.")
    if payment.match_status == "rejected":
        return payment
    if not _is_subscription_false_positive(payment):
        raise ValueError("Only auto-detected subscription false-positive loan payments can be rejected here.")
    settled_payment_ids = _finalized_settlement_payment_ids(payment.loan)
    if settled_payment_ids is not None and payment.id in settled_payment_ids:
        raise ValueError("Payments in a finalized foreclosure settlement cannot be accepted or rejected through payment review.")

    if payment.loan_effect_applied and settled_payment_ids is None and not _predates_verified_balance(payment):
        _reverse_payment_from_loan(payment.loan, payment)
    payment.loan_effect_applied = False
    payment.match_status = "rejected"
    _append_review_note(payment, "Rejected as subscription false positive", notes)
    payment.save(update_fields=["match_status", "loan_effect_applied", "detection_reason"])
    _sync_loan_from_applied_matches(payment.loan)
    operational_logging_service.log(
        user=payment.loan.user,
        module="loans",
        category="api",
        scope="loan_payment_review",
        event_type="loan_payment_subscription_false_positive_rejected",
        severity="info",
        document_id=payment.id,
        file_name="",
        message="Subscription false-positive loan payment excluded from debt confidence.",
        payload={
            "payment_id": payment.id,
            "loan_id": payment.loan_id,
            "reviewer_id": getattr(reviewer, "id", None),
            "notes": notes,
            "expense_reference_id": payment.expense_reference_id,
            "expense_category": getattr(payment.expense_reference, "category", ""),
        },
    )
    return payment


def _finalized_settlement_payment_ids(loan: Loan) -> set[int] | None:
    payment_ids = None
    for audit in loan.foreclosure_snapshots.values_list("audit_payload", flat=True).iterator():
        posting = (audit or {}).get("settlement_posting") or {}
        if not posting.get("finalized_at"):
            continue
        if payment_ids is None:
            payment_ids = set()
        payment_ids.update(posting.get("created_payment_history_ids") or [])
        payment_ids.update(
            item["payment_history_id"]
            for item in posting.get("preserved_existing_payment_history") or []
            if item.get("payment_history_id") is not None
        )
    return payment_ids


def _predates_verified_balance(payment: LoanPaymentHistory) -> bool:
    verified_at = payment.loan.verified_at
    return bool(verified_at and (
        payment.created_at <= verified_at or payment.payment_date <= timezone.localtime(verified_at).date()
    ))


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
    loan.total_paid = loan_money(loan.total_paid) + loan_money(payment.amount)
    if payment.remaining_balance is not None:
        loan.remaining_balance = loan_money(max(loan_money(payment.remaining_balance), 0))
    else:
        current_balance = loan_money(loan.remaining_balance if loan.remaining_balance is not None else loan.principal)
        loan.remaining_balance = loan_money(max(current_balance - principal_paid, 0))

    if loan.remaining_balance <= 100:
        loan.is_active = False
        loan.status = "closed"
        loan.closed_on = payment.payment_date
        loan.remaining_balance = loan_money(0)

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
    current_balance = loan_money(loan.remaining_balance)
    loan.remaining_balance = loan_money(max(current_balance + principal_paid, 0))
    loan.total_paid = loan_money(max(loan_money(loan.total_paid) - loan_money(payment.amount), 0))
    remaining_applied_count = (
        LoanPaymentHistory.objects.filter(loan=loan, loan_effect_applied=True).exclude(id=payment.id).count()
    )
    latest_applied = (
        LoanPaymentHistory.objects.filter(loan=loan, loan_effect_applied=True, match_status="matched")
        .exclude(id=payment.id)
        .order_by("-payment_date", "-id")
        .first()
    )
    loan.last_payment_date = latest_applied.payment_date if latest_applied else None
    if loan.auto_detected and not loan.is_confirmed and remaining_applied_count == 0:
        loan.remaining_balance = loan_money(0)
        loan.total_paid = loan_money(0)
        loan.is_active = False
        loan.status = "closed"
        loan.closed_on = payment.payment_date
        note = "Auto-detected loan excluded after review rejected all applied payment evidence."
        loan.notes = f"{loan.notes}\n{note}".strip() if loan.notes else note
    elif loan.status in {"closed", "prepaid"} and loan.remaining_balance > 100:
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
            "notes",
            "updated_at",
        ]
    )


def _principal_paid(payment: LoanPaymentHistory) -> Decimal:
    return loan_money(payment.principal_paid or payment.principal_component or 0)


def _sync_loan_from_applied_matches(loan: Loan) -> bool:
    if not loan.is_confirmed or _finalized_settlement_payment_ids(loan) is not None:
        return False
    applied = LoanPaymentHistory.objects.filter(loan=loan, loan_effect_applied=True, match_status="matched")
    if loan.verified_at:
        applied = applied.filter(created_at__gt=loan.verified_at, payment_date__gt=timezone.localtime(loan.verified_at).date())
    latest_applied = (
        applied
        .order_by("-payment_date", "-id")
        .first()
    )
    if latest_applied is None:
        return False

    paid_amounts = LoanPaymentHistory.objects.filter(
        loan=loan, loan_effect_applied=True, match_status="matched",
    ).values_list("amount", flat=True).iterator()
    total_paid = sum((loan_money(amount) for amount in paid_amounts), loan_money(0))
    loan.last_payment_date = latest_applied.payment_date
    loan.total_paid = loan_money(total_paid)
    if latest_applied.remaining_balance is not None:
        loan.remaining_balance = loan_money(max(loan_money(latest_applied.remaining_balance), 0))

    if loan.remaining_balance is not None and loan.remaining_balance <= 100:
        loan.is_active = False
        loan.status = "closed"
        loan.closed_on = latest_applied.payment_date
        loan.remaining_balance = loan_money(0)
    elif loan.remaining_balance is not None and loan.status in {"closed", "prepaid"}:
        loan.is_active = True
        loan.status = "active"
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
    return True


def _is_subscription_false_positive(payment: LoanPaymentHistory) -> bool:
    expense = payment.expense_reference
    if expense is None:
        return False
    if not (payment.is_auto_detected or payment.loan.auto_detected):
        return False
    if (expense.category or "").lower() != "subscription":
        return False

    text = " ".join(
        part for part in [
            expense.description,
            expense.raw_description,
            expense.external_reference,
            expense.company_name,
            expense.merchant,
            expense.counterparty,
            payment.loan.lender,
        ]
        if part
    ).upper()
    return any(keyword in text for keyword in SUBSCRIPTION_FALSE_POSITIVE_KEYWORDS)
