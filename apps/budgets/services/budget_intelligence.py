"""
Budget Intelligence Service
Location-based budget suggestions, daily expenditure calculator, and smart forecasting.
"""
from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.db.models import Sum, Avg, Q
from django.utils import timezone
import requests

from apps.budgets.models import Budget
from apps.expenses.models import Expense
from apps.loans.models import Loan


class BudgetIntelligenceService:
    """ML-powered budget recommendations based on location, income, and spending patterns."""

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
        Generate ML-powered budget suggestions based on:
        - User's location
        - Income level
        - Historical spending patterns
        - City cost of living
        """
        monthly_income = getattr(user, "monthly_income", 0) or 0
        city = getattr(user, "city", "").lower()

        if monthly_income <= 0:
            return {
                "success": False,
                "message": "Please update your monthly income in profile to get budget suggestions.",
            }

        # Calculate cost adjustment based on city
        city_multiplier = self._get_city_cost_multiplier(city)

        # Calculate fixed obligations
        fixed_obligations = self._calculate_fixed_obligations(user)

        # Disposable income after fixed costs
        disposable_income = monthly_income - fixed_obligations

        if disposable_income <= 0:
            return {
                "success": False,
                "message": "Your fixed obligations exceed your income. Consider debt restructuring.",
                "fixed_obligations": fixed_obligations,
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
        }

    def calculate_daily_affordability(self, user) -> Dict[str, any]:
        """
        Calculate how much user can afford to spend daily in their current situation.
        Considers remaining budget, days left in month, and upcoming obligations.
        """
        today = timezone.now().date()
        month_start = today.replace(day=1)
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        days_remaining = days_in_month - today.day + 1

        # Get current month spending
        month_spending = Expense.objects.filter(
            user=user,
            transaction_date__gte=month_start,
            transaction_date__lte=today,
            direction="debit",
        ).aggregate(total=Sum("amount"))["total"] or 0

        # Get monthly budget or income
        monthly_income = getattr(user, "monthly_income", 0) or 0
        fixed_obligations = self._calculate_fixed_obligations(user)
        monthly_budget = monthly_income - fixed_obligations

        remaining_budget = monthly_budget - month_spending

        # Calculate safe daily spend
        safe_daily_spend = remaining_budget / days_remaining if days_remaining > 0 else 0

        # Get today's spending
        today_spending = Expense.objects.filter(
            user=user,
            transaction_date=today,
            direction="debit",
        ).aggregate(total=Sum("amount"))["total"] or 0

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
        }

    def forecast_finances(self, user, months_ahead: int = 6) -> Dict[str, any]:
        """
        Forecast user's financial situation for next N months using ML.
        Predicts spending, income, and savings trajectory.
        """
        # Get historical data (last 6 months)
        six_months_ago = timezone.now().date() - timedelta(days=180)

        monthly_expenses = []
        for i in range(6):
            month_start = six_months_ago + timedelta(days=30 * i)
            month_end = month_start + timedelta(days=30)

            expense_total = Expense.objects.filter(
                user=user,
                transaction_date__gte=month_start,
                transaction_date__lt=month_end,
                direction="debit",
            ).aggregate(total=Sum("amount"))["total"] or 0

            monthly_expenses.append(expense_total)

        # Calculate trend
        if len(monthly_expenses) >= 3:
            avg_expense = sum(monthly_expenses) / len(monthly_expenses)
            recent_avg = sum(monthly_expenses[-3:]) / 3
            trend = "increasing" if recent_avg > avg_expense * 1.1 else "stable"
        else:
            avg_expense = sum(monthly_expenses) / len(monthly_expenses) if monthly_expenses else 0
            trend = "unknown"

        # Forecast future months
        monthly_income = getattr(user, "monthly_income", 0) or 0
        fixed_obligations = self._calculate_fixed_obligations(user)

        forecasts = []
        for i in range(months_ahead):
            # Simple linear forecast with trend adjustment
            trend_multiplier = 1.0 + (0.03 * i if trend == "increasing" else 0)
            predicted_expense = avg_expense * trend_multiplier

            predicted_savings = monthly_income - predicted_expense - fixed_obligations

            forecasts.append({
                "month": (timezone.now().date() + timedelta(days=30 * (i + 1))).strftime("%B %Y"),
                "predicted_expense": round(predicted_expense, 2),
                "predicted_savings": round(predicted_savings, 2),
                "cumulative_savings": round(predicted_savings * (i + 1), 2),
            })

        return {
            "current_monthly_expense_avg": round(avg_expense, 2),
            "trend": trend,
            "forecasts": forecasts,
            "insights": self._generate_forecast_insights(forecasts, trend),
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
        rent_or_emi = getattr(user, "rent_or_emi", 0) or 0

        # Add active loan EMIs
        active_loan_emis = Loan.objects.filter(
            user=user,
            is_active=True
        ).aggregate(total=Sum("emi"))["total"] or 0

        return rent_or_emi + active_loan_emis

    def _generate_category_budgets(
        self, disposable_income: float, city_multiplier: float, user
    ) -> Dict[str, Dict]:
        """Generate category-wise budget allocations."""
        category_budgets = {}

        # Get user's historical spending patterns
        last_3_months = timezone.now().date() - timedelta(days=90)
        user_spending = {}

        for category, _ in Expense.CATEGORY_CHOICES:
            if category in ["income", "transfer", "loan", "credit_card", "investment"]:
                continue

            historical_avg = Expense.objects.filter(
                user=user,
                category=category,
                direction="debit",
                transaction_date__gte=last_3_months,
            ).aggregate(avg=Avg("amount"))["avg"] or 0

            # Blend historical data with ideal allocation
            ideal_allocation = (disposable_income * self.CATEGORY_ALLOCATION.get(category, 5) / 100) * city_multiplier

            # Weight: 60% ideal, 40% historical
            suggested_budget = (ideal_allocation * 0.6) + (historical_avg * 0.4) if historical_avg > 0 else ideal_allocation

            category_budgets[category] = {
                "suggested": round(suggested_budget, 2),
                "historical_avg": round(historical_avg, 2),
            }

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
                f"⚠️ Your debt-to-income ratio is {dti:.1f}%. Aim to keep it below 40% for financial health."
            )
        elif dti < 25:
            recommendations.append(
                f"✓ Excellent debt management! Your DTI is {dti:.1f}%."
            )

        # Savings recommendation
        ideal_savings = monthly_income * 0.2
        recommendations.append(
            f"Aim to save at least ₹{ideal_savings:,.0f}/month (20% of income) for financial security."
        )

        # Emergency fund
        months_of_expenses = 6
        emergency_fund_target = disposable_income * months_of_expenses
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
            return f"✓ You're on track! You can safely spend up to ₹{safe_spend:.0f} today."

    def _generate_forecast_insights(self, forecasts: List[Dict], trend: str) -> List[str]:
        """Generate insights from financial forecasts."""
        insights = []

        total_predicted_savings = sum(f["predicted_savings"] for f in forecasts)

        if total_predicted_savings > 0:
            insights.append(
                f"You're projected to save ₹{total_predicted_savings:,.0f} over the next {len(forecasts)} months."
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
