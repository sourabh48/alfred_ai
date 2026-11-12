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
