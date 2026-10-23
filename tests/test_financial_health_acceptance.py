from datetime import date

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from apps.expenses.models import Expense
from apps.expenses.services.financial_intelligence import build_financial_intelligence


class FinancialHealthAcceptanceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = get_user_model().objects.create_user(username="health_owner")
        for month in (1, 2):
            self.row(month, "100000.01", "income", "credit")
            self.row(month, "40000.00", "utilities", "debit")

    def row(self, month, amount, category, direction, **kwargs):
        return Expense.objects.create(
            user=kwargs.pop("user", self.user), amount=amount, category=category,
            classification=kwargs.pop("classification", "expense" if direction == "debit" else "other"),
            direction=direction, transaction_date=date(2026, month, 10), source="manual", **kwargs,
        )

    def test_stable_recorded_history_has_independently_expected_bounded_indicators(self):
        before = list(Expense.objects.filter(user=self.user).values())
        payload = build_financial_intelligence(self.user)
        summary = payload["summary"]
        self.assertEqual(summary["reference_month"], "February 2026")
        self.assertEqual(summary["history_income"], 200000.02)
        self.assertEqual(summary["history_outflow"], 80000)
        self.assertEqual(summary["current_month_income"], 100000.01)
        self.assertEqual(summary["current_month_outflow"], 40000)
        self.assertEqual(summary["observed_savings_rate"], 60)
        # Stable, non-discretionary spending with positive savings saturates the existing heuristic.
        self.assertEqual(summary["financial_health_score"], 100)
        self.assertEqual(summary["stress_score"], 0)
        self.assertEqual(payload["charts"]["monthly_outflow_values"], [40000, 40000])
        self.assertEqual(before, list(Expense.objects.filter(user=self.user).values()))

    def test_transfers_and_pending_debits_do_not_become_confirmed_income_or_spending(self):
        self.row(2, "999999.99", "transfer", "credit")
        self.row(2, "999999.99", "transfer", "debit")
        pending = self.row(2, "52345.67", "other", "debit", classification="other")
        summary = build_financial_intelligence(self.user)["summary"]
        self.assertEqual(summary["history_income"], 200000.02)
        self.assertEqual(summary["history_outflow"], 80000)
        self.assertEqual(summary["history_review_required"], 52345.67)
        pending.refresh_from_db()
        self.assertEqual(pending.category, "other")

    def test_foreign_history_cannot_change_owned_cached_or_fresh_indicators(self):
        original = build_financial_intelligence(self.user)
        foreign = get_user_model().objects.create_user(username="health_private")
        self.row(12, "999999999.99", "shopping", "debit", user=foreign, description="PRIVATE-HEALTH")
        cached = build_financial_intelligence(self.user)
        self.assertEqual(cached["summary"], original["summary"])
        cache.clear()
        fresh = build_financial_intelligence(self.user)
        self.assertEqual(fresh["summary"], original["summary"])
        self.assertEqual(fresh["charts"], original["charts"])
        self.assertNotIn("PRIVATE-HEALTH", str(fresh))

    def test_empty_and_loss_making_histories_are_distinct_and_scores_stay_bounded(self):
        Expense.objects.filter(user=self.user).delete()
        empty = build_financial_intelligence(self.user)["summary"]
        self.assertEqual(empty["transactions"], 0)
        self.assertEqual(empty["risk_level"], "No data")
        self.row(2, "100.01", "income", "credit")
        self.row(2, "500.05", "shopping", "debit")
        summary = build_financial_intelligence(self.user)["summary"]
        self.assertEqual(summary["observed_savings_rate"], -400)
        self.assertEqual(summary["current_month_net"], -400.04)
        for name in ("financial_health_score", "stability_score", "discipline_score", "liquidity_score", "stress_score"):
            self.assertGreaterEqual(summary[name], 0)
            self.assertLessEqual(summary[name], 100)
        self.assertLess(summary["financial_health_score"], 100)
