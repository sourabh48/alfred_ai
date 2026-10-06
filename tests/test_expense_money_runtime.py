from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase
from rest_framework.test import APIClient

from apps.expenses.models import BankAccount, BankAccountMoneySnapshot, Expense, ExpenseMoneySnapshot, StatementUpload
from apps.expenses.money import expense_money, money_float
from apps.expenses.serializers import BankAccountSerializer, ExpenseSerializer
from apps.expenses.services.transaction_intelligence import build_transaction_fingerprint, sync_account_balance
from apps.expenses.services.statement_lifecycle import apply_parsed_statement_upload
from apps.users.services import clear_user_fed_data
from tests.test_expense_money_identity import parsed_fixture


class ExpenseMoneyRuntimeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="expense-money-owner")
        self.context = {"request": SimpleNamespace(user=self.user)}
        self.predict = patch("apps.expenses.services.transaction_intelligence.alfred_engine.predict_emotional_spend", return_value={"confidence": .1, "is_emotional": False})
        self.predict.start()
        self.addCleanup(self.predict.stop)

    def test_orm_rounds_required_and_nullable_currency_to_decimal_cents(self):
        account = BankAccount.objects.create(user=self.user, account_number="MONEY0001", current_balance="10.005")
        row = Expense.objects.create(user=self.user, bank_account=account, amount="2.675", closing_balance="-1.005")
        account.refresh_from_db()
        row.refresh_from_db()
        self.assertEqual(row.amount, Decimal("2.68"))
        self.assertEqual(row.closing_balance, Decimal("-1.01"))
        self.assertEqual(account.current_balance, Decimal("10.01"))
        self.assertIsInstance(row.amount, Decimal)

    def test_serializer_currency_is_half_up_numeric_and_keeps_null_zero(self):
        serializer = ExpenseSerializer(data={"amount": "2.675", "closing_balance": "0.005", "raw_description": "Synthetic purchase"}, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        row = serializer.save(user=self.user)
        row.refresh_from_db()
        self.assertEqual(row.amount, Decimal("2.68"))
        self.assertEqual(row.closing_balance, Decimal("0.01"))
        self.assertIsInstance(ExpenseSerializer(row).data["amount"], float)
        for balance in (None, 0):
            account = BankAccountSerializer(data={"account_number": f"NULL{balance}", "current_balance": balance})
            self.assertTrue(account.is_valid(), account.errors)
            saved = account.save(user=self.user)
            saved.refresh_from_db()
            self.assertEqual(saved.current_balance, None if balance is None else Decimal("0.00"))

    def test_invalid_currency_is_rejected_at_api_boundaries(self):
        for value in (True, "NaN", "Infinity", "1e100", "999999999999.995"):
            with self.subTest(value=value):
                self.assertFalse(ExpenseSerializer(data={"amount": value}, context=self.context).is_valid())
                self.assertFalse(BankAccountSerializer(data={"account_number": "BAD", "current_balance": value}).is_valid())

    def test_metadata_edit_preserves_raw_half_cent_fingerprint(self):
        account = BankAccount.objects.create(user=self.user, account_number="MONEY0002")
        serializer = ExpenseSerializer(data={"amount": "2.675", "closing_balance": "10.005", "bank_account": account.pk, "raw_description": "Synthetic purchase"}, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        row = serializer.save(user=self.user)
        before = row.transaction_fingerprint
        expected = build_transaction_fingerprint(bank_account=account, transaction_date=row.transaction_date, amount=2.675, direction="debit", raw_description="Synthetic purchase", closing_balance=10.005)
        self.assertEqual(before, expected)
        row.refresh_from_db()
        correction = ExpenseSerializer(row, data={"category": "food"}, partial=True, context=self.context)
        self.assertTrue(correction.is_valid(), correction.errors)
        correction.save()
        row.refresh_from_db()
        self.assertEqual(row.transaction_fingerprint, before)
        self.assertEqual(row.amount, Decimal("2.68"))

    def test_resubmitted_displayed_amount_keeps_identity_but_real_edit_replaces_it(self):
        serializer = ExpenseSerializer(data={"amount": "2.675", "closing_balance": "10.005", "raw_description": "Synthetic purchase"}, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        row = serializer.save(user=self.user)
        row.refresh_from_db()
        fingerprint, identity = row.transaction_fingerprint, row.transaction_identity
        update = ExpenseSerializer(row, data={"amount": "2.68", "closing_balance": "10.01", "category": "food"}, partial=True, context=self.context)
        self.assertTrue(update.is_valid(), update.errors)
        update.save()
        row.refresh_from_db()
        self.assertEqual((row.transaction_fingerprint, row.transaction_identity), (fingerprint, identity))
        update = ExpenseSerializer(row, data={"amount": "3.335", "closing_balance": None}, partial=True, context=self.context)
        self.assertTrue(update.is_valid(), update.errors)
        update.save()
        row.refresh_from_db()
        self.assertEqual((row.amount, row.closing_balance), (Decimal("3.34"), None))
        self.assertEqual(row.transaction_identity, {"amount": "3.335", "closing_balance": None})
        self.assertNotEqual(row.transaction_fingerprint, fingerprint)

    def test_invalid_orm_and_statement_amounts_do_not_mutate_accounts_or_uploads(self):
        account = BankAccount.objects.create(user=self.user, account_number="TEST0001", current_balance=20)
        for value in (True, "NaN", "Infinity", "1e100", "999999999999.995"):
            with self.subTest(value=value), self.assertRaises(ValidationError), transaction.atomic():
                Expense.objects.create(user=self.user, amount=value)
        parsed = parsed_fixture()
        parsed.transactions.append(parsed_fixture(amount=float("inf")).transactions[0])
        with self.assertRaises(ValueError):
            apply_parsed_statement_upload(user=self.user, parsed=parsed, statement_kind="bank_statement")
        account.refresh_from_db()
        self.assertEqual(account.current_balance, Decimal("20.00"))
        self.assertFalse(Expense.objects.exists())
        self.assertFalse(StatementUpload.objects.exists())

    def test_api_rolls_back_expense_when_balance_posting_fails(self):
        client = APIClient()
        client.force_authenticate(self.user)
        account = BankAccount.objects.create(user=self.user, account_number="ATOMIC", current_balance=20)
        with patch("apps.expenses.views.sync_account_balance", side_effect=ValueError("posting failed")):
            with self.assertRaises(ValueError):
                client.post("/api/expenses/", {"amount": "1.005", "closing_balance": "10.005", "bank_account": account.pk}, format="json")
        account.refresh_from_db()
        self.assertFalse(Expense.objects.exists())
        self.assertEqual(account.current_balance, Decimal("20.00"))

    def test_balance_sync_distinguishes_unknown_and_zero(self):
        account = BankAccount.objects.create(user=self.user, account_number="SYNC", current_balance=20)
        sync_account_balance(account, None)
        account.refresh_from_db()
        self.assertEqual(account.current_balance, Decimal("20.00"))
        sync_account_balance(account, 0)
        account.refresh_from_db()
        self.assertEqual(account.current_balance, Decimal("0.00"))
        sync_account_balance(account, "-1.005")
        account.refresh_from_db()
        self.assertEqual(account.current_balance, Decimal("-1.01"))

    def test_exact_aggregates_numeric_api_and_virtual_totals_above_field_bound(self):
        client = APIClient()
        client.force_authenticate(self.user)
        for amount in ("0.10", "0.20"):
            Expense.objects.create(user=self.user, amount=amount, category="food")
        for path in ("timeline/", "chart/", "dashboard/"):
            response = client.get("/api/expenses/" + path)
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            if path == "chart/":
                self.assertEqual(payload["expense_values"], [0.3])
            elif path == "timeline/":
                self.assertEqual(payload["summary"]["expense_total"], 0.3)
            else:
                self.assertEqual(payload["summary"]["history_outflow"], 0.3)
        for number in ("MAX1", "MAX2"):
            BankAccount.objects.create(user=self.user, account_number=number, current_balance="999999999999.99")
        from apps.expenses.services.financial_intelligence import _build_balance_sheet
        self.assertEqual(_build_balance_sheet(user=self.user, loans=[])["assets"][0]["amount"], 1999999999999.98)
        self.assertEqual(money_float(Decimal("1999999999999.98")), 1999999999999.98)
        self.assertEqual(expense_money("-1.005"), Decimal("-1.01"))
        from apps.expenses.services.multi_bank_aggregator import MultiBankAggregatorService
        consolidated = MultiBankAggregatorService().get_consolidated_view(self.user)
        self.assertEqual(consolidated["total_balance"], 1999999999999.98)
        self.assertIsInstance(consolidated["accounts"][0]["balance"], float)

    def test_reset_deletes_owned_orphan_snapshots_only(self):
        other = get_user_model().objects.create_user(username="expense-money-other")
        for owner in (self.user, other):
            account = BankAccount.objects.create(user=owner, account_number="RESET")
            row = Expense.objects.create(user=owner, amount=1, bank_account=account)
            ExpenseMoneySnapshot.objects.create(user=owner, expense=row, original_expense_id=row.pk, source_values={}, normalized_values={})
            BankAccountMoneySnapshot.objects.create(user=owner, bank_account=account, original_bank_account_id=account.pk, source_values={}, normalized_values={})
            if owner == self.user:
                row.delete()
                account.delete()
        result = clear_user_fed_data(self.user)
        self.assertEqual((result["expense_money_snapshots"], result["bank_account_money_snapshots"]), (1, 1))
        for Snapshot in (ExpenseMoneySnapshot, BankAccountMoneySnapshot):
            self.assertFalse(Snapshot.objects.filter(user=self.user).exists())
            self.assertEqual(Snapshot.objects.filter(user=other).count(), 1)
