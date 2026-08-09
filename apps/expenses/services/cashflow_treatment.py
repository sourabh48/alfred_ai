from __future__ import annotations

from dataclasses import dataclass


CASHFLOW_REVIEW_AMOUNT_THRESHOLD = 50000.0
SUSPICIOUS_OTHER_DEBIT_TERMS = (
    "SELF CHQ",
    "SELF CHEQUE",
    "LOAN",
    "REPAYMENT",
    "FINCORP",
    "POONAWALLA",
    "SLICE",
    "FORECLOS",
    "CLOSURE",
    "SETTLEMENT",
)


@dataclass(frozen=True)
class CashflowTreatment:
    bucket: str
    reason: str
    counts_income: bool = False
    counts_direct_expense: bool = False
    counts_cashflow_outflow: bool = False
    counts_debt_service: bool = False
    counts_credit_card_payment: bool = False
    counts_investment: bool = False
    counts_transfer: bool = False
    requires_review: bool = False


def classify_cashflow(expense) -> CashflowTreatment:
    direction = _normalized(getattr(expense, "direction", ""))
    category = _normalized(getattr(expense, "category", ""))
    classification = _normalized(getattr(expense, "classification", ""))

    if direction == "credit":
        if category == "income":
            return CashflowTreatment(
                bucket="income",
                reason="credit_income_category",
                counts_income=True,
            )
        if category == "transfer":
            return CashflowTreatment(
                bucket="transfer_in",
                reason="credit_transfer_excluded_from_income",
                counts_transfer=True,
            )
        return CashflowTreatment(
            bucket="other_credit",
            reason="credit_not_confirmed_as_income",
        )

    if category == "transfer":
        return CashflowTreatment(
            bucket="transfer_out",
            reason="debit_transfer_excluded_from_spend",
            counts_transfer=True,
        )
    if category == "credit_card":
        return CashflowTreatment(
            bucket="credit_card_payment",
            reason="credit_card_settlement_separate_from_direct_expense",
            counts_cashflow_outflow=True,
            counts_credit_card_payment=True,
            counts_debt_service=True,
        )
    if category == "investment":
        return CashflowTreatment(
            bucket="investment",
            reason="investment_flow_separate_from_direct_expense",
            counts_cashflow_outflow=True,
            counts_investment=True,
        )
    if category == "loan" or classification == "loan":
        return CashflowTreatment(
            bucket="loan",
            reason="loan_or_emi_debit",
            counts_cashflow_outflow=True,
            counts_debt_service=True,
        )
    if _requires_other_debit_review(expense, category=category, classification=classification):
        return CashflowTreatment(
            bucket="review_required",
            reason="large_or_loan_like_other_debit_requires_review",
            requires_review=True,
        )
    if classification == "expense":
        return CashflowTreatment(
            bucket="expense",
            reason="direct_expense",
            counts_income=False,
            counts_direct_expense=True,
            counts_cashflow_outflow=True,
        )
    return CashflowTreatment(
        bucket="other",
        reason="uncategorized_cashflow_outflow",
        counts_cashflow_outflow=True,
    )


def empty_cashflow_bucket() -> dict:
    return {
        "income_total": 0.0,
        "transfer_in_total": 0.0,
        "other_credit_total": 0.0,
        "bank_credit_total": 0.0,
        "expense_total": 0.0,
        "loan_total": 0.0,
        "credit_card_payment_total": 0.0,
        "investment_total": 0.0,
        "transfer_out_total": 0.0,
        "other_total": 0.0,
        "review_required_total": 0.0,
        "unwanted_total": 0.0,
        "bank_debit_total": 0.0,
        "outflow_total": 0.0,
        "count": 0,
    }


def add_expense_to_cashflow_bucket(bucket: dict, expense) -> CashflowTreatment:
    amount = _amount(expense)
    treatment = classify_cashflow(expense)
    direction = _normalized(getattr(expense, "direction", ""))

    if direction == "credit":
        bucket["bank_credit_total"] += amount
    elif direction == "debit":
        bucket["bank_debit_total"] += amount

    if treatment.bucket == "income":
        bucket["income_total"] += amount
    elif treatment.bucket == "transfer_in":
        bucket["transfer_in_total"] += amount
    elif treatment.bucket == "other_credit":
        bucket["other_credit_total"] += amount
    elif treatment.bucket == "expense":
        bucket["expense_total"] += amount
    elif treatment.bucket == "loan":
        bucket["loan_total"] += amount
    elif treatment.bucket == "credit_card_payment":
        bucket["credit_card_payment_total"] += amount
    elif treatment.bucket == "investment":
        bucket["investment_total"] += amount
    elif treatment.bucket == "transfer_out":
        bucket["transfer_out_total"] += amount
    elif treatment.bucket == "review_required":
        bucket["review_required_total"] += amount
    else:
        bucket["other_total"] += amount

    if treatment.counts_cashflow_outflow:
        bucket["outflow_total"] += amount
    bucket["count"] += 1
    return treatment


def summarize_cashflow(expenses) -> dict:
    bucket = empty_cashflow_bucket()
    for expense in expenses:
        add_expense_to_cashflow_bucket(bucket, expense)
    return bucket


def rounded_cashflow_bucket(bucket: dict) -> dict:
    payload = {}
    for key, value in bucket.items():
        if isinstance(value, float):
            payload[key] = round(value, 2)
        else:
            payload[key] = value
    payload["net_total"] = round(payload.get("income_total", 0.0) - payload.get("outflow_total", 0.0), 2)
    payload["transaction_count"] = int(payload.get("count", 0))
    payload["excluded_transfer_total"] = round(
        payload.get("transfer_in_total", 0.0) + payload.get("transfer_out_total", 0.0),
        2,
    )
    return payload


def _requires_other_debit_review(expense, *, category: str, classification: str) -> bool:
    if category != "other" and classification != "other":
        return False
    amount = _amount(expense)
    text = " ".join(
        str(value or "")
        for value in (
            getattr(expense, "merchant", ""),
            getattr(expense, "description", ""),
            getattr(expense, "raw_description", ""),
            getattr(expense, "counterparty", ""),
            getattr(expense, "company_name", ""),
        )
    ).upper()
    if any(term in text for term in SUSPICIOUS_OTHER_DEBIT_TERMS):
        return True
    return amount >= CASHFLOW_REVIEW_AMOUNT_THRESHOLD


def _normalized(value) -> str:
    return str(value or "").strip().lower()


def _amount(expense) -> float:
    try:
        return float(getattr(expense, "amount", 0) or 0)
    except (TypeError, ValueError):
        return 0.0
