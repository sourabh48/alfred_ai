"""Preserve legacy currency/identity evidence before explicit HALF_UP conversion."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext

import apps.expenses.money
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models, transaction
from django.utils import timezone

POLICY = "expense-bank-money-v1"
FIELDS = {"Expense": ("amount", "closing_balance"), "BankAccount": ("current_balance",)}
LINKS = {"Expense": "expense", "BankAccount": "bank_account"}


def normalized_amount(value):
    # Immutable migration policy: never delegate historical rounding to runtime.
    if value is None:
        return None
    try:
        amount = Decimal(str(value))
        if isinstance(value, bool) or not amount.is_finite() or abs(amount) > Decimal("1000000000000"):
            raise ValueError("Invalid currency.")
        with localcontext() as context:
            context.prec = 30
            amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if abs(amount) > Decimal("999999999999.99"):
            raise ValueError("Invalid currency.")
        return amount
    except (InvalidOperation, TypeError, OverflowError) as exc:
        raise ValueError("Invalid currency.") from exc


def snapshot_values(row, model_name):
    source, normalized = {}, {}
    for field in FIELDS[model_name]:
        value = getattr(row, field)
        try:
            if field == "amount" and value is None:
                raise ValueError("Required currency is null.")
            rounded = normalized_amount(value)
        except ValueError as exc:
            raise ValueError(f"{model_name} {row.pk}: invalid currency field {field}.") from exc
        source[field] = None if value is None else repr(float(value))
        normalized[field] = None if rounded is None else format(rounded, ".2f")
    return source, normalized


def capture_legacy_money(apps, schema_editor):
    alias = schema_editor.connection.alias
    pending = {}
    for name in FIELDS:
        Model = apps.get_model("expenses", name)
        Snapshot = apps.get_model("expenses", name + "MoneySnapshot")
        recorded = Snapshot.objects.using(alias).values_list("original_" + LINKS[name] + "_id", flat=True)
        pending[name] = Model.objects.using(alias).exclude(pk__in=recorded).order_by("pk")
        for row in pending[name].iterator(chunk_size=500):
            snapshot_values(row, name)
    # Validate both registers completely before writing any evidence.
    for name, rows in pending.items():
        Snapshot = apps.get_model("expenses", name + "MoneySnapshot")
        for row in rows.iterator(chunk_size=500):
            source, normalized = snapshot_values(row, name)
            Snapshot.objects.using(alias).get_or_create(
                **{"original_" + LINKS[name] + "_id": row.pk},
                defaults={LINKS[name] + "_id": row.pk, "user_id": row.user_id,
                          "source_values": source, "normalized_values": normalized, "policy": POLICY},
            )
            if name == "Expense":
                rows.model.objects.using(alias).filter(pk=row.pk).update(transaction_identity=source)


def apply_normalized_money(apps, schema_editor):
    alias = schema_editor.connection.alias
    with transaction.atomic(using=alias):
        for name in FIELDS:
            Model = apps.get_model("expenses", name)
            Snapshot = apps.get_model("expenses", name + "MoneySnapshot")
            pending = Snapshot.objects.using(alias).select_for_update().filter(
                **{LINKS[name] + "_id__isnull": False}, applied_at__isnull=True,
            )
            for snapshot in pending.iterator(chunk_size=500):
                values = {field: None if snapshot.normalized_values[field] is None else Decimal(snapshot.normalized_values[field])
                          for field in FIELDS[name]}
                changed = Model.objects.using(alias).filter(pk=getattr(snapshot, LINKS[name] + "_id"), user_id=snapshot.user_id).update(**values)
                if changed:
                    Snapshot.objects.using(alias).filter(pk=snapshot.pk).update(applied_at=timezone.now())


def restore_legacy_money(apps, schema_editor):
    alias = schema_editor.connection.alias
    # Reverse runs after AlterField restores floats. Only unchanged, still-owned
    # amounts regain original precision. New rows and corrections are retained.
    for name in FIELDS:
        Model = apps.get_model("expenses", name)
        Snapshot = apps.get_model("expenses", name + "MoneySnapshot")
        for snapshot in Snapshot.objects.using(alias).filter(
            **{LINKS[name] + "_id__isnull": False}, applied_at__isnull=False,
        ).iterator(chunk_size=500):
            row = Model.objects.using(alias).filter(pk=getattr(snapshot, LINKS[name] + "_id"), user_id=snapshot.user_id).first()
            if row is None:
                continue
            restored = {}
            for field in FIELDS[name]:
                text = snapshot.normalized_values[field]
                expected = None if text is None else Decimal(text)
                try:
                    current = normalized_amount(getattr(row, field))
                except ValueError:
                    continue
                if current == expected:
                    source = snapshot.source_values[field]
                    restored[field] = None if source is None else float(source)
            if restored:
                Model.objects.using(alias).filter(pk=row.pk, user_id=snapshot.user_id).update(**restored)


def snapshot_model(name, link, target):
    return migrations.CreateModel(name=name, fields=[
        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
        ("original_" + link + "_id", models.PositiveBigIntegerField(unique=True)),
        ("source_values", models.JSONField()),
        ("normalized_values", models.JSONField()),
        ("policy", models.CharField(default=POLICY, max_length=30)),
        ("applied_at", models.DateTimeField(blank=True, null=True)),
        ("created_at", models.DateTimeField(auto_now_add=True)),
        (link, models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="money_snapshots", to=target)),
        ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name=("expense" if link == "expense" else "bank_account") + "_money_snapshots", to=settings.AUTH_USER_MODEL)),
    ])


class Migration(migrations.Migration):
    atomic = True
    dependencies = [("expenses", "0004_statementupload_extracted_payload_and_more"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        snapshot_model("ExpenseMoneySnapshot", "expense", "expenses.expense"),
        snapshot_model("BankAccountMoneySnapshot", "bank_account", "expenses.bankaccount"),
        migrations.AddField(model_name="expense", name="transaction_identity", field=models.JSONField(blank=True, default=dict)),
        migrations.RunPython(capture_legacy_money, migrations.RunPython.noop),
        migrations.RunPython(migrations.RunPython.noop, restore_legacy_money),
        migrations.AlterField(model_name="expense", name="amount", field=apps.expenses.money.ExpenseMoneyField(max_digits=14, decimal_places=2)),
        migrations.AlterField(model_name="expense", name="closing_balance", field=apps.expenses.money.ExpenseMoneyField(max_digits=14, decimal_places=2, null=True, blank=True)),
        migrations.AlterField(model_name="bankaccount", name="current_balance", field=apps.expenses.money.ExpenseMoneyField(max_digits=14, decimal_places=2, null=True, blank=True)),
        migrations.RunPython(apply_normalized_money, migrations.RunPython.noop),
    ]
