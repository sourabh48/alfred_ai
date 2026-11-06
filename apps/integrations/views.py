"""
API Views for Integration module
"""

from django.db.models import Count, Max, Sum
from django.utils.text import slugify
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from alfred_ai.services.materialized_cache import materialize_payload
from apps.expenses.models import Expense
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.family.models import Dependent
from apps.investments.models import Investment
from .models import VerifiedExternalInsight
from .services import verified_intelligence
from .services.verified_intelligence import freshness_snapshot, proof_contract_payload
from apps.loans.models import Loan
from apps.loans.money import loan_money_float
from apps.ml_engine.services.recommendation_engine import recommendation_engine
from apps.ml_engine.services.tax_optimizer import tax_optimizer
from apps.ml_engine.services.tax_policy import POLICY_VERSION, TaxPolicyError, amount, get_policy, policy_coverage


def _query_float(request, key, default):
    value = request.query_params.get(key)
    if value in (None, ""):
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _request_params_token(request, keys) -> str:
    return ":".join(f"{key}={request.query_params.get(key, '')}" for key in keys)


def _integration_dashboard_revision(user) -> str:
    expense_meta = Expense.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_date=Max("transaction_date"),
        total_amount=Sum("amount"),
    )
    loan_meta = Loan.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_update=Max("updated_at"),
        total_balance=Sum("remaining_balance"),
    )
    investment_meta = Investment.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_update=Max("updated_at"),
        total_value=Sum("current_value"),
    )
    dependent_meta = Dependent.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"))
    evidence_meta = VerifiedExternalInsight.objects.filter(is_active=True).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_verified=Max("verified_at"),
    )
    profile_token = ":".join(
        str(value or "")
        for value in (
            getattr(user, "age", ""),
            getattr(user, "city", ""),
            getattr(user, "city_type", ""),
            getattr(user, "monthly_income", ""),
            getattr(user, "monthly_income_basis", ""),
            getattr(user, "rent_or_emi", ""),
            getattr(user, "income_currency", ""),
            getattr(user, "rent_currency", ""),
        )
    )
    return "|".join(
        str(value or "")
        for value in (
            "integrations-dashboard-v3",
            expense_meta["count"],
            expense_meta["max_id"],
            expense_meta["latest_date"],
            expense_meta["total_amount"],
            loan_meta["count"],
            loan_meta["max_id"],
            loan_meta["latest_update"],
            loan_meta["total_balance"],
            investment_meta["count"],
            investment_meta["max_id"],
            investment_meta["latest_update"],
            investment_meta["total_value"],
            dependent_meta["count"],
            dependent_meta["max_id"],
            evidence_meta["count"],
            evidence_meta["max_id"],
            evidence_meta["latest_verified"],
            profile_token,
        )
    )


def _metro_city(city: str) -> bool:
    return slugify(city or "") in {"mumbai", "delhi", "new-delhi", "bangalore", "bengaluru", "chennai", "hyderabad", "kolkata"}


def _dedupe_evidence(items):
    seen = set()
    result = []
    for item in items or []:
        if not item:
            continue
        key = (
            item.get("source_url", ""),
            item.get("verified_at", ""),
            item.get("title", "") or item.get("source_name", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _proof_contract_payload(*, evidence_items, freshness, required_sources=None):
    return proof_contract_payload(
        evidence_items=evidence_items,
        freshness=freshness,
        required_sources=required_sources,
    )


def _grounding_payload(*, history, evidence=None, notes=None, required_sources=None):
    evidence_items = _dedupe_evidence(evidence or [])
    freshness = freshness_snapshot(evidence_items)
    return {
        "history": history,
        "evidence": evidence_items,
        "freshness": freshness,
        "proof_contract": _proof_contract_payload(
            evidence_items=evidence_items,
            freshness=freshness,
            required_sources=required_sources,
        ),
        "notes": notes or [],
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def recommendation_overview(request):
    """Expose product recommendation engines to the frontend dashboard."""
    revision = "|".join(
        (
            _integration_dashboard_revision(request.user),
            _request_params_token(request, ["investment_amount", "time_horizon"]),
        )
    )
    payload = materialize_payload(
        namespace="recommendation-overview",
        user_id=request.user.id,
        revision=revision,
        ttl_seconds=120,
        builder=lambda: _build_recommendation_overview_payload(request),
    )
    return Response(payload)


def _build_recommendation_overview_payload(request) -> dict:
    """Build product recommendation engines for the frontend dashboard."""
    investment_amount = _query_float(request, "investment_amount", 0)
    time_horizon = request.query_params.get("time_horizon", "long_term")
    market = verified_intelligence.market_snapshot()
    inflation = verified_intelligence.world_bank_indicator("FP.CPI.TOTL.ZG", "India inflation rate")
    profile = recommendation_engine.build_user_profile(request.user)
    financial_baseline = profile.get("financial_baseline", {})
    investments = recommendation_engine.recommend_investments(
        request.user,
        investment_amount=investment_amount or None,
        time_horizon=time_horizon,
    )
    insurance = recommendation_engine.recommend_insurance(request.user)

    investments_grounding = _grounding_payload(
        history={
            "monthly_income": round(profile.get("income", 0), 2),
            "monthly_expenses": round(profile.get("monthly_expenses", 0), 2),
            "monthly_savings": round(profile.get("monthly_savings", 0), 2),
            "savings_rate": round(profile.get("savings_rate", 0), 2),
            "risk_appetite": profile.get("risk_appetite", ""),
            "available_amount": round(investments.get("your_profile", {}).get("available_amount", 0), 2),
            "time_horizon": investments.get("your_profile", {}).get("time_horizon", time_horizon),
            "recommendation_count": len(investments.get("recommendations", [])),
        },
        evidence=[market.evidence, inflation.evidence],
        required_sources=["Yahoo Finance", "World Bank"],
        notes=[
            "Investment matching is grounded in your savings capacity, persona, and risk appetite, then contextualized with verified market and inflation evidence.",
            "External evidence shapes market posture and real-return context, not a guarantee that any product will outperform.",
        ],
    )
    insurance_grounding = _grounding_payload(
        history={
            "monthly_income": round(profile.get("income", 0), 2),
            "dependents": int(profile.get("dependents", 0) or 0),
            "age": int(profile.get("age", 0) or 0),
            "essential_recommendations": sum(1 for item in insurance.get("recommendations", []) if item.get("is_essential")),
            "total_annual_premium": round(insurance.get("total_annual_premium", 0), 2),
        },
        evidence=[inflation.evidence],
        required_sources=["World Bank"],
        notes=[
            "Insurance matching is grounded in household dependence, age, and affordability. Verified inflation evidence is attached only as protection-cost context.",
            "Coverage suggestions remain planning guidance, not insurer underwriting approval or premium quotes.",
        ],
    )
    credit_cards_grounding = _grounding_payload(
        history={
            "monthly_income": round(profile.get("income", 0), 2),
            "monthly_expenses": round(profile.get("monthly_expenses", 0), 2),
            "savings_rate": round(profile.get("savings_rate", 0), 2),
            "dti_ratio": round(profile.get("dti_ratio", 0), 2),
            "policy_state": "disabled",
        },
        evidence=[inflation.evidence],
        required_sources=["World Bank"],
        notes=[
            "Credit-card recommendations are intentionally disabled for this workspace, so no card ranking or acquisition advice is produced.",
            "The evidence contract is retained to distinguish a policy suppression from missing user data.",
        ],
    )
    personal_loans_grounding = _grounding_payload(
        history={
            "monthly_income": round(profile.get("income", 0), 2),
            "recurring_emi_burden": round(financial_baseline.get("recurring_emi_burden", 0), 2),
            "debt_burden_ratio": round(profile.get("dti_ratio", 0), 2),
            "liquid_runway_months": round(financial_baseline.get("liquid_runway_months", 0), 2),
            "policy_state": "disabled",
        },
        evidence=[market.evidence, inflation.evidence],
        required_sources=["Yahoo Finance", "World Bank"],
        notes=[
            "Personal-loan recommendations are intentionally disabled for this workspace, so no borrowing shortlist is produced.",
            "Market and inflation evidence is attached only to document the suppressed decision context.",
        ],
    )
    investments = {**investments, "grounding": investments_grounding}
    insurance = {**insurance, "grounding": insurance_grounding}
    combined_evidence = _dedupe_evidence(
        [
            *investments_grounding["evidence"],
            *insurance_grounding["evidence"],
            *credit_cards_grounding["evidence"],
            *personal_loans_grounding["evidence"],
        ]
    )
    combined_freshness = freshness_snapshot(combined_evidence)

    return {
        "profile": profile,
        "financial_baseline": financial_baseline,
        "credit_cards": {
            "enabled": False,
            "recommendations": [],
            "message": "Credit card suggestions are disabled for this workspace.",
            "grounding": credit_cards_grounding,
        },
        "loans": {
            "enabled": False,
            "recommendations": [],
            "message": "Personal loan suggestions are disabled for this workspace.",
            "grounding": personal_loans_grounding,
        },
        "investments": investments,
        "insurance": insurance,
        "disabled_modules": [
            {"key": "credit_cards", "label": "Credit cards", "reason": "Suppressed by product preference for this workspace."},
            {"key": "personal_loans", "label": "Personal loans", "reason": "Suppressed by product preference for this workspace."},
        ],
        "grounding": {
            "history": {
                "monthly_income": profile.get("income", 0),
                "monthly_expenses": round(profile.get("monthly_expenses", 0), 2),
                "savings_rate": round(profile.get("savings_rate", 0), 2),
                "dti_ratio": round(profile.get("dti_ratio", 0), 2),
                "tracked_personas": profile.get("persona", []),
            },
            "evidence": combined_evidence,
            "freshness": combined_freshness,
            "proof_contract": _proof_contract_payload(
                evidence_items=combined_evidence,
                freshness=combined_freshness,
                required_sources=["Yahoo Finance", "World Bank"],
            ),
            "modules": [
                {
                    "key": "investments",
                    "label": "Investment stack",
                    "freshness": investments_grounding["freshness"],
                    "evidence_count": len(investments_grounding["evidence"]),
                },
                {
                    "key": "insurance",
                    "label": "Insurance coverage",
                    "freshness": insurance_grounding["freshness"],
                    "evidence_count": len(insurance_grounding["evidence"]),
                },
                {
                    "key": "credit_cards",
                    "label": "Credit cards",
                    "freshness": credit_cards_grounding["freshness"],
                    "evidence_count": len(credit_cards_grounding["evidence"]),
                    "status": "disabled",
                },
                {
                    "key": "personal_loans",
                    "label": "Personal loans",
                    "freshness": personal_loans_grounding["freshness"],
                    "evidence_count": len(personal_loans_grounding["evidence"]),
                    "status": "disabled",
                },
            ],
            "notes": [
                "Recommendations are grounded in current user history plus verified external market context where relevant.",
                "Product matching is still rule-driven and evidence-blended, not a claim of institution-approved suitability.",
            ],
        },
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tax_optimizer_overview(request):
    """Return a dated planning estimate; reject unsupported years explicitly."""
    try:
        get_policy(financial_year=request.query_params.get("financial_year"),
                   assessment_year=request.query_params.get("assessment_year"))
        for key in ("annual_income", "basic_salary", "hra_received", "rent_paid"):
            if key in request.query_params:
                amount(request.query_params[key], key.replace("_", " ").capitalize())
    except TaxPolicyError as exc:
        return Response({"error": str(exc)}, status=400)
    revision = "|".join(
        (
            POLICY_VERSION,
            _integration_dashboard_revision(request.user),
            _request_params_token(request, ["annual_income", "basic_salary", "hra_received", "rent_paid", "metro", "financial_year", "assessment_year"]),
        )
    )
    payload = materialize_payload(
        namespace="tax-optimizer-overview",
        user_id=request.user.id,
        revision=revision,
        ttl_seconds=120,
        builder=lambda: _build_tax_optimizer_overview_payload(request),
    )
    return Response(payload)


def _build_tax_optimizer_overview_payload(request) -> dict:
    """Build a user-ready tax dashboard based on current profile defaults."""
    policy = get_policy(financial_year=request.query_params.get("financial_year"),
                        assessment_year=request.query_params.get("assessment_year"))
    financial_baseline = resolve_canonical_financial_baseline(request.user)
    annual_income = amount(request.query_params.get("annual_income", financial_baseline.get("confirmed_annual_income", 0) or 0), "Annual income")
    deductions = tax_optimizer._calculate_current_deductions(request.user, financial_year=policy.financial_year)
    basic_salary = _query_float(request, "basic_salary", annual_income / 24 if annual_income else 0)
    hra_received = _query_float(request, "hra_received", basic_salary * 0.4)
    rent_paid = _query_float(request, "rent_paid", financial_baseline.get("rent_burden", 0) or basic_salary * 0.45)
    metro_city = request.query_params.get("metro")
    if metro_city is None:
        metro_city = _metro_city(getattr(request.user, "city", ""))
    else:
        metro_city = str(metro_city).lower() in {"1", "true", "yes", "on"}

    home_loan = Loan.objects.filter(user=request.user, loan_type="home", is_active=True, verification_status="confirmed").in_rupee_totals().order_by("-id").first()
    home_loan_benefits = None
    if home_loan:
        annual_emi = loan_money_float(home_loan.emi or 0) * 12
        estimated_interest = min(
            annual_emi,
            (loan_money_float(home_loan.remaining_balance or home_loan.principal or 0) * (home_loan.interest_rate or 0) / 100),
        )
        principal_paid = max(annual_emi - estimated_interest, 0)
        home_loan_benefits = tax_optimizer.calculate_home_loan_benefits(
            loan_principal_paid=principal_paid,
            loan_interest_paid=estimated_interest,
            is_first_home=True,
        )
    tax_regime = verified_intelligence.tax_regime_reference()
    nps_reference = verified_intelligence.nps_tax_reference()
    ppf_reference = verified_intelligence.ppf_reference()
    evidence_items = [tax_regime.evidence, nps_reference.evidence, ppf_reference.evidence]
    evidence_freshness = freshness_snapshot(evidence_items)

    return {
        "annual_income": annual_income,
        "tax_policy": policy.metadata(),
        "tax_policy_coverage": policy_coverage(budget_check=verified_intelligence.stored_budget_publication()),
        "financial_baseline": financial_baseline,
        "inputs": {
            "financial_year": policy.financial_year,
            "assessment_year": policy.assessment_year,
            "annual_income": annual_income,
            "basic_salary": basic_salary,
            "hra_received": hra_received,
            "rent_paid": rent_paid,
            "metro": metro_city,
        },
        "deductions": deductions,
        "regime_comparison": tax_optimizer.compare_regimes(annual_income, deductions, financial_year=policy.financial_year),
        "tax_savings": tax_optimizer.suggest_tax_saving_investments(
            request.user, annual_income=annual_income, deductions=deductions, financial_year=policy.financial_year,
        ),
        "hra": tax_optimizer.calculate_hra_exemption(
            basic_salary=basic_salary,
            hra_received=hra_received,
            rent_paid=rent_paid,
            metro_city=metro_city,
        ),
        "home_loan": home_loan_benefits,
        "deduction_catalog": [
            {
                "section": section,
                "name": value["name"],
                "max_limit": value["max_limit"],
                "instruments": value["instruments"],
            }
            for section, value in tax_optimizer.DEDUCTIONS.items()
        ],
        "tax_evidence": {
            "evidence": evidence_items,
            "freshness": evidence_freshness,
            "proof_contract": proof_contract_payload(
                evidence_items=evidence_items,
                freshness=evidence_freshness,
                required_sources=["Income Tax Department", "India Post", "NPS Trust"],
                advisory_surface="tax_optimizer",
            ),
            "notes": [
                "This scenario assumes a resident individual under 60 with salary income only; review these assumptions before relying on it.",
                "The selected FY/AY is explicit. Other years and special-rate income require separately verified rules.",
                "Tax guidance is grounded in stored user deductions plus official reference sources for regime and instrument treatment.",
                "This overview is still planning guidance, not a substitute for a chartered accountant or filed return review.",
            ],
        },
    }
