from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from math import log
from statistics import mean, pstdev

from django.db.models import Count, Max
from django.utils import timezone

from alfred_ai.services.materialized_cache import materialize_payload
from apps.expenses.models import BankAccount, Expense
from apps.expenses.services.cashflow_treatment import classify_cashflow
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
MONEY_QUANT = Decimal("0.01")
PERCENT_QUANT = Decimal("0.01")

BASELINE_FORMULAS = {
    "monthly_income": "Normalized reliable monthly income from salary credits, reported income, career salary, or observed credit inflow fallback.",
    "annual_income": "monthly_income * 12",
    "recurring_emi_burden": "Sum of active loan EMIs that still report an outstanding balance.",
    "rent_burden": "User-reported monthly rent or housing obligation.",
    "fixed_obligations": "rent_burden + recurring_emi_burden",
    "disposable_cash_flow": "monthly_income - fixed_obligations",
    "observed_average_monthly_variable_spend": "Three-month average of observed non-loan debit outflows.",
    "savings_capacity": "monthly_income - fixed_obligations - observed_average_monthly_variable_spend",
    "liquid_cash": "Positive active non-credit bank balances.",
    "essential_monthly_outflow": "fixed_obligations + observed_average_monthly_variable_spend",
    "liquid_runway_months": "liquid_cash / essential_monthly_outflow",
    "total_assets": "Cash, investments, and recognized asset positions.",
    "total_liabilities": "Open loan, pending foreclosure, credit, and recognized liability positions.",
    "net_worth": "total_assets - total_liabilities",
    "pending_foreclosure_balance": "Foreclosure-pending balances kept in liabilities until closure proof is accepted.",
    "debt_burden_ratio": "fixed_obligations / monthly_income * 100",
}


def build_financial_intelligence(user) -> dict:
    revision = _financial_revision(user)
    return materialize_payload(
        namespace="financial-intelligence",
        user_id=user.id,
        revision=revision,
        ttl_seconds=45,
        builder=lambda: _build_financial_intelligence_uncached(user),
    )


def build_canonical_financial_baseline(user) -> dict:
    revision = _financial_revision(user)
    return materialize_payload(
        namespace="financial-baseline",
        user_id=user.id,
        revision=revision,
        ttl_seconds=45,
        builder=lambda: _build_canonical_financial_baseline_uncached(user),
    )


def resolve_canonical_financial_baseline(user) -> dict:
    payload = build_canonical_financial_baseline(user)
    return {key: value for key, value in payload.items() if key != "_materialized"}


def _build_financial_intelligence_uncached(user) -> dict:
    expenses = list(Expense.objects.filter(user=user).order_by("transaction_date", "id"))
    loans = list(Loan.objects.filter(user=user).order_by("-start_date", "-id"))
    payment_rows = fetch_payment_history_rows(user=user) if loans else []

    intelligence = _empty_intelligence()
    today = timezone.localdate()
    reference_date = max([item.transaction_date for item in expenses], default=today)
    monthly_buckets = _build_monthly_buckets(expenses)
    balance_sheet = _build_balance_sheet(user=user, loans=loans, payment_rows=payment_rows)
    intelligence["balance_sheet"] = balance_sheet
    intelligence["baseline"] = _build_canonical_financial_baseline_uncached(
        user,
        expenses=expenses,
        loans=loans,
        payment_rows=payment_rows,
        balance_sheet=balance_sheet,
        monthly_buckets=monthly_buckets,
        reference_date=reference_date,
    )
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

    current_key = (reference_date.year, reference_date.month)
    previous_date = _shift_month(reference_date, -1)
    previous_key = (previous_date.year, previous_date.month)
    current_bucket = monthly_buckets.get(current_key, _empty_month_bucket())
    previous_bucket = monthly_buckets.get(previous_key, _empty_month_bucket())

    treated_expenses = [(item, classify_cashflow(item)) for item in expenses]
    debit_expenses = [item for item, treatment in treated_expenses if treatment.counts_cashflow_outflow]
    income_entries = [item for item, treatment in treated_expenses if treatment.counts_income]
    debt_entries = [item for item, treatment in treated_expenses if treatment.counts_debt_service]

    income_total = sum(item.amount for item in income_entries)
    debit_total = sum(item.amount for item in debit_expenses)
    expense_total = sum(item.amount for item, treatment in treated_expenses if treatment.counts_direct_expense)
    loan_total = sum(item.amount for item, treatment in treated_expenses if treatment.bucket == "loan")
    other_total = sum(
        item.amount
        for item, treatment in treated_expenses
        if treatment.bucket in {"other", "credit_card_payment", "investment"}
    )
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
    monthly_outflows = [bucket["outflow"] for _, bucket in sorted(monthly_buckets.items())]
    monthly_stress = [
        _build_monthly_stress_score(
            bucket["expense"],
            bucket["loan"] + bucket["credit_card_payment"],
            bucket["other"] + bucket["investment"],
            bucket["income"],
        )
        for _, bucket in sorted(monthly_buckets.items())
    ]
    avg_monthly_outflow = mean(monthly_outflows) if monthly_outflows else 0.0
    volatility_ratio = _safe_ratio(_series_std(monthly_outflows), max(avg_monthly_outflow, 1))
    signature = behavior_signature.generate_signature(monthly_outflows, monthly_stress)
    signature_readability = _humanize_behavior_signature(signature)
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
                "current_month_credit_card_payments": round(current_bucket["credit_card_payment"], 2),
                "current_month_investments": round(current_bucket["investment"], 2),
                "current_month_review_required": round(current_bucket["review_required"], 2),
                "current_month_transfer_in": round(current_bucket["transfer_in"], 2),
                "current_month_transfer_out": round(current_bucket["transfer_out"], 2),
                "current_month_bank_credit": round(current_bucket["bank_credit"], 2),
                "current_month_bank_debit": round(current_bucket["bank_debit"], 2),
                "current_month_outflow": round(current_bucket["outflow"], 2),
                "current_month_net": round(current_bucket["income"] - current_bucket["outflow"], 2),
                "monthly_expense_delta": round(current_bucket["expense"] - previous_bucket["expense"], 2),
                "financial_health_score": round(health_score, 1),
                "stability_score": round(stability_score, 1),
                "discipline_score": round(discipline_score, 1),
                "liquidity_score": round(liquidity_score, 1),
                "stress_score": round(stress_score, 1),
                "financial_stress_score": round(stress_score, 1),
                "risk_level": risk_level,
                "savings_rate": round(savings_rate * 100, 1),
                "observed_savings_rate": round(savings_rate * 100, 1),
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
                "monthly_outflow_values": [round(bucket["outflow"], 2) for _, bucket in sorted(monthly_buckets.items())],
                "monthly_bank_debit_values": [round(bucket["bank_debit"], 2) for _, bucket in sorted(monthly_buckets.items())],
                "monthly_bank_credit_values": [round(bucket["bank_credit"], 2) for _, bucket in sorted(monthly_buckets.items())],
                "monthly_transfer_in_values": [round(bucket["transfer_in"], 2) for _, bucket in sorted(monthly_buckets.items())],
                "monthly_transfer_out_values": [round(bucket["transfer_out"], 2) for _, bucket in sorted(monthly_buckets.items())],
                "monthly_credit_card_payment_values": [round(bucket["credit_card_payment"], 2) for _, bucket in sorted(monthly_buckets.items())],
                "monthly_investment_values": [round(bucket["investment"], 2) for _, bucket in sorted(monthly_buckets.items())],
                "monthly_review_required_values": [round(bucket["review_required"], 2) for _, bucket in sorted(monthly_buckets.items())],
                "category_labels": [item["label"] for item in category_distribution],
                "category_values": [item["amount"] for item in category_distribution],
                "debt_labels": debt_trend["labels"],
                "debt_values": debt_trend["values"],
            },
            "behavior": {
                "personality": personality,
                "coach_tone": tone,
                "signature": signature,
                "signature_readability": signature_readability,
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
            "loan_portfolio": _build_loan_portfolio(loans, debt_entries, current_bucket, payment_rows=payment_rows),
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
    from apps.career.models import CareerProfile, CareerResume

    expense_meta = Expense.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_date=Max("transaction_date"))
    loan_meta = Loan.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_updated=Max("updated_at"))
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
    career_profile_meta = CareerProfile.objects.filter(user=user).aggregate(count=Count("id"), max_last_salary=Max("last_salary"))
    career_resume_meta = CareerResume.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_updated=Max("updated_at"))
    return "|".join(
        str(value or "")
        for value in [
            user.monthly_income, user.variable_income, user.rent_or_emi, user.city,
            expense_meta["count"], expense_meta["max_id"], expense_meta["max_date"],
            loan_meta["count"], loan_meta["max_id"], loan_meta["max_updated"],
            payment_meta["count"], payment_meta["max_id"], payment_meta["max_date"], payment_meta["max_created"],
            account_meta["count"], account_meta["max_id"], account_meta["max_sync"],
            investment_meta["count"], investment_meta["max_id"],
            foreclosure_meta["count"], foreclosure_meta["max_id"], foreclosure_meta["max_updated"],
            credit_meta["count"], credit_meta["max_id"], credit_meta["max_updated"],
            vehicle_meta["count"], vehicle_meta["max_id"], vehicle_meta["max_updated"],
            service_meta["count"], service_meta["max_id"], service_meta["max_date"],
            trip_meta["count"], trip_meta["max_id"], trip_meta["max_date"],
            career_profile_meta["count"], career_profile_meta["max_last_salary"],
            career_resume_meta["count"], career_resume_meta["max_id"], career_resume_meta["max_updated"],
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
            "financial_stress_score": 0.0,
            "risk_level": "No data",
            "savings_rate": 0.0,
            "observed_savings_rate": 0.0,
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
            "signature_readability": {
                "volatility": {
                    "label": "No pattern yet",
                    "summary": "ALFRED needs more months of spending before it can describe how steady your outflow is.",
                },
                "spike_factor": {
                    "label": "No pattern yet",
                    "summary": "ALFRED needs more months of spending before it can explain how sharply your spend jumps.",
                },
            },
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
            "pending_foreclosure_balance": 0.0,
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
            "home_ownership_summary": {
                "positions": 0,
                "financed_asset_value_total": 0.0,
                "property_acquisition_cost_total": 0.0,
                "down_payment_total": 0.0,
                "other_upfront_payments_total": 0.0,
                "upfront_cash_invested_total": 0.0,
                "equity_built_total": 0.0,
                "principal_paid_recorded_total": 0.0,
                "interest_and_cost_paid_recorded_total": 0.0,
            },
            "home_ownership_positions": [],
            "detected_repayments": [],
        },
        "balance_sheet": {
            "total_assets": 0.0,
            "total_liabilities": 0.0,
            "net_worth": 0.0,
            "asset_liability_ratio": 0.0,
            "pending_foreclosure_balance": 0.0,
            "pending_foreclosure_excluded_balance": 0.0,
            "home_loan_asset_proxy_total": 0.0,
            "home_loan_upfront_cash_total": 0.0,
            "assets": [],
            "liabilities": [],
            "home_ownership_positions": [],
            "vehicle_positions": [],
            "summary": "Add account balances, investments, loans, or vehicle profiles to build the balance-sheet view.",
        },
        "baseline": _empty_canonical_financial_baseline(),
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


def _decimal_amount(value) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _decimal_average(values) -> Decimal:
    items = [_decimal_amount(value) for value in values]
    if not items:
        return Decimal("0")
    return (sum(items, Decimal("0")) / Decimal(len(items))).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _money_float(value) -> float:
    return float(_decimal_amount(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))


def _percent_float(value) -> float:
    return float(_decimal_amount(value).quantize(PERCENT_QUANT, rounding=ROUND_HALF_UP))


def _baseline_metric_state(status: str, source: str, formula_key: str, *, inputs: list[str] | None = None, note: str = "") -> dict:
    return {
        "status": status,
        "source": source,
        "formula": BASELINE_FORMULAS.get(formula_key, ""),
        "inputs": inputs or [],
        "note": note,
    }


def _income_metric_status(income_source: str) -> str:
    if income_source == "salary_credits":
        return "observed"
    if income_source in {"reported_annual_ctc", "reported_monthly_income", "career_profile_last_salary"}:
        return "user-reported"
    if income_source == "observed_credit_inflow":
        return "observed"
    return "unavailable"


def _empty_canonical_financial_baseline() -> dict:
    metric_states = {
        key: _baseline_metric_state(
            "unavailable",
            "not_evidenced",
            key,
            note="No reliable source is available yet.",
        )
        for key in BASELINE_FORMULAS
    }
    return {
        "reference_month": timezone.localdate().strftime("%B %Y"),
        "sample_months": 0,
        "monthly_income": 0.0,
        "annual_income": 0.0,
        "income_source": "not_evidenced",
        "income_source_summary": "ALFRED needs salary credits, a reported income baseline, or other credit history before it can set a monthly income baseline.",
        "supplemental_variable_income": 0.0,
        "observed_average_monthly_inflow": 0.0,
        "observed_average_monthly_variable_spend": 0.0,
        "observed_average_monthly_total_outflow": 0.0,
        "current_month_variable_spend": 0.0,
        "current_month_total_outflow": 0.0,
        "recurring_emi_burden": 0.0,
        "rent_burden": 0.0,
        "fixed_obligations": 0.0,
        "debt_burden_ratio": 0.0,
        "disposable_cash_flow": 0.0,
        "savings_capacity": 0.0,
        "savings_rate": 0.0,
        "baseline_savings_rate": 0.0,
        "savings_capacity_rate": 0.0,
        "liquid_cash": 0.0,
        "essential_monthly_outflow": 0.0,
        "liquid_runway_months": 0.0,
        "pending_foreclosure_balance": 0.0,
        "total_assets": 0.0,
        "total_liabilities": 0.0,
        "net_worth": 0.0,
        "asset_liability_ratio": 0.0,
        "baseline_formulas": BASELINE_FORMULAS,
        "metric_states": metric_states,
        "metric_provenance": metric_states,
    }


def _build_canonical_financial_baseline_uncached(
    user,
    *,
    expenses: list[Expense] | None = None,
    loans: list[Loan] | None = None,
    payment_rows: list[dict] | None = None,
    balance_sheet: dict | None = None,
    monthly_buckets: dict[tuple[int, int], dict] | None = None,
    reference_date: date | None = None,
) -> dict:
    from apps.career.models import CareerProfile, CareerResume
    from apps.career.services import build_employment_income_signals

    expenses = list(expenses) if expenses is not None else list(Expense.objects.filter(user=user).order_by("transaction_date", "id"))
    loans = list(loans) if loans is not None else list(Loan.objects.filter(user=user).order_by("-start_date", "-id"))
    payment_rows = list(payment_rows or [])
    if loans and not payment_rows:
        payment_rows = fetch_payment_history_rows(user=user)

    today = timezone.localdate()
    resolved_reference_date = reference_date or max([item.transaction_date for item in expenses], default=today)
    monthly_buckets = monthly_buckets or _build_monthly_buckets(expenses)
    recent_month_keys = sorted(monthly_buckets.keys())[-3:]
    recent_buckets = [monthly_buckets[key] for key in recent_month_keys]
    current_key = (resolved_reference_date.year, resolved_reference_date.month)
    current_bucket = monthly_buckets.get(current_key, _empty_month_bucket())

    observed_average_monthly_inflow_amount = _decimal_average(bucket["income"] for bucket in recent_buckets)
    observed_average_monthly_variable_spend_amount = _decimal_average(
        (_decimal_amount(bucket["expense"]) + _decimal_amount(bucket["other"])) for bucket in recent_buckets
    )
    observed_average_monthly_total_outflow_amount = _decimal_average(
        _decimal_amount(bucket["outflow"]) for bucket in recent_buckets
    )
    current_month_variable_spend_amount = _decimal_amount(current_bucket["expense"]) + _decimal_amount(current_bucket["other"])
    current_month_total_outflow_amount = _decimal_amount(current_bucket["outflow"])

    profile = CareerProfile.objects.filter(user=user).first()
    latest_resume = CareerResume.objects.filter(user=user).order_by("-updated_at", "-id").first()
    income_signals = build_employment_income_signals(user=user, latest_resume=latest_resume, profile=profile)

    reported_income = income_signals.get("reported_income", {}) or {}
    salary_signal = income_signals.get("salary_credit_signal") or {}
    profile_last_salary = _decimal_amount(getattr(profile, "last_salary", 0) or 0)
    monthly_income_amount = _decimal_amount(income_signals.get("monthly_cash_income", 0) or 0)
    income_source = "not_evidenced"
    income_source_summary = income_signals.get("source_summary") or ""
    if salary_signal:
        income_source = "salary_credits"
    elif _decimal_amount(reported_income.get("value", 0) or 0) > 0:
        income_source = "reported_annual_ctc" if reported_income.get("mode") == "annual_ctc" else "reported_monthly_income"
    elif profile_last_salary > 0:
        income_source = "career_profile_last_salary"
        income_source_summary = "Monthly income falls back to the last salary stored in the career profile because stronger salary signals are not available yet."
    elif observed_average_monthly_inflow_amount > 0:
        monthly_income_amount = observed_average_monthly_inflow_amount
        income_source = "observed_credit_inflow"
        income_source_summary = "Monthly income falls back to the recent average of observed credit inflows because a cleaner salary signal is not evidenced yet."

    monthly_income_amount = monthly_income_amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    annual_income_amount = (monthly_income_amount * Decimal("12")).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    supplemental_variable_income_amount = _decimal_amount(income_signals.get("variable_income", 0) or 0).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    rent_burden_amount = _decimal_amount(getattr(user, "rent_or_emi", 0) or 0).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    recurring_emi_burden_amount = Decimal("0")
    for loan in loans:
        balance = _loan_reporting_balance(loan, today=today)
        if _loan_counts_toward_recurring_emi(loan, balance):
            recurring_emi_burden_amount += _decimal_amount(loan.emi or 0)
    recurring_emi_burden_amount = recurring_emi_burden_amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    fixed_obligations_amount = (rent_burden_amount + recurring_emi_burden_amount).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    disposable_cash_flow_amount = (monthly_income_amount - fixed_obligations_amount).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    savings_capacity_amount = (
        monthly_income_amount - fixed_obligations_amount - observed_average_monthly_variable_spend_amount
    ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    savings_rate_amount = (
        (savings_capacity_amount / monthly_income_amount * Decimal("100")).quantize(PERCENT_QUANT, rounding=ROUND_HALF_UP)
        if monthly_income_amount > 0
        else Decimal("0")
    )
    debt_burden_ratio_amount = (
        (fixed_obligations_amount / monthly_income_amount * Decimal("100")).quantize(PERCENT_QUANT, rounding=ROUND_HALF_UP)
        if monthly_income_amount > 0
        else Decimal("0")
    )

    accounts = list(BankAccount.objects.filter(user=user, is_active=True))
    liquid_cash_amount = sum(
        (
            max(_decimal_amount(account.current_balance or 0), Decimal("0"))
            for account in accounts
            if account.account_type != "credit"
        ),
        Decimal("0"),
    ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    essential_monthly_outflow_amount = (fixed_obligations_amount + observed_average_monthly_variable_spend_amount).quantize(
        MONEY_QUANT,
        rounding=ROUND_HALF_UP,
    )
    liquid_runway_months_amount = (
        (liquid_cash_amount / essential_monthly_outflow_amount).quantize(PERCENT_QUANT, rounding=ROUND_HALF_UP)
        if essential_monthly_outflow_amount > 0
        else Decimal("0")
    )

    resolved_balance_sheet = balance_sheet or _build_balance_sheet(user=user, loans=loans, payment_rows=payment_rows)
    pending_foreclosure_balance_amount = _decimal_amount(
        resolved_balance_sheet.get("pending_foreclosure_balance", resolved_balance_sheet.get("pending_foreclosure_excluded_balance", 0)) or 0
    ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    total_assets_amount = _decimal_amount(resolved_balance_sheet.get("total_assets", 0) or 0).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    total_liabilities_amount = _decimal_amount(resolved_balance_sheet.get("total_liabilities", 0) or 0).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    net_worth_amount = (total_assets_amount - total_liabilities_amount).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    asset_liability_ratio_amount = (
        (total_assets_amount / total_liabilities_amount).quantize(PERCENT_QUANT, rounding=ROUND_HALF_UP)
        if total_liabilities_amount > 0
        else Decimal("0")
    )
    income_status = _income_metric_status(income_source)
    observed_status = "observed" if recent_buckets else "unavailable"
    balance_status = "derived" if total_assets_amount or total_liabilities_amount else "unavailable"
    liquid_status = "observed" if accounts else "unavailable"
    metric_states = {
        "monthly_income": _baseline_metric_state(
            income_status,
            income_source,
            "monthly_income",
            inputs=["salary_credits", "reported_income", "career_profile_last_salary", "observed_credit_inflow"],
            note=income_source_summary,
        ),
        "annual_income": _baseline_metric_state(
            "derived" if monthly_income_amount > 0 else "unavailable",
            "canonical_monthly_income",
            "annual_income",
            inputs=["monthly_income"],
        ),
        "recurring_emi_burden": _baseline_metric_state(
            "derived",
            "active_loans",
            "recurring_emi_burden",
            inputs=["loan.emi", "loan.status", "loan.remaining_balance"],
        ),
        "rent_burden": _baseline_metric_state(
            "user-reported" if rent_burden_amount > 0 else "unavailable",
            "user.rent_or_emi",
            "rent_burden",
            inputs=["user.rent_or_emi"],
        ),
        "fixed_obligations": _baseline_metric_state(
            "derived",
            "canonical_baseline",
            "fixed_obligations",
            inputs=["rent_burden", "recurring_emi_burden"],
        ),
        "disposable_cash_flow": _baseline_metric_state(
            "derived" if monthly_income_amount > 0 else "unavailable",
            "canonical_baseline",
            "disposable_cash_flow",
            inputs=["monthly_income", "fixed_obligations"],
        ),
        "observed_average_monthly_variable_spend": _baseline_metric_state(
            observed_status,
            "recent_transaction_history",
            "observed_average_monthly_variable_spend",
            inputs=["expense.direct_debit", "expense.uncategorized_cashflow_debit"],
            note="Transfers, investments, card settlements, and review-gated large other debits are separated from variable living spend.",
        ),
        "savings_capacity": _baseline_metric_state(
            "derived" if monthly_income_amount > 0 and recent_buckets else "unavailable",
            "canonical_baseline",
            "savings_capacity",
            inputs=["monthly_income", "fixed_obligations", "observed_average_monthly_variable_spend"],
            note="Unavailable when income or observed spend history is missing; numeric zero is kept for backward-compatible clients.",
        ),
        "liquid_cash": _baseline_metric_state(
            liquid_status,
            "active_bank_accounts",
            "liquid_cash",
            inputs=["bank_account.current_balance", "bank_account.account_type"],
        ),
        "essential_monthly_outflow": _baseline_metric_state(
            "derived" if essential_monthly_outflow_amount > 0 else "unavailable",
            "canonical_baseline",
            "essential_monthly_outflow",
            inputs=["fixed_obligations", "observed_average_monthly_variable_spend"],
        ),
        "liquid_runway_months": _baseline_metric_state(
            "derived" if essential_monthly_outflow_amount > 0 and accounts else "unavailable",
            "canonical_baseline",
            "liquid_runway_months",
            inputs=["liquid_cash", "essential_monthly_outflow"],
        ),
        "pending_foreclosure_balance": _baseline_metric_state(
            "derived" if pending_foreclosure_balance_amount > 0 else "unavailable",
            "loan_balance_sheet",
            "pending_foreclosure_balance",
            inputs=["loan.status", "loan.remaining_balance"],
        ),
        "total_assets": _baseline_metric_state(
            balance_status,
            "balance_sheet",
            "total_assets",
            inputs=["bank_accounts", "investments", "recognized_asset_positions"],
        ),
        "total_liabilities": _baseline_metric_state(
            balance_status,
            "balance_sheet",
            "total_liabilities",
            inputs=["active_loans", "pending_foreclosures", "credit_balances", "recognized_liability_positions"],
        ),
        "net_worth": _baseline_metric_state(
            "derived" if total_assets_amount or total_liabilities_amount else "unavailable",
            "balance_sheet",
            "net_worth",
            inputs=["total_assets", "total_liabilities"],
        ),
        "debt_burden_ratio": _baseline_metric_state(
            "derived" if monthly_income_amount > 0 else "unavailable",
            "canonical_baseline",
            "debt_burden_ratio",
            inputs=["fixed_obligations", "monthly_income"],
        ),
    }
    return {
        "reference_month": resolved_reference_date.strftime("%B %Y"),
        "sample_months": len(recent_buckets),
        "monthly_income": _money_float(monthly_income_amount),
        "annual_income": _money_float(annual_income_amount),
        "income_source": income_source,
        "income_source_summary": income_source_summary or _empty_canonical_financial_baseline()["income_source_summary"],
        "supplemental_variable_income": _money_float(supplemental_variable_income_amount),
        "observed_average_monthly_inflow": _money_float(observed_average_monthly_inflow_amount),
        "observed_average_monthly_variable_spend": _money_float(observed_average_monthly_variable_spend_amount),
        "observed_average_monthly_total_outflow": _money_float(observed_average_monthly_total_outflow_amount),
        "current_month_variable_spend": _money_float(current_month_variable_spend_amount),
        "current_month_total_outflow": _money_float(current_month_total_outflow_amount),
        "recurring_emi_burden": _money_float(recurring_emi_burden_amount),
        "rent_burden": _money_float(rent_burden_amount),
        "fixed_obligations": _money_float(fixed_obligations_amount),
        "debt_burden_ratio": _percent_float(debt_burden_ratio_amount),
        "disposable_cash_flow": _money_float(disposable_cash_flow_amount),
        "savings_capacity": _money_float(savings_capacity_amount),
        "savings_rate": _percent_float(savings_rate_amount),
        "baseline_savings_rate": _percent_float(savings_rate_amount),
        "savings_capacity_rate": _percent_float(savings_rate_amount),
        "liquid_cash": _money_float(liquid_cash_amount),
        "essential_monthly_outflow": _money_float(essential_monthly_outflow_amount),
        "liquid_runway_months": _percent_float(liquid_runway_months_amount),
        "pending_foreclosure_balance": _money_float(pending_foreclosure_balance_amount),
        "total_assets": _money_float(total_assets_amount),
        "total_liabilities": _money_float(total_liabilities_amount),
        "net_worth": _money_float(net_worth_amount),
        "asset_liability_ratio": _percent_float(asset_liability_ratio_amount),
        "baseline_formulas": BASELINE_FORMULAS,
        "metric_states": metric_states,
        "metric_provenance": metric_states,
    }


def _build_monthly_buckets(expenses: list[Expense]) -> dict[tuple[int, int], dict]:
    buckets: dict[tuple[int, int], dict] = defaultdict(_empty_month_bucket)

    for item in expenses:
        key = (item.transaction_date.year, item.transaction_date.month)
        bucket = buckets[key]
        treatment = classify_cashflow(item)
        amount = float(item.amount or 0)
        if item.direction == "credit":
            bucket["bank_credit"] += amount
        elif item.direction == "debit":
            bucket["bank_debit"] += amount

        if treatment.bucket == "income":
            bucket["income"] += amount
        elif treatment.bucket == "transfer_in":
            bucket["transfer_in"] += amount
        elif treatment.bucket == "other_credit":
            bucket["other_credit"] += amount
        elif treatment.bucket == "expense":
            bucket["expense"] += amount
        elif treatment.bucket == "loan":
            bucket["loan"] += amount
        elif treatment.bucket == "credit_card_payment":
            bucket["credit_card_payment"] += amount
        elif treatment.bucket == "investment":
            bucket["investment"] += amount
        elif treatment.bucket == "transfer_out":
            bucket["transfer_out"] += amount
        elif treatment.bucket == "review_required":
            bucket["review_required"] += amount
        else:
            bucket["other"] += amount
        if treatment.counts_cashflow_outflow:
            bucket["outflow"] += amount
        bucket["count"] += 1

    return buckets


def _empty_month_bucket() -> dict:
    return {
        "income": 0.0,
        "transfer_in": 0.0,
        "other_credit": 0.0,
        "bank_credit": 0.0,
        "expense": 0.0,
        "loan": 0.0,
        "credit_card_payment": 0.0,
        "investment": 0.0,
        "transfer_out": 0.0,
        "other": 0.0,
        "review_required": 0.0,
        "bank_debit": 0.0,
        "outflow": 0.0,
        "count": 0,
    }


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


def _build_loan_portfolio(loans: list[Loan], debt_entries: list[Expense], current_bucket: dict, *, payment_rows: list[dict] | None = None) -> dict:
    manual_loans = _serialize_loans(loans, timezone.localdate())
    active_manual_loans = [item for item in manual_loans if item["is_active"]]
    liability_manual_loans = [item for item in manual_loans if item["counts_toward_liabilities"]]
    pending_manual_loans = [item for item in liability_manual_loans if item["status"] == "foreclosure_pending"]
    total_outstanding = sum(item["estimated_balance"] for item in liability_manual_loans)
    total_emi = sum(item["emi"] for item in active_manual_loans)
    interest_remaining = sum(item["interest_remaining"] for item in active_manual_loans)
    pending_foreclosure_balance = round(sum(item["estimated_balance"] for item in pending_manual_loans), 2)
    current_month_repayment = current_bucket["loan"]
    payment_rows = list(payment_rows or [])
    payment_user = loans[0].user if loans else (debt_entries[0].user if debt_entries else None)
    if payment_user and not payment_rows:
        payment_rows = fetch_payment_history_rows(user=payment_user, include_loan_fields=True)
    expense_reference_ids = {entry.id for entry in debt_entries if entry.id}
    linked_payment_rows = [item for item in payment_rows if item.get("expense_reference_id") in expense_reference_ids]
    linked_payments = {
        item.get("expense_reference_id"): item
        for item in linked_payment_rows
        if item.get("expense_reference_id")
    }
    home_ownership_positions, home_ownership_summary = _build_home_ownership_positions(loans=loans, payment_rows=payment_rows)
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
        "pending_foreclosure_balance": pending_foreclosure_balance,
        "pending_foreclosure_excluded_balance": pending_foreclosure_balance,
        "payment_component_totals": payment_component_totals,
        "foreclosure_pending_count": sum(1 for item in manual_loans if item["status"] == "foreclosure_pending"),
        "reconciled_foreclosures": sum(1 for item in snapshots if item.reconciliation_status == "full_match"),
        "foreclosure_watchlist": foreclosure_watchlist,
        "detected_repayment_total": round(sum(item.amount for item in debt_entries), 2),
        "current_month_repayment": round(current_month_repayment, 2),
        "projected_payoff_months": projected_months,
        "manual_loans": manual_loans,
        "home_ownership_summary": home_ownership_summary,
        "home_ownership_positions": home_ownership_positions,
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
        home_purchase_price = loan.resolved_home_purchase_price
        home_down_payment = loan.resolved_home_down_payment
        home_other_upfront_payments = loan.resolved_home_other_upfront_payments
        home_upfront_cash_invested = loan.resolved_home_upfront_cash_invested
        home_property_acquisition_cost = loan.resolved_home_property_acquisition_cost
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
                "home_purchase_price": home_purchase_price,
                "home_down_payment": home_down_payment,
                "home_other_upfront_payments": home_other_upfront_payments,
                "home_upfront_cash_invested": home_upfront_cash_invested,
                "home_property_acquisition_cost": home_property_acquisition_cost,
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


def _build_balance_sheet(*, user, loans: list[Loan], payment_rows: list[dict] | None = None) -> dict:
    accounts = list(BankAccount.objects.filter(user=user, is_active=True))
    investments = list(Investment.objects.filter(user=user))
    vehicle_profiles = list(BikeProfile.objects.filter(user=user))
    vehicle_services = list(BikeServiceRecord.objects.filter(user=user).select_related("bike_profile"))
    trip_logs = list(TripLog.objects.filter(user=user).select_related("travel_plan", "travel_plan__vehicle_profile"))
    payment_rows = list(payment_rows or [])
    if loans and not payment_rows:
        payment_rows = fetch_payment_history_rows(user=user)

    liquid_cash = round(sum(max(account.current_balance or 0, 0) for account in accounts if account.account_type != "credit"), 2)
    credit_liability = round(sum(abs(account.current_balance or 0) for account in accounts if account.account_type == "credit"), 2)
    investment_assets = round(sum(item.current_value or 0 for item in investments), 2)
    home_ownership_positions, home_ownership_summary = _build_home_ownership_positions(loans=loans, payment_rows=payment_rows)
    home_loan_asset_proxy_total = round(home_ownership_summary["property_acquisition_cost_total"], 2)
    home_loan_upfront_cash_total = round(home_ownership_summary["upfront_cash_invested_total"], 2)
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
    if home_loan_asset_proxy_total:
        assets.append({"label": "Home property acquisition-cost base (proxy)", "amount": home_loan_asset_proxy_total})
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
        if home_loan_asset_proxy_total:
            summary = (
                f"{summary} Home-property acquisition cost of INR {home_loan_asset_proxy_total:,.0f} is shown as a conservative proxy, "
                f"including tracked upfront cash of INR {home_loan_upfront_cash_total:,.0f}. "
                "This still excludes appreciation and sale value unless you track them separately."
            )
    else:
        summary = "Add account balances, investments, loans, or vehicle profiles to build the balance-sheet view."

    return {
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": net_worth,
        "asset_liability_ratio": ratio,
        "pending_foreclosure_balance": pending_foreclosure_balance,
        "pending_foreclosure_excluded_balance": pending_foreclosure_balance,
        "home_loan_asset_proxy_total": home_loan_asset_proxy_total,
        "home_loan_upfront_cash_total": home_loan_upfront_cash_total,
        "assets": assets,
        "liabilities": liabilities,
        "home_ownership_positions": home_ownership_positions,
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


def _loan_counts_toward_recurring_emi(loan: Loan, estimated_balance: float) -> bool:
    if round(float(estimated_balance or 0), 2) <= 0:
        return False
    if loan.status in {"foreclosed", "closed", "prepaid", "foreclosure_pending"}:
        return False
    return bool(loan.is_active and float(loan.emi or 0) > 0)


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


def _build_home_ownership_positions(*, loans: list[Loan], payment_rows: list[dict]) -> tuple[list[dict], dict]:
    today = timezone.localdate()
    payment_totals_by_loan: dict[int, dict[str, float]] = defaultdict(
        lambda: {
            "principal_paid": 0.0,
            "interest_and_cost_paid": 0.0,
        }
    )
    for item in payment_rows:
        loan_id = item.get("loan_id")
        if not loan_id:
            continue
        payment_totals_by_loan[loan_id]["principal_paid"] += float(item.get("principal_paid") or item.get("principal_component") or 0)
        payment_totals_by_loan[loan_id]["interest_and_cost_paid"] += (
            float(item.get("interest_paid") or item.get("interest_component") or 0)
            + float(item.get("charges_paid") or 0)
            + float(item.get("penalties_paid") or 0)
            + float(item.get("tax_paid") or 0)
        )

    positions = []
    for loan in loans:
        if loan.loan_type != "home" or loan.status in {"foreclosed", "defaulted"}:
            continue
        financed_asset_value = round(max(float(loan.principal or 0), 0), 2)
        purchase_price = loan.resolved_home_purchase_price
        down_payment = loan.resolved_home_down_payment
        other_upfront_payments = loan.resolved_home_other_upfront_payments
        upfront_cash_invested = loan.resolved_home_upfront_cash_invested
        property_acquisition_cost = loan.resolved_home_property_acquisition_cost
        if property_acquisition_cost <= 0:
            continue
        current_loan_balance = _loan_reporting_balance(loan, today=today)
        estimated_principal_repaid = round(max(financed_asset_value - current_loan_balance, 0), 2)
        equity_built = round(max(upfront_cash_invested + estimated_principal_repaid, 0), 2)
        recorded = payment_totals_by_loan.get(loan.id, {})
        principal_paid_recorded = round(float(recorded.get("principal_paid") or 0), 2)
        interest_and_cost_paid_recorded = round(float(recorded.get("interest_and_cost_paid") or 0), 2)
        ownership_progress_pct = round((equity_built / property_acquisition_cost) * 100, 1) if property_acquisition_cost else 0.0
        positions.append(
            {
                "loan_id": loan.id,
                "lender": loan.lender,
                "loan_account_number": loan.loan_account_number,
                "status": loan.status,
                "status_label": loan.get_status_display(),
                "monthly_emi": round(float(loan.emi or 0), 2),
                "financed_asset_value": financed_asset_value,
                "purchase_price": purchase_price,
                "property_acquisition_cost": property_acquisition_cost,
                "down_payment": down_payment,
                "other_upfront_payments": other_upfront_payments,
                "upfront_cash_invested": upfront_cash_invested,
                "current_loan_balance": round(current_loan_balance, 2),
                "equity_built": equity_built,
                "estimated_principal_repaid": estimated_principal_repaid,
                "ownership_progress_pct": ownership_progress_pct,
                "principal_paid_recorded": principal_paid_recorded,
                "interest_and_cost_paid_recorded": interest_and_cost_paid_recorded,
                "insight": (
                    f"Property acquisition cost proxy is INR {property_acquisition_cost:,.0f}, including "
                    f"upfront cash of INR {upfront_cash_invested:,.0f} "
                    f"against a purchase-price base of INR {purchase_price:,.0f}. "
                    f"Estimated owner equity built is INR {equity_built:,.0f}; recorded non-equity borrowing cost is INR {interest_and_cost_paid_recorded:,.0f}."
                ),
            }
        )

    summary = {
        "positions": len(positions),
        "financed_asset_value_total": round(sum(item["financed_asset_value"] for item in positions), 2),
        "purchase_price_total": round(sum(item["purchase_price"] for item in positions), 2),
        "property_acquisition_cost_total": round(sum(item["property_acquisition_cost"] for item in positions), 2),
        "down_payment_total": round(sum(item["down_payment"] for item in positions), 2),
        "other_upfront_payments_total": round(sum(item["other_upfront_payments"] for item in positions), 2),
        "upfront_cash_invested_total": round(sum(item["upfront_cash_invested"] for item in positions), 2),
        "equity_built_total": round(sum(item["equity_built"] for item in positions), 2),
        "principal_paid_recorded_total": round(sum(item["principal_paid_recorded"] for item in positions), 2),
        "interest_and_cost_paid_recorded_total": round(sum(item["interest_and_cost_paid_recorded"] for item in positions), 2),
    }
    return positions, summary


def _humanize_behavior_signature(signature: dict) -> dict:
    average_expense = float(signature.get("avg_expense") or 0)
    volatility = float(signature.get("expense_volatility") or 0)
    spike_factor = float(signature.get("spike_factor") or 0)
    volatility_ratio = _safe_ratio(volatility, max(average_expense, 1))
    spike_ratio = _safe_ratio(spike_factor, max(average_expense, 1))

    if volatility_ratio <= 0.15:
        volatility_label = "Very steady"
    elif volatility_ratio <= 0.35:
        volatility_label = "Mostly steady"
    elif volatility_ratio <= 0.6:
        volatility_label = "Noticeable swings"
    else:
        volatility_label = "High swings"

    if spike_ratio <= 0.25:
        spike_label = "Small peaks"
    elif spike_ratio <= 0.55:
        spike_label = "Occasional peaks"
    elif spike_ratio <= 0.9:
        spike_label = "Large peaks"
    else:
        spike_label = "Extreme peaks"

    return {
        "volatility": {
            "label": volatility_label,
            "summary": (
                f"Your monthly spending variation is about {volatility_ratio * 100:.0f}% of a typical month, "
                "so Alfred is describing how smooth or uneven your spending pattern feels."
            ),
        },
        "spike_factor": {
            "label": spike_label,
            "summary": (
                f"Your biggest gap between low-spend and high-spend months is about {spike_ratio * 100:.0f}% of a typical month, "
                "which Alfred uses to explain how sharply your spending can jump."
            ),
        },
    }


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
