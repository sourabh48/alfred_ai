import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.utils import timezone

from apps.behavioral.models import BehavioralSignal
from apps.expenses.models import Expense
from apps.integrations.services.verified_intelligence import freshness_snapshot


class BehavioralLinkageTests(TestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="behavior_link_user",
            password="Pass12345!",
            monthly_income=98000,
            rent_or_emi=26000,
            city="Bengaluru",
        )
        self.client = Client()
        self.client.force_login(self.user)
        self.planning_context_patch = patch(
            "apps.behavioral.services.verified_intelligence.household_planning_context",
            return_value=_planning_context(),
        )
        self.planning_context_patch.start()
        self.addCleanup(self.planning_context_patch.stop)

    def _seed_transaction_history(self):
        today = timezone.localdate()
        for week in range(6):
            tx_date = today - timedelta(days=week * 7)
            Expense.objects.create(
                user=self.user,
                amount=95000,
                classification="other",
                category="income",
                payment_mode="BANK",
                merchant="Employer",
                description="Salary credit",
                raw_description="Salary credit",
                transaction_date=tx_date,
                direction="credit",
                source="manual",
            )
            Expense.objects.create(
                user=self.user,
                amount=12000 + (week * 900),
                classification="loan",
                category="loan",
                payment_mode="BANK",
                merchant="Home Loan EMI",
                description="Home loan EMI",
                raw_description="Home loan EMI",
                transaction_date=tx_date,
                direction="debit",
                source="manual",
            )
            Expense.objects.create(
                user=self.user,
                amount=2200 + (week * 150),
                classification="expense",
                category="shopping",
                payment_mode="UPI",
                merchant="Amazon",
                description="Shopping burst",
                raw_description="Shopping burst",
                transaction_date=tx_date,
                direction="debit",
                source="manual",
                is_emotional=True,
                model_confidence=0.91,
            )
            Expense.objects.create(
                user=self.user,
                amount=799,
                classification="expense",
                category="subscription",
                payment_mode="UPI",
                merchant="Spotify",
                description="Music subscription",
                raw_description="Music subscription",
                transaction_date=tx_date - timedelta(days=2),
                direction="debit",
                source="manual",
            )

    def test_behavioral_fingerprint_links_existing_transaction_history(self):
        self._seed_transaction_history()

        response = self.client.get("/api/behavioral/fingerprint/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertNotEqual(payload["fingerprint"], "No data")
        self.assertEqual(payload["linked_data"]["transactions"], 24)
        self.assertGreater(len(payload["pressure_map"]), 0)
        self.assertGreater(len(payload["pattern_flags"]), 0)
        self.assertIn("Linked", payload["message"])
        self.assertEqual(payload["grounding"]["freshness"]["tracked_records"], 2)
        self.assertTrue(payload["grounding"]["freshness"]["proof_complete"])
        self.assertTrue(payload["grounding"]["proof_contract"]["complete"])
        self.assertEqual(payload["grounding"]["proof_contract"]["refresh_contract"]["scheduled_refresh"], "refresh_due_records")
        self.assertEqual(payload["grounding"]["history"]["transactions"], 24)

    def test_behavioral_stress_uses_transaction_history_without_manual_logs(self):
        self._seed_transaction_history()

        response = self.client.get("/api/behavioral/stress/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertGreater(payload["current_stress"], 0)
        self.assertGreater(len(payload["weekly_data"]), 0)
        self.assertEqual(payload["linked_transactions"], 24)
        self.assertEqual(payload["manual_signal_count"], 0)
        self.assertGreater(len(payload["pressure_map"]), 0)
        self.assertEqual(payload["grounding"]["history"]["transactions"], 24)
        self.assertEqual(payload["grounding"]["freshness"]["tracked_records"], 2)
        self.assertTrue(payload["grounding"]["proof_contract"]["complete"])
        self.assertTrue(payload["grounding"]["proof_contract"]["refresh_contract"]["stale_fallback"])

    def test_behavioral_stress_blends_manual_logs_with_financial_pressure(self):
        self._seed_transaction_history()
        BehavioralSignal.objects.create(
            user=self.user,
            stress_score=8.0,
            sleep_hours=5.5,
            work_hours=10.0,
        )

        response = self.client.get("/api/behavioral/stress/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["manual_signal_count"], 1)
        self.assertGreater(payload["current_stress"], 0)
        self.assertIn("manual behavioral logs", payload["message"])


def _planning_context():
    stale_after = (timezone.now() + timedelta(days=2)).isoformat()
    evidence = [
        {
            "source_name": "World Bank",
            "source_url": "https://example.com/world-bank",
            "summary": "Inflation reference is fresh.",
            "status": "fresh",
            "stale_after": stale_after,
        },
        {
            "source_name": "Yahoo Finance",
            "source_url": "https://example.com/market",
            "summary": "Market snapshot is fresh.",
            "status": "fresh",
            "stale_after": stale_after,
        },
    ]
    return {
        "payload": {
            "inflation": {"latest_value": 4.8, "latest_year": 2026},
            "market": {"india_vix": 13.0, "one_month_return_pct": 1.8},
        },
        "evidence": evidence,
        "freshness": freshness_snapshot(evidence),
        "notes": ["Household planning evidence fixture is fresh."],
    }
