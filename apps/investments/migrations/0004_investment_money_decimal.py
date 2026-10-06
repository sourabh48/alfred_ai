"""Move the Investment register to cents while retaining its original float values."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext

import apps.investments.money
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models, transaction
from django.utils import timezone


# Keep this conversion policy immutable; historical data must not depend on a
# future version of the runtime money helper.
MONEY_FIELDS = ("invested_amount", "monthly_sip", "current_value")
PAISE = Decimal("0.01")
LIMIT = Decimal("999999999999.99")
POLICY = "investment-money-v1"


def normalized_amount(value):
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("Investment currency must be finite and within the supported range.")
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or abs(amount) > LIMIT + PAISE:
            raise ValueError("Investment currency must be finite and within the supported range.")
        with localcontext() as context:
            context.prec = 30
            amount = amount.quantize(PAISE, rounding=ROUND_HALF_UP)
        if abs(amount) > LIMIT:
            raise ValueError("Investment currency must be finite and within the supported range.")
    except (InvalidOperation, TypeError, OverflowError) as exc:
        raise ValueError("Investment currency must be finite and within the supported range.") from exc
    return amount


def snapshot_values(investment):
    source_values = {}
    normalized_values = {}
    for field in MONEY_FIELDS:
        value = getattr(investment, field)
        if value is None:
            raise ValueError(f"Investment {investment.pk}: required currency field {field} is null.")
        try:
            normalized = normalized_amount(value)
        except ValueError as exc:
            raise ValueError(f"Investment {investment.pk}: invalid currency field {field}.") from exc
        source_values[field] = None if value is None else repr(float(value))
        normalized_values[field] = None if normalized is None else format(normalized, ".2f")
    return source_values, normalized_values


def capture_legacy_money(apps, schema_editor):
    Investment = apps.get_model("investments", "Investment")
    Snapshot = apps.get_model("investments", "InvestmentMoneySnapshot")
    alias = schema_editor.connection.alias
    recorded = Snapshot.objects.using(alias).values_list("original_investment_id", flat=True)
    pending = Investment.objects.using(alias).exclude(pk__in=recorded).order_by("pk")
    # Validate every source row before writing any snapshot. The enclosing
    # atomic migration also rolls back the schema if validation rejects a row.
    for investment in pending.iterator(chunk_size=500):
        snapshot_values(investment)
    for investment in pending.iterator(chunk_size=500):
        source, normalized = snapshot_values(investment)
        Snapshot.objects.using(alias).get_or_create(
            original_investment_id=investment.pk,
            defaults={
                "investment_id": investment.pk,
                "user_id": investment.user_id,
                "source_values": source,
                "normalized_values": normalized,
                "policy": POLICY,
            },
        )


def apply_normalized_money(apps, schema_editor):
    Investment = apps.get_model("investments", "Investment")
    Snapshot = apps.get_model("investments", "InvestmentMoneySnapshot")
    alias = schema_editor.connection.alias
    # Do not rely on a backend's implicit Float-to-Decimal rounding policy.
    # Snapshots were captured before AlterField, so half-cent evidence survives.
    with transaction.atomic(using=alias):
        pending = Snapshot.objects.using(alias).select_for_update().filter(
            investment_id__isnull=False, applied_at__isnull=True,
        )
        for snapshot in pending.iterator(chunk_size=500):
            values = {
                field: None if snapshot.normalized_values[field] is None else Decimal(snapshot.normalized_values[field])
                for field in MONEY_FIELDS
            }
            updated = Investment.objects.using(alias).filter(pk=snapshot.investment_id, user_id=snapshot.user_id).update(**values)
            if updated:
                Snapshot.objects.using(alias).filter(pk=snapshot.pk).update(applied_at=timezone.now())


def restore_legacy_money(apps, schema_editor):
    Investment = apps.get_model("investments", "Investment")
    Snapshot = apps.get_model("investments", "InvestmentMoneySnapshot")
    alias = schema_editor.connection.alias
    # This reverse operation runs after the three fields have become floats.
    # Restore original precision only where the amount has not since changed;
    # corrections, new rows, and explicit null/zero edits retain current values.
    for snapshot in Snapshot.objects.using(alias).filter(investment_id__isnull=False, applied_at__isnull=False).iterator(chunk_size=500):
        investment = Investment.objects.using(alias).filter(pk=snapshot.investment_id, user_id=snapshot.user_id).first()
        if investment is None:
            continue
        restored = {}
        for field in MONEY_FIELDS:
            expected_text = snapshot.normalized_values[field]
            expected = None if expected_text is None else Decimal(expected_text)
            try:
                current = normalized_amount(getattr(investment, field))
            except ValueError:
                continue
            if current == expected:
                source_text = snapshot.source_values[field]
                restored[field] = None if source_text is None else float(source_text)
        if restored:
            Investment.objects.using(alias).filter(pk=investment.pk, user_id=snapshot.user_id).update(**restored)


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ("investments", "0003_rename_investmenti_user_id_a9ad33_idx_investments_user_id_cbfa4c_idx_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="InvestmentMoneySnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("original_investment_id", models.PositiveBigIntegerField(unique=True)),
                ("source_values", models.JSONField()),
                ("normalized_values", models.JSONField()),
                ("policy", models.CharField(default=POLICY, max_length=30)),
                ("applied_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("investment", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="money_snapshots", to="investments.investment")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="investment_money_snapshots", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(capture_legacy_money, migrations.RunPython.noop),
        migrations.RunPython(migrations.RunPython.noop, restore_legacy_money),
        migrations.AlterField(
            model_name="investment", name="invested_amount",
            field=apps.investments.money.InvestmentMoneyField(max_digits=14, decimal_places=2, default=0),
        ),
        migrations.AlterField(
            model_name="investment", name="monthly_sip",
            field=apps.investments.money.InvestmentMoneyField(max_digits=14, decimal_places=2, default=0),
        ),
        migrations.AlterField(
            model_name="investment", name="current_value",
            field=apps.investments.money.InvestmentMoneyField(max_digits=14, decimal_places=2, default=0),
        ),
        migrations.RunPython(apply_normalized_money, migrations.RunPython.noop),
    ]
