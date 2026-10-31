import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.utils import timezone

from apps.behavioral.models import BehavioralSignal
from apps.behavioral.services import _build_combined_stress_series, _build_derived_pressure_series
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


class EmptySpendingWindowTests(TestCase):
    """FAMILY-06: a week without debits is missing evidence, not measured zero pressure."""

    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user("behavior_empty_window", password="Pass12345!", monthly_income=98000)
        self.client = Client()
        self.client.force_login(self.user)
        patcher = patch("apps.behavioral.services.verified_intelligence.household_planning_context",
                        return_value=_planning_context())
        patcher.start()
        self.addCleanup(patcher.stop)

    def debit(self, days_ago, amount=20000):
        Expense.objects.create(user=self.user, amount=amount, classification="loan", category="loan", payment_mode="BANK",
                               merchant="Synthetic EMI", description="Synthetic EMI", raw_description="Synthetic EMI",
                               transaction_date=timezone.localdate() - timedelta(days=days_ago), direction="debit", source="manual")

    def stress(self):
        response = self.client.get("/api/behavioral/stress/")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_empty_recent_week_does_not_dilute_manual_stress(self):
        self.debit(21)
        BehavioralSignal.objects.create(user=self.user, stress_score=8, sleep_hours=7, work_hours=8)
        self.assertEqual(self.stress()["current_stress"], 8)

    def test_active_week_still_blends_with_manual_stress(self):
        self.debit(1)
        BehavioralSignal.objects.create(user=self.user, stress_score=8, sleep_hours=7, work_hours=8)
        score = _build_derived_pressure_series(self.user)[0]["score"]
        self.assertGreater(score, 0)
        self.assertEqual(self.stress()["current_stress"], round(8*0.65 + score*0.35, 2))

    def test_gaps_do_not_fake_a_decreasing_trend(self):
        self.debit(21)
        self.debit(28)
        payload = self.stress()
        self.assertEqual(len(payload["weekly_data"]), 2)
        self.assertGreater(min(payload["weekly_data"]), 0)
        self.assertEqual(payload["trend"], "Stable")

    def test_empty_window_keeps_its_driver_and_is_marked(self):
        self.debit(21)
        windows = _build_derived_pressure_series(self.user)
        self.assertEqual(len(windows), 7)
        self.assertEqual(windows[0]["driver"], "No debit activity captured in this window.")
        self.assertEqual((windows[0]["has_activity"], windows[0]["outflow_total"]), (False, 0.0))
        self.assertTrue(windows[3]["has_activity"])

    def test_behavior_pressure_averages_active_windows_only(self):
        self.debit(21)
        active = [item["score"] for item in _build_derived_pressure_series(self.user) if item["has_activity"]]
        response = self.client.get("/api/behavioral/fingerprint/")
        self.assertEqual(response.status_code, 200)
        behavior = next(item for item in response.json()["pressure_map"] if item["label"] == "Behavior pressure")
        self.assertEqual(behavior["score"], round(round(sum(active)/len(active), 2)*10, 1))

    def test_series_skips_missing_values_and_falls_back_only_when_empty(self):
        self.assertEqual(_build_combined_stress_series(manual_series=[], derived_scores=[None, 4.0, None], fallback_stress=70), [4.0])
        self.assertEqual(_build_combined_stress_series(manual_series=[6.0], derived_scores=[None, None], fallback_stress=70), [6.0])
        self.assertEqual(_build_combined_stress_series(manual_series=[], derived_scores=[None, None], fallback_stress=70), [7.0])
        self.assertEqual(_build_combined_stress_series(manual_series=[], derived_scores=[], fallback_stress=70), [7.0])

    def test_windows_stay_owner_isolated(self):
        other = get_user_model().objects.create_user("behavior_empty_other", password="Pass12345!")
        Expense.objects.create(user=other, amount=9000, classification="loan", category="loan", payment_mode="BANK",
                               merchant="Other", description="Other", raw_description="Other",
                               transaction_date=timezone.localdate(), direction="debit", source="manual")
        self.debit(21)
        self.assertFalse(_build_derived_pressure_series(self.user)[0]["has_activity"])


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
