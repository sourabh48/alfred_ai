"""
Alfred Financial Brain - Central ML Intelligence Hub
Orchestrates all financial intelligence services for comprehensive AI-powered insights.
"""
from __future__ import annotations

from typing import Dict, Any, Optional
from django.utils import timezone

from apps.loans.services import loan_intelligence_service
from apps.investments.services import portfolio_intelligence_service
from apps.budgets.services import budget_intelligence_service
from apps.expenses.services.multi_bank_aggregator import multi_bank_aggregator
from apps.expenses.services.transaction_intelligence import (
    hydrate_expense_data,
    enrich_imported_expense,
)
from apps.ml_engine.inference_adapters.transaction_classifier import transaction_classifier


class AlfredFinancialBrain:
    """
    Central AI brain that coordinates all financial intelligence services.
    Provides unified API for comprehensive financial analysis and recommendations.
    """

    def __init__(self):
        self.loan_service = loan_intelligence_service
        self.portfolio_service = portfolio_intelligence_service
        self.budget_service = budget_intelligence_service
        self.bank_service = multi_bank_aggregator
        self.transaction_classifier = transaction_classifier

    def initialize(self):
        """Initialize all ML models."""
        try:
            self.transaction_classifier.load()
            print("[OK] Alfred Financial Brain initialized successfully")
        except Exception as e:
            print(f"[WARN] Alfred Financial Brain initialization warning: {e}")

    def get_comprehensive_financial_snapshot(self, user) -> Dict[str, Any]:
        """
        Generate a complete financial snapshot for the user including:
        - Multi-account overview
        - Loan status
        - Investment portfolio
        - Budget health
        - Daily affordability
        - Financial forecast
        """
        snapshot = {
            "generated_at": timezone.now().isoformat(),
            "user": user.username,
        }

        # Canonical current-state finance must be read once and reused by advisory layers.
        try:
            from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline

            snapshot["financial_baseline"] = resolve_canonical_financial_baseline(user)
        except Exception as e:
            snapshot["financial_baseline"] = {"error": str(e)}

        # 1. Bank Accounts Overview
        try:
            snapshot["accounts"] = self.bank_service.get_consolidated_view(user)
        except Exception as e:
            snapshot["accounts"] = {"error": str(e)}

        # 2. Loan Intelligence
        try:
            loan_metrics = self.loan_service.calculate_loan_metrics(user)
            snapshot["loans"] = loan_metrics
        except Exception as e:
            snapshot["loans"] = {"error": str(e)}

        # 3. Investment Portfolio
        try:
            portfolio_analysis = self.portfolio_service.analyze_portfolio_risk(user)
            snapshot["investments"] = portfolio_analysis
        except Exception as e:
            snapshot["investments"] = {"error": str(e)}

        # 4. Budget Intelligence
        try:
            budget_suggestion = self.budget_service.suggest_budget(user)
            snapshot["budget"] = budget_suggestion
        except Exception as e:
            snapshot["budget"] = {"error": str(e)}

        # 5. Daily Affordability
        try:
            affordability = self.budget_service.calculate_daily_affordability(user)
            snapshot["daily_affordability"] = affordability
        except Exception as e:
            snapshot["daily_affordability"] = {"error": str(e)}

        # 6. Financial Forecast
        try:
            forecast = self.budget_service.forecast_finances(user, months_ahead=6)
            snapshot["forecast"] = forecast
        except Exception as e:
            snapshot["forecast"] = {"error": str(e)}

        # 7. Market Trends & Investment Suggestions
        try:
            market_suggestions = self.portfolio_service.get_market_trends_and_suggestions(user)
            snapshot["market_intelligence"] = market_suggestions
        except Exception as e:
            snapshot["market_intelligence"] = {"error": str(e)}

        # 8. Overall Financial Health Score (0-100)
        snapshot["health_score"] = self._calculate_financial_health_score(snapshot)

        # 9. Top Priority Actions
        snapshot["priority_actions"] = self._generate_priority_actions(snapshot)

        return snapshot

    def process_new_transaction(
        self, user, transaction_text: str, amount: float, direction: str, transaction_date
    ) -> Dict[str, Any]:
        """
        Process a new transaction using ML to classify and enrich it.
        Auto-detects loans, investments, and spending patterns.
        """
        # Use ML classifier to understand transaction
        classification = self.transaction_classifier.predict(transaction_text, direction)

        # Enrich with additional intelligence
        enriched = enrich_imported_expense(
            user=user,
            amount=amount,
            classification=classification["classification"],
            category=classification["category"],
            payment_mode=classification["payment_mode"],
            merchant=classification["merchant"],
            description=transaction_text[:140],
            raw_description=transaction_text,
            direction=direction,
            transaction_date=transaction_date,
            external_reference="",
            counterparty=classification["counterparty"],
            company_name=classification["company_name"],
        )

        # Check if it's a loan payment
        if enriched["classification"] == "loan":
            loan_detection = {
                "is_loan_payment": True,
                "recommendation": "This appears to be a loan payment. Alfred will track it automatically.",
            }
        else:
            loan_detection = {"is_loan_payment": False}

        # Suggest which account to use (if not already specified)
        account_suggestion = self.bank_service.suggest_account_for_transaction(
            user, amount, enriched["category"]
        )

        return {
            "classification": enriched,
            "loan_detection": loan_detection,
            "account_suggestion": account_suggestion,
            "ml_confidence": classification.get("confidence", 0.85),
        }

    def auto_detect_and_sync_loans(self, user) -> Dict[str, Any]:
        """
        Automatically detect loan payments from transaction history and sync loan records.
        """
        return self.loan_service.detect_loan_payments(user)

    def import_investment_portfolio(self, user, pdf_file) -> Dict[str, Any]:
        """
        Import investment portfolio from broker statement PDF.
        """
        return self.portfolio_service.parse_portfolio_pdf(pdf_file, user)

    def get_smart_budget_recommendations(self, user) -> Dict[str, Any]:
        """
        Get AI-powered budget recommendations based on location, income, and spending.
        """
        return self.budget_service.suggest_budget(user)

    def analyze_spending_patterns(self, user) -> Dict[str, Any]:
        """
        Deep analysis of spending patterns including emotional spending detection.
        """
        from apps.expenses.models import Expense
        from datetime import timedelta

        thirty_days_ago = timezone.now().date() - timedelta(days=30)

        total_expenses = Expense.objects.filter(
            user=user,
            direction="debit",
            transaction_date__gte=thirty_days_ago
        )

        emotional_expenses = total_expenses.filter(is_emotional=True)

        emotional_spending_total = sum(exp.amount for exp in emotional_expenses)
        total_spending = sum(exp.amount for exp in total_expenses)

        emotional_percentage = (
            (emotional_spending_total / total_spending * 100) if total_spending > 0 else 0
        )

        # Category-wise emotional spending
        emotional_by_category = {}
        for exp in emotional_expenses:
            category = exp.get_category_display()
            if category not in emotional_by_category:
                emotional_by_category[category] = 0
            emotional_by_category[category] += exp.amount

        # Insights
        insights = []
        if emotional_percentage > 25:
            insights.append(
                f"⚠️ {emotional_percentage:.1f}% of your spending is emotionally driven. "
                "Consider a 24-hour rule before discretionary purchases."
            )
        elif emotional_percentage > 15:
            insights.append(
                f"Moderate emotional spending detected ({emotional_percentage:.1f}%). "
                "Track your mood when making impulse purchases."
            )
        else:
            insights.append(
                f"✓ Healthy spending discipline! Only {emotional_percentage:.1f}% is emotional."
            )

        return {
            "total_spending": round(total_spending, 2),
            "emotional_spending": round(emotional_spending_total, 2),
            "emotional_percentage": round(emotional_percentage, 2),
            "emotional_by_category": emotional_by_category,
            "insights": insights,
        }

    def _calculate_financial_health_score(self, snapshot: Dict) -> Dict[str, Any]:
        """
        Calculate overall financial health score (0-100) based on multiple factors.
        """
        score = 50  # Base score
        factors = []

        # Account health (20 points)
        accounts = snapshot.get("accounts", {})
        total_balance = accounts.get("total_balance", 0)
        if total_balance > 100000:
            score += 20
            factors.append("Strong liquidity position")
        elif total_balance > 50000:
            score += 15
            factors.append("Good cash reserves")
        elif total_balance > 20000:
            score += 10
            factors.append("Adequate cash buffer")
        else:
            factors.append("Low cash reserves - build emergency fund")

        # Loan health (20 points)
        baseline = snapshot.get("financial_baseline", {})
        loans = snapshot.get("loans", {})
        dti = float(baseline.get("debt_burden_ratio", loans.get("debt_to_income_ratio", 0)) or 0)
        if dti == 0:
            score += 20
            factors.append("Debt-free lifestyle")
        elif dti < 25:
            score += 18
            factors.append("Excellent debt management")
        elif dti < 40:
            score += 12
            factors.append("Manageable debt levels")
        else:
            score -= 10
            factors.append("High debt burden - consider restructuring")

        # Investment health (20 points)
        investments = snapshot.get("investments", {})
        portfolio_value = investments.get("total_portfolio_value", 0)
        if portfolio_value > 500000:
            score += 20
            factors.append("Strong investment portfolio")
        elif portfolio_value > 100000:
            score += 15
            factors.append("Growing investment base")
        elif portfolio_value > 0:
            score += 8
            factors.append("Investment journey started")
        else:
            factors.append("Start investing for wealth creation")

        # Budget discipline (20 points)
        affordability = snapshot.get("daily_affordability", {})
        status = affordability.get("status", "UNKNOWN")
        if status == "GOOD":
            score += 20
            factors.append("Excellent budget discipline")
        elif status == "WARNING":
            score += 10
            factors.append("Budget needs attention")
        elif status == "OVER_BUDGET":
            score -= 10
            factors.append("Budget overspending - reduce expenses")

        # Forecast health (20 points)
        forecast = snapshot.get("forecast", {})
        if "forecasts" in forecast and forecast["forecasts"]:
            avg_savings = sum(f.get("predicted_savings", 0) for f in forecast["forecasts"]) / len(
                forecast["forecasts"]
            )
            if avg_savings > 10000:
                score += 20
                factors.append("Strong savings trajectory")
            elif avg_savings > 5000:
                score += 15
                factors.append("Healthy savings pattern")
            elif avg_savings > 0:
                score += 8
                factors.append("Positive savings trend")
            else:
                score -= 10
                factors.append("Negative savings - immediate action needed")

        # Clamp score
        score = max(0, min(100, score))

        # Overall assessment
        if score >= 80:
            assessment = "EXCELLENT"
            message = "Outstanding financial health! Keep up the great work."
        elif score >= 60:
            assessment = "GOOD"
            message = "Good financial position. Focus on improvements."
        elif score >= 40:
            assessment = "FAIR"
            message = "Fair financial health. Important improvements needed."
        else:
            assessment = "POOR"
            message = "Financial health needs urgent attention."

        return {
            "score": round(score, 1),
            "assessment": assessment,
            "message": message,
            "contributing_factors": factors,
        }

    def _generate_priority_actions(self, snapshot: Dict) -> list:
        """Generate top 5 priority actions for user."""
        actions = []

        # Check daily affordability
        affordability = snapshot.get("daily_affordability", {})
        if affordability.get("status") == "OVER_BUDGET":
            actions.append({
                "priority": "HIGH",
                "action": "Budget Overspending",
                "description": "You've exceeded your monthly budget. Review and cut discretionary expenses immediately.",
            })

        # Check debt burden
        baseline = snapshot.get("financial_baseline", {})
        loans = snapshot.get("loans", {})
        dti = float(baseline.get("debt_burden_ratio", loans.get("debt_to_income_ratio", 0)) or 0)
        if dti > 40:
            actions.append({
                "priority": "HIGH",
                "action": "High Debt Burden",
                "description": f"Your debt-to-income ratio is {dti:.1f}%. Consider debt consolidation or restructuring.",
            })

        # Check investment portfolio
        investments = snapshot.get("investments", {})
        if investments.get("total_portfolio_value", 0) == 0:
            actions.append({
                "priority": "MEDIUM",
                "action": "Start Investing",
                "description": "You have no investments. Start a SIP in index funds or mutual funds for wealth creation.",
            })

        # Check portfolio diversification
        div_score = investments.get("diversification_score", 0)
        if div_score < 40 and investments.get("total_portfolio_value", 0) > 0:
            actions.append({
                "priority": "MEDIUM",
                "action": "Diversify Portfolio",
                "description": "Low portfolio diversification. Spread investments across asset classes.",
            })

        # Check emergency fund
        accounts = snapshot.get("accounts", {})
        total_balance = float(baseline.get("liquid_cash", accounts.get("total_balance", 0)) or 0)
        fixed_obligations = float(baseline.get("fixed_obligations", 0) or 0)
        observed_total_outflow = float(baseline.get("observed_average_monthly_total_outflow", 0) or 0)
        monthly_emergency_base = max(fixed_obligations, observed_total_outflow, 0)
        emergency_fund_target = monthly_emergency_base * 6

        if emergency_fund_target and total_balance < emergency_fund_target:
            actions.append({
                "priority": "HIGH",
                "action": "Build Emergency Fund",
                "description": f"Your emergency fund goal is ₹{emergency_fund_target:,.0f}. Current: ₹{total_balance:,.0f}",
            })

        # Limit to top 5
        return actions[:5]


# Singleton instance
alfred_brain = AlfredFinancialBrain()
