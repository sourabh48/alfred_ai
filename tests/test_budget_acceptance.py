"""Synthetic budget lifecycle and independent cents/affordability checks."""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

from apps.budgets.models import Budget
from apps.budgets.services.budget_intelligence import budget_intelligence_service
from apps.expenses.models import Expense


class BudgetAcceptanceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = get_user_model().objects.create_user("budget_acceptance_owner", monthly_income="1200000", rent_or_emi="10000")
        self.other = get_user_model().objects.create_user("budget_acceptance_other")
        self.owner.refresh_from_db()
        self.other.refresh_from_db()
        self.client.force_login(self.owner)
        self.today = date(2026, 4, 29)
        self.enterContext(patch("django.utils.timezone.localdate", return_value=self.today))

    def plan(self, limit, month="Apr 2026", user=None):
        return Budget.objects.create(user=user or self.owner, month=month, base_budget=limit, inflation_adjusted=limit)

    def dashboard(self):
        response = self.client.get("/api/budgets/dashboard/")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_half_up_daily_guide_keeps_cents_and_remaining_days(self):
        self.plan("5.35")
        guide = budget_intelligence_service.calculate_daily_affordability(self.owner)
        self.assertEqual(guide["safe_daily_spend"], 2.68)
        self.assertEqual(guide["remaining_budget"], 5.35)
        self.assertEqual(guide["days_remaining"], 2)

    def test_category_limits_conserve_the_plan_to_the_cent(self):
        self.plan("0.05")
        suggestions = {"disposable_income": 90000, "category_budgets": {
            key: {"suggested": 1, "historical_avg": 0} for key in ("food", "groceries", "travel")}}
        with patch.object(budget_intelligence_service, "suggest_budget", return_value=suggestions):
            data = self.dashboard()
        limits = {r["category"]: Decimal(str(r["limit"])) for r in data["budgets"]}
        self.assertEqual(sum(limits.values()), Decimal("0.05"))
        self.assertEqual(limits, {"food": Decimal("0.02"), "groceries": Decimal("0.02"), "travel": Decimal("0.01")})

    def test_unknown_income_abstains_without_a_plan_and_qualifies_an_explicit_plan(self):
        self.client.force_login(self.other)
        guide = self.dashboard()["daily_affordability"]
        self.assertEqual(guide["status"], "UNAVAILABLE")
        self.assertIsNone(guide["safe_daily_spend"])
        self.plan("10.00", user=self.other)
        guide = self.dashboard()["daily_affordability"]
        self.assertEqual(guide["status"], "PLAN_ONLY")
        self.assertEqual(guide["safe_daily_spend"], 5)
        self.assertIn("income", guide["message"].lower())

    def test_plan_above_disposable_cash_flow_warns_instead_of_confirming_affordability(self):
        self.plan("100000")
        guide = self.dashboard()["daily_affordability"]
        self.assertEqual(guide["status"], "WARNING")
        self.assertIn("exceeds", guide["message"].lower())
        self.assertEqual(guide["financial_baseline"]["disposable_cash_flow"], 90000)

    def test_zero_plan_and_overspend_preserve_negative_remaining_and_unknown_utilization(self):
        self.plan("0")
        Expense.objects.create(user=self.owner, amount="0.01", category="food", transaction_date=self.today)
        data = self.dashboard()
        self.assertEqual(data["summary"]["total_remaining"], -.01)
        self.assertIsNone(data["summary"]["percent_used"])
        self.assertEqual(data["daily_affordability"]["status"], "OVER_BUDGET")
        self.assertEqual(data["daily_affordability"]["safe_daily_spend"], 0)

    def test_month_formats_leap_boundary_and_owner_history_do_not_reuse_old_plans(self):
        self.plan("999", month="Mar 2026")
        active = self.plan("20", month="2026-04")
        self.plan("500", month="May 2026")
        self.plan("9999", user=self.other)
        self.assertEqual(self.dashboard()["plan"]["id"], active.pk)
        for day, days_left in ((date(2028, 2, 28), 2), (date(2028, 2, 29), 1), (date(2026, 12, 31), 1)):
            with self.subTest(date=day), patch("django.utils.timezone.localdate", return_value=day):
                self.assertEqual(budget_intelligence_service.calculate_daily_affordability(self.owner)["days_remaining"], days_left)

    def test_cache_corrections_and_cashflow_boundaries_preserve_registers(self):
        plan = self.plan("10")
        plan.spent = Decimal("999.99"); plan.save()
        food = Expense.objects.create(user=self.owner, amount="2.68", category="food", transaction_date=self.today)
        for user, category, direction, day in ((self.owner,"transfer","debit",self.today),
                (self.owner,"food","credit",self.today), (self.owner,"rent","debit",self.today),
                (self.other,"food","debit",self.today), (self.owner,"food","debit",date(2026,3,31)),
                (self.owner,"food","debit",self.today+timedelta(days=1))):
            Expense.objects.create(user=user, amount="100", category=category, direction=direction, transaction_date=day)
        before = list(Expense.objects.values())
        data = self.dashboard()
        self.assertEqual(data["summary"]["total_spent"], 2.68)
        self.assertEqual(data["summary"]["total_remaining"], 7.32)
        self.assertEqual(list(Expense.objects.values()), before)
        self.assertEqual(self.client.patch(f"/api/budgets/{plan.pk}/", {"inflation_adjusted":"20.01"}, content_type="application/json").status_code, 200)
        self.assertEqual(self.dashboard()["summary"]["total_remaining"], 17.33)
        self.assertEqual(self.client.patch(f"/api/expenses/{food.pk}/", {"amount":"3.01"}, content_type="application/json").status_code, 200)
        self.assertEqual(self.dashboard()["summary"]["total_remaining"], 17)
        plan.refresh_from_db(); self.assertEqual(plan.spent, Decimal("999.99"))

    def test_owner_crud_and_csrf_preserve_foreign_plans(self):
        foreign = self.plan("77", user=self.other)
        csrf = Client(enforce_csrf_checks=True); csrf.force_login(self.owner)
        self.assertEqual(csrf.post("/api/budgets/", {"month":"2026-04","base_budget":10,"inflation_adjusted":10}).status_code, 403)
        self.assertEqual(self.client.delete(f"/api/budgets/{foreign.pk}/").status_code, 404)
        own = self.plan("10")
        self.assertEqual(self.client.delete(f"/api/budgets/{own.pk}/").status_code, 204)
        self.assertTrue(Budget.objects.filter(pk=foreign.pk).exists())

    def test_allocation_zero_large_virtual_totals_and_service_suggestions_reconcile(self):
        from apps.budgets.money import allocate_budget
        self.assertEqual(allocate_budget("10", {"food":0}), {"food":Decimal("0")})
        self.assertEqual(allocate_budget("0", {"food":1}), {"food":Decimal("0.00")})
        limits = allocate_budget("1000000000000.01", {"food":1,"travel":1})
        self.assertEqual(sum(limits.values()),Decimal("1000000000000.01"))
        self.assertEqual(limits["food"],Decimal("500000000000.01"))
        for weight in ("-1","NaN","Infinity"):
            with self.subTest(weight=weight), self.assertRaises(ValueError):
                allocate_budget("10", {"food":weight})
        suggestions = budget_intelligence_service.suggest_budget(self.owner)
        self.assertEqual(sum(Decimal(str(v["suggested"])) for v in suggestions["category_budgets"].values()),Decimal("90000"))

    def test_forecast_failure_does_not_discard_independent_budget_guidance(self):
        self.plan("5.35")
        with patch.object(budget_intelligence_service, "forecast_finances", side_effect=RuntimeError("Synthetic forecast outage")):
            data = self.dashboard()
        self.assertEqual(data["daily_affordability"]["safe_daily_spend"], 2.68)
        self.assertEqual(data["summary"]["fixed_obligations"], 10000)
        self.assertEqual(data["forecast"], [])
        self.assertEqual(data["unavailable_sections"], ["forecast"])

    def test_missing_income_does_not_erase_evidenced_fixed_obligations(self):
        self.other.rent_or_emi = Decimal("25.01"); self.other.save()
        self.client.force_login(self.other)
        data = self.dashboard()
        self.assertEqual(data["financial_baseline"]["fixed_obligations"], 25.01)
        self.assertEqual(data["summary"]["fixed_obligations"], 25.01)
