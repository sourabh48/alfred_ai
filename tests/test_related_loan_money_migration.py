"""Disposable SQLite upgrades/rollbacks for the ancillary Loan currency cutover."""

from decimal import Decimal
from importlib import import_module
from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Sum
from django.test import TransactionTestCase
from django.utils import timezone


FIELDS = {
    "LoanPaymentHistory": (
        "amount", "principal_component", "interest_component", "principal_paid",
        "interest_paid", "charges_paid", "penalties_paid", "tax_paid", "remaining_balance",
    ),
    "LoanClosureDocument": ("closure_amount",),
    "LoanForeclosureSnapshot": (
        "outstanding_principal", "accrued_interest", "foreclosure_charges", "taxes_gst",
        "overdue_charges", "total_amount_payable", "matched_payment_total",
    ),
}
MIGRATION = "apps.loans.migrations.0015_related_loan_money_decimal"


class RelatedLoanMoneyMigrationTests(TransactionTestCase):
    migrate_from = ("loans", "0014_loan_money_decimal")
    migrate_to = ("loans", "0015_related_loan_money_decimal")

    def setUp(self):
        executor = MigrationExecutor(connection)
        self.leaves = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(self.leaves))
        executor.migrate([self.migrate_from])
        self.old_targets = [self.migrate_from if node[0] == "loans" else node for node in self.leaves]
        self.new_targets = [self.migrate_to if node[0] == "loans" else node for node in self.leaves]
        self.old_apps = executor.loader.project_state(self.old_targets).apps
        User = self.old_apps.get_model("users", "User")
        self.user = User.objects.create(username="related-money-migration")
        self.other_user = User.objects.create(username="related-money-other")
        self.loan = self.make_loan()

    def make_loan(self, user=None):
        return self.old_apps.get_model("loans", "Loan").objects.create(
            user_id=(user or self.user).pk, principal="100.00", emi="1.00",
            remaining_balance="97.99", total_paid="2.01", interest_rate=8.123456789,
            start_date=timezone.localdate(), status="foreclosure_pending",
        )

    def make_rows(self, loan=None, balance=None):
        loan = loan or self.loan
        expense = self.old_apps.get_model("expenses", "Expense").objects.create(
            user_id=loan.user_id, amount=1.005, description="Raw evidence", classification="loan",
        )
        payment = self.old_apps.get_model("loans", "LoanPaymentHistory").objects.create(
            loan_id=loan.pk, payment_date=timezone.localdate(), amount=1.005,
            principal_component=2.675, interest_component=-2.675,
            principal_paid=0.005, interest_paid=-0.005, charges_paid=0.1 + 0.2,
            penalties_paid=10.004, tax_paid=0, remaining_balance=balance,
            expense_reference_id=expense.pk, detection_confidence=76.54321,
            match_status="review", loan_effect_applied=False, detection_reason="Recorded reason",
        )
        document = self.old_apps.get_model("loans", "LoanClosureDocument").objects.create(
            loan_id=loan.pk, file_name="retained.txt", closure_amount=2.675,
            extracted_text="Original source", extracted_payload={"closure_amount": 2.675},
            parse_confidence=87.654321, verification_status="verified",
        )
        foreclosure = self.old_apps.get_model("loans", "LoanForeclosureSnapshot").objects.create(
            loan_id=loan.pk, closure_document_id=document.pk,
            outstanding_principal=10.005, accrued_interest=0.005, foreclosure_charges=-0.005,
            taxes_gst=2.675, overdue_charges=0.1 + 0.2, total_amount_payable=13.185,
            matched_payment_total=0, classification_confidence=81.234567,
            linkage_confidence=73.456789, reconciliation_confidence=64.123456,
            reconciliation_status="partial_match", audit_payload={"raw_total": 13.185},
            matched_closure_transaction_ids=[expense.pk], reconciliation_notes="Recorded history",
        )
        return {"LoanPaymentHistory": payment, "LoanClosureDocument": document, "LoanForeclosureSnapshot": foreclosure}

    def migrate_up(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.new_apps = executor.loader.project_state(self.new_targets).apps
        self.Snapshot = self.new_apps.get_model("loans", "LoanRelatedMoneySnapshot")
        return {name: self.new_apps.get_model("loans", name) for name in FIELDS}

    def test_upgrade_normalizes_all_fields_reconciles_totals_and_preserves_evidence_and_register(self):
        first, second = self.make_rows(), self.make_rows(balance=0)
        Loan = self.old_apps.get_model("loans", "Loan")
        loan_before = Loan.objects.values().get(pk=self.loan.pk)
        expected = {
            "LoanPaymentHistory": ("1.01", "2.68", "-2.68", "0.01", "-0.01", "0.30", "10.00", "0.00", None),
            "LoanClosureDocument": ("2.68",),
            "LoanForeclosureSnapshot": ("10.01", "0.01", "-0.01", "2.68", "0.30", "13.19", "0.00"),
        }
        raw = {(name, row.pk): {field: getattr(row, field) for field in FIELDS[name]} for rows in (first, second) for name, row in rows.items()}
        metadata = {
            name: list(self.old_apps.get_model("loans", name).objects.order_by("pk").values(
                *[field.attname for field in self.old_apps.get_model("loans", name)._meta.fields if field.name not in FIELDS[name]]
            )) for name in FIELDS
        }
        expenses_before = list(self.old_apps.get_model("expenses", "Expense").objects.order_by("pk").values())

        models = self.migrate_up()

        self.assertEqual(self.Snapshot.objects.count(), 6)
        self.assertEqual(loan_before, self.new_apps.get_model("loans", "Loan").objects.values().get(pk=self.loan.pk))
        for name, Model in models.items():
            self.assertEqual(metadata[name], list(Model.objects.order_by("pk").values(*metadata[name][0].keys())))
            for row in Model.objects.order_by("pk"):
                snapshot = self.Snapshot.objects.get(source_model=name, original_source_id=row.pk)
                self.assertEqual((snapshot.user_id, snapshot.loan_id, snapshot.original_loan_id), (self.user.pk, self.loan.pk, self.loan.pk))
                self.assertEqual(snapshot.policy, "loan-money-v1")
                self.assertIsNotNone(snapshot.applied_at)
                if name == "LoanPaymentHistory":
                    self.assertEqual(snapshot.payment_history_id, row.pk)
                    self.assertEqual(snapshot.original_parent_ids, {"expense_reference_id": row.expense_reference_id})
                elif name == "LoanForeclosureSnapshot":
                    self.assertEqual((snapshot.foreclosure_snapshot_id, snapshot.closure_document_id), (row.pk, row.closure_document_id))
                    self.assertEqual(snapshot.original_parent_ids, {"closure_document_id": row.closure_document_id})
                else:
                    self.assertEqual(snapshot.closure_document_id, row.pk)
                    self.assertEqual(snapshot.original_parent_ids, {})
                for field, text in zip(FIELDS[name], expected[name]):
                    if name == "LoanPaymentHistory" and field == "remaining_balance" and row.pk == second[name].pk:
                        text = "0.00"
                    with self.subTest(model=name, row=row.pk, field=field):
                        value = getattr(row, field)
                        self.assertEqual(value, None if text is None else Decimal(text))
                        self.assertEqual(snapshot.normalized_values[field], text)
                        original = raw[(name, row.pk)][field]
                        self.assertEqual(snapshot.source_values[field], None if original is None else repr(float(original)))
                        if value is not None:
                            self.assertIsInstance(value, Decimal)
                            self.assertEqual(value.as_tuple().exponent, -2)
            totals = Model.objects.aggregate(**{field: Sum(field) for field in FIELDS[name]})
            for field in FIELDS[name]:
                # SQLite SQL SUM can contain binary residue; reconcile it to the
                # exact cents summed from the actual retrieved records.
                per_row = sum((getattr(row, field) or Decimal("0")) for row in Model.objects.all())
                self.assertEqual(totals[field].quantize(Decimal("0.01")), per_row)
        self.assertEqual(expenses_before, list(self.new_apps.get_model("expenses", "Expense").objects.order_by("pk").values()))
        child_total = sum(models["LoanPaymentHistory"].objects.values_list("amount", flat=True), Decimal("0"))
        register_total = self.new_apps.get_model("loans", "Loan").objects.get(pk=self.loan.pk).total_paid
        self.assertEqual((child_total, register_total, child_total - register_total), (Decimal("2.02"), Decimal("2.01"), Decimal("0.01")))

    def test_supported_signed_bounds_round_trip_in_every_ancillary_field(self):
        rows = self.make_rows(balance=0)
        for name, row in rows.items():
            self.old_apps.get_model("loans", name).objects.filter(pk=row.pk).update(**{
                field: 999999999999.99 if index % 2 == 0 else -999999999999.99
                for index, field in enumerate(FIELDS[name])
            })
        models = self.migrate_up()
        for name, row in rows.items():
            current = models[name].objects.get(pk=row.pk)
            self.assertEqual(tuple(getattr(current, field) for field in FIELDS[name]), tuple(
                Decimal("999999999999.99") if index % 2 == 0 else Decimal("-999999999999.99")
                for index, _ in enumerate(FIELDS[name])
            ))

    def test_repeat_capture_and_apply_preserve_later_edits_and_original_snapshots(self):
        rows = self.make_rows()
        models = self.migrate_up()
        models["LoanPaymentHistory"].objects.filter(pk=rows["LoanPaymentHistory"].pk).update(amount="7.77")
        before = list(self.Snapshot.objects.order_by("pk").values())
        migration = import_module(MIGRATION)
        with connection.schema_editor() as editor:
            migration.capture_legacy_money(self.new_apps, editor)
            migration.apply_normalized_money(self.new_apps, editor)
            migration.capture_legacy_money(self.new_apps, editor)
        self.assertEqual(before, list(self.Snapshot.objects.order_by("pk").values()))
        self.assertEqual(models["LoanPaymentHistory"].objects.get(pk=rows["LoanPaymentHistory"].pk).amount, Decimal("7.77"))

    def test_reverse_restores_original_precision_for_all_fields_and_preserves_null_zero(self):
        self.make_rows()
        self.make_rows(balance=0)
        before = {name: list(self.old_apps.get_model("loans", name).objects.order_by("pk").values()) for name in FIELDS}
        self.migrate_up()
        MigrationExecutor(connection).migrate([self.migrate_from])
        for name in FIELDS:
            after = list(self.old_apps.get_model("loans", name).objects.order_by("pk").values())
            self.assertEqual(before[name], after)
            for original, restored in zip(before[name], after):
                for field in FIELDS[name]:
                    if original[field] is not None:
                        self.assertEqual(original[field].hex(), restored[field].hex())

    def test_reverse_keeps_currency_edits_null_zero_transitions_and_new_rows(self):
        null_rows, zero_rows = self.make_rows(), self.make_rows(balance=0)
        models = self.migrate_up()
        models["LoanPaymentHistory"].objects.filter(pk=null_rows["LoanPaymentHistory"].pk).update(amount="7.77", remaining_balance="0.00", detection_reason="Edited reason")
        models["LoanPaymentHistory"].objects.filter(pk=zero_rows["LoanPaymentHistory"].pk).update(remaining_balance=None)
        models["LoanClosureDocument"].objects.filter(pk=null_rows["LoanClosureDocument"].pk).update(closure_amount="8.88")
        models["LoanForeclosureSnapshot"].objects.filter(pk=null_rows["LoanForeclosureSnapshot"].pk).update(total_amount_payable="9.99")
        fresh = models["LoanPaymentHistory"].objects.create(loan_id=self.loan.pk, payment_date=timezone.localdate(), amount="3.33")
        MigrationExecutor(connection).migrate([self.migrate_from])
        Payment = self.old_apps.get_model("loans", "LoanPaymentHistory")
        null_row = Payment.objects.get(pk=null_rows["LoanPaymentHistory"].pk)
        self.assertEqual((null_row.amount, null_row.remaining_balance, null_row.detection_reason), (7.77, 0, "Edited reason"))
        self.assertEqual(null_row.principal_component, 2.675)
        self.assertIsNone(Payment.objects.get(pk=zero_rows["LoanPaymentHistory"].pk).remaining_balance)
        self.assertEqual(Payment.objects.get(pk=fresh.pk).amount, 3.33)
        self.assertEqual(self.old_apps.get_model("loans", "LoanClosureDocument").objects.get(pk=null_rows["LoanClosureDocument"].pk).closure_amount, 8.88)
        self.assertEqual(self.old_apps.get_model("loans", "LoanForeclosureSnapshot").objects.get(pk=null_rows["LoanForeclosureSnapshot"].pk).total_amount_payable, 9.99)

    def test_owner_and_parent_changes_prevent_restore_and_pending_application(self):
        owner_rows = self.make_rows()
        parent_rows = self.make_rows()
        models = self.migrate_up()
        NewLoan = self.new_apps.get_model("loans", "Loan")
        # Reassign all owner_rows through their shared loan. Parent_rows change
        # payment/foreclosure parent IDs independently, retaining their owner.
        separate_loan = NewLoan.objects.create(user_id=self.user.pk, principal="50.00", emi="1.00", interest_rate=8, start_date=timezone.localdate())
        for name, row in parent_rows.items():
            models[name].objects.filter(pk=row.pk).update(loan_id=separate_loan.pk)
        NewLoan.objects.filter(pk=self.loan.pk).update(user_id=self.other_user.pk)
        new_document = models["LoanClosureDocument"].objects.create(loan_id=separate_loan.pk, file_name="new-parent.txt", closure_amount="1.00")
        models["LoanForeclosureSnapshot"].objects.filter(pk=parent_rows["LoanForeclosureSnapshot"].pk).update(closure_document_id=new_document.pk)
        models["LoanPaymentHistory"].objects.filter(pk=parent_rows["LoanPaymentHistory"].pk).update(expense_reference_id=None)
        self.Snapshot.objects.update(applied_at=None)
        models["LoanPaymentHistory"].objects.filter(pk=owner_rows["LoanPaymentHistory"].pk).update(amount="7.77")
        with connection.schema_editor() as editor:
            import_module(MIGRATION).apply_normalized_money(self.new_apps, editor)
        self.assertFalse(self.Snapshot.objects.filter(applied_at__isnull=False).exists())
        self.assertEqual(models["LoanPaymentHistory"].objects.get(pk=owner_rows["LoanPaymentHistory"].pk).amount, Decimal("7.77"))
        self.Snapshot.objects.update(applied_at=timezone.now())
        MigrationExecutor(connection).migrate([self.migrate_from])
        for name in FIELDS:
            field = FIELDS[name][0]
            for rows in (owner_rows, parent_rows):
                current = self.old_apps.get_model("loans", name).objects.get(pk=rows[name].pk)
                expected = 7.77 if name == "LoanPaymentHistory" and rows is owner_rows else {"LoanPaymentHistory": 1.01, "LoanClosureDocument": 2.68, "LoanForeclosureSnapshot": 10.01}[name]
                self.assertEqual(getattr(current, field), expected)

    def test_parent_only_changes_prevent_restore_without_a_loan_change(self):
        rows = self.make_rows()
        models = self.migrate_up()
        new_document = models["LoanClosureDocument"].objects.create(loan_id=self.loan.pk, file_name="replacement.txt", closure_amount="0.00")
        models["LoanPaymentHistory"].objects.filter(pk=rows["LoanPaymentHistory"].pk).update(expense_reference_id=None)
        models["LoanForeclosureSnapshot"].objects.filter(pk=rows["LoanForeclosureSnapshot"].pk).update(closure_document_id=new_document.pk)
        MigrationExecutor(connection).migrate([self.migrate_from])
        self.assertEqual(self.old_apps.get_model("loans", "LoanPaymentHistory").objects.get(pk=rows["LoanPaymentHistory"].pk).amount, 1.01)
        self.assertEqual(self.old_apps.get_model("loans", "LoanForeclosureSnapshot").objects.get(pk=rows["LoanForeclosureSnapshot"].pk).outstanding_principal, 10.01)
        self.assertEqual(self.old_apps.get_model("loans", "LoanClosureDocument").objects.get(pk=rows["LoanClosureDocument"].pk).closure_amount, 2.675)

    def test_deleted_sources_retain_evidence_and_are_not_recreated_on_reverse(self):
        rows = self.make_rows()
        models = self.migrate_up()
        before = list(self.Snapshot.objects.order_by("pk").values_list("source_model", "original_source_id", "source_values", "normalized_values", "user_id"))
        models["LoanPaymentHistory"].objects.filter(pk=rows["LoanPaymentHistory"].pk).delete()
        self.new_apps.get_model("loans", "Loan").objects.filter(pk=self.loan.pk).delete()
        self.assertEqual(before, list(self.Snapshot.objects.order_by("pk").values_list("source_model", "original_source_id", "source_values", "normalized_values", "user_id")))
        self.assertFalse(self.Snapshot.objects.filter(loan_id__isnull=False).exists())
        self.assertFalse(self.Snapshot.objects.filter(payment_history_id__isnull=False).exists())
        self.assertFalse(self.Snapshot.objects.filter(closure_document_id__isnull=False).exists())
        self.assertFalse(self.Snapshot.objects.filter(foreclosure_snapshot_id__isnull=False).exists())
        MigrationExecutor(connection).migrate([self.migrate_from])
        for name in FIELDS:
            self.assertFalse(self.old_apps.get_model("loans", name).objects.exists())

    def test_owner_reset_and_owner_deletion_remove_only_owned_retained_evidence(self):
        self.make_rows()
        other_loan = self.make_loan(self.other_user)
        self.make_rows(other_loan)
        self.migrate_up()
        self.new_apps.get_model("loans", "Loan").objects.filter(pk=self.loan.pk).delete()
        from apps.users.models import User
        from apps.users.services import clear_user_fed_data
        result = clear_user_fed_data(User.objects.get(pk=self.user.pk))
        self.assertEqual(result["loan_related_money_snapshots"], 3)
        self.assertFalse(self.Snapshot.objects.filter(user_id=self.user.pk).exists())
        self.assertEqual(self.Snapshot.objects.filter(user_id=self.other_user.pk).count(), 3)
        self.new_apps.get_model("users", "User").objects.filter(pk=self.other_user.pk).delete()
        self.assertFalse(self.Snapshot.objects.exists())

    def assert_invalid_upgrade(self, name, field, value):
        rows = self.make_rows()
        invalid = rows[name]
        Model = self.old_apps.get_model("loans", name)
        Model.objects.filter(pk=invalid.pk).update(**{field: value})
        self.addCleanup(lambda: Model.objects.filter(pk=invalid.pk).update(**{field: 0}))
        with self.assertRaisesRegex(ValueError, f"{name} {invalid.pk}: invalid currency field {field}"):
            MigrationExecutor(connection).migrate([self.migrate_to])
        self.assertNotIn("loans_loanrelatedmoneysnapshot", connection.introspection.table_names())
        self.assertNotIn(self.migrate_to, MigrationExecutor(connection).loader.applied_migrations)
        self.assertEqual(Model.objects.get(pk=invalid.pk).__dict__[field], value)
        self.assertEqual(self.old_apps.get_model("loans", "LoanPaymentHistory").objects.get(pk=rows["LoanPaymentHistory"].pk).principal_component, 2.675)

    def test_out_of_range_legacy_currency_aborts_the_entire_upgrade(self):
        self.assert_invalid_upgrade("LoanForeclosureSnapshot", "matched_payment_total", 1000000000000.0)

    def test_nonfinite_legacy_currency_aborts_the_entire_upgrade(self):
        self.assert_invalid_upgrade("LoanClosureDocument", "closure_amount", float("inf"))

    def test_inconsistent_foreclosure_document_loan_aborts_without_repairs(self):
        rows = self.make_rows()
        other_loan = self.make_loan(self.other_user)
        Model = self.old_apps.get_model("loans", "LoanForeclosureSnapshot")
        pk = rows["LoanForeclosureSnapshot"].pk
        Model.objects.filter(pk=pk).update(loan_id=other_loan.pk)
        self.addCleanup(lambda: Model.objects.filter(pk=pk).delete())
        with self.assertRaisesRegex(ValueError, f"LoanForeclosureSnapshot {pk}: closure document loan does not match"):
            MigrationExecutor(connection).migrate([self.migrate_to])
        self.assertEqual(Model.objects.get(pk=pk).loan_id, other_loan.pk)
        self.assertNotIn("loans_loanrelatedmoneysnapshot", connection.introspection.table_names())

    def test_upgrade_and_reverse_use_a_disposable_nondefault_database_alias(self):
        self.make_rows()
        self.migrate_up()
        before = list(self.Snapshot.objects.order_by("pk").values())
        alias = "related_money_migration_test"
        disposable = connection.copy(alias=alias)
        disposable.settings_dict["NAME"] = ":memory:"
        connections[alias] = disposable
        try:
            executor = MigrationExecutor(disposable)
            executor.migrate(self.old_targets)
            old_apps = executor.loader.project_state(self.old_targets).apps
            user = old_apps.get_model("users", "User").objects.using(alias).create(username="alias-only-owner")
            loan = old_apps.get_model("loans", "Loan").objects.using(alias).create(
                user_id=user.pk, principal="10.00", emi="1.00", interest_rate=8, start_date=timezone.localdate(),
            )
            payment = old_apps.get_model("loans", "LoanPaymentHistory").objects.using(alias).create(
                loan_id=loan.pk, payment_date=timezone.localdate(), amount=2.675,
            )
            document = old_apps.get_model("loans", "LoanClosureDocument").objects.using(alias).create(
                loan_id=loan.pk, file_name="alias.txt", closure_amount=3.335,
            )
            foreclosure = old_apps.get_model("loans", "LoanForeclosureSnapshot").objects.using(alias).create(
                loan_id=loan.pk, closure_document_id=document.pk, total_amount_payable=4.445,
            )
            MigrationExecutor(disposable).migrate(self.new_targets)
            self.assertEqual(self.Snapshot.objects.using(alias).count(), 3)
            for name, row, field, expected in (
                ("LoanPaymentHistory", payment, "amount", "2.68"),
                ("LoanClosureDocument", document, "closure_amount", "3.34"),
                ("LoanForeclosureSnapshot", foreclosure, "total_amount_payable", "4.45"),
            ):
                self.assertEqual(getattr(self.new_apps.get_model("loans", name).objects.using(alias).get(pk=row.pk), field), Decimal(expected))
            MigrationExecutor(disposable).migrate(self.old_targets)
            self.assertEqual(old_apps.get_model("loans", "LoanPaymentHistory").objects.using(alias).get(pk=payment.pk).amount, 2.675)
            self.assertEqual(old_apps.get_model("loans", "LoanClosureDocument").objects.using(alias).get(pk=document.pk).closure_amount, 3.335)
            self.assertEqual(old_apps.get_model("loans", "LoanForeclosureSnapshot").objects.using(alias).get(pk=foreclosure.pk).total_amount_payable, 4.445)
        finally:
            disposable.close()
            del connections[alias]
        self.assertEqual(before, list(self.Snapshot.objects.order_by("pk").values()))
