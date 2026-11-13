"""Home: plain figures from the canonical baseline, first-run steps and a read-only attention list."""
import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.budgets.models import Budget
from apps.career.models import CareerProfile
from apps.expenses.models import BankAccount, Expense


class HomePageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("synthetic-home", password="synthetic-pass-123")
        self.client.force_login(self.user)

    def home(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        return response

    def test_new_account_sees_what_to_add_instead_of_zero_figures(self):
        CareerProfile.objects.create(user=self.user, role="Profile pending", experience_years=0, skills="")  # Career's placeholder
        response = self.home()
        self.assertEqual([tile["amount"] for tile in response.context["glance"]], [None, None, None, None])
        self.assertContains(response, "Not added yet", count=4)
        self.assertContains(response, "Get started: 0 of 6 done")
        self.assertEqual([item["action"] for item in response.context["attention"]], ["Add key", "Add sign-in"])  # this account manages ALFRED

    def test_missing_keys_are_asked_for_only_from_the_manager_and_only_while_missing(self):
        keys = {"TRAVEL_GOOGLE_MAPS_API_KEY": "synthetic-google", "ALFRED_GOOGLE_CLIENT_ID": "synthetic-id", "ALFRED_GOOGLE_CLIENT_SECRET": "synthetic-secret"}
        with patch.dict(os.environ, keys):
            self.assertNotContains(self.home(), "Needs your attention")
        other = get_user_model().objects.create_user("synthetic-home-2", password="synthetic-pass-123")
        self.client.force_login(other)
        self.assertNotContains(self.home(), "Add your Google Maps Platform key")

    def test_figures_are_the_canonical_ones_and_reading_home_writes_nothing(self):
        self.user.monthly_income, self.user.monthly_income_basis = 100000, "monthly"
        self.user.save()
        today = timezone.localdate()
        account = BankAccount.objects.create(user=self.user, account_number="SYNHOME01", account_type="savings", current_balance="150000.00", currency="INR")
        BankAccount.objects.create(user=self.user, account_number="SYNHOME02", account_type="credit", current_balance="-30000.00", currency="INR")
        Expense.objects.create(user=self.user, bank_account=account, amount="12000.50", category="Groceries", transaction_date=today,
                               direction="debit", currency="INR")
        Budget.objects.create(user=self.user, month=today.strftime("%b %Y"), base_budget="10000.00", inflation_adjusted="10000.00", currency="INR")
        before = [list(model.objects.values()) for model in (BankAccount, Expense, Budget)]
        response = self.home()
        amounts = [tile["amount"] for tile in response.context["glance"]]
        self.assertEqual(amounts, [150000.0, 30000.0, 12000.5, 87999.5])  # 100,000 - 0 EMI - 12,000.50
        attention = response.context["attention"]
        self.assertEqual([(item["tone"], item["spent"], item["limit"]) for item in attention if "spent" in item],
                         [("danger", 12000.5, 10000)])
        self.assertContains(response, "over this month&#x27;s budget")
        self.assertEqual([list(model.objects.values()) for model in (BankAccount, Expense, Budget)], before)

    def test_budget_in_another_currency_is_not_compared_in_rupees(self):
        today = timezone.localdate()
        Budget.objects.create(user=self.user, month=today.strftime("%b %Y"), base_budget="1.00", inflation_adjusted="1.00", currency="USD")
        self.assertEqual([item for item in self.home().context["attention"] if "spent" in item], [])
