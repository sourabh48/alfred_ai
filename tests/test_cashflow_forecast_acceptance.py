from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

from apps.budgets.services.budget_intelligence import budget_intelligence_service as service
from apps.expenses.models import Expense


class CashflowForecastAcceptanceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = get_user_model().objects.create_user("synthetic_forecast_owner", monthly_income="100", rent_or_emi="10")
        self.other = get_user_model().objects.create_user("synthetic_forecast_other")
        self.owner.refresh_from_db(); self.other.refresh_from_db()
        self.today = date(2026, 1, 15)
        self.enterContext(patch("django.utils.timezone.localdate", return_value=self.today))

    def spend(self, month, amount, **kwargs):
        return Expense.objects.create(user=kwargs.pop("user", self.owner), transaction_date=date.fromisoformat(month + "-01"),
            amount=amount, category=kwargs.pop("category", "food"), classification="expense", direction=kwargs.pop("direction", "debit"), **kwargs)

    def test_partial_and_future_months_are_not_training_observations(self):
        self.spend("2026-01", "999"); self.spend("2026-02", "999")
        result = service.forecast_finances(self.owner)
        self.assertEqual(result["forecasts"], [])
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["observations"], [])
        self.assertIsNone(result["current_monthly_expense_avg"])

    def test_cent_rounding_reconciles_each_month_and_cumulative_savings(self):
        self.spend("2025-11", ".01"); self.spend("2025-12", ".02")
        result = service.forecast_finances(self.owner, months_ahead=3)
        for index, row in enumerate(result["forecasts"], 1):
            self.assertEqual(row["predicted_expense"], .02)
            self.assertEqual(row["predicted_savings"], 89.98)
            self.assertEqual(Decimal(str(row["cumulative_savings"])), Decimal("89.98") * index)
        self.assertEqual(result["forecasts"][0]["month_key"], "2026-02")

    def test_calendar_rollover_is_next_calendar_month(self):
        self.spend("2025-11", "10")
        with patch("django.utils.timezone.localdate", return_value=date(2026, 12, 31)):
            result = service.forecast_finances(self.owner, months_ahead=2)
        self.assertEqual([r["month_key"] for r in result["forecasts"]], ["2027-01", "2027-02"])

    def test_missing_months_are_unknown_not_zero_and_records_are_unchanged(self):
        self.spend("2025-10", "10"); self.spend("2025-12", "30")
        self.spend("2026-01", "999"); self.spend("2026-02", "999")
        before = list(Expense.objects.values())
        result = service.forecast_finances(self.owner)
        self.assertEqual(result["current_monthly_expense_avg"], 20)
        self.assertEqual([r["month"] for r in result["observations"]], ["2025-10", "2025-12"])
        self.assertEqual(result["uncertainty"]["status"], "UNAVAILABLE")
        self.assertEqual(before, list(Expense.objects.values()))

    def test_uncertainty_is_observed_range_not_an_invented_prediction_interval(self):
        for month, amount in (("2025-10", "10"), ("2025-11", "20"), ("2025-12", "30")):
            self.spend(month, amount)
        result = service.forecast_finances(self.owner)
        uncertainty = result["uncertainty"]
        self.assertEqual(uncertainty["status"], "HISTORICAL_RANGE")
        self.assertEqual((uncertainty["expense_low"], uncertainty["expense_high"]), (10, 30))
        self.assertEqual((uncertainty["savings_low"], uncertainty["savings_high"]), (60, 80))
        self.assertIn("not a prediction interval", uncertainty["method"])
        self.assertIsNone(uncertainty["coverage_probability"])

    def test_walk_forward_holdouts_use_only_earlier_observations(self):
        rows = [self.spend(f"2025-{month:02}", str(amount)) for month, amount in zip(range(7, 13), range(10, 70, 10))]
        first = service.forecast_finances(self.owner)["backtest"]
        self.assertEqual(first["status"], "OBSERVED_ERROR")
        self.assertEqual(first["samples"], 3)
        self.assertEqual(first["mae"], 20)
        self.assertEqual(first["holdouts"][-1]["predicted_expense"], 40)
        for row in first["holdouts"]:
            self.assertLess(row["training_through"], row["month"])
        rows[-1].amount = "600"; rows[-1].save()
        second = service.forecast_finances(self.owner)["backtest"]
        self.assertEqual(second["holdouts"][-1]["predicted_expense"], 40)
        self.assertGreater(second["mae"], first["mae"])

    def test_canonical_directions_fixed_bills_future_income_and_ownership(self):
        self.spend("2025-11", "10"); self.spend("2025-12", "20")
        for category, direction in (("transfer", "debit"), ("loan", "debit"), ("food", "credit")):
            self.spend("2025-12", "1000", category=category, direction=direction)
        self.spend("2025-12", "10", category="rent")
        self.spend("2026-02", "999999", category="income", direction="credit")
        self.spend("2025-12", "999999", user=self.other)
        result = service.forecast_finances(self.owner)
        self.assertEqual(result["current_monthly_expense_avg"], 15)
        self.assertEqual(result["forecasts"][0]["predicted_savings"], 75)
        self.assertEqual(result["financial_baseline"]["monthly_income"], 100)

    def test_income_absence_abstains_and_a_known_zero_can_show_a_deficit(self):
        self.spend("2025-12", "20", user=self.other)
        result = service.forecast_finances(self.other)
        self.assertEqual(result["forecasts"], [])
        self.spend("2025-12", "20")
        baseline = {"monthly_income": 0, "fixed_obligations": 10,
            "metric_states": {"monthly_income": {"status": "reported"}}}
        with patch("apps.budgets.services.budget_intelligence.resolve_canonical_financial_baseline", return_value=baseline):
            self.assertEqual(service.forecast_finances(self.owner)["forecasts"][0]["predicted_savings"], -30)

    def test_dated_forecast_does_not_replace_the_ordinary_cached_baseline(self):
        from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
        self.spend("2025-12", "20"); self.spend("2026-02", "999999")
        before = resolve_canonical_financial_baseline(self.owner)
        self.assertEqual(service.forecast_finances(self.owner)["current_monthly_expense_avg"], 20)
        self.assertEqual(resolve_canonical_financial_baseline(self.owner), before)

    def test_horizon_is_bounded_and_integral(self):
        for value in (0, -1, 25, True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                service.forecast_finances(self.owner, months_ahead=value)

    def test_break_even_is_not_mislabeled_negative(self):
        self.spend("2025-12", "90")
        result = service.forecast_finances(self.owner)
        self.assertEqual(result["forecasts"][0]["predicted_savings"], 0)
        self.assertIn("breaks even", " ".join(result["insights"]))

    def test_dashboard_exposes_owned_method_and_explicit_unavailable_states(self):
        self.spend("2025-12", "20")
        self.client.force_login(self.owner)
        data = self.client.get("/api/budgets/dashboard/").json()
        self.assertEqual(data["forecast_evidence"]["observations"][0]["month"], "2025-12")
        self.assertEqual(data["forecast_evidence"]["backtest"]["status"], "UNAVAILABLE")
        self.assertEqual(Client().get("/api/budgets/dashboard/").status_code, 403)
        self.client.force_login(self.other)
        foreign = self.client.get("/api/budgets/dashboard/").json()
        self.assertEqual(foreign["forecast"], [])
        self.assertEqual(foreign["forecast_evidence"]["observations"], [])
