"""Normalize ancillary Loan currency without repairing register/history totals."""

from decimal import Decimal
from importlib import import_module

import apps.loans.money
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models, transaction
from django.utils import timezone


# Reuse the immutable historical policy, never a future runtime converter.
_register_migration = import_module("apps.loans.migrations.0014_loan_money_decimal")
normalized_amount = _register_migration.normalized_amount
POLICY = _register_migration.POLICY
MONEY_FIELDS = {
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
SOURCE_LINKS = {
    "LoanPaymentHistory": "payment_history_id",
    "LoanClosureDocument": "closure_document_id",
    "LoanForeclosureSnapshot": "foreclosure_snapshot_id",
}


def parent_ids(row):
    if row.__class__.__name__ == "LoanPaymentHistory":
        return {"expense_reference_id": row.expense_reference_id}
    if row.__class__.__name__ == "LoanForeclosureSnapshot":
        return {"closure_document_id": row.closure_document_id}
    return {}


def snapshot_values(row):
    model_name = row.__class__.__name__
    if model_name == "LoanForeclosureSnapshot" and row.closure_document.loan_id != row.loan_id:
        raise ValueError(f"{model_name} {row.pk}: closure document loan does not match source loan.")
    source, normalized = {}, {}
    for field in MONEY_FIELDS[model_name]:
        value = getattr(row, field)
        if value is None and field != "remaining_balance":
            raise ValueError(f"{model_name} {row.pk}: required currency field {field} is null.")
        try:
            amount = normalized_amount(value)
        except ValueError as exc:
            raise ValueError(f"{model_name} {row.pk}: invalid currency field {field}.") from exc
        source[field] = None if value is None else repr(float(value))
        normalized[field] = None if amount is None else format(amount, ".2f")
    return source, normalized


def pending_rows(apps, Snapshot, alias):
    for model_name in MONEY_FIELDS:
        Model = apps.get_model("loans", model_name)
        recorded = Snapshot.objects.using(alias).filter(source_model=model_name).values_list("original_source_id", flat=True)
        rows = Model.objects.using(alias).exclude(pk__in=recorded).select_related("loan")
        if model_name == "LoanForeclosureSnapshot":
            rows = rows.select_related("closure_document")
        for row in rows.order_by("pk").iterator(chunk_size=500):
            yield model_name, row


def capture_legacy_money(apps, schema_editor):
    Snapshot = apps.get_model("loans", "LoanRelatedMoneySnapshot")
    alias = schema_editor.connection.alias
    # Validate across all three models before retaining any original values.
    for _, row in pending_rows(apps, Snapshot, alias):
        snapshot_values(row)
    for model_name, row in pending_rows(apps, Snapshot, alias):
        source, normalized = snapshot_values(row)
        links = {SOURCE_LINKS[model_name]: row.pk}
        if model_name == "LoanForeclosureSnapshot":
            links["closure_document_id"] = row.closure_document_id
        Snapshot.objects.using(alias).get_or_create(
            source_model=model_name, original_source_id=row.pk,
            defaults={
                "user_id": row.loan.user_id, "loan_id": row.loan_id,
                "original_loan_id": row.loan_id, "original_parent_ids": parent_ids(row),
                "source_values": source, "normalized_values": normalized, "policy": POLICY,
                **links,
            },
        )


def owned_source(apps, snapshot, alias):
    model_name = snapshot.source_model
    if model_name not in MONEY_FIELDS or snapshot.loan_id != snapshot.original_loan_id:
        return None
    if getattr(snapshot, SOURCE_LINKS[model_name]) != snapshot.original_source_id:
        return None
    rows = apps.get_model("loans", model_name).objects.using(alias).filter(
        pk=snapshot.original_source_id, loan_id=snapshot.original_loan_id, loan__user_id=snapshot.user_id,
        **snapshot.original_parent_ids,
    )
    if model_name == "LoanForeclosureSnapshot":
        if snapshot.closure_document_id != snapshot.original_parent_ids.get("closure_document_id"):
            return None
        rows = rows.filter(closure_document__loan_id=snapshot.original_loan_id)
    return rows


def apply_normalized_money(apps, schema_editor):
    Snapshot = apps.get_model("loans", "LoanRelatedMoneySnapshot")
    alias = schema_editor.connection.alias
    with transaction.atomic(using=alias):
        pending = Snapshot.objects.using(alias).select_for_update().filter(applied_at__isnull=True)
        for snapshot in pending.iterator(chunk_size=500):
            rows = owned_source(apps, snapshot, alias)
            if rows is None:
                continue
            values = {
                field: None if snapshot.normalized_values[field] is None else Decimal(snapshot.normalized_values[field])
                for field in MONEY_FIELDS[snapshot.source_model]
            }
            if rows.update(**values):
                Snapshot.objects.using(alias).filter(pk=snapshot.pk).update(applied_at=timezone.now())


def restore_legacy_money(apps, schema_editor):
    Snapshot = apps.get_model("loans", "LoanRelatedMoneySnapshot")
    alias = schema_editor.connection.alias
    # Reverse AlterField has already restored FloatFields. Only unchanged,
    # still-owned cells may recover their pre-cutover float precision.
    for snapshot in Snapshot.objects.using(alias).filter(applied_at__isnull=False).iterator(chunk_size=500):
        rows = owned_source(apps, snapshot, alias)
        row = None if rows is None else rows.first()
        if row is None:
            continue
        restored = {}
        for field in MONEY_FIELDS[snapshot.source_model]:
            expected = snapshot.normalized_values[field]
            try:
                current = normalized_amount(getattr(row, field))
            except ValueError:
                continue
            if current == (None if expected is None else Decimal(expected)):
                source = snapshot.source_values[field]
                restored[field] = None if source is None else float(source)
        if restored:
            rows.update(**restored)


class Migration(migrations.Migration):
    atomic = True
    dependencies = [("loans", "0014_loan_money_decimal")]
    operations = [
        migrations.CreateModel(
            name="LoanRelatedMoneySnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_model", models.CharField(max_length=40)),
                ("original_source_id", models.PositiveBigIntegerField()),
                ("original_loan_id", models.PositiveBigIntegerField()),
                ("original_parent_ids", models.JSONField(default=dict)),
                ("source_values", models.JSONField()),
                ("normalized_values", models.JSONField()),
                ("policy", models.CharField(default=POLICY, max_length=30)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("applied_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="loan_related_money_snapshots", to=settings.AUTH_USER_MODEL)),
                ("loan", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="related_money_snapshots", to="loans.loan")),
                ("payment_history", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="money_snapshots", to="loans.loanpaymenthistory")),
                ("closure_document", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="money_snapshots", to="loans.loanclosuredocument")),
                ("foreclosure_snapshot", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="money_snapshots", to="loans.loanforeclosuresnapshot")),
            ],
            options={"constraints": [models.UniqueConstraint(fields=("source_model", "original_source_id"), name="loan_related_money_source_unique")]},
        ),
        migrations.RunPython(capture_legacy_money, migrations.RunPython.noop),
        migrations.RunPython(migrations.RunPython.noop, restore_legacy_money),
        *[
            migrations.AlterField(
                model_name=model_name.lower(), name=field,
                field=apps.loans.money.LoanMoneyField(
                    max_digits=14, decimal_places=2,
                    **({"null": True, "blank": True} if field == "remaining_balance" else {} if field == "amount" else {"default": 0}),
                ),
            )
            for model_name, fields in MONEY_FIELDS.items() for field in fields
        ],
        migrations.RunPython(apply_normalized_money, migrations.RunPython.noop),
    ]
