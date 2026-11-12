"""Overdrawn non-credit accounts are a liability, not zero cash; synthetic data only."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.expenses.models import BankAccount
from apps.expenses.services.financial_intelligence import _build_balance_sheet


class OverdraftNetWorthTests(TestCase):
    def test_negative_savings_balance_is_counted_as_overdrawn_liability(self):
        user = get_user_model().objects.create_user(username="synthetic-overdraft-owner")
        BankAccount.objects.create(user=user, account_number="SYNOD0001", account_type="savings", current_balance="1000.00")
        BankAccount.objects.create(user=user, account_number="SYNOD0002", account_type="current", current_balance="-250.50")
        BankAccount.objects.create(user=user, account_number="SYNOD0003", account_type="credit", current_balance="-100.00")
        sheet = _build_balance_sheet(user=user, loans=[])
        self.assertEqual(sheet["assets"][0], {"label": "Cash and bank balances", "amount": 1000.0})
        liabilities = {row["label"]: row["amount"] for row in sheet["liabilities"]}
        self.assertEqual(liabilities, {"Credit card liability": 100.0, "Overdrawn accounts": 250.5})
        self.assertEqual(sheet["net_worth"], 649.5)


class InvestmentAccountNetWorthTests(TestCase):
    def test_investment_accounts_are_not_cash_and_count_only_when_no_record_covers_them(self):
        from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
        from apps.investments.models import Investment
        user = get_user_model().objects.create_user(username="synthetic-invest-account-owner")
        BankAccount.objects.create(user=user, account_number="SYNCASH01", account_type="savings", current_balance="500.00")
        # Covered by the investment record below: must not be counted twice.
        BankAccount.objects.create(user=user, account_number="SYN-DEMAT-01", account_type="investment", current_balance="9000.00")
        BankAccount.objects.create(user=user, account_number="SYNDEMAT02", account_type="investment", current_balance="300.00")
        Investment.objects.create(user=user, asset_type="stock", asset_name="Synthetic holding", account_number="SYNDEMAT01",
                                  current_value="10000.00", currency="INR")
        sheet = _build_balance_sheet(user=user, loans=[])
        cash, investments = sheet["assets"][0], sheet["assets"][1]
        self.assertEqual(cash["amount"], 500.0)
        self.assertEqual(investments["amount"], 10300.0)
        self.assertEqual([(row["source"], row["count"], row["amount"]) for row in investments["sources"]],
                         [("investment_records", 1, 10000.0), ("investment_accounts", 1, 300.0)])
        self.assertIn("investment-type bank accounts", investments["note"])
        self.assertEqual(resolve_canonical_financial_baseline(user, fresh=True)["liquid_cash"], 500.0)
