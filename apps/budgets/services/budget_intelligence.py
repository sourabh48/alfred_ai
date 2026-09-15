"""
Budget Intelligence Service
Location-based budget suggestions, daily expenditure calculator, and smart forecasting.
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import datetime
from typing import Dict, List
from django.utils import timezone

from apps.budgets.models import Budget
from apps.expenses.models import Expense
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.expenses.services.cashflow_treatment import variable_spend_rows


def current_budget_plan(user, *, today=None, budgets=None):
    today = today or timezone.localdate()
    plans = budgets if budgets is not None else Budget.objects.filter(user=user).order_by("-id")
    for plan in plans:
        for pattern in ("%b %Y", "%B %Y", "%Y-%m"):
            try:
                month = datetime.strptime(plan.month.strip(), pattern)
            except ValueError:
                continue
            if (month.year, month.month) == (today.year, today.month):
                return plan
    return None


class BudgetIntelligenceService:
    """Rule-based budget estimates from location, income, and spending history."""

    # Cost of living indices by major Indian cities (base = 100)
    CITY_COST_INDEX = {
        "mumbai": 100,
        "bangalore": 95,
        "delhi": 90,
        "gurgaon": 90,
        "noida": 85,
        "pune": 85,
        "hyderabad": 80,
        "chennai": 80,
        "kolkata": 75,
        "ahmedabad": 70,
        "jaipur": 65,
        "lucknow": 60,
        "indore": 58,
        "bhopal": 55,
    }

    # Category-wise typical allocation (percentage of disposable income)
    CATEGORY_ALLOCATION = {
        "food": 15,
        "groceries": 12,
        "shopping": 10,
        "bills": 8,
        "utilities": 7,
        "travel": 10,
        "fuel": 6,
        "health": 5,
        "subscription": 3,
        "entertainment": 8,
        "other": 16,
    }

    def suggest_budget(self, user) -> Dict[str, any]:
        """
        Generate rule-based budget suggestions based on:
        - User's location
        - Income level
        - Historical spending patterns
        - City cost of living
        """
        baseline = resolve_canonical_financial_baseline(user)
        monthly_income = float(baseline.get("monthly_income", 0) or 0)
        city = getattr(user, "city", "").lower()

        if monthly_income <= 0:
            return {
                "success": False,
                "message": "Please update your monthly income in profile to get budget suggestions.",
                "financial_baseline": baseline,
            }

        # Calculate cost adjustment based on city
        city_multiplier = self._get_city_cost_multiplier(city)

        # Calculate fixed obligations
        fixed_obligations = float(baseline.get("fixed_obligations", 0) or 0)

        # Disposable income after fixed costs
        disposable_income = float(baseline.get("disposable_cash_flow", monthly_income - fixed_obligations) or 0)

        if disposable_income <= 0:
            return {
                "success": False,
                "message": "Your fixed obligations exceed your income. Consider debt restructuring.",
                "fixed_obligations": fixed_obligations,
                "financial_baseline": baseline,
            }

        # Generate category-wise budget
        category_budgets = self._generate_category_budgets(
            disposable_income, city_multiplier, user
        )

        # Calculate daily expenditure affordability
        daily_expenditure = self._calculate_daily_expenditure(disposable_income)

        # Generate personalized recommendations
        recommendations = self._generate_budget_recommendations(
            user, monthly_income, fixed_obligations, disposable_income, category_budgets
        )

        return {
            "success": True,
            "monthly_income": monthly_income,
            "fixed_obligations": round(fixed_obligations, 2),
            "disposable_income": round(disposable_income, 2),
            "city": city.title() or "Unknown",
            "city_cost_index": city_multiplier,
            "category_budgets": category_budgets,
            "daily_expenditure_limit": round(daily_expenditure, 2),
            "recommendations": recommendations,
            "financial_baseline": baseline,
        }

    def calculate_daily_affordability(self, user) -> Dict[str, any]:
        """
        Calculate how much user can afford to spend daily in their current situation.
        Considers remaining budget, days left in month, and upcoming obligations.
        """
        today = timezone.localdate()
        month_start = today.replace(day=1)
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        days_remaining = days_in_month - today.day + 1

        # Get current month spending
        baseline = resolve_canonical_financial_baseline(user)
        expenses = Expense.objects.filter(
            user=user,
            transaction_date__gte=month_start,
            transaction_date__lte=today,
            direction="debit",
        )
        rows = list(variable_spend_rows(expenses, monthly_housing=user.rent_or_emi))
        month_spending = float(sum(amount for _, amount in rows))

        # Get monthly budget from the canonical baseline so EMI burden is not double counted.
        monthly_budget = float(baseline.get("disposable_cash_flow", 0) or 0)
        plan = current_budget_plan(user, today=today)
        if plan is not None:
            monthly_budget = float(plan.inflation_adjusted)

        remaining_budget = monthly_budget - month_spending

        # Calculate safe daily spend
        safe_daily_spend = remaining_budget / days_remaining if days_remaining > 0 else 0

        # Get today's spending
        today_spending = float(sum(amount for expense, amount in rows if expense.transaction_date == today))

        # Calculate average daily spending this month
        days_elapsed = (today - month_start).days + 1
        avg_daily_spending = month_spending / days_elapsed if days_elapsed > 0 else 0

        status = "GOOD"
        if safe_daily_spend < 0:
            status = "OVER_BUDGET"
        elif today_spending > safe_daily_spend * 1.5:
            status = "WARNING"

        return {
            "today_spending": round(today_spending, 2),
            "safe_daily_spend": round(max(0, safe_daily_spend), 2),
            "remaining_budget": round(remaining_budget, 2),
            "days_remaining": days_remaining,
            "avg_daily_spending": round(avg_daily_spending, 2),
            "status": status,
            "message": self._get_affordability_message(status, safe_daily_spend, today_spending),
            "financial_baseline": baseline,
        }

    def forecast_finances(self, user, months_ahead: int = 6) -> Dict[str, any]:
        """
        Estimate the next N calendar months from recent recorded living costs.
        """
        # A transparent planning estimate based on observed living costs.
        # Missing months are not observations of zero spending.
        baseline = resolve_canonical_financial_baseline(user)
        avg_expense = float(baseline.get("observed_average_monthly_variable_spend", 0) or 0)
        has_history = baseline.get("metric_states", {}).get("observed_average_monthly_variable_spend", {}).get("status") != "unavailable"
        trend = "held_constant" if has_history else "unknown"
        monthly_income = float(baseline.get("monthly_income", 0) or 0)
        fixed_obligations = float(baseline.get("fixed_obligations", 0) or 0)

        forecasts = []
        today = timezone.localdate()
        for i in range(months_ahead):
            predicted_expense = avg_expense
            predicted_savings = monthly_income - predicted_expense - fixed_obligations
            month_index = today.year * 12 + today.month + i
            forecast_month = today.replace(year=month_index // 12, month=month_index % 12 + 1, day=1)
            forecasts.append({
                "month": forecast_month.strftime("%B %Y"),
                "predicted_expense": round(predicted_expense, 2),
                "predicted_savings": round(predicted_savings, 2),
                "cumulative_savings": round(predicted_savings * (i + 1), 2),
            })

        return {
            "current_monthly_expense_avg": round(avg_expense, 2),
            "trend": trend,
            "forecasts": forecasts if has_history and monthly_income > 0 else [],
            "method": "Recent living-spend average; income and fixed costs held constant. Before investments and card settlements.",
            "insights": self._generate_forecast_insights(forecasts, trend) if has_history and monthly_income > 0 else ["Add income and spending history before using a forecast."],
            "financial_baseline": baseline,
        }

    def _get_city_cost_multiplier(self, city: str) -> float:
        """Get cost of living multiplier for city."""
        city_lower = city.lower()
        for city_name, index in self.CITY_COST_INDEX.items():
            if city_name in city_lower:
                return index / 100

        return 0.85  # Default for tier-2/3 cities

    def _calculate_fixed_obligations(self, user) -> float:
        """Calculate fixed monthly obligations (rent, EMIs, etc.)."""
        baseline = resolve_canonical_financial_baseline(user)
        return float(baseline.get("fixed_obligations", 0) or 0)

    def _generate_category_budgets(
        self, disposable_income: float, city_multiplier: float, user
    ) -> Dict[str, Dict]:
        """Generate category-wise budget allocations."""
        category_budgets = {}

        expenses = list(Expense.objects.filter(user=user, transaction_date__lte=timezone.localdate()))
        recent_months = sorted({(item.transaction_date.year, item.transaction_date.month) for item in expenses})[-3:]
        category_totals = defaultdict(float)
        for expense, amount in variable_spend_rows(expenses, monthly_housing=user.rent_or_emi):
            if (expense.transaction_date.year, expense.transaction_date.month) in recent_months:
                category_totals[expense.category] += float(amount)

        for category, _ in Expense.CATEGORY_CHOICES:
            if category in ["income", "transfer", "loan", "credit_card", "investment"]:
                continue

            historical_avg = category_totals[category] / len(recent_months) if recent_months else 0
            if category == "rent" and user.rent_or_emi > 0 and historical_avg == 0:
                continue

            # Blend historical data with ideal allocation
            ideal_allocation = (disposable_income * self.CATEGORY_ALLOCATION.get(category, 5) / 100) * city_multiplier

            # Weight: 60% ideal, 40% historical
            suggested_budget = (ideal_allocation * 0.6) + (historical_avg * 0.4) if historical_avg > 0 else ideal_allocation

            category_budgets[category] = {
                "suggested": round(suggested_budget, 2),
                "historical_avg": round(historical_avg, 2),
            }

        total = sum(item["suggested"] for item in category_budgets.values())
        for item in category_budgets.values():
            item["suggested"] = round(item["suggested"] / total * disposable_income, 2) if total else 0
        return category_budgets

    def _calculate_daily_expenditure(self, disposable_income: float) -> float:
        """Calculate safe daily expenditure."""
        # Reserve 20% for savings
        spendable = disposable_income * 0.8
        return spendable / 30

    def _generate_budget_recommendations(
        self, user, monthly_income: float, fixed_obligations: float,
        disposable_income: float, category_budgets: Dict
    ) -> List[str]:
        """Generate personalized budget recommendations."""
        recommendations = []

        # Debt-to-income ratio
        dti = (fixed_obligations / monthly_income * 100) if monthly_income > 0 else 0
        if dti > 40:
            recommendations.append(
                f"Housing and loan EMIs use {dti:.1f}% of monthly income, leaving less for everyday spending."
            )
        elif dti < 25:
            recommendations.append(
                f"Housing and loan EMIs use {dti:.1f}% of monthly income."
            )

        # Savings recommendation
        ideal_savings = monthly_income * 0.2
        recommendations.append(
            f"Aim to save at least ₹{ideal_savings:,.0f}/month (20% of income) for financial security."
        )

        # Emergency fund
        months_of_expenses = 6
        baseline = resolve_canonical_financial_baseline(user)
        emergency_fund_target = float(baseline.get("essential_monthly_outflow", 0) or 0) * months_of_expenses
        recommendations.append(
            f"Build an emergency fund of ₹{emergency_fund_target:,.0f} (6 months of expenses)."
        )

        return recommendations

    def _get_affordability_message(self, status: str, safe_spend: float, today_spend: float) -> str:
        """Get personalized affordability message."""
        if status == "OVER_BUDGET":
            return "⚠️ You've exceeded your monthly budget. Focus on essential spending only."
        elif status == "WARNING":
            return f"⚠️ Today's spending (₹{today_spend:.0f}) is high. Safe limit: ₹{safe_spend:.0f}"
        else:
            return f"About ₹{safe_spend:,.0f} per day remains in your flexible budget. Allow separately for savings and unrecorded bills."

    def _generate_forecast_insights(self, forecasts: List[Dict], trend: str) -> List[str]:
        """Generate insights from financial forecasts."""
        insights = []

        total_predicted_savings = sum(f["predicted_savings"] for f in forecasts)

        if total_predicted_savings > 0:
            insights.append(
                f"Estimated income left before investments and card payments: ₹{total_predicted_savings:,.0f} over {len(forecasts)} months."
            )
        else:
            insights.append(
                f"⚠️ Current trajectory shows negative savings. Reduce discretionary spending."
            )

        if trend == "increasing":
            insights.append(
                "Your expenses are trending upward. Review subscriptions and discretionary spending."
            )
        elif trend == "stable":
            insights.append(
                "Your spending is stable. Maintain this consistency."
            )

        return insights


# Singleton instance
budget_intelligence_service = BudgetIntelligenceService()
