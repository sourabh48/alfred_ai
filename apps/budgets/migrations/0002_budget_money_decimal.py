"""Retain original float values, then convert only Budget register money."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext

import apps.budgets.money
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models, transaction
from django.utils import timezone

FIELDS = ("base_budget", "inflation_adjusted", "spent")
POLICY = "budget-money-v1"


def normalized_amount(value):
    # Immutable historical policy; runtime validation may evolve independently.
    try:
        amount = Decimal(str(value))
        if isinstance(value, bool) or not amount.is_finite() or amount < 0 or amount > Decimal("1000000000000"):
            raise ValueError("Invalid budget amount.")
        with localcontext() as context:
            context.prec = 30
            amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if amount > Decimal("999999999999.99"):
            raise ValueError("Invalid budget amount.")
        return amount
    except (InvalidOperation, TypeError, OverflowError):
        raise ValueError("Invalid budget amount.") from None


def snapshot_values(row):
    source, normalized = {}, {}
    for field in FIELDS:
        value = getattr(row, field)
        try:
            normalized[field] = format(normalized_amount(value), ".2f")
        except ValueError:
            raise ValueError(f"Budget {row.pk}: invalid money field {field}.") from None
        source[field] = repr(float(value))
    return source, normalized


def capture_legacy_money(apps, schema_editor):
    alias = schema_editor.connection.alias
    Budget = apps.get_model("budgets", "Budget")
    Snapshot = apps.get_model("budgets", "BudgetMoneySnapshot")
    recorded = Snapshot.objects.using(alias).values_list("original_budget_id", flat=True)
    pending = Budget.objects.using(alias).exclude(pk__in=recorded).order_by("pk")
    for row in pending.iterator(chunk_size=500):
        snapshot_values(row)
    # Refuse the entire conversion before evidence writes if any row is invalid.
    for row in pending.iterator(chunk_size=500):
        source, normalized = snapshot_values(row)
        Snapshot.objects.using(alias).get_or_create(original_budget_id=row.pk, defaults={
            "budget_id": row.pk, "user_id": row.user_id, "source_values": source,
            "normalized_values": normalized, "policy": POLICY,
        })


def apply_normalized_money(apps, schema_editor):
    alias = schema_editor.connection.alias
    Budget = apps.get_model("budgets", "Budget")
    Snapshot = apps.get_model("budgets", "BudgetMoneySnapshot")
    with transaction.atomic(using=alias):
        for snapshot in Snapshot.objects.using(alias).select_for_update().filter(
            budget_id__isnull=False, applied_at__isnull=True,
        ).iterator(chunk_size=500):
            values = {field: Decimal(snapshot.normalized_values[field]) for field in FIELDS}
            changed = Budget.objects.using(alias).filter(pk=snapshot.budget_id, user_id=snapshot.user_id).update(**values)
            if changed:
                Snapshot.objects.using(alias).filter(pk=snapshot.pk).update(applied_at=timezone.now())


def restore_legacy_money(apps, schema_editor):
    alias = schema_editor.connection.alias
    Budget = apps.get_model("budgets", "Budget")
    Snapshot = apps.get_model("budgets", "BudgetMoneySnapshot")
    # Reverse follows the FloatField restoration; do not overwrite corrections.
    for snapshot in Snapshot.objects.using(alias).filter(
        budget_id__isnull=False, applied_at__isnull=False,
    ).iterator(chunk_size=500):
        row = Budget.objects.using(alias).filter(pk=snapshot.budget_id, user_id=snapshot.user_id).first()
        if row is None:
            continue
        restored = {}
        for field in FIELDS:
            try:
                if normalized_amount(getattr(row, field)) == Decimal(snapshot.normalized_values[field]):
                    restored[field] = float(snapshot.source_values[field])
            except ValueError:
                continue
        if restored:
            Budget.objects.using(alias).filter(pk=row.pk, user_id=snapshot.user_id).update(**restored)


class Migration(migrations.Migration):
    atomic = True
    dependencies = [("budgets", "0001_initial"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="BudgetMoneySnapshot", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("original_budget_id", models.PositiveBigIntegerField(unique=True)),
            ("source_values", models.JSONField()),
            ("normalized_values", models.JSONField()),
            ("policy", models.CharField(default=POLICY, max_length=30)),
            ("applied_at", models.DateTimeField(blank=True, null=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("budget", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="money_snapshots", to="budgets.budget")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="budget_money_snapshots", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.RunPython(capture_legacy_money, migrations.RunPython.noop),
        migrations.RunPython(migrations.RunPython.noop, restore_legacy_money),
        *[migrations.AlterField(model_name="budget", name=field,
            field=apps.budgets.money.BudgetMoneyField(max_digits=14, decimal_places=2, **({"default": 0} if field == "spent" else {})))
          for field in FIELDS],
        migrations.RunPython(apply_normalized_money, migrations.RunPython.noop),
    ]
