"""Exercise the Loan-only currency cutover against disposable migration states."""

from decimal import Decimal
from importlib import import_module

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Sum
from django.test import TransactionTestCase
from django.utils import timezone


FIELDS = (
    "principal", "emi", "remaining_balance", "home_purchase_price",
    "home_down_payment", "home_other_upfront_payments", "total_paid",
)


class LoanMoneyMigrationTests(TransactionTestCase):
    migrate_from = ("loans", "0013_loan_verification")
    migrate_to = ("loans", "0014_loan_money_decimal")

    def setUp(self):
        executor = MigrationExecutor(connection)
        self.leaves = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(self.leaves))
        executor.migrate([self.migrate_from])
        targets = [self.migrate_from if node[0] == "loans" else node for node in self.leaves]
        self.old_apps = executor.loader.project_state(targets).apps
        self.OldLoan = self.old_apps.get_model("loans", "Loan")
        self.user = self.old_apps.get_model("users", "User").objects.create(username="loan-money-migration")

    def make_loan(self, **changes):
        values = dict(
            user_id=self.user.pk, loan_type="home", lender="Recorded Lender",
            principal=1234.565, emi=12.345, remaining_balance=987.655,
            home_purchase_price=1400.005, home_down_payment=165.44,
            home_other_upfront_payments=10.005, total_paid=246.915,
            interest_rate=8.123456789, start_date=timezone.localdate(),
            loan_account_number=f"MONEY-{self.OldLoan.objects.count()}",
        )
        values.update(changes)
        return self.OldLoan.objects.create(**values)

    def migrate_up(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        targets = [self.migrate_to if node[0] == "loans" else node for node in self.leaves]
        self.new_apps = executor.loader.project_state(targets).apps
        return self.new_apps.get_model("loans", "Loan"), self.new_apps.get_model("loans", "LoanMoneySnapshot")

    def test_upgrade_reconciles_each_record_aggregates_and_preserves_nonmoney_history(self):
        first = self.make_loan()
        second = self.make_loan(
            principal=1000, emi=10, remaining_balance=0, home_purchase_price=0,
            home_down_payment=0, home_other_upfront_payments=0, total_paid=1000,
            status="closed", is_active=False,
        )
        third = self.make_loan(
            principal=99.995, emi=1.005, remaining_balance=None, home_purchase_price=0,
            home_down_payment=0, home_other_upfront_payments=0, total_paid=0.1 + 0.2,
            verification_status="estimated", verification_source="emi_pattern", auto_detected=True,
        )
        Payment = self.old_apps.get_model("loans", "LoanPaymentHistory")
        payment = Payment.objects.create(
            loan_id=first.pk, payment_date=timezone.localdate(), amount=200.12345,
            principal_component=150.98765, interest_component=49.1358,
            detection_confidence=76.54321, match_status="review", loan_effect_applied=False,
        )
        metadata_fields = (
            "pk", "user_id", "interest_rate", "status", "is_active", "verification_status",
            "verification_source", "auto_detected", "start_date", "created_at", "updated_at",
        )
        metadata = list(self.OldLoan.objects.order_by("pk").values_list(*metadata_fields))
        raw = {loan.pk: {field: getattr(loan, field) for field in FIELDS} for loan in (first, second, third)}
        payment_before = Payment.objects.filter(pk=payment.pk).values().get()
        expected = {
            first.pk: ("1234.57", "12.35", "987.66", "1400.01", "165.44", "10.01", "246.92"),
            second.pk: ("1000.00", "10.00", "0.00", "0.00", "0.00", "0.00", "1000.00"),
            third.pk: ("100.00", "1.01", None, "0.00", "0.00", "0.00", "0.30"),
        }

        NewLoan, Snapshot = self.migrate_up()

        self.assertEqual(Snapshot.objects.count(), 3)
        self.assertEqual(metadata, list(NewLoan.objects.order_by("pk").values_list(*metadata_fields)))
        for loan in NewLoan.objects.order_by("pk"):
            snapshot = Snapshot.objects.get(original_loan_id=loan.pk)
            self.assertEqual(snapshot.loan_id, loan.pk)
            self.assertEqual(snapshot.user_id, loan.user_id)
            self.assertEqual(snapshot.policy, "loan-money-v1")
            self.assertIsNotNone(snapshot.applied_at)
            for field, text in zip(FIELDS, expected[loan.pk]):
                with self.subTest(loan=loan.pk, field=field):
                    value = getattr(loan, field)
                    self.assertEqual(value, None if text is None else Decimal(text))
                    self.assertEqual(snapshot.normalized_values[field], text)
                    self.assertEqual(snapshot.source_values[field], None if raw[loan.pk][field] is None else repr(float(raw[loan.pk][field])))
                    if value is not None:
                        self.assertIsInstance(value, Decimal)
                        self.assertEqual(value.as_tuple().exponent, -2)
        totals = NewLoan.objects.aggregate(**{field: Sum(field) for field in FIELDS})
        expected_totals = ("2334.57", "23.36", "987.66", "1400.01", "165.44", "10.01", "1247.22")
        self.assertEqual(totals, {field: Decimal(text) for field, text in zip(FIELDS, expected_totals)})
        self.assertEqual(
            payment_before,
            self.new_apps.get_model("loans", "LoanPaymentHistory").objects.filter(pk=payment.pk).values().get(),
        )

    def test_half_up_conversion_preserves_signed_values_and_sqlite_supported_bounds(self):
        loan = self.make_loan(
            principal=999999999999.99, emi=-1.005, remaining_balance=-999999999999.99,
            home_purchase_price=2.675, home_down_payment=-2.675,
            home_other_upfront_payments=0.005, total_paid=-0.005,
        )

        NewLoan, _ = self.migrate_up()

        row = NewLoan.objects.get(pk=loan.pk)
        expected = ("999999999999.99", "-1.01", "-999999999999.99", "2.68", "-2.68", "0.01", "-0.01")
        self.assertEqual(tuple(getattr(row, field) for field in FIELDS), tuple(Decimal(text) for text in expected))

    def test_repeat_capture_and_normalization_keep_original_snapshot_immutable(self):
        self.make_loan()
        NewLoan, Snapshot = self.migrate_up()
        migration = import_module("apps.loans.migrations.0014_loan_money_decimal")
        before = list(Snapshot.objects.order_by("pk").values())
        normalized = list(NewLoan.objects.order_by("pk").values_list(*FIELDS))

        with connection.schema_editor() as editor:
            migration.capture_legacy_money(self.new_apps, editor)
            migration.apply_normalized_money(self.new_apps, editor)
            migration.capture_legacy_money(self.new_apps, editor)

        self.assertEqual(before, list(Snapshot.objects.order_by("pk").values()))
        self.assertEqual(normalized, list(NewLoan.objects.order_by("pk").values_list(*FIELDS)))

    def test_repeat_normalization_preserves_postcutover_edits_and_original_snapshot(self):
        loan = self.make_loan()
        NewLoan, Snapshot = self.migrate_up()
        migration = import_module("apps.loans.migrations.0014_loan_money_decimal")
        snapshot_before = Snapshot.objects.get(original_loan_id=loan.pk)
        self.assertIsNotNone(snapshot_before.applied_at)
        before = Snapshot.objects.filter(pk=snapshot_before.pk).values().get()
        NewLoan.objects.filter(pk=loan.pk).update(remaining_balance=Decimal("500.01"))

        with connection.schema_editor() as editor:
            migration.capture_legacy_money(self.new_apps, editor)
            migration.apply_normalized_money(self.new_apps, editor)

        self.assertEqual(NewLoan.objects.get(pk=loan.pk).remaining_balance, Decimal("500.01"))
        self.assertEqual(before, Snapshot.objects.filter(pk=snapshot_before.pk).values().get())

    def test_reverse_restores_original_float_precision_without_changing_null_or_zero(self):
        self.make_loan()
        self.make_loan(remaining_balance=None)
        self.make_loan(remaining_balance=0)
        before = list(self.OldLoan.objects.order_by("pk").values_list("pk", *FIELDS, "interest_rate"))
        self.migrate_up()

        MigrationExecutor(connection).migrate([self.migrate_from])

        after = list(self.OldLoan.objects.order_by("pk").values_list("pk", *FIELDS, "interest_rate"))
        self.assertEqual(before, after)
        for old, restored in zip(before, after):
            for original, current in zip(old[1:], restored[1:]):
                if original is not None:
                    self.assertEqual(float(original).hex(), float(current).hex())

    def test_reverse_preserves_postmigration_edits_and_new_loans(self):
        changed = self.make_loan()
        null_balance = self.make_loan(remaining_balance=None)
        zero_balance = self.make_loan(remaining_balance=0)
        NewLoan, Snapshot = self.migrate_up()
        snapshot_before = Snapshot.objects.get(original_loan_id=changed.pk).source_values.copy()
        NewLoan.objects.filter(pk=changed.pk).update(principal=Decimal("2000.01"), emi=Decimal("20.02"), total_paid=Decimal("300.03"))
        NewLoan.objects.filter(pk=null_balance.pk).update(remaining_balance=Decimal("0.00"))
        NewLoan.objects.filter(pk=zero_balance.pk).update(remaining_balance=None)
        fresh = NewLoan.objects.create(
            user_id=self.user.pk, principal=Decimal("500.12"), emi=Decimal("25.34"),
            remaining_balance=Decimal("400.56"), interest_rate=8, start_date=timezone.localdate(),
        )
        self.assertEqual(snapshot_before, Snapshot.objects.get(original_loan_id=changed.pk).source_values)

        MigrationExecutor(connection).migrate([self.migrate_from])

        restored = self.OldLoan.objects.get(pk=changed.pk)
        self.assertEqual((restored.principal, restored.emi, restored.total_paid), (2000.01, 20.02, 300.03))
        self.assertEqual(restored.home_purchase_price, 1400.005)
        self.assertEqual(self.OldLoan.objects.get(pk=null_balance.pk).remaining_balance, 0)
        self.assertIsNone(self.OldLoan.objects.get(pk=zero_balance.pk).remaining_balance)
        restored_new = self.OldLoan.objects.get(pk=fresh.pk)
        self.assertEqual((restored_new.principal, restored_new.emi, restored_new.remaining_balance), (500.12, 25.34, 400.56))

    def test_snapshot_retains_original_values_after_loan_deletion(self):
        loan = self.make_loan()
        NewLoan, Snapshot = self.migrate_up()
        source = Snapshot.objects.get(original_loan_id=loan.pk).source_values.copy()

        NewLoan.objects.filter(pk=loan.pk).delete()

        snapshot = Snapshot.objects.get(original_loan_id=loan.pk)
        self.assertIsNone(snapshot.loan_id)
        self.assertEqual(snapshot.source_values, source)

    def assert_invalid_upgrade_aborts(self, value):
        good = self.make_loan()
        invalid = self.make_loan(principal=value)
        self.addCleanup(lambda: self.OldLoan.objects.filter(pk=invalid.pk).delete())
        before = list(self.OldLoan.objects.order_by("pk").values_list("pk", *FIELDS))

        with self.assertRaisesRegex(ValueError, f"Loan {invalid.pk}: invalid currency field principal"):
            MigrationExecutor(connection).migrate([self.migrate_to])

        self.assertEqual(before, list(self.OldLoan.objects.order_by("pk").values_list("pk", *FIELDS)))
        self.assertNotIn("loans_loanmoneysnapshot", connection.introspection.table_names())
        self.assertNotIn(self.migrate_to, MigrationExecutor(connection).loader.applied_migrations)
        self.assertTrue(self.OldLoan.objects.filter(pk=good.pk).exists())

    def test_out_of_range_legacy_amount_aborts_the_atomic_upgrade(self):
        self.assert_invalid_upgrade_aborts(1000000000000.0)

    def test_nonfinite_legacy_amount_aborts_the_atomic_upgrade(self):
        self.assert_invalid_upgrade_aborts(float("inf"))

    def test_frozen_conversion_rejects_nan_and_infinity_without_silently_zeroing(self):
        migration = import_module("apps.loans.migrations.0014_loan_money_decimal")
        for value in (float("nan"), float("inf"), float("-inf"), True, "1e1000", "-1000000000000"):
            with self.subTest(value=str(value)):
                with self.assertRaises(ValueError):
                    migration.normalized_amount(value)
