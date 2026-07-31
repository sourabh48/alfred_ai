from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.utils import timezone

from apps.behavioral.models import BehavioralSignal
from apps.budgets.models import Budget
from apps.career.models import CareerProfile
from apps.expenses.models import Expense
from apps.family.models import Dependent
from apps.investments.models import Investment
from apps.loans.models import Loan
from apps.mobility.models import BikeConditionSnapshot, BikeProfile
from apps.risk.models import RiskSignal


class LargeDataMaterializationTests(TestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="large_data_user",
            password="Pass12345!",
            monthly_income=110000,
            rent_or_emi=28000,
            city="Bengaluru",
        )
        self.client = Client()
        self.client.force_login(self.user)
        self._seed_history()

    def tearDown(self):
        cache.clear()

    def test_financial_and_behavioral_dashboards_return_materialized_hits(self):
        endpoints = [
            ("/api/budgets/dashboard/", "budget-dashboard"),
            ("/api/loans/summary/", "loan-summary"),
            ("/api/loans/metrics/", "loan-metrics"),
            ("/api/loans/networth/", "loan-networth"),
            ("/api/behavioral/fingerprint/", "behavioral-fingerprint"),
            ("/api/behavioral/stress/", "behavioral-stress"),
        ]

        for path, namespace in endpoints:
            with self.subTest(path=path):
                self._assert_materialized_hit(path, namespace)

    def test_budget_dashboard_revision_invalidates_when_history_changes(self):
        first = self.client.get("/api/budgets/dashboard/")
        second = self.client.get("/api/budgets/dashboard/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        first_key = first.json()["_materialized"]["cache_key"]
        self.assertTrue(second.json()["_materialized"]["cached"])

        Expense.objects.create(
            user=self.user,
            amount=1450,
            classification="expense",
            category="fuel",
            payment_mode="UPI",
            merchant="Fuel Station",
            description="Fuel topup",
            raw_description="Fuel topup",
            transaction_date=timezone.localdate(),
            direction="debit",
            source="manual",
        )

        refreshed = self.client.get("/api/budgets/dashboard/")
        self.assertEqual(refreshed.status_code, 200)
        self.assertFalse(refreshed.json()["_materialized"]["cached"])
        self.assertNotEqual(first_key, refreshed.json()["_materialized"]["cache_key"])

    def test_evidence_heavy_dashboards_return_materialized_hits(self):
        with patch(
            "apps.risk.services.risk_intelligence.job_intelligence.market_outlook",
            return_value={
                "risk_score": 24,
                "layoff_news": [],
                "job_market_news": [],
                "macro_context": {
                    "unemployment": {"latest_value": 5.0},
                    "inflation": {"latest_value": 4.8},
                    "market": {"one_month_return_pct": 1.8, "india_vix": 14.0},
                },
                "insights": ["Market pressure is controlled."],
                "evidence": [_evidence("World Bank")],
            },
        ), patch(
            "apps.risk.services.risk_intelligence.bike_service_intelligence.risk_snapshot",
            return_value={
                "summary": {
                    "critical_faults": 0,
                    "expired_documents": 0,
                    "expiring_documents": 0,
                    "latest_condition_score": 88,
                    "document_compliance_score": 100,
                },
                "pending_tasks": [],
            },
        ), patch(
            "apps.risk.services.risk_intelligence.verified_intelligence.google_news_search",
            return_value=_insight("Google News"),
        ), patch(
            "apps.integrations.views.verified_intelligence.market_snapshot",
            return_value=_insight("Yahoo Finance"),
        ), patch(
            "apps.integrations.views.verified_intelligence.world_bank_indicator",
            return_value=_insight("World Bank"),
        ), patch(
            "apps.integrations.views.verified_intelligence.tax_regime_reference",
            return_value=_insight("Income Tax Department"),
        ), patch(
            "apps.integrations.views.verified_intelligence.nps_tax_reference",
            return_value=_insight("PFRDA"),
        ), patch(
            "apps.integrations.views.verified_intelligence.ppf_reference",
            return_value=_insight("India Post"),
        ):
            self._assert_materialized_hit("/api/risk/outlook/", "risk-outlook")
            self._assert_materialized_hit(
                "/api/integrations/recommendations/overview/?investment_amount=5000&time_horizon=short_term",
                "recommendation-overview",
            )
            self._assert_materialized_hit(
                "/api/integrations/tax/overview/?annual_income=1320000&basic_salary=55000",
                "tax-optimizer-overview",
            )

    def _assert_materialized_hit(self, path: str, namespace: str):
        first = self.client.get(path)
        second = self.client.get(path)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        first_meta = first.json()["_materialized"]
        second_meta = second.json()["_materialized"]
        self.assertEqual(first_meta["namespace"], namespace)
        self.assertFalse(first_meta["cached"])
        self.assertTrue(second_meta["cached"])
        self.assertEqual(first_meta["cache_key"], second_meta["cache_key"])

    def _seed_history(self):
        Budget.objects.create(
            user=self.user,
            month="July 2026",
            base_budget=76000,
            inflation_adjusted=79000,
            spent=42000,
        )
        Expense.objects.create(
            user=self.user,
            amount=42000,
            classification="expense",
            category="household",
            payment_mode="UPI",
            merchant="Household",
            description="Monthly spend",
            raw_description="Monthly spend",
            transaction_date=date(2026, 7, 20),
            direction="debit",
            source="manual",
        )
        Loan.objects.create(
            user=self.user,
            lender="HDFC",
            loan_type="personal",
            principal=500000,
            interest_rate=11.5,
            emi=12800,
            tenure_months=48,
            remaining_balance=390000,
            start_date=date(2025, 8, 1),
            is_active=True,
            status="active",
        )
        Investment.objects.create(
            user=self.user,
            asset_type="mutual_fund",
            asset_name="Index Fund",
            institution="Groww",
            invested_amount=150000,
            current_value=172000,
            monthly_sip=8000,
            annual_return_rate=11,
            risk_level="Moderate",
        )
        BehavioralSignal.objects.create(user=self.user, stress_score=5, sleep_hours=7, work_hours=9)
        RiskSignal.objects.create(user=self.user, layoff_risk=22, illness_risk=18, relocation_risk=12)
        Dependent.objects.create(user=self.user, name="Parent", age=64, relation="parent")
        CareerProfile.objects.create(
            user=self.user,
            role="Data Analyst",
            experience_years=5,
            skills="Python, SQL, BI",
            last_salary=1400000,
        )
        bike = BikeProfile.objects.create(
            user=self.user,
            display_name="Activa",
            make="Honda",
            model_name="Activa 125",
            vehicle_type="scooter",
            bike_class="scooter",
            vehicle_number="KA03XY1111",
            is_primary=True,
        )
        BikeConditionSnapshot.objects.create(
            user=self.user,
            bike_profile=bike,
            bike_name=bike.display_name,
            vehicle_number=bike.vehicle_number,
            overall_status="good",
            engine_status="good",
            brake_status="good",
            tyre_status="good",
            battery_status="good",
            body_status="good",
            odometer_km=6200,
        )


def _evidence(source_name: str) -> dict:
    return {
        "source_name": source_name,
        "source_url": "https://example.com/proof",
        "status": "fresh",
        "stale_after": "2026-08-31T00:00:00+05:30",
    }


def _insight(source_name: str):
    class DummyInsight:
        def __init__(self):
            self.payload = {"latest_value": 4.8, "one_month_return_pct": 1.8, "india_vix": 14.0}
            self.evidence = _evidence(source_name)

    return DummyInsight()
