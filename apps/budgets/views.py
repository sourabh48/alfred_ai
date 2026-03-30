from collections import defaultdict

from django.db.models import Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes as perm_classes
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.expenses.models import Expense

from .models import Budget
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
    from .services.budget_intelligence import budget_intelligence_service

    today = timezone.localdate()
    start_of_month = today.replace(day=1)
    budgets = list(Budget.objects.filter(user=request.user).order_by("-id"))
    active_plan = budgets[0] if budgets else None
    monthly_expenses = Expense.objects.filter(
        user=request.user,
        transaction_date__gte=start_of_month,
        transaction_date__lte=today,
        direction="debit",
    )
    spent_by_category = defaultdict(float)
    for item in monthly_expenses.values("category").annotate(total=Sum("amount")):
        spent_by_category[item["category"]] = float(item["total"] or 0)

    try:
        suggestions = budget_intelligence_service.suggest_budget(request.user) or {}
        daily_affordability = budget_intelligence_service.calculate_daily_affordability(request.user)
        forecast = budget_intelligence_service.forecast_finances(request.user, months_ahead=3)
    except Exception:
        suggestions = {}
        daily_affordability = {}
        forecast = {}

    plan_limit = float(
        getattr(active_plan, "inflation_adjusted", 0)
        or getattr(active_plan, "base_budget", 0)
        or suggestions.get("disposable_income", 0)
        or 0
    )
    actual_spent = float(monthly_expenses.aggregate(total=Sum("amount"))["total"] or 0)
    total_budget = round(plan_limit, 2)
    total_spent = round(actual_spent, 2)
    total_remaining = round(total_budget - total_spent, 2)

    category_labels = dict(Expense.CATEGORY_CHOICES)
    category_suggestions = suggestions.get("category_budgets", {})
    categories = set(category_suggestions.keys()) | set(spent_by_category.keys())
    hidden_categories = {"income", "transfer", "loan", "credit_card", "investment"}
    budget_data = []
    for category in categories:
        if category in hidden_categories:
            continue
        suggested_limit = float(category_suggestions.get(category, {}).get("suggested", 0) or 0)
        historical_avg = float(category_suggestions.get(category, {}).get("historical_avg", 0) or 0)
        spent = round(spent_by_category.get(category, 0.0), 2)
        percent_used = round((spent / suggested_limit * 100) if suggested_limit > 0 else 0, 1)
        status = "good"
        if suggested_limit and spent > suggested_limit:
            status = "over"
        elif suggested_limit and spent > suggested_limit * 0.8:
            status = "warning"

        budget_data.append(
            {
                "category": category,
                "label": category_labels.get(category, category.replace("_", " ").title()),
                "limit": round(suggested_limit, 2),
                "spent": spent,
                "remaining": round(suggested_limit - spent, 2),
                "percent_used": percent_used,
                "historical_avg": round(historical_avg, 2),
                "status": status,
            }
        )

    budget_data.sort(key=lambda item: (max(item["limit"], item["spent"]), item["label"]), reverse=True)
    budget_history = [
        {
            "id": budget.id,
            "month": budget.month,
            "base_budget": round(float(budget.base_budget or 0), 2),
            "inflation_adjusted": round(float(budget.inflation_adjusted or 0), 2),
            "spent": round(float(budget.spent or 0), 2),
        }
        for budget in budgets[:6]
    ]

    return Response(
        {
            "summary": {
                "month": today.strftime("%B %Y"),
                "total_budget": total_budget,
                "total_spent": total_spent,
                "total_remaining": total_remaining,
                "percent_used": round((total_spent / total_budget * 100) if total_budget > 0 else 0, 1),
                "fixed_obligations": round(float(suggestions.get("fixed_obligations", 0) or 0), 2),
                "disposable_income": round(float(suggestions.get("disposable_income", 0) or 0), 2),
                "tracked_categories": len(budget_data),
            },
            "plan": {
                "id": active_plan.id,
                "month": active_plan.month,
                "base_budget": round(float(active_plan.base_budget or 0), 2),
                "inflation_adjusted": round(float(active_plan.inflation_adjusted or 0), 2),
                "spent": round(float(active_plan.spent or 0), 2),
            } if active_plan else None,
            "budget_history": budget_history,
            "budgets": budget_data[:8],
            "daily_affordability": daily_affordability,
            "ai_suggestions": suggestions.get("recommendations", []),
            "forecast": forecast.get("forecasts", []),
        }
    )
