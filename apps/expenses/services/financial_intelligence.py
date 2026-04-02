from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from math import log
from statistics import mean, pstdev

from django.db.models import Count, Max
from django.utils import timezone

from alfred_ai.services.materialized_cache import materialize_payload
from apps.expenses.models import BankAccount, Expense
from apps.integrations.models import CreditReportUpload
from apps.investments.models import Investment
from apps.loans.models import Loan, LoanForeclosureSnapshot, LoanPaymentHistory
from apps.loans.services.payment_history_access import fetch_payment_history_rows
from apps.ml_engine.behavior.anomaly_detector import anomaly_detector
from apps.ml_engine.behavior.behavior_signature import behavior_signature
from apps.ml_engine.behavior.insight_generator import insight_generator
from apps.ml_engine.behavior.personalizer import personalizer
from apps.mobility.models import BikeProfile, BikeServiceRecord, TripLog
from .financial_relationships import build_financial_relationships


DISCRETIONARY_CATEGORIES = {
    "food",
    "groceries",
    "shopping",
    "travel",
    "subscription",
    "entertainment",
}
RECURRING_CATEGORIES = {"loan", "utilities", "subscription", "rent", "bills", "credit_card"}


def build_financial_intelligence(user) -> dict:
    revision = _financial_revision(user)
    return materialize_payload(
        namespace="financial-intelligence",
        user_id=user.id,
        revision=revision,
        ttl_seconds=45,
        builder=lambda: _build_financial_intelligence_uncached(user),
    )


def _build_financial_intelligence_uncached(user) -> dict:
    expenses = list(Expense.objects.filter(user=user).order_by("transaction_date", "id"))
    loans = list(Loan.objects.filter(user=user).order_by("-start_date", "-id"))

    intelligence = _empty_intelligence()
    balance_sheet = _build_balance_sheet(user=user, loans=loans)
    intelligence["balance_sheet"] = balance_sheet
    financial_relationships, transaction_relationships = build_financial_relationships(user=user, expenses=expenses, loans=loans)
    intelligence["financial_relationships"] = financial_relationships
    if not expenses and not loans:
        if balance_sheet["total_assets"] or balance_sheet["total_liabilities"] or balance_sheet["vehicle_positions"]:
            intelligence["summary"]["risk_level"] = "Limited data"
            intelligence["summary"]["liquidity_score"] = 55.0 if balance_sheet["total_assets"] else 0.0
            intelligence["behavior"]["ai_insights"] = [
                "ALFRED has balance-sheet data, but it still needs transaction history to learn spending patterns."
            ]
            intelligence["behavior"]["strategy"] = "Import a statement to combine cash-flow behavior with the balance-sheet view."
        return intelligence

    today = timezone.localdate()
    reference_date = max([item.transaction_date for item in expenses], default=today)

    monthly_buckets = _build_monthly_buckets(expenses)
    current_key = (reference_date.year, reference_date.month)
    previous_date = _shift_month(reference_date, -1)
    previous_key = (previous_date.year, previous_date.month)
    current_bucket = monthly_buckets.get(current_key, _empty_month_bucket())
    previous_bucket = monthly_buckets.get(previous_key, _empty_month_bucket())

    debit_expenses = [item for item in expenses if item.direction == "debit"]
    income_entries = [item for item in expenses if item.direction == "credit"]
    debt_entries = [item for item in debit_expenses if item.classification == "loan" or item.category == "credit_card"]

    income_total = sum(item.amount for item in income_entries)
    debit_total = sum(item.amount for item in debit_expenses)
    expense_total = sum(item.amount for item in debit_expenses if item.classification == "expense")
    loan_total = sum(item.amount for item in debit_expenses if item.classification == "loan")
    other_total = sum(item.amount for item in debit_expenses if item.classification == "other")
    discretionary_total = sum(item.amount for item in debit_expenses if item.category in DISCRETIONARY_CATEGORIES)
    savings_rate = ((income_total - debit_total) / income_total) if income_total else 0.0
    loan_ratio = (loan_total / debit_total) if debit_total else 0.0
    debt_service_ratio = (sum(item.amount for item in debt_entries) / income_total) if income_total else 0.0
    discretionary_ratio = (discretionary_total / debit_total) if debit_total else 0.0

    category_distribution = _build_category_distribution(debit_expenses)
    lifestyle = _build_lifestyle_profile(category_distribution, debit_total, discretionary_ratio)
    recurring_commitments = _build_recurring_commitments(debit_expenses)
    spike_days = _build_spike_days(debit_expenses)
    recent_transactions = _serialize_recent_transactions(expenses, transaction_relationships)
    manual_loans = _serialize_loans(loans, today)
    debt_trend = _build_debt_trend(monthly_buckets)
    monthly_outflows = [bucket["expense"] + bucket["loan"] + bucket["other"] for _, bucket in sorted(monthly_buckets.items())]
    monthly_stress = [
        _build_monthly_stress_score(bucket["expense"], bucket["loan"], bucket["other"], bucket["income"])
        for _, bucket in sorted(monthly_buckets.items())
    ]
    avg_monthly_outflow = mean(monthly_outflows) if monthly_outflows else 0.0
    volatility_ratio = _safe_ratio(_series_std(monthly_outflows), max(avg_monthly_outflow, 1))
    signature = behavior_signature.generate_signature(monthly_outflows, monthly_stress)
    expense_spike, spike_amount = anomaly_detector.detect_expense_spike(monthly_outflows)
    burnout_spike = anomaly_detector.detect_burnout_spike(monthly_stress)
    ai_insights = insight_generator.generate_insights(
        signature,
        {"expense_spike": expense_spike, "spike_amount": spike_amount},
    )

    stability_score = _clamp(100 - volatility_ratio * 100)
    discipline_score = _clamp(70 + (savings_rate * 80) - (discretionary_ratio * 65) - (debt_service_ratio * 50))
    liquidity_score = _clamp(55 + (savings_rate * 120) - (loan_ratio * 55))
    stress_score = _clamp(
        (loan_ratio * 42)
        + (debt_service_ratio * 35)
        + (volatility_ratio * 28)
        + (_safe_ratio(len(spike_days), max(len(monthly_buckets), 1)) * 18)
        + max(0.0, (0.12 - savings_rate) * 110)
    )
    health_score = _clamp((stability_score + discipline_score + liquidity_score + (100 - stress_score)) / 4)
    risk_level = _risk_level(stress_score)
    personality = _behavior_personality(savings_rate, loan_ratio, discretionary_ratio, stability_score)
    strategy = personalizer.suggest_savings_strategy(signature)
    tone = personalizer.personalize_ai_tone(min(10, signature["stress_avg"]))
    if burnout_spike:
        ai_insights.append("Stress signals have accelerated. Slow down new obligations and protect liquidity.")

    top_categories = [item["label"] for item in category_distribution[:3]]
    top_recurring = recurring_commitments[0]["merchant"] if recurring_commitments else "No recurring pattern yet"
    peak_day = spike_days[0]["date"] if spike_days else None

    intelligence.update(
        {
            "summary": {
                "reference_month": reference_date.strftime("%B %Y"),
                "current_month_income": round(current_bucket["income"], 2),
                "current_month_expense": round(current_bucket["expense"], 2),
                "current_month_loans": round(current_bucket["loan"], 2),
                "current_month_other": round(current_bucket["other"], 2),
                "current_month_net": round(current_bucket["income"] - (current_bucket["expense"] + current_bucket["loan"] + current_bucket["other"]), 2),
                "monthly_expense_delta": round(current_bucket["expense"] - previous_bucket["expense"], 2),
                "financial_health_score": round(health_score, 1),
                "stability_score": round(stability_score, 1),
                "discipline_score": round(discipline_score, 1),
                "liquidity_score": round(liquidity_score, 1),
                "stress_score": round(stress_score, 1),
                "risk_level": risk_level,
                "savings_rate": round(savings_rate * 100, 1),
                "loan_ratio": round(loan_ratio * 100, 1),
                "debt_service_ratio": round(debt_service_ratio * 100, 1),
                "discretionary_ratio": round(discretionary_ratio * 100, 1),
                "lifestyle_diversity_score": lifestyle["diversity_score"],
                "lifestyle_risk_level": lifestyle["risk_level"],
                "transactions": len(expenses),
            },
            "charts": {
                "monthly_labels": [f"{_month_name(year, month)} {year}" for year, month in sorted(monthly_buckets.keys())],
                "monthly_expense_values": [round(bucket["expense"], 2) for _, bucket in sorted(monthly_buckets.items())],
                "monthly_loan_values": [round(bucket["loan"], 2) for _, bucket in sorted(monthly_buckets.items())],
                "monthly_other_values": [round(bucket["other"], 2) for _, bucket in sorted(monthly_buckets.items())],
                "monthly_income_values": [round(bucket["income"], 2) for _, bucket in sorted(monthly_buckets.items())],
                "category_labels": [item["label"] for item in category_distribution],
                "category_values": [item["amount"] for item in category_distribution],
                "debt_labels": debt_trend["labels"],
                "debt_values": debt_trend["values"],
            },
            "behavior": {
                "personality": personality,
                "coach_tone": tone,
                "signature": signature,
                "strategy": strategy,
                "ai_insights": ai_insights,
                "pattern_flags": _build_pattern_flags(
                    savings_rate=savings_rate,
                    loan_ratio=loan_ratio,
                    discretionary_ratio=discretionary_ratio,
                    top_categories=top_categories,
                    recurring_commitments=recurring_commitments,
                    spike_days=spike_days,
                ),
                "stress_drivers": _build_stress_drivers(loan_ratio, debt_service_ratio, discretionary_ratio, spike_days),
                "minute_details": _build_minute_details(
                    debit_expenses=debit_expenses,
                    income_entries=income_entries,
                    recurring_commitments=recurring_commitments,
                    peak_day=peak_day,
                ),
            },
            "loan_portfolio": _build_loan_portfolio(loans, debt_entries, current_bucket),
            "balance_sheet": balance_sheet,
            "financial_relationships": financial_relationships,
            "lifestyle": lifestyle,
            "recent_transactions": recent_transactions,
            "recurring_commitments": recurring_commitments,
            "spike_days": spike_days,
        }
    )

    return intelligence


def _financial_revision(user) -> str:
    expense_meta = Expense.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_date=Max("transaction_date"))
    loan_meta = Loan.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"))
    payment_meta = LoanPaymentHistory.objects.filter(loan__user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        max_date=Max("payment_date"),
        max_created=Max("created_at"),
    )
    account_meta = BankAccount.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_sync=Max("last_synced_at"))
    investment_meta = Investment.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"))
    foreclosure_meta = LoanForeclosureSnapshot.objects.filter(loan__user=user).aggregate(count=Count("id"), max_id=Max("id"), max_updated=Max("updated_at"))
    credit_meta = CreditReportUpload.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_updated=Max("updated_at"))
    vehicle_meta = BikeProfile.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_updated=Max("updated_at"))
    service_meta = BikeServiceRecord.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_date=Max("service_date"))
    trip_meta = TripLog.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_date=Max("log_date"))
    return "|".join(
        str(value or "")
        for value in [
            expense_meta["count"], expense_meta["max_id"], expense_meta["max_date"],
            loan_meta["count"], loan_meta["max_id"],
            payment_meta["count"], payment_meta["max_id"], payment_meta["max_date"], payment_meta["max_created"],
            account_meta["count"], account_meta["max_id"], account_meta["max_sync"],
            investment_meta["count"], investment_meta["max_id"],
            foreclosure_meta["count"], foreclosure_meta["max_id"], foreclosure_meta["max_updated"],
            credit_meta["count"], credit_meta["max_id"], credit_meta["max_updated"],
            vehicle_meta["count"], vehicle_meta["max_id"], vehicle_meta["max_updated"],
            service_meta["count"], service_meta["max_id"], service_meta["max_date"],
            trip_meta["count"], trip_meta["max_id"], trip_meta["max_date"],
        ]
    )


def _empty_intelligence() -> dict:
    return {
        "summary": {
            "reference_month": timezone.localdate().strftime("%B %Y"),
            "current_month_income": 0.0,
            "current_month_expense": 0.0,
            "current_month_loans": 0.0,
            "current_month_other": 0.0,
            "current_month_net": 0.0,
            "monthly_expense_delta": 0.0,
            "financial_health_score": 0.0,
            "stability_score": 0.0,
            "discipline_score": 0.0,
            "liquidity_score": 0.0,
            "stress_score": 0.0,
            "risk_level": "No data",
            "savings_rate": 0.0,
            "loan_ratio": 0.0,
            "debt_service_ratio": 0.0,
            "discretionary_ratio": 0.0,
            "lifestyle_diversity_score": 0.0,
            "lifestyle_risk_level": "No data",
            "transactions": 0,
        },
        "charts": {
            "monthly_labels": [],
            "monthly_expense_values": [],
            "monthly_loan_values": [],
            "monthly_other_values": [],
            "monthly_income_values": [],
            "category_labels": [],
            "category_values": [],
            "debt_labels": [],
            "debt_values": [],
        },
        "behavior": {
            "personality": "Awaiting history",
            "coach_tone": "energetic",
            "signature": {"avg_expense": 0.0, "expense_volatility": 0.0, "stress_avg": 0.0, "spike_factor": 0.0},
            "strategy": "Import bank statements or add expenses so ALFRED can build your profile.",
            "ai_insights": ["ALFRED needs transaction history before it can learn your patterns."],
            "pattern_flags": [],
            "stress_drivers": [],
            "minute_details": [],
        },
        "loan_portfolio": {
            "active_loans": 0,
            "manual_total_outstanding": 0.0,
            "manual_total_emi": 0.0,
            "manual_interest_remaining": 0.0,
            "pending_foreclosure_excluded_balance": 0.0,
            "payment_component_totals": {
                "principal_paid": 0.0,
                "interest_paid": 0.0,
                "charges_paid": 0.0,
                "penalties_paid": 0.0,
                "tax_paid": 0.0,
            },
            "foreclosure_pending_count": 0,
            "reconciled_foreclosures": 0,
            "foreclosure_watchlist": [],
            "detected_repayment_total": 0.0,
            "current_month_repayment": 0.0,
            "projected_payoff_months": 0,
            "manual_loans": [],
            "detected_repayments": [],
        },
        "balance_sheet": {
            "total_assets": 0.0,
            "total_liabilities": 0.0,
            "net_worth": 0.0,
            "asset_liability_ratio": 0.0,
            "pending_foreclosure_excluded_balance": 0.0,
            "assets": [],
            "liabilities": [],
            "vehicle_positions": [],
            "summary": "Add account balances, investments, loans, or vehicle profiles to build the balance-sheet view.",
        },
        "financial_relationships": {
            "summary": {
                "tracked_events": 0,
                "self_transfers": 0,
                "loan_disbursements": 0,
                "loan_repayments": 0,
                "loan_part_payments": 0,
                "loan_closure_payments": 0,
                "bureau_accounts": 0,
                "bureau_accounts_linked": 0,
            },
            "bureau_report": {
                "source_upload_id": None,
                "bureau": "",
                "report_date": "",
                "file_name": "",
            },
            "bureau_accounts": [],
            "events": [],
        },
        "lifestyle": {
            "diversity_score": 0.0,
            "concentration_ratio": 0.0,
            "dominant_categories": [],
            "risk_level": "No data",
            "summary": "Lifestyle diversification will appear once Alfred has enough spending history.",
        },
        "recent_transactions": [],
        "recurring_commitments": [],
        "spike_days": [],
    }


def _build_monthly_buckets(expenses: list[Expense]) -> dict[tuple[int, int], dict]:
    buckets: dict[tuple[int, int], dict] = defaultdict(_empty_month_bucket)

    for item in expenses:
        key = (item.transaction_date.year, item.transaction_date.month)
        bucket = buckets[key]
        if item.direction == "credit":
            bucket["income"] += item.amount
        elif item.classification == "expense":
            bucket["expense"] += item.amount
        elif item.classification == "loan":
            bucket["loan"] += item.amount
        else:
            bucket["other"] += item.amount
        bucket["count"] += 1

    return buckets


def _empty_month_bucket() -> dict:
    return {"income": 0.0, "expense": 0.0, "loan": 0.0, "other": 0.0, "count": 0}


def _build_category_distribution(expenses: list[Expense]) -> list[dict]:
    totals: Counter[str] = Counter()
    labels = dict(Expense.CATEGORY_CHOICES)

    for item in expenses:
        totals[item.category] += item.amount

    return [
        {"key": key, "label": labels.get(key, key.replace("_", " ").title()), "amount": round(amount, 2)}
        for key, amount in totals.most_common(6)
    ]


def _build_recurring_commitments(expenses: list[Expense]) -> list[dict]:
    grouped: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"count": 0, "total": 0.0, "months": set(), "category": "other", "merchant": "Unspecified"}
    )
    labels = dict(Expense.CATEGORY_CHOICES)

    for item in expenses:
        merchant = _normalized_merchant(item.merchant or item.raw_description or item.description)
        key = (merchant, item.category)
        grouped[key]["count"] += 1
        grouped[key]["total"] += item.amount
        grouped[key]["months"].add((item.transaction_date.year, item.transaction_date.month))
        grouped[key]["category"] = item.category
        grouped[key]["merchant"] = item.merchant or merchant.title()

    commitments = []
    for (_, _), value in grouped.items():
        recurring = len(value["months"]) >= 2 or (value["count"] >= 2 and value["category"] in RECURRING_CATEGORIES)
        if not recurring:
            continue

        commitments.append(
            {
                "merchant": value["merchant"],
                "category": labels.get(value["category"], value["category"].title()),
                "average_amount": round(value["total"] / value["count"], 2),
                "count": value["count"],
                "cadence": "Recurring",
            }
        )

    commitments.sort(key=lambda item: (-item["average_amount"], -item["count"]))
    return commitments[:5]


def _build_spike_days(expenses: list[Expense]) -> list[dict]:
    daily_totals: dict[date, float] = defaultdict(float)
    daily_merchants: dict[date, list[str]] = defaultdict(list)

    for item in expenses:
        daily_totals[item.transaction_date] += item.amount
        if item.merchant:
            daily_merchants[item.transaction_date].append(item.merchant)

    if len(daily_totals) < 3:
        return []

    totals = list(daily_totals.values())
    threshold = mean(totals) + (_series_std(totals) * 1.35)
    spikes = [
        {
            "date": day.isoformat(),
            "amount": round(amount, 2),
            "driver": ", ".join(daily_merchants[day][:2]) if daily_merchants[day] else "Multiple transactions",
        }
        for day, amount in daily_totals.items()
        if amount >= threshold
    ]
    spikes.sort(key=lambda item: item["amount"], reverse=True)
    return spikes[:5]


def _serialize_recent_transactions(expenses: list[Expense], transaction_relationships: dict[int, list[dict]] | None = None) -> list[dict]:
    category_labels = dict(Expense.CATEGORY_CHOICES)
    classification_labels = dict(Expense.CLASSIFICATION_CHOICES)
    transaction_relationships = transaction_relationships or {}

    recent = sorted(expenses, key=lambda item: (item.transaction_date, item.id), reverse=True)[:8]
    return [
        {
            "date": item.transaction_date.isoformat(),
            "merchant": item.merchant or "Unspecified",
            "classification": item.classification,
            "classification_label": classification_labels.get(item.classification, item.classification.title()),
            "category": item.category,
            "category_label": category_labels.get(item.category, item.category.title()),
            "direction": item.direction,
            "amount": round(item.amount, 2),
            "description": item.description or item.raw_description,
            "relationship_types": [relationship.get("relation_type", "") for relationship in transaction_relationships.get(item.id, [])],
            "linked_relationships": transaction_relationships.get(item.id, []),
        }
        for item in recent
    ]


def _build_loan_portfolio(loans: list[Loan], debt_entries: list[Expense], current_bucket: dict) -> dict:
    manual_loans = _serialize_loans(loans, timezone.localdate())
    active_manual_loans = [item for item in manual_loans if item["is_active"]]
    liability_manual_loans = [item for item in manual_loans if item["counts_toward_liabilities"]]
    pending_manual_loans = [item for item in liability_manual_loans if item["status"] == "foreclosure_pending"]
    total_outstanding = sum(item["estimated_balance"] for item in liability_manual_loans)
    total_emi = sum(item["emi"] for item in active_manual_loans)
    interest_remaining = sum(item["interest_remaining"] for item in active_manual_loans)
    pending_foreclosure_balance = round(sum(item["estimated_balance"] for item in pending_manual_loans), 2)
    current_month_repayment = current_bucket["loan"]
    payment_user = loans[0].user if loans else (debt_entries[0].user if debt_entries else None)
    linked_payment_rows = (
        fetch_payment_history_rows(
            user=payment_user,
            expense_reference_ids=[entry.id for entry in debt_entries if entry.id],
            include_loan_fields=True,
        )
        if payment_user
        else []
    )
    linked_payments = {
        item.get("expense_reference_id"): item
        for item in linked_payment_rows
        if item.get("expense_reference_id")
    }
    payment_component_totals = {
        "principal_paid": round(sum(float(item.get("principal_paid") or item.get("principal_component") or 0) for item in linked_payment_rows), 2),
        "interest_paid": round(sum(float(item.get("interest_paid") or item.get("interest_component") or 0) for item in linked_payment_rows), 2),
        "charges_paid": round(sum(float(item.get("charges_paid") or 0) for item in linked_payment_rows), 2),
        "penalties_paid": round(sum(float(item.get("penalties_paid") or 0) for item in linked_payment_rows), 2),
        "tax_paid": round(sum(float(item.get("tax_paid") or 0) for item in linked_payment_rows), 2),
    }
    detected_repayments = [
        {
            "date": item.transaction_date.isoformat(),
            "merchant": item.merchant or "Detected repayment",
            "amount": round(item.amount, 2),
            "description": item.description or item.raw_description,
            "category": dict(Expense.CATEGORY_CHOICES).get(item.category, item.category.title()),
            "linked_loan": linked_payments[item.id].get("loan__lender", "") if item.id in linked_payments else "",
            "match_status": linked_payments[item.id].get("match_status", "") if item.id in linked_payments else "",
            "principal_paid": round(float(linked_payments[item.id].get("principal_paid") or linked_payments[item.id].get("principal_component") or 0), 2) if item.id in linked_payments else 0.0,
            "interest_paid": round(float(linked_payments[item.id].get("interest_paid") or linked_payments[item.id].get("interest_component") or 0), 2) if item.id in linked_payments else 0.0,
            "charges_paid": round(float(linked_payments[item.id].get("charges_paid") or 0), 2) if item.id in linked_payments else 0.0,
            "penalties_paid": round(float(linked_payments[item.id].get("penalties_paid") or 0), 2) if item.id in linked_payments else 0.0,
            "tax_paid": round(float(linked_payments[item.id].get("tax_paid") or 0), 2) if item.id in linked_payments else 0.0,
        }
        for item in sorted(debt_entries, key=lambda value: (value.transaction_date, value.id), reverse=True)[:8]
    ]

    projected_months = max([loan["months_remaining"] for loan in active_manual_loans], default=0)
    snapshots = list(
        LoanForeclosureSnapshot.objects.select_related("loan")
        .filter(loan__in=[loan.id for loan in loans])
        .order_by("-updated_at", "-id")
    )
    foreclosure_watchlist = [
        {
            "loan_id": item.loan_id,
            "lender": item.loan.lender,
            "document_type": item.get_document_type_display(),
            "status": item.get_reconciliation_status_display(),
            "effective_closure_date": item.effective_closure_date.isoformat() if item.effective_closure_date else "",
            "amount_payable": round(item.total_amount_payable or 0, 2),
            "matched_payment_total": round(item.matched_payment_total or 0, 2),
            "settlement_allocation": dict((item.audit_payload or {}).get("settlement_allocation") or {}),
            "notes": item.reconciliation_notes,
        }
        for item in snapshots[:6]
    ]

    return {
        "active_loans": sum(1 for item in manual_loans if item["is_active"]),
        "manual_total_outstanding": round(total_outstanding, 2),
        "manual_total_emi": round(total_emi, 2),
        "manual_interest_remaining": round(interest_remaining, 2),
        "pending_foreclosure_excluded_balance": pending_foreclosure_balance,
        "payment_component_totals": payment_component_totals,
        "foreclosure_pending_count": sum(1 for item in manual_loans if item["status"] == "foreclosure_pending"),
        "reconciled_foreclosures": sum(1 for item in snapshots if item.reconciliation_status == "full_match"),
        "foreclosure_watchlist": foreclosure_watchlist,
        "detected_repayment_total": round(sum(item.amount for item in debt_entries), 2),
        "current_month_repayment": round(current_month_repayment, 2),
        "projected_payoff_months": projected_months,
        "manual_loans": manual_loans,
        "detected_repayments": detected_repayments,
    }


def _serialize_loans(loans: list[Loan], today: date) -> list[dict]:
    result = []

    for loan in loans:
        months_elapsed = max(0, _months_between(loan.start_date, today))
        estimated_balance = _loan_reporting_balance(loan, today=today, months_elapsed=months_elapsed)
        months_to_close, interest_remaining = _forecast_payoff_months(
            balance=estimated_balance,
            annual_rate=loan.interest_rate,
            emi=loan.emi,
        )
        months_remaining = months_to_close
        projected_end_date = _shift_month(today, months_remaining)
        result.append(
            {
                "id": loan.id,
                "loan_type": loan.loan_type,
                "loan_type_label": loan.get_loan_type_display(),
                "lender": loan.lender,
                "loan_account_number": loan.loan_account_number,
                "principal": round(loan.principal, 2),
                "interest_rate": round(loan.interest_rate, 2),
                "emi": round(loan.emi, 2),
                "tenure_months": loan.tenure_months,
                "start_date": loan.start_date.isoformat(),
                "remaining_balance": round(loan.remaining_balance, 2) if loan.remaining_balance is not None else None,
                "estimated_balance": round(estimated_balance, 2),
                "status": loan.status,
                "closure_reason": loan.closure_reason,
                "consolidation_group": loan.consolidation_group,
                "consolidated_into_id": loan.consolidated_into_id,
                "months_elapsed": months_elapsed,
                "months_remaining": max(months_remaining, 0),
                "interest_remaining": round(interest_remaining, 2),
                "projected_end_date": projected_end_date.isoformat(),
                "recommended_prepayment": round(min(max(loan.emi * 2, 0), estimated_balance * 0.1 if estimated_balance else 0), 2),
                "notes": loan.notes,
                "is_active": loan.is_active and estimated_balance > 0,
                "counts_toward_liabilities": _loan_counts_toward_liabilities(loan, estimated_balance),
            }
        )

    return result


def _build_debt_trend(monthly_buckets: dict[tuple[int, int], dict]) -> dict:
    keys = sorted(monthly_buckets.keys())
    return {
        "labels": [f"{_month_name(year, month)} {year}" for year, month in keys],
        "values": [round(monthly_buckets[key]["loan"], 2) for key in keys],
    }


def _build_balance_sheet(*, user, loans: list[Loan]) -> dict:
    accounts = list(BankAccount.objects.filter(user=user, is_active=True))
    investments = list(Investment.objects.filter(user=user))
    vehicle_profiles = list(BikeProfile.objects.filter(user=user))
    vehicle_services = list(BikeServiceRecord.objects.filter(user=user).select_related("bike_profile"))
    trip_logs = list(TripLog.objects.filter(user=user).select_related("travel_plan", "travel_plan__vehicle_profile"))

    liquid_cash = round(sum(max(account.current_balance or 0, 0) for account in accounts if account.account_type != "credit"), 2)
    credit_liability = round(sum(abs(account.current_balance or 0) for account in accounts if account.account_type == "credit"), 2)
    investment_assets = round(sum(item.current_value or 0 for item in investments), 2)
    liability_loans = []
    pending_foreclosure_balance = 0.0
    open_loan_liability = 0.0
    today = timezone.localdate()
    for loan in loans:
        balance = _loan_reporting_balance(loan, today=today)
        if not _loan_counts_toward_liabilities(loan, balance):
            continue
        liability_loans.append((loan, balance))
        if loan.status == "foreclosure_pending":
            pending_foreclosure_balance += balance
        else:
            open_loan_liability += balance

    open_loan_liability = round(open_loan_liability, 2)
    pending_foreclosure_balance = round(pending_foreclosure_balance, 2)
    loan_liability = round(open_loan_liability + pending_foreclosure_balance, 2)

    vehicle_positions = _build_vehicle_positions(vehicle_profiles, vehicle_services, trip_logs)
    vehicle_assets = round(sum(item["recognized_value"] for item in vehicle_positions if item["bucket"] == "asset"), 2)
    vehicle_liabilities = round(sum(item["recognized_value"] for item in vehicle_positions if item["bucket"] == "liability"), 2)

    assets = [
        {"label": "Cash and bank balances", "amount": liquid_cash},
        {"label": "Investments", "amount": investment_assets},
    ]
    if vehicle_assets:
        assets.append({"label": "Utility and income-supporting vehicles", "amount": vehicle_assets})

    liabilities = []
    if open_loan_liability:
        liabilities.append({"label": "Open loan liabilities", "amount": open_loan_liability})
    if pending_foreclosure_balance:
        liabilities.append({"label": "Pending foreclosure liabilities", "amount": pending_foreclosure_balance})
    if credit_liability:
        liabilities.append({"label": "Credit card liability", "amount": credit_liability})
    if vehicle_liabilities:
        liabilities.append({"label": "Lifestyle vehicle burden", "amount": vehicle_liabilities})

    total_assets = round(sum(item["amount"] for item in assets), 2)
    total_liabilities = round(sum(item["amount"] for item in liabilities), 2)
    net_worth = round(total_assets - total_liabilities, 2)
    ratio = round((total_assets / total_liabilities), 2) if total_liabilities else 0.0
    if total_assets or total_liabilities:
        summary = f"Tracked assets total INR {total_assets:,.0f} and liabilities total INR {total_liabilities:,.0f}."
        if pending_foreclosure_balance:
            summary = (
                f"{summary} Pending foreclosure balances of INR {pending_foreclosure_balance:,.0f} "
                "remain in liabilities until a full closure-payment match is confirmed."
            )
    else:
        summary = "Add account balances, investments, loans, or vehicle profiles to build the balance-sheet view."

    return {
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": net_worth,
        "asset_liability_ratio": ratio,
        "pending_foreclosure_excluded_balance": pending_foreclosure_balance,
        "assets": assets,
        "liabilities": liabilities,
        "vehicle_positions": vehicle_positions,
        "summary": summary,
    }


def _loan_reporting_balance(loan: Loan, *, today: date, months_elapsed: int | None = None) -> float:
    if loan.status in {"foreclosed", "closed", "prepaid"}:
        return 0.0
    if loan.remaining_balance is not None:
        return round(max(float(loan.remaining_balance or 0), 0), 2)
    elapsed = months_elapsed if months_elapsed is not None else max(0, _months_between(loan.start_date, today))
    return round(
        _amortized_balance(
            principal=loan.principal,
            annual_rate=loan.interest_rate,
            emi=loan.emi,
            months_elapsed=elapsed,
            tenure_months=loan.tenure_months,
        ),
        2,
    )


def _loan_counts_toward_liabilities(loan: Loan, estimated_balance: float) -> bool:
    return loan.status not in {"foreclosed", "closed", "prepaid"} and round(float(estimated_balance or 0), 2) > 0


def _build_vehicle_positions(
    vehicle_profiles: list[BikeProfile],
    vehicle_services: list[BikeServiceRecord],
    trip_logs: list[TripLog],
) -> list[dict]:
    service_by_profile: dict[int | None, float] = defaultdict(float)
    for item in vehicle_services:
        service_by_profile[item.bike_profile_id] += item.cost or 0

    trip_by_profile: dict[int | None, float] = defaultdict(float)
    for item in trip_logs:
        profile_id = getattr(item.travel_plan, "vehicle_profile_id", None)
        trip_by_profile[profile_id] += item.spend_amount or 0

    positions = []
    for profile in vehicle_profiles:
        annual_service = service_by_profile.get(profile.id, 0.0)
        annual_trip_spend = trip_by_profile.get(profile.id, 0.0)
        annual_cost = annual_service + annual_trip_spend
        monthly_cost = annual_cost / 12 if annual_cost else 0.0
        market_value = profile.estimated_market_value or 0.0
        monthly_income_support = profile.monthly_income_support or 0.0

        if profile.usage_pattern == "commercial" or (
            profile.usage_pattern == "mixed" and monthly_income_support >= monthly_cost and monthly_income_support > 0
        ):
            bucket = "asset"
            recognized_value = market_value or max(monthly_income_support * 6, 0)
            rationale = "Vehicle is treated as an asset because its usage pattern or income support offsets the running cost."
        elif profile.usage_pattern == "essential":
            bucket = "asset"
            recognized_value = round(market_value * 0.35, 2) if market_value else round(monthly_cost * 6, 2)
            rationale = "Vehicle is treated as a utility asset because it supports essential mobility even if it is not directly income generating."
        else:
            bucket = "liability"
            recognized_value = round(max(monthly_cost * 12, market_value * 0.15 if market_value else 0), 2)
            rationale = "Vehicle is treated as a liability because current usage is primarily personal and the running cost is not offset by utility income."

        positions.append(
            {
                "vehicle": profile.display_name,
                "usage_pattern": profile.get_usage_pattern_display(),
                "bucket": bucket,
                "recognized_value": round(recognized_value, 2),
                "estimated_market_value": round(market_value, 2),
                "monthly_income_support": round(monthly_income_support, 2),
                "monthly_running_cost": round(monthly_cost, 2),
                "rationale": rationale,
            }
        )

    return positions


def _build_monthly_stress_score(expense: float, loan: float, other: float, income: float) -> float:
    total_outflow = expense + loan + other
    loan_ratio = _safe_ratio(loan, max(total_outflow, 1))
    liquidity_pressure = max(0.0, 1 - _safe_ratio(income, max(total_outflow, 1)))
    return round(min(10.0, (loan_ratio * 5.0) + (liquidity_pressure * 5.0)), 2)


def _build_pattern_flags(
    *,
    savings_rate: float,
    loan_ratio: float,
    discretionary_ratio: float,
    top_categories: list[str],
    recurring_commitments: list[dict],
    spike_days: list[dict],
) -> list[str]:
    flags = []

    if savings_rate < 0.1:
        flags.append("Savings conversion is below 10% of inflows. ALFRED should prioritize cash-buffer protection.")
    if loan_ratio > 0.2:
        flags.append("Loan repayments are consuming a meaningful share of your outflows. Prepayment or refinance options matter.")
    if discretionary_ratio > 0.35:
        flags.append("Lifestyle-led categories are driving more than a third of your outflows. This is the easiest optimization zone.")
    if top_categories:
        flags.append(f"Your spending is concentrated in {', '.join(top_categories[:3])}. That concentration defines your behavior fingerprint.")
    if recurring_commitments:
        flags.append(f"{len(recurring_commitments)} recurring commitments were detected from transaction history.")
    if spike_days:
        flags.append(f"ALFRED detected {len(spike_days)} spike days that should be reviewed before they become habits.")

    return flags[:6]


def _build_stress_drivers(loan_ratio: float, debt_service_ratio: float, discretionary_ratio: float, spike_days: list[dict]) -> list[str]:
    drivers = []
    if debt_service_ratio > 0.25:
        drivers.append("Debt servicing is taking a large share of monthly cash-in.")
    if loan_ratio > 0.2:
        drivers.append("Loan-heavy outflows are reducing flexibility for savings and investments.")
    if discretionary_ratio > 0.35:
        drivers.append("Variable lifestyle spending is amplifying cash-flow pressure.")
    if spike_days:
        drivers.append("High-intensity spend days indicate episodic bursts rather than controlled pacing.")
    return drivers[:4]


def _build_minute_details(
    *,
    debit_expenses: list[Expense],
    income_entries: list[Expense],
    recurring_commitments: list[dict],
    peak_day: str | None,
) -> list[str]:
    details = []

    if debit_expenses:
        avg_ticket = sum(item.amount for item in debit_expenses) / len(debit_expenses)
        by_weekday = Counter(item.transaction_date.strftime("%A") for item in debit_expenses)
        most_active_day, most_active_count = by_weekday.most_common(1)[0]
        details.append(f"Average debit ticket size is INR {avg_ticket:,.0f}.")
        details.append(f"{most_active_day} is your busiest spending day with {most_active_count} transactions.")

    if income_entries:
        avg_credit = sum(item.amount for item in income_entries) / len(income_entries)
        details.append(f"Average credit inflow ticket size is INR {avg_credit:,.0f}.")

    if recurring_commitments:
        first = recurring_commitments[0]
        details.append(f"Largest recurring commitment currently looks like {first['merchant']} at roughly INR {first['average_amount']:,.0f}.")

    if peak_day:
        details.append(f"Peak spending intensity occurred on {peak_day}.")

    return details[:5]


def _behavior_personality(savings_rate: float, loan_ratio: float, discretionary_ratio: float, stability_score: float) -> str:
    if savings_rate >= 0.25 and stability_score >= 75:
        return "Strategic Accumulator"
    if loan_ratio >= 0.25:
        return "Debt-Weighted Planner"
    if discretionary_ratio >= 0.38:
        return "Experience-Led Spender"
    return "Adaptive Balancer"


def _risk_level(stress_score: float) -> str:
    if stress_score >= 75:
        return "High"
    if stress_score >= 55:
        return "Guarded"
    if stress_score >= 35:
        return "Stable"
    return "Low"


def _normalized_merchant(value: str) -> str:
    cleaned = "".join(char for char in value.upper() if char.isalpha() or char == " ")
    return " ".join(cleaned.split())[:48] or "UNSPECIFIED"


def _months_between(start: date, end: date) -> int:
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return max(months, 0)


def _amortized_balance(*, principal: float, annual_rate: float, emi: float, months_elapsed: int, tenure_months: int) -> float:
    balance = principal
    monthly_rate = annual_rate / 1200 if annual_rate else 0

    for _ in range(min(months_elapsed, tenure_months)):
        if balance <= 0:
            break
        interest = balance * monthly_rate
        principal_component = emi - interest if emi > interest else 0
        if principal_component <= 0:
            break
        balance = max(balance - principal_component, 0)

    return balance


def _forecast_payoff_months(*, balance: float, annual_rate: float, emi: float) -> tuple[int, float]:
    if balance <= 0 or emi <= 0:
        return 0, 0.0

    monthly_rate = annual_rate / 1200 if annual_rate else 0
    months = 0
    interest_total = 0.0
    current_balance = balance

    while current_balance > 0 and months < 600:
        interest = current_balance * monthly_rate
        principal_component = emi - interest if emi > interest else 0
        if principal_component <= 0:
            return 600, interest_total
        current_balance = max(current_balance - principal_component, 0)
        interest_total += interest
        months += 1

    return months, interest_total


def _shift_month(target: date, delta_months: int) -> date:
    month_index = (target.year * 12 + target.month - 1) + delta_months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    day = min(target.day, _days_in_month(year, month))
    return date(year, month, day)


def _days_in_month(year: int, month: int) -> int:
    if month == 2:
        leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        return 29 if leap else 28
    if month in {4, 6, 9, 11}:
        return 30
    return 31


def _month_name(year: int, month: int) -> str:
    return date(year, month, 1).strftime("%b")


def _build_lifestyle_profile(category_distribution: list[dict], debit_total: float, discretionary_ratio: float) -> dict:
    if not category_distribution or debit_total <= 0:
        return {
            "diversity_score": 0.0,
            "concentration_ratio": 0.0,
            "dominant_categories": [],
            "risk_level": "No data",
            "summary": "Lifestyle diversification will appear once Alfred has enough spending history.",
        }

    shares = [item["amount"] / debit_total for item in category_distribution if item["amount"] > 0]
    entropy = -sum(share * log(share) for share in shares if share > 0)
    max_entropy = log(len(shares)) if len(shares) > 1 else 1
    diversity_score = round((entropy / max_entropy) * 100, 1) if max_entropy else 0.0
    concentration_ratio = round((category_distribution[0]["amount"] / debit_total) * 100, 1)

    if concentration_ratio >= 45 or discretionary_ratio >= 0.4:
        risk_level = "High"
    elif concentration_ratio >= 30 or discretionary_ratio >= 0.28:
        risk_level = "Guarded"
    else:
        risk_level = "Stable"

    dominant = [item["label"] for item in category_distribution[:3]]
    summary = (
        f"Top spending concentration is {concentration_ratio:.1f}% in {dominant[0]}. "
        f"Lifestyle diversity score is {diversity_score:.1f}/100 across {len(shares)} active categories."
    )
    return {
        "diversity_score": diversity_score,
        "concentration_ratio": concentration_ratio,
        "dominant_categories": dominant,
        "risk_level": risk_level,
        "summary": summary,
    }


def _series_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return pstdev(values)


def _safe_ratio(value: float, base: float) -> float:
    if not base:
        return 0.0
    return value / base


def _clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))
