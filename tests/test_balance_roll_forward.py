from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.expenses.models import BankAccount, Expense
from apps.expenses.services.balance_roll_forward import balance_roll_forward


class BalanceRollForwardTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("roll-owner", password="synthetic-pass-1")
        self.other = User.objects.create_user("roll-other", password="synthetic-pass-2")
        self.account = BankAccount.objects.create(user=self.owner, account_number="TEST-ROLL-1", currency="INR",
                                                  current_balance="10000.00")
        self.row(date(2026, 10, 1), "300.00", "debit", closing="10300.00")  # older statement row, superseded
        self.row(date(2026, 11, 1), "100.00", "debit", closing="10000.00")  # the anchor

    def row(self, day, amount, direction, *, closing=None, user=None, currency="INR", account=None):
        return Expense.objects.create(user=user or self.owner, bank_account=account or self.account, amount=amount,
                                      direction=direction, transaction_date=day, closing_balance=closing,
                                      currency=currency, source="bank_statement" if closing else "manual")

    def test_only_entries_after_the_statement_day_are_rolled_forward(self):
        self.row(date(2026, 11, 1), "999.00", "debit")  # same day: order against the closing balance unknown
        self.row(date(2026, 10, 20), "777.00", "debit")  # before the anchor: already inside its balance
        self.row(date(2026, 11, 3), "500.10", "debit")
        self.row(date(2026, 11, 5), "2000.00", "credit")
        self.row(date(2026, 11, 6), "50000.00", "credit", user=self.other)  # another owner's row is never counted
        result = balance_roll_forward(self.account)
        self.assertEqual(result["status"], "estimated")
        self.assertEqual((result["anchor_date"], result["entries"], result["same_day_not_counted"]), ("2026-11-01", 2, 1))
        self.assertEqual((result["credits"], result["debits"]), (Decimal("2000.00"), Decimal("500.10")))
        self.assertEqual(result["estimated_balance"], Decimal("11499.90"))

    def test_no_later_entries_keeps_the_statement_balance(self):
        result = balance_roll_forward(self.account)
        self.assertEqual((result["status"], result["estimated_balance"]), ("no_newer_entries", Decimal("10000.00")))

    def test_hand_edited_balance_other_currency_cards_and_no_statement_abstain(self):
        self.account.current_balance = Decimal("12000.00"); self.account.save()
        self.assertEqual(balance_roll_forward(self.account)["status"], "unavailable")
        self.account.current_balance = Decimal("10000.00"); self.account.save()
        self.row(date(2026, 11, 4), "10.00", "debit", currency="USD")
        self.assertIn("never converted", balance_roll_forward(self.account)["reason"])
        card = BankAccount.objects.create(user=self.owner, account_number="TEST-CARD", account_type="credit",
                                          current_balance="500.00")
        self.row(date(2026, 11, 1), "500.00", "debit", closing="500.00", account=card)
        self.assertEqual(balance_roll_forward(card)["status"], "unavailable")
        empty = BankAccount.objects.create(user=self.owner, account_number="TEST-EMPTY", current_balance="5.00")
        self.assertIn("No imported statement", balance_roll_forward(empty)["reason"])

    def test_api_shows_numbers_to_the_owner_only_and_writes_nothing(self):
        self.row(date(2026, 11, 3), "250.50", "debit")
        before = (Expense.objects.count(), BankAccount.objects.get(pk=self.account.pk).current_balance)
        self.client.force_login(self.owner)
        body = self.client.get(f"/api/expenses/accounts/{self.account.pk}/").json()["balance_since_statement"]
        self.assertEqual((body["status"], body["estimated_balance"], body["entries"]), ("estimated", 9749.5, 1))
        self.assertEqual(before, (Expense.objects.count(), BankAccount.objects.get(pk=self.account.pk).current_balance))
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(f"/api/expenses/accounts/{self.account.pk}/").status_code, 404)
