from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from apps.expenses.models import Expense
from apps.investments.models import Investment
from apps.loans.models import Loan
from apps.relationship.models import RelationshipProfile


class InvestmentAndRelationshipAdvisoryTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="advisory_user",
            password="Pass12345!",
            monthly_income=125000,
            rent_or_emi=30000,
            city="Bengaluru",
        )
        self.client = Client()
        self.client.force_login(self.user)
        Investment.objects.create(
            user=self.user,
            asset_type="equity",
            asset_name="Index Fund",
            institution="Groww",
            invested_amount=180000,
            current_value=210000,
            monthly_sip=10000,
            annual_return_rate=12,
            risk_level="Moderate",
        )
        Investment.objects.create(
            user=self.user,
            asset_type="debt",
            asset_name="Debt Fund",
            institution="Zerodha",
            invested_amount=80000,
            current_value=83500,
            monthly_sip=3000,
            annual_return_rate=7,
            risk_level="Low",
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
            transaction_date="2026-03-20",
            direction="debit",
            source="manual",
        )
        Loan.objects.create(
            user=self.user,
            lender="HDFC",
            loan_type="personal",
            principal=400000,
            interest_rate=11.5,
            emi=9800,
            tenure_months=48,
            remaining_balance=275000,
            start_date="2025-08-01",
            is_active=True,
        )
        RelationshipProfile.objects.create(
            user=self.user,
            partner_name="Ananya",
            partner_financial_score=74,
            partner_savings_habits=4,
            compatibility_score=78,
        )

    def test_investment_summary_exposes_materialized_grounding(self):
        with patch(
            "apps.investments.services.portfolio_intelligence.verified_intelligence.market_snapshot",
            return_value=_insight({"one_month_return_pct": 2.6, "india_vix": 13.4}, "Yahoo Finance", "Market snapshot is fresh."),
        ), patch(
            "apps.investments.services.portfolio_intelligence.verified_intelligence.world_bank_indicator",
            return_value=_insight({"latest_value": 4.9, "latest_year": 2025}, "World Bank", "Inflation snapshot is fresh."),
        ):
            first = self.client.get("/api/investments/summary/")
            second = self.client.get("/api/investments/summary/")

        self.assertEqual(first.status_code, 200)
        payload = first.json()
        self.assertFalse(payload["_materialized"]["cached"])
        self.assertEqual(payload["grounding"]["freshness"]["tracked_records"], 2)
        self.assertEqual(len(payload["grounding"]["evidence"]), 2)
        self.assertIn("Portfolio guidance is grounded", payload["grounding"]["notes"][0])
        self.assertTrue(second.json()["_materialized"]["cached"])

    def test_relationship_alignment_exposes_grounding_and_materialization(self):
        with patch(
            "apps.relationship.services.relationship_intelligence.verified_intelligence.world_bank_indicator",
            return_value=_insight({"latest_value": 5.2, "latest_year": 2025}, "World Bank", "Inflation reference is fresh."),
        ), patch(
            "apps.relationship.services.relationship_intelligence.verified_intelligence.market_snapshot",
            return_value=_insight({"one_month_return_pct": 1.8, "india_vix": 12.8}, "Yahoo Finance", "Market snapshot is fresh."),
        ), patch(
            "apps.relationship.services.relationship_intelligence.relationship_model_predictor.predict_score",
            return_value=76.0,
        ):
            first = self.client.get("/api/relationship/alignment/")
            second = self.client.get("/api/relationship/alignment/")

        self.assertEqual(first.status_code, 200)
        payload = first.json()
        self.assertFalse(payload["_materialized"]["cached"])
        self.assertEqual(payload["compatibility"], "Good")
        self.assertEqual(len(payload["factors"]), 4)
        self.assertEqual(payload["grounding"]["freshness"]["tracked_records"], 2)
        self.assertGreater(payload["alignment_score"], 0)
        self.assertTrue(second.json()["_materialized"]["cached"])


def _insight(payload, source_name, summary):
    class DummyInsight:
        def __init__(self):
            self.payload = payload
            self.evidence = {
                "source_name": source_name,
                "summary": summary,
                "status": "fresh",
                "stale_after": "2026-04-30T00:00:00+05:30",
                "source_url": "https://example.com/proof",
            }

    return DummyInsight()
