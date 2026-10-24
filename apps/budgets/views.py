from collections import defaultdict
from decimal import Decimal

from django.db.models import Count, Max, Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes as perm_classes
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from alfred_ai.services.materialized_cache import materialize_payload
from apps.expenses.models import Expense
from apps.expenses.money import money_float
from apps.expenses.services.cashflow_treatment import variable_spend_rows

from .models import Budget
from .money import allocate_budget
from .serializers import BudgetSerializer


class BudgetListCreateView(ListCreateAPIView):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BudgetDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)


@api_view(['GET'])
@perm_classes([IsAuthenticated])
def get_budget_dashboard(request):
    """Return the active monthly budget plan plus AI-backed spending guidance."""
    payload = materialize_payload(
        namespace="budget-dashboard",
        user_id=request.user.id,
        revision=_budget_dashboard_revision(request.user),
        ttl_seconds=60,
        builder=lambda: _build_budget_dashboard_payload(request),
    )
    return Response(payload)


def _budget_dashboard_revision(user) -> str:
    today = timezone.localdate()
    budget_meta = Budget.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        total_budget=Sum("inflation_adjusted"),
        total_spent=Sum("spent"),
    )
    expense_meta = Expense.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_date=Max("transaction_date"),
        total_amount=Sum("amount"),
    )
    profile_token = ":".join(
        str(value or "")
        for value in (
            getattr(user, "monthly_income", ""),
            getattr(user, "rent_or_emi", ""),
            getattr(user, "city_type", ""),
        )
    )
    return "|".join(
        str(value or "")
        for value in (
            "budget-dashboard-v5",
            today.strftime("%Y-%m-%d"),
            budget_meta["count"],
            budget_meta["max_id"],
            budget_meta["total_budget"],
            budget_meta["total_spent"],
            expense_meta["count"],
            expense_meta["max_id"],
            expense_meta["latest_date"],
            expense_meta["total_amount"],
            profile_token,
        )
    )


def _build_budget_dashboard_payload(request) -> dict:
    """Build the active monthly budget plan plus AI-backed spending guidance."""
    from .services.budget_intelligence import budget_intelligence_service, current_budget_plan

    today = timezone.localdate()
    start_of_month = today.replace(day=1)
    budgets = list(Budget.objects.filter(user=request.user).order_by("-id"))
    active_plan = current_budget_plan(request.user, today=today, budgets=budgets)
    monthly_expenses = Expense.objects.filter(
        user=request.user,
        transaction_date__gte=start_of_month,
        transaction_date__lte=today,
        direction="debit",
    )
    spent_by_category = defaultdict(Decimal)
    for expense, amount in variable_spend_rows(monthly_expenses, monthly_housing=request.user.rent_or_emi):
        spent_by_category[expense.category] += amount

    unavailable_sections = []
    def guidance(name, method, **kwargs):
        try:
            return method(request.user, **kwargs) or {}
        except Exception:
            unavailable_sections.append(name)
            return {}
    suggestions = guidance("suggestions", budget_intelligence_service.suggest_budget)
    daily_affordability = guidance("daily guide", budget_intelligence_service.calculate_daily_affordability)
    forecast = guidance("forecast", budget_intelligence_service.forecast_finances, months_ahead=3)
    baseline = suggestions.get("financial_baseline") or daily_affordability.get("financial_baseline") or forecast.get("financial_baseline") or {}

    plan_limit = max(Decimal("0"), Decimal(str(active_plan.inflation_adjusted if active_plan else suggestions.get("disposable_income", 0) or 0)))
    total_spent = sum(spent_by_category.values(), Decimal("0"))
    total_remaining = plan_limit - total_spent

    category_labels = dict(Expense.CATEGORY_CHOICES)
    category_suggestions = suggestions.get("category_budgets", {})
    categories = set(category_suggestions.keys()) | set(spent_by_category.keys())
    hidden_categories = {"income", "transfer", "loan", "credit_card", "investment"}
    limits = allocate_budget(plan_limit, {key: item.get("suggested", 0) or 0 for key, item in category_suggestions.items() if key not in hidden_categories})
    budget_data = []
    for category in categories:
        if category in hidden_categories:
            continue
        suggested_limit = limits.get(category, Decimal("0"))
        historical_avg = category_suggestions.get(category, {}).get("historical_avg", 0) or 0
        spent = spent_by_category.get(category, Decimal("0"))
        percent_used = round(spent / suggested_limit * 100, 1) if suggested_limit > 0 else None
        status = "good"
        if suggested_limit and spent > suggested_limit:
            status = "over"
        elif suggested_limit and spent > suggested_limit * Decimal("0.8"):
            status = "warning"

        budget_data.append(
            {
                "category": category,
                "label": category_labels.get(category, category.replace("_", " ").title()),
                "limit": money_float(suggested_limit),
                "spent": money_float(spent),
                "remaining": money_float(suggested_limit - spent),
                "percent_used": float(percent_used) if percent_used is not None else None,
                "historical_avg": money_float(historical_avg),
                "status": status,
            }
        )

    budget_data.sort(key=lambda item: (max(item["limit"], item["spent"]), item["label"]), reverse=True)
    budget_history = [
        {
            "id": budget.id,
            "month": budget.month,
            "base_budget": money_float(budget.base_budget),
            "inflation_adjusted": money_float(budget.inflation_adjusted),
            "spent": money_float(budget.spent),
        }
        for budget in budgets[:6]
    ]

    return {
        "summary": {
            "month": today.strftime("%B %Y"),
            "total_budget": money_float(plan_limit),
            "total_spent": money_float(total_spent),
            "total_remaining": money_float(total_remaining),
            "percent_used": float(round(total_spent / plan_limit * 100, 1)) if plan_limit > 0 else None,
            "fixed_obligations": money_float(baseline.get("fixed_obligations", 0)),
            "disposable_income": money_float(baseline.get("disposable_cash_flow", 0)),
            "tracked_categories": len(budget_data),
        },
        "plan": {
            "id": active_plan.id,
            "month": active_plan.month,
            "base_budget": money_float(active_plan.base_budget),
            "inflation_adjusted": money_float(active_plan.inflation_adjusted),
            "spent": money_float(active_plan.spent),
        } if active_plan else None,
        "budget_history": budget_history,
        "budgets": budget_data,
        "daily_affordability": daily_affordability,
        "ai_suggestions": suggestions.get("recommendations", []),
        "forecast": forecast.get("forecasts", []),
        "forecast_evidence": {key: forecast[key] for key in ("as_of", "status", "method", "observations", "uncertainty", "backtest", "calibration_status", "assumptions") if key in forecast},
        "financial_baseline": baseline,
        "unavailable_sections": unavailable_sections,
    }
