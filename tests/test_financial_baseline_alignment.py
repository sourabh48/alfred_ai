from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.utils import timezone

from apps.budgets.services.budget_intelligence import budget_intelligence_service
from apps.career.models import CareerProfile
from apps.career.services import build_employment_income_signals
from apps.career.views import _career_timing_payload
from apps.expenses.models import BankAccount, Expense
from apps.expenses.services.financial_intelligence import build_financial_intelligence, resolve_canonical_financial_baseline
from apps.loans.models import Loan
from apps.ml_engine.services.recommendation_engine import recommendation_engine
from apps.relationship.models import RelationshipProfile
from apps.relationship.services.relationship_intelligence import build_relationship_alignment
from apps.risk.services.risk_intelligence import risk_intelligence


class FinancialBaselineAlignmentTests(TestCase):
    def setUp(self):
        cache.clear()
        recommendation_engine.user_profiles.clear()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="baseline_user",
            password="Pass12345!",
            monthly_income=1200000,
            variable_income=60000,
            rent_or_emi=25000,
            city="Bengaluru",
        )
        self.profile = CareerProfile.objects.create(
            user=self.user,
            role="Data Analyst",
            experience_years=5,
            skills="Python, SQL, Power BI",
            last_salary=0,
        )
        RelationshipProfile.objects.create(
            user=self.user,
            partner_name="Ananya",
            partner_financial_score=72,
            partner_savings_habits=4,
            compatibility_score=78,
        )
        BankAccount.objects.create(
            user=self.user,
            bank_name="HDFC",
            account_number="000012340001",
            account_type="savings",
            current_balance=210000,
            is_active=True,
        )
        self.active_loan = Loan.objects.create(
            user=self.user,
            lender="HDFC",
            loan_type="personal",
            principal=500000,
            interest_rate=11.5,
            emi=15000,
            tenure_months=48,
            remaining_balance=320000,
            start_date="2025-01-01",
            is_active=True,
            status="active",
        )
        for month in (1, 2, 3):
            Expense.objects.create(
                user=self.user,
                amount=22000,
                classification="expense",
                category="utilities",
                payment_mode="BANK",
                merchant=f"Utilities {month}",
                description="Monthly recurring spend",
                raw_description="MONTHLY RECURRING SPEND",
                transaction_date=date(2026, month, 10),
                direction="debit",
                source="manual",
            )
        self.client = Client()
        self.client.force_login(self.user)

    def _risk_market_payload(self):
        return {
            "risk_score": 32,
            "layoff_news": [],
            "job_market_news": [],
            "macro_context": {
                "unemployment": {"latest_value": 5.0},
                "inflation": {"latest_value": 4.8},
                "market": {"one_month_return_pct": 1.8, "india_vix": 13.0},
            },
            "insights": ["Signals are stable."],
            "evidence": [],
        }

    def _career_market_payload(self):
        return {
            "risk_score": 28,
            "layoff_news": [],
            "job_market_news": [],
            "macro_context": {
                "unemployment": {"latest_value": 5.0},
                "inflation": {"latest_value": 4.8},
                "market": {"one_month_return_pct": 1.8, "india_vix": 13.0},
            },
            "insights": ["Market is stable."],
            "evidence": [],
        }

    def test_canonical_baseline_aligns_budget_recommendation_risk_relationship_and_career(self):
        baseline = resolve_canonical_financial_baseline(self.user)
        self.assertEqual(baseline["monthly_income"], 100000.0)
        self.assertEqual(baseline["income_source"], "reported_annual_ctc")
        self.assertEqual(baseline["recurring_emi_burden"], 15000.0)
        self.assertEqual(baseline["fixed_obligations"], 40000.0)
        self.assertEqual(baseline["disposable_cash_flow"], 60000.0)
        self.assertEqual(baseline["observed_average_monthly_variable_spend"], 22000.0)
        self.assertEqual(baseline["savings_capacity"], 38000.0)
        self.assertEqual(baseline["savings_rate"], 38.0)
        self.assertEqual(baseline["baseline_savings_rate"], baseline["savings_rate"])
        self.assertEqual(baseline["debt_burden_ratio"], 40.0)
        self.assertEqual(baseline["liquid_cash"], 210000.0)
        self.assertEqual(baseline["liquid_runway_months"], 5.25)

        intelligence = build_financial_intelligence(self.user)
        self.assertEqual(intelligence["baseline"]["monthly_income"], baseline["monthly_income"])
        self.assertEqual(intelligence["baseline"]["fixed_obligations"], baseline["fixed_obligations"])
        self.assertEqual(intelligence["summary"]["observed_savings_rate"], intelligence["summary"]["savings_rate"])
        self.assertEqual(intelligence["summary"]["financial_stress_score"], intelligence["summary"]["stress_score"])

        budget = budget_intelligence_service.suggest_budget(self.user)
        self.assertTrue(budget["success"])
        self.assertEqual(budget["monthly_income"], baseline["monthly_income"])
        self.assertEqual(budget["fixed_obligations"], baseline["fixed_obligations"])
        self.assertEqual(budget["disposable_income"], baseline["disposable_cash_flow"])
        self.assertEqual(budget["financial_baseline"]["savings_capacity"], baseline["savings_capacity"])

        loan_metrics = self.client.get("/api/loans/metrics/").json()
        self.assertEqual(loan_metrics["monthly_income"], baseline["monthly_income"])
        self.assertEqual(loan_metrics["monthly_emi_burden"], baseline["recurring_emi_burden"])
        self.assertEqual(loan_metrics["fixed_obligations"], baseline["fixed_obligations"])
        self.assertEqual(loan_metrics["disposable_cash_flow"], baseline["disposable_cash_flow"])
        self.assertEqual(loan_metrics["savings_capacity"], baseline["savings_capacity"])
        self.assertEqual(loan_metrics["debt_to_income_ratio"], 15.0)
        self.assertEqual(loan_metrics["financial_baseline"]["monthly_income"], baseline["monthly_income"])

        recommendation_profile = recommendation_engine.build_user_profile(self.user)
        self.assertEqual(recommendation_profile["income"], baseline["monthly_income"])
        self.assertEqual(recommendation_profile["monthly_expenses"], baseline["observed_average_monthly_variable_spend"])
        self.assertEqual(recommendation_profile["monthly_savings"], baseline["savings_capacity"])
        self.assertEqual(recommendation_profile["total_emi"], baseline["recurring_emi_burden"])
        self.assertEqual(recommendation_profile["dti_ratio"], baseline["debt_burden_ratio"])

        with patch(
            "apps.relationship.services.relationship_intelligence.verified_intelligence.world_bank_indicator",
            return_value=_insight({"latest_value": 4.8}, "World Bank"),
        ), patch(
            "apps.relationship.services.relationship_intelligence.verified_intelligence.market_snapshot",
            return_value=_insight({"india_vix": 13.0, "one_month_return_pct": 1.8}, "Yahoo Finance"),
        ), patch(
            "apps.relationship.services.relationship_intelligence.relationship_model_predictor.predict_score",
            return_value=None,
        ):
            relationship = build_relationship_alignment(self.user).payload

        self.assertEqual(relationship["financial_baseline"]["monthly_income"], baseline["monthly_income"])
        self.assertEqual(relationship["grounding"]["history"]["monthly_income"], baseline["monthly_income"])
        self.assertEqual(relationship["grounding"]["history"]["monthly_expenses"], baseline["observed_average_monthly_variable_spend"])
        self.assertEqual(relationship["grounding"]["history"]["monthly_emi"], baseline["recurring_emi_burden"])
        self.assertEqual(relationship["grounding"]["history"]["fixed_load"], baseline["fixed_obligations"])
        self.assertEqual(relationship["grounding"]["history"]["savings_rate"], baseline["savings_rate"])
        self.assertEqual(relationship["grounding"]["history"]["debt_pressure"], baseline["debt_burden_ratio"])
        self.assertTrue(relationship["grounding"]["proof_contract"]["complete"])

        with patch(
            "apps.risk.services.risk_intelligence.job_intelligence.market_outlook",
            return_value=self._risk_market_payload(),
        ), patch(
            "apps.risk.services.risk_intelligence.bike_service_intelligence.risk_snapshot",
            return_value={"summary": {"critical_faults": 0, "expired_documents": 0, "expiring_documents": 0, "latest_condition_score": 84, "document_compliance_score": 100}},
        ):
            risk = risk_intelligence.build_outlook(self.user)

        self.assertEqual(risk["financial_baseline"]["monthly_income"], baseline["monthly_income"])
        self.assertEqual(risk["grounding"]["history"]["monthly_income"], baseline["monthly_income"])
        self.assertEqual(risk["grounding"]["history"]["monthly_emi"], baseline["recurring_emi_burden"])
        self.assertEqual(risk["grounding"]["history"]["fixed_obligations"], baseline["fixed_obligations"])
        self.assertEqual(risk["module_signals"]["debt_burden_pct"], baseline["debt_burden_ratio"])
        self.assertEqual(risk["module_signals"]["emergency_months"], round(baseline["liquid_runway_months"], 1))

        income_signals = build_employment_income_signals(user=self.user, profile=self.profile)
        career_timing = _career_timing_payload(
            self.user,
            self.profile,
            self._career_market_payload(),
            latest_analysis=None,
            income_signals=income_signals,
        )
        self.assertEqual(career_timing["financial_baseline"]["monthly_income"], baseline["monthly_income"])
        self.assertEqual(career_timing["financial_baseline"]["fixed_obligations"], baseline["fixed_obligations"])
        self.assertEqual(career_timing["financial_baseline"]["liquid_runway_months"], baseline["liquid_runway_months"])

    def test_pending_foreclosure_balance_stays_in_liabilities_while_recurring_emi_baseline_stays_stable(self):
        Loan.objects.create(
            user=self.user,
            lender="SBI",
            loan_type="home",
            principal=700000,
            interest_rate=9.1,
            emi=12000,
            tenure_months=120,
            remaining_balance=180000,
            start_date="2024-06-01",
            is_active=False,
            status="foreclosure_pending",
        )
        Loan.objects.create(
            user=self.user,
            lender="Axis Bank",
            loan_type="personal",
            principal=250000,
            interest_rate=13.2,
            emi=9200,
            tenure_months=48,
            remaining_balance=0,
            start_date="2024-01-01",
            is_active=False,
            status="closed",
        )
        cache.clear()
        recommendation_engine.user_profiles.clear()

        baseline = resolve_canonical_financial_baseline(self.user)
        intelligence = build_financial_intelligence(self.user)
        budget = budget_intelligence_service.suggest_budget(self.user)
        recommendation_profile = recommendation_engine.build_user_profile(self.user)
        loan_metrics = self.client.get("/api/loans/metrics/").json()

        self.assertEqual(baseline["pending_foreclosure_balance"], 180000.0)
        self.assertEqual(baseline["recurring_emi_burden"], 15000.0)
        self.assertEqual(baseline["fixed_obligations"], 40000.0)
        self.assertEqual(intelligence["baseline"]["pending_foreclosure_balance"], 180000.0)
        self.assertEqual(intelligence["loan_portfolio"]["pending_foreclosure_balance"], 180000.0)
        self.assertEqual(intelligence["loan_portfolio"]["pending_foreclosure_excluded_balance"], 180000.0)
        self.assertEqual(intelligence["balance_sheet"]["pending_foreclosure_balance"], 180000.0)
        self.assertEqual(intelligence["balance_sheet"]["pending_foreclosure_excluded_balance"], 180000.0)
        self.assertEqual(intelligence["balance_sheet"]["total_liabilities"], 500000.0)
        self.assertEqual(budget["financial_baseline"]["pending_foreclosure_balance"], 180000.0)
        self.assertEqual(recommendation_profile["financial_baseline"]["pending_foreclosure_balance"], 180000.0)
        self.assertEqual(recommendation_profile["total_emi"], 15000.0)
        self.assertEqual(loan_metrics["active_loan_count"], 1)
        self.assertEqual(loan_metrics["monthly_emi_burden"], 15000.0)
        self.assertEqual(loan_metrics["pending_foreclosure_balance"], 180000.0)
        self.assertEqual(loan_metrics["financial_baseline"]["pending_foreclosure_balance"], 180000.0)
        self.assertEqual(loan_metrics["disposable_cash_flow"], baseline["disposable_cash_flow"])
        self.assertEqual(loan_metrics["savings_capacity"], baseline["savings_capacity"])

        from apps.integrations.services.credit_score_tracker import credit_score_service

        alerts = credit_score_service.get_comprehensive_report(self.user)["alerts"]
        self.assertFalse(any(item["type"] == "DTI_WARNING" for item in alerts))

    def test_api_responses_expose_the_same_financial_baseline(self):
        baseline = resolve_canonical_financial_baseline(self.user)

        with patch(
            "apps.career.views.verified_intelligence.macro_context",
            return_value={"payload": self._career_market_payload()["macro_context"], "evidence": []},
        ), patch(
            "apps.career.views.job_intelligence.market_outlook",
            return_value=self._career_market_payload(),
        ), patch(
            "apps.career.views.job_intelligence.suggest_openings",
            return_value={"openings": [], "evidence": []},
        ), patch(
            "apps.risk.services.risk_intelligence.job_intelligence.market_outlook",
            return_value=self._risk_market_payload(),
        ), patch(
            "apps.risk.services.risk_intelligence.bike_service_intelligence.risk_snapshot",
            return_value={"summary": {"critical_faults": 0, "expired_documents": 0, "expiring_documents": 0, "latest_condition_score": 84, "document_compliance_score": 100}},
        ), patch(
            "apps.relationship.services.relationship_intelligence.verified_intelligence.world_bank_indicator",
            return_value=_insight({"latest_value": 4.8}, "World Bank"),
        ), patch(
            "apps.relationship.services.relationship_intelligence.verified_intelligence.market_snapshot",
            return_value=_insight({"india_vix": 13.0, "one_month_return_pct": 1.8}, "Yahoo Finance"),
        ), patch(
            "apps.relationship.services.relationship_intelligence.relationship_model_predictor.predict_score",
            return_value=None,
        ), patch(
            "apps.integrations.views.verified_intelligence.market_snapshot",
            return_value=_insight({"india_vix": 13.0, "one_month_return_pct": 1.8}, "Yahoo Finance"),
        ), patch(
            "apps.integrations.views.verified_intelligence.world_bank_indicator",
            return_value=_insight({"latest_value": 4.8}, "World Bank"),
        ):
            budget_payload = self.client.get("/api/budgets/dashboard/").json()
            loan_metrics_payload = self.client.get("/api/loans/metrics/").json()
            risk_payload = self.client.get("/api/risk/outlook/").json()
            relationship_payload = self.client.get("/api/relationship/alignment/").json()
            recommendation_payload = self.client.get("/api/integrations/recommendations/overview/").json()
            career_payload = self.client.get("/api/career/dashboard/").json()
            family_payload = self.client.get("/api/family/growth/").json()

        self.assertEqual(budget_payload["financial_baseline"]["monthly_income"], baseline["monthly_income"])
        self.assertEqual(loan_metrics_payload["financial_baseline"]["monthly_income"], baseline["monthly_income"])
        self.assertEqual(loan_metrics_payload["financial_baseline"]["recurring_emi_burden"], baseline["recurring_emi_burden"])
        self.assertEqual(loan_metrics_payload["fixed_obligations"], baseline["fixed_obligations"])
        self.assertEqual(loan_metrics_payload["disposable_cash_flow"], baseline["disposable_cash_flow"])
        self.assertEqual(risk_payload["financial_baseline"]["fixed_obligations"], baseline["fixed_obligations"])
        self.assertEqual(relationship_payload["financial_baseline"]["savings_capacity"], baseline["savings_capacity"])
        self.assertEqual(recommendation_payload["financial_baseline"]["recurring_emi_burden"], baseline["recurring_emi_burden"])
        self.assertEqual(recommendation_payload["profile"]["income"], baseline["monthly_income"])
        self.assertEqual(career_payload["career_timing"]["financial_baseline"]["liquid_runway_months"], baseline["liquid_runway_months"])
        self.assertEqual(family_payload["financial_baseline"]["net_worth"], baseline["net_worth"])
        self.assertEqual(family_payload["current_net_worth"], baseline["net_worth"])
        self.assertEqual(family_payload["total_assets"], baseline["total_assets"])
        self.assertEqual(family_payload["total_liabilities"], baseline["total_liabilities"])
        self.assertEqual(family_payload["grounding"]["history"]["current_net_worth"], baseline["net_worth"])
        self.assertEqual(family_payload["grounding"]["freshness"]["tracked_records"], 2)
        self.assertTrue(family_payload["grounding"]["proof_contract"]["complete"])
        self.assertEqual(family_payload["grounding"]["proof_contract"]["refresh_contract"]["scheduled_refresh"], "refresh_due_records")

    def test_credit_travel_and_alfred_brain_read_canonical_financial_baseline(self):
        Loan.objects.create(
            user=self.user,
            lender="ICICI",
            loan_type="car",
            principal=180000,
            interest_rate=10.5,
            emi=35000,
            tenure_months=12,
            remaining_balance=150000,
            start_date="2026-01-01",
            is_active=True,
            status="active",
        )
        cache.clear()
        recommendation_engine.user_profiles.clear()

        baseline = resolve_canonical_financial_baseline(self.user)
        self.assertEqual(baseline["recurring_emi_burden"], 50000.0)
        self.assertEqual(baseline["fixed_obligations"], 75000.0)
        self.assertEqual(baseline["debt_burden_ratio"], 75.0)
        self.assertEqual(baseline["savings_capacity"], 3000.0)

        from apps.integrations.services.credit_score_tracker import credit_score_service
        from apps.mobility.services.travel_advisor import travel_advisor
        from apps.ml_engine.services.alfred_financial_brain import alfred_brain

        alerts = credit_score_service.get_comprehensive_report(self.user)["alerts"]
        dti_alerts = [item for item in alerts if item["type"] == "DTI_WARNING"]
        self.assertEqual(len(dti_alerts), 1)
        self.assertIn("50.0%", dti_alerts[0]["message"])

        stay_advice = travel_advisor._stay_advice(self.user, per_day_budget=12000, duration_days=1)
        self.assertEqual(stay_advice["tier"], "budget")
        self.assertEqual(stay_advice["affordability_basis"]["savings_capacity"], baseline["savings_capacity"])
        self.assertEqual(stay_advice["affordability_basis"]["debt_burden_ratio"], baseline["debt_burden_ratio"])

        with patch.object(alfred_brain.bank_service, "get_consolidated_view", return_value={"total_balance": baseline["liquid_cash"]}), patch.object(
            alfred_brain.loan_service,
            "calculate_loan_metrics",
            return_value={"debt_to_income_ratio": 1.0},
        ), patch.object(
            alfred_brain.portfolio_service,
            "analyze_portfolio_risk",
            return_value={"total_portfolio_value": 0, "diversification_score": 0},
        ), patch.object(
            alfred_brain.budget_service,
            "suggest_budget",
            return_value={"disposable_income": 999999},
        ), patch.object(
            alfred_brain.budget_service,
            "calculate_daily_affordability",
            return_value={"status": "GOOD"},
        ), patch.object(
            alfred_brain.budget_service,
            "forecast_finances",
            return_value={"forecasts": [{"predicted_savings": 1000}]},
        ), patch.object(
            alfred_brain.portfolio_service,
            "get_market_trends_and_suggestions",
            return_value={"recommendations": []},
        ):
            snapshot = alfred_brain.get_comprehensive_financial_snapshot(self.user)

        self.assertEqual(snapshot["financial_baseline"]["monthly_income"], baseline["monthly_income"])
        self.assertEqual(snapshot["financial_baseline"]["debt_burden_ratio"], baseline["debt_burden_ratio"])
        self.assertIn("High debt burden - consider restructuring", snapshot["health_score"]["contributing_factors"])
        self.assertTrue(any(item["action"] == "High Debt Burden" for item in snapshot["priority_actions"]))


def _insight(payload, source_name):
    class DummyInsight:
        def __init__(self):
            self.payload = payload
            self.evidence = {
                "source_name": source_name,
                "source_url": "https://example.com/proof",
                "status": "fresh",
                "stale_after": _future_stale_after(),
            }

    return DummyInsight()


def _future_stale_after():
    return (timezone.now() + timedelta(days=2)).isoformat()
