"""Isolated migration reconciliation, identity retention and rollback guards."""
from datetime import date
from decimal import Decimal
from importlib import import_module
from unittest.mock import patch

from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from apps.expenses.services.transaction_intelligence import build_transaction_fingerprint
from tests.test_expense_money_identity import parsed_fixture


class ExpenseMoneyMigrationTests(TransactionTestCase):
    migrate_from = ("expenses", "0004_statementupload_extracted_payload_and_more")
    migrate_to = ("expenses", "0005_expense_bank_money_decimal")

    def setUp(self):
        executor = MigrationExecutor(connection)
        self.leaves = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(self.leaves))
        self.old_targets = [self.migrate_from if node[0] == "expenses" else node for node in self.leaves]
        executor.migrate(self.old_targets)
        self.old = executor.loader.project_state(self.old_targets).apps
        self.user = self.old.get_model("users", "User").objects.create(username="expense-migration-owner")
        self.module = import_module("apps.expenses.migrations.0005_expense_bank_money_decimal")

    def seed(self, apps=None, alias="default", user=None):
        apps, user = apps or self.old, user or self.user
        account = apps.get_model("expenses", "BankAccount").objects.using(alias).create(user_id=user.pk, account_number="TEST0001", current_balance=-1.005)
        upload = apps.get_model("expenses", "StatementUpload").objects.using(alias).create(user_id=user.pk, bank_account_id=account.pk, file_name="synthetic.pdf", extracted_payload={"raw": "2.675;10.005"})
        fingerprint = build_transaction_fingerprint(bank_account=account, transaction_date=date(2026, 9, 1), amount=2.675, direction="debit", external_reference="REF-001", raw_description="UPI SAMPLE MERCHANT", closing_balance=10.005)
        row = apps.get_model("expenses", "Expense").objects.using(alias).create(user_id=user.pk, bank_account_id=account.pk, statement_upload_id=upload.pk, amount=2.675, closing_balance=10.005, source="bank_statement", transaction_date=date(2026, 9, 1), external_reference="REF-001", raw_description="UPI SAMPLE MERCHANT", transaction_fingerprint=fingerprint, model_confidence=.8123456)
        return account, upload, row

    def upgrade(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.leaves)
        return executor.loader.project_state(self.leaves).apps

    def test_reconciliation_preserves_all_identity_linkage_evidence_and_reference_dedup(self):
        account, upload, row = self.seed()
        before = {key: row.__dict__[key] for key in ("user_id", "bank_account_id", "statement_upload_id", "transaction_date", "transaction_fingerprint", "external_reference", "raw_description", "timestamp", "model_confidence")}
        apps = self.upgrade()
        New = apps.get_model("expenses", "Expense")
        converted = New.objects.get(pk=row.pk)
        self.assertEqual({key: converted.__dict__[key] for key in before}, before)
        self.assertEqual((converted.amount, converted.closing_balance), (Decimal("2.68"), Decimal("10.01")))
        self.assertEqual(converted.transaction_identity, {"amount": "2.675", "closing_balance": "10.005"})
        self.assertEqual(apps.get_model("expenses", "BankAccount").objects.get(pk=account.pk).current_balance, Decimal("-1.01"))
        self.assertEqual(apps.get_model("expenses", "StatementUpload").objects.get(pk=upload.pk).extracted_payload, upload.extracted_payload)
        for name in ("Expense", "BankAccount"):
            snapshot = apps.get_model("expenses", name + "MoneySnapshot").objects.get()
            self.assertIsNotNone(snapshot.applied_at)
            self.assertEqual(snapshot.user_id, self.user.pk)
        from apps.users.models import User
        from apps.expenses.models import BankAccount, StatementUpload
        from apps.expenses.services.statement_lifecycle import _import_statement_transactions
        with patch("apps.expenses.services.transaction_intelligence.alfred_engine.predict_emotional_spend", return_value={"confidence": .1, "is_emotional": False}):
            for closing in (10.005, 15.005):
                created, skipped = _import_statement_transactions(user=User.objects.get(pk=self.user.pk), upload=StatementUpload.objects.get(pk=upload.pk), bank_account=BankAccount.objects.get(pk=account.pk), parsed=parsed_fixture(closing=closing))
                self.assertEqual((len(created), skipped, New.objects.count()), (0, 1, 1))

    def test_repeat_capture_apply_is_immutable_and_rollback_preserves_edits_and_new_rows(self):
        account, _, row = self.seed()
        apps = self.upgrade()
        New = apps.get_model("expenses", "Expense")
        Snap = apps.get_model("expenses", "ExpenseMoneySnapshot")
        source = Snap.objects.get().source_values
        New.objects.filter(pk=row.pk).update(amount=30)
        fresh = New.objects.create(user_id=self.user.pk, amount=40)
        with connection.schema_editor() as editor:
            self.module.capture_legacy_money(apps, editor)
            self.module.apply_normalized_money(apps, editor)
            self.module.apply_normalized_money(apps, editor)
        self.assertEqual(New.objects.get(pk=row.pk).amount, 30)
        self.assertEqual(Snap.objects.get(original_expense_id=row.pk).source_values, source)
        MigrationExecutor(connection).migrate(self.old_targets)
        Old = self.old.get_model("expenses", "Expense")
        self.assertEqual((Old.objects.get(pk=row.pk).amount, Old.objects.get(pk=row.pk).closing_balance), (30, 10.005))
        self.assertEqual(Old.objects.get(pk=fresh.pk).amount, 40)
        self.assertEqual(self.old.get_model("expenses", "BankAccount").objects.get(pk=account.pk).current_balance, -1.005)

    def test_unapplied_changed_owner_and_orphan_evidence_do_not_restore(self):
        account, _, row = self.seed()
        apps = self.upgrade()
        other = apps.get_model("users", "User").objects.create(username="new-owner")
        apps.get_model("expenses", "Expense").objects.filter(pk=row.pk).update(user_id=other.pk)
        apps.get_model("expenses", "BankAccountMoneySnapshot").objects.filter(bank_account_id=account.pk).update(applied_at=None)
        orphan = apps.get_model("expenses", "Expense").objects.create(user_id=self.user.pk, amount=1)
        Snapshot = apps.get_model("expenses", "ExpenseMoneySnapshot")
        Snapshot.objects.create(user_id=self.user.pk, expense_id=orphan.pk, original_expense_id=orphan.pk, source_values={"amount": "1.005", "closing_balance": None}, normalized_values={"amount": "1.01", "closing_balance": None})
        orphan_id = orphan.pk
        orphan.delete()
        self.assertIsNone(Snapshot.objects.get(original_expense_id=orphan_id).expense_id)
        MigrationExecutor(connection).migrate(self.old_targets)
        self.assertEqual(self.old.get_model("expenses", "Expense").objects.get(pk=row.pk).amount, 2.68)
        self.assertEqual(self.old.get_model("expenses", "BankAccount").objects.get(pk=account.pk).current_balance, -1.01)

    def test_null_zero_negative_and_independently_rounded_balances(self):
        Account = self.old.get_model("expenses", "BankAccount")
        Row = self.old.get_model("expenses", "Expense")
        for number, balance in (("UNKNOWN", None), ("ZERO", 0), ("NEGATIVE", -1.005)):
            account = Account.objects.create(user_id=self.user.pk, account_number=number, current_balance=balance)
            Row.objects.create(user_id=self.user.pk, bank_account_id=account.pk, amount=.005, closing_balance=balance)
        apps = self.upgrade()
        self.assertEqual(list(apps.get_model("expenses", "BankAccount").objects.order_by("pk").values_list("current_balance", flat=True)), [None, Decimal("0.00"), Decimal("-1.01")])
        self.assertEqual(sum(apps.get_model("expenses", "Expense").objects.values_list("amount", flat=True)), Decimal("0.03"))

    def assert_invalid_upgrade(self, name, field, value):
        account, _, row = self.seed()
        Model = self.old.get_model("expenses", name)
        pk = row.pk if name == "Expense" else account.pk
        Model.objects.filter(pk=pk).update(**{field: value})
        self.addCleanup(lambda: Model.objects.filter(pk=pk).update(**{field: 0}))
        with self.assertRaisesRegex(ValueError, f"{name} {pk}: invalid currency field {field}"):
            self.upgrade()
        self.assertNotIn("expenses_expensemoneysnapshot", connection.introspection.table_names())
        self.assertNotIn(self.migrate_to, MigrationExecutor(connection).loader.applied_migrations)
        self.assertEqual(getattr(Model.objects.get(pk=pk), field), value)

    def test_invalid_expense_aborts_entire_upgrade(self):
        self.assert_invalid_upgrade("Expense", "amount", 1e20)

    def test_invalid_bank_balance_aborts_entire_upgrade(self):
        self.assert_invalid_upgrade("BankAccount", "current_balance", float("inf"))

    def test_selected_database_alias_upgrade_reverse_does_not_touch_default(self):
        self.seed()
        apps = self.upgrade()
        before = list(apps.get_model("expenses", "ExpenseMoneySnapshot").objects.values())
        alias = "expense_money_disposable"
        disposable = connection.copy(alias=alias)
        disposable.settings_dict["NAME"] = ":memory:"
        connections[alias] = disposable
        try:
            executor = MigrationExecutor(disposable)
            executor.migrate(self.old_targets)
            old = executor.loader.project_state(self.old_targets).apps
            user = old.get_model("users", "User").objects.using(alias).create(username="alias-owner")
            account, _, row = self.seed(old, alias, user)
            MigrationExecutor(disposable).migrate(self.leaves)
            self.assertEqual(apps.get_model("expenses", "Expense").objects.using(alias).get(pk=row.pk).amount, Decimal("2.68"))
            self.assertEqual(apps.get_model("expenses", "BankAccount").objects.using(alias).get(pk=account.pk).current_balance, Decimal("-1.01"))
            MigrationExecutor(disposable).migrate(self.old_targets)
            self.assertEqual(old.get_model("expenses", "Expense").objects.using(alias).get(pk=row.pk).amount, 2.675)
            self.assertEqual(old.get_model("expenses", "BankAccount").objects.using(alias).get(pk=account.pk).current_balance, -1.005)
            self.assertEqual(list(apps.get_model("expenses", "ExpenseMoneySnapshot").objects.values()), before)
        finally:
            disposable.close()
            del connections[alias]
