"""Independent arithmetic and isolation checks for a realistic signed-up user."""
import json
import os
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from apps.expenses.models import BankAccount
from apps.loans.models import Loan
from alfred_ai.services.materialized_cache import invalidate_user_materialized_payloads, materialize_payload
from scripts.exercise_materialized_cache_traffic import _offline_fixture_patches
from tests.user_acceptance_scenario import seed_acceptance_user, month_start


class UserDataAcceptanceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.offline = _offline_fixture_patches()
        self.addCleanup(self.offline.close)
        self.scenario = seed_acceptance_user(self.client)

    def get_payload(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, response.content[:2000])
        return response.json()

    def test_inflight_old_response_cannot_repopulate_cache_after_a_write(self):
        user_id = self.scenario["user"].pk

        def old_snapshot():
            invalidate_user_materialized_payloads(user_id, reason="concurrent_edit")
            return {"amount": 6000}

        materialize_payload(namespace="financial-intelligence", user_id=user_id,
            revision="same-row-count", ttl_seconds=45, builder=old_snapshot)
        fresh = materialize_payload(namespace="financial-intelligence", user_id=user_id,
            revision="same-row-count", ttl_seconds=45, builder=lambda: {"amount": 7000})
        self.assertEqual(fresh["amount"], 7000)

    def test_sample_financial_totals_and_cross_module_consistency(self):
        dashboard = self.get_payload("/api/expenses/dashboard/")
        budget = self.get_payload("/api/budgets/dashboard/")
        networth = self.get_payload("/api/loans/networth/")
        investment = self.get_payload("/api/investments/summary/")
        if os.environ.get("ALFRED_ACCEPTANCE_REPORT"):
            path = Path(os.environ["ALFRED_ACCEPTANCE_REPORT"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"synthetic": True, "dashboard": dashboard,
                "budget": budget, "networth": networth, "investment": investment},
                indent=2, default=str), encoding="utf-8")
        expected_summary = {
            "current_month_income": 80000, "current_month_expense": 30000,
            "current_month_loans": 10000, "current_month_investments": 5000,
            "current_month_credit_card_payments": 2000, "current_month_outflow": 47000,
            "current_month_net": 33000, "current_month_review_required": 60000,
            "current_month_transfer_in": 10000, "current_month_transfer_out": 10000,
            "savings_rate": 48.8,
        }
        for key, value in expected_summary.items():
            with self.subTest(metric=key):
                self.assertEqual(dashboard["summary"][key], value)
        expected_baseline = {
            "monthly_income": 80000, "fixed_obligations": 30000,
            "disposable_cash_flow": 50000, "current_month_variable_spend": 10000,
            "observed_average_monthly_variable_spend": 8666.67,
            "savings_capacity": 41333.33, "essential_monthly_outflow": 38666.67,
            "liquid_runway_months": 3.88, "net_worth": 160000,
            "total_assets": 260000, "total_liabilities": 100000,
        }
        for key, value in expected_baseline.items():
            with self.subTest(baseline=key):
                self.assertEqual(dashboard["baseline"][key], value)
                self.assertEqual(budget["financial_baseline"][key], value)
        self.assertEqual(networth["net_worth"], 160000)
        self.assertEqual(investment["summary"]["total_value"], 110000)
        self.assertEqual(investment["summary"]["gain_loss"], 10000)

    def test_budget_and_daily_guidance_use_the_same_flexible_spend(self):
        budget = self.get_payload("/api/budgets/dashboard/")
        self.assertEqual(budget["summary"]["total_budget"], 30000)
        self.assertEqual(budget["summary"]["total_spent"], 10000)
        self.assertEqual(budget["summary"]["total_remaining"], 20000)
        self.assertEqual(sum(item["spent"] for item in budget["budgets"]), 10000)
        self.assertEqual(budget["daily_affordability"]["remaining_budget"], 20000)
        self.assertEqual(budget["forecast"][0]["predicted_expense"], 8666.67)
        self.assertEqual(budget["forecast"][0]["predicted_savings"], 41333.33)

    def test_edits_refresh_cached_dashboard_and_networth(self):
        self.get_payload("/api/expenses/dashboard/")
        self.get_payload("/api/loans/networth/")
        groceries = self.scenario["transactions"]["0:groceries"]["id"]
        response = self.client.patch(f"/api/expenses/{groceries}/", {"amount": 7000}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        dashboard = self.get_payload("/api/expenses/dashboard/")
        self.assertEqual(dashboard["summary"]["current_month_expense"], 31000)
        self.assertEqual(dashboard["summary"]["current_month_net"], 32000)
        account = self.scenario["account"]["id"]
        response = self.client.patch(f"/api/expenses/accounts/{account}/", {"current_balance": 160000}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_payload("/api/loans/networth/")["net_worth"], 170000)
        investment = self.scenario["investment"]["id"]
        self.assertEqual(self.client.patch(f"/api/investments/{investment}/", {"current_value": 120000}, content_type="application/json").status_code, 200)
        self.assertEqual(self.get_payload("/api/loans/networth/")["net_worth"], 180000)
        self.assertEqual(self.client.delete(f"/api/expenses/{groceries}/").status_code, 204)
        self.assertEqual(self.get_payload("/api/budgets/dashboard/")["summary"]["total_spent"], 4000)

    def test_rent_allowance_is_applied_once_and_excess_is_counted(self):
        rent = self.scenario["transactions"]["0:rent"]["id"]
        self.assertEqual(self.client.patch(f"/api/expenses/{rent}/", {"amount": 12000}, content_type="application/json").status_code, 200)
        self.assertEqual(self.client.post("/api/expenses/", {
            "amount": 13000, "category": "rent", "classification": "expense",
            "description": "Second rent payment", "transaction_date": str(month_start()),
        }, content_type="application/json").status_code, 201)
        self.assertEqual(self.get_payload("/api/budgets/dashboard/")["summary"]["total_spent"], 15000)
        self.assertEqual(self.client.patch("/api/users/profile/", {"rent_or_emi": 0}, content_type="application/json").status_code, 200)
        self.assertEqual(self.get_payload("/api/budgets/dashboard/")["summary"]["total_spent"], 35000)

    def test_current_month_plan_is_used_even_when_an_older_plan_is_saved_later(self):
        self.assertEqual(self.client.post("/api/budgets/", {
            "month": month_start(-1).strftime("%Y-%m"), "base_budget": 90000, "inflation_adjusted": 90000,
        }, content_type="application/json").status_code, 201)
        self.assertEqual(self.get_payload("/api/budgets/dashboard/")["summary"]["total_budget"], 30000)
        plan = self.scenario["budget"]["id"]
        self.assertEqual(self.client.patch(f"/api/budgets/{plan}/", {"inflation_adjusted": 0}, content_type="application/json").status_code, 200)
        budget = self.get_payload("/api/budgets/dashboard/")
        self.assertEqual(budget["summary"]["total_budget"], 0)
        self.assertEqual(budget["daily_affordability"]["remaining_budget"], -10000)
        for update in ({"base_budget": -1}, {"inflation_adjusted": "Infinity"}, {"month": "whenever"}):
            with self.subTest(update=update):
                self.assertEqual(self.client.patch(f"/api/budgets/{plan}/", update, content_type="application/json").status_code, 400)

    def test_minimal_expense_uses_defaults_and_category_only_edits_refresh_totals(self):
        response = self.client.post("/api/expenses/", {"amount": 100}, content_type="application/json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(response.json()["payment_mode"])
        self.get_payload("/api/expenses/dashboard/")
        transfer = self.scenario["transactions"]["0:transfer_out"]["id"]
        response = self.client.patch(f"/api/expenses/{transfer}/", {"category": "groceries", "classification": "expense"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_payload("/api/expenses/dashboard/")["summary"]["current_month_transfer_out"], 0)

    def test_other_users_records_are_private_and_cannot_be_linked(self):
        other = get_user_model().objects.create_user(username="separate_demo", password="Different936!")
        foreign_account = BankAccount.objects.create(user=other, bank_name="Private", account_number="PRIVATE999")
        response = self.client.post("/api/expenses/", {
            "amount": 100, "category": "groceries", "classification": "expense",
            "bank_account": foreign_account.pk,
        }, content_type="application/json")
        self.assertEqual(response.status_code, 400, "A user must not link someone else's account")
        foreign_loan = Loan.objects.create(user=other, lender="Private", principal=10000, emi=1000,
            interest_rate=8, tenure_months=12, start_date=month_start())
        loan = self.scenario["loan"]["id"]
        self.assertEqual(self.client.patch(f"/api/loans/{loan}/", {"consolidated_into": foreign_loan.pk}, content_type="application/json").status_code, 400)
        self.assertEqual(self.client.patch(f"/api/loans/{loan}/", {"consolidated_into": loan}, content_type="application/json").status_code, 400)
        self.client.force_login(other)
        dashboard = self.get_payload("/api/expenses/dashboard/")
        self.assertEqual(dashboard["summary"]["transactions"], 0)
        self.assertEqual(dashboard["summary"]["current_month_income"], 0)
        foreign_loan.delete()
        self.assertEqual(self.get_payload("/api/loans/networth/")["health"]["status"], "No data")
        for path in (
            f'/api/expenses/{self.scenario["transactions"]["0:groceries"]["id"]}/',
            f'/api/expenses/accounts/{self.scenario["account"]["id"]}/',
            f'/api/loans/{self.scenario["loan"]["id"]}/',
            f'/api/investments/{self.scenario["investment"]["id"]}/',
            f'/api/budgets/{self.scenario["budget"]["id"]}/',
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)
