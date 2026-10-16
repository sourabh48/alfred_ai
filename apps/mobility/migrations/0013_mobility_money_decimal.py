"""Owned Mobility money originals with typed links and guarded parent restoration."""
from decimal import Decimal
from importlib import import_module

import apps.expenses.money
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models, transaction
from django.utils import timezone

# Reuse the immutable M13 policy, as the related-Loan migration does.
normalized_amount = import_module("apps.expenses.migrations.0005_expense_bank_money_decimal").normalized_amount
MONEY_FIELDS = {
    "BikeProfile": ("estimated_market_value", "monthly_income_support"),
    "BikeServiceRecord": ("cost",),
    "FuelRefillLog": ("total_cost",),
    "TravelPlan": ("budget",),
    "TripLog": ("spend_amount",),
    "BikeIssueReport": ("projected_cost", "actual_cost"),
    "BikeDocument": ("premium_amount",),
}
SOURCE_LINKS = {"BikeProfile": "bike_profile", "BikeServiceRecord": "service_record", "FuelRefillLog": "fuel_refill",
                "TravelPlan": "travel_plan", "TripLog": "trip_log", "BikeIssueReport": "issue_report", "BikeDocument": "document"}


def parent_ids(row):
    return {field.attname: getattr(row, field.attname) for field in row._meta.concrete_fields
            if field.is_relation and field.name != "user"}


def pending_rows(apps, alias):
    Snapshot = apps.get_model("mobility", "MobilityMoneySnapshot")
    for name in MONEY_FIELDS:
        recorded = Snapshot.objects.using(alias).filter(source_model=name).values_list("original_source_id", flat=True)
        yield from apps.get_model("mobility", name).objects.using(alias).exclude(pk__in=recorded).order_by("pk").iterator(chunk_size=500)


def snapshot_values(row):
    name = row.__class__.__name__
    source, normalized = {}, {}
    for field in MONEY_FIELDS[name]:
        value = getattr(row, field)
        try:
            if value is None and (name, field) != ("BikeIssueReport", "actual_cost"):
                raise ValueError("Required money is null.")
            amount = normalized_amount(value)
        except ValueError:
            raise ValueError(f"{name} {row.pk}: invalid money field {field}.") from None
        source[field] = None if value is None else repr(float(value))
        normalized[field] = None if amount is None else format(amount, ".2f")
    return source, normalized


def capture_legacy_money(apps, schema_editor):
    alias = schema_editor.connection.alias
    Snapshot = apps.get_model("mobility", "MobilityMoneySnapshot")
    for row in pending_rows(apps, alias):
        snapshot_values(row)
        for field in row._meta.concrete_fields:
            if not field.is_relation or field.name == "user" or getattr(row, field.attname) is None:
                continue
            if any(item.name == "user" for item in field.related_model._meta.concrete_fields):
                if not field.related_model.objects.using(alias).filter(pk=getattr(row, field.attname), user_id=row.user_id).exists():
                    raise ValueError(f"{row.__class__.__name__} {row.pk}: parent ownership mismatch.")
    # Validate every register before writing any recovery evidence.
    for row in pending_rows(apps, alias):
        name = row.__class__.__name__
        source, normalized = snapshot_values(row)
        Snapshot.objects.using(alias).get_or_create(source_model=name, original_source_id=row.pk, defaults={
            SOURCE_LINKS[name]+"_id": row.pk, "user_id": row.user_id, "original_parent_ids": parent_ids(row),
            "source_values": source, "normalized_values": normalized,
        })


def retained_row(apps, alias, snapshot, name):
    pk = getattr(snapshot, SOURCE_LINKS[name]+"_id")
    if pk != snapshot.original_source_id:
        return None
    row = apps.get_model("mobility", name).objects.using(alias).filter(pk=pk, user_id=snapshot.user_id).first()
    return row if row is not None and parent_ids(row) == snapshot.original_parent_ids else None


def apply_normalized_money(apps, schema_editor):
    alias = schema_editor.connection.alias
    Snapshot = apps.get_model("mobility", "MobilityMoneySnapshot")
    with transaction.atomic(using=alias):
        for name, fields in MONEY_FIELDS.items():
            for snapshot in Snapshot.objects.using(alias).select_for_update().filter(source_model=name,
                applied_at__isnull=True, **{SOURCE_LINKS[name]+"__isnull": False}).iterator(chunk_size=500):
                row = retained_row(apps, alias, snapshot, name)
                if row is None:
                    continue
                values = {field: None if snapshot.normalized_values[field] is None else Decimal(snapshot.normalized_values[field]) for field in fields}
                apps.get_model("mobility", name).objects.using(alias).filter(pk=row.pk, user_id=snapshot.user_id).update(**values)
                Snapshot.objects.using(alias).filter(pk=snapshot.pk).update(applied_at=timezone.now())


def restore_legacy_money(apps, schema_editor):
    alias = schema_editor.connection.alias
    Snapshot = apps.get_model("mobility", "MobilityMoneySnapshot")
    for name, fields in MONEY_FIELDS.items():
        for snapshot in Snapshot.objects.using(alias).filter(source_model=name, applied_at__isnull=False,
            **{SOURCE_LINKS[name]+"__isnull": False}).iterator(chunk_size=500):
            row = retained_row(apps, alias, snapshot, name)
            if row is None:
                continue
            restored = {}
            for field in fields:
                text = snapshot.normalized_values[field]
                expected = None if text is None else Decimal(text)
                try:
                    if normalized_amount(getattr(row, field)) == expected:
                        source = snapshot.source_values[field]
                        restored[field] = None if source is None else float(source)
                except ValueError:
                    continue
            if restored:
                apps.get_model("mobility", name).objects.using(alias).filter(pk=row.pk, user_id=snapshot.user_id).update(**restored)


class Migration(migrations.Migration):
    atomic = True
    dependencies = [("mobility", "0012_travel_bus_mode"), ("expenses", "0005_expense_bank_money_decimal"),
                    migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="MobilityMoneySnapshot", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("source_model", models.CharField(max_length=40)),
            ("original_source_id", models.PositiveBigIntegerField()),
            ("original_parent_ids", models.JSONField(default=dict)),
            ("source_values", models.JSONField()),
            ("normalized_values", models.JSONField()),
            ("policy", models.CharField(default="mobility-money-v1", max_length=30)),
            ("applied_at", models.DateTimeField(blank=True, null=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mobility_money_snapshots", to=settings.AUTH_USER_MODEL)),
            *[(link, models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="money_snapshots", to="mobility."+name.lower()))
              for name, link in SOURCE_LINKS.items()],
        ], options={"constraints": [models.UniqueConstraint(fields=("source_model", "original_source_id"), name="mobility_money_source_unique")]}),
        migrations.RunPython(capture_legacy_money, migrations.RunPython.noop),
        migrations.RunPython(migrations.RunPython.noop, restore_legacy_money),
        *[migrations.AlterField(model_name=name.lower(), name=field, field=apps.expenses.money.ExpenseMoneyField(
            max_digits=14, decimal_places=2, **({"null": True, "blank": True} if (name, field)==("BikeIssueReport", "actual_cost") else {"default": 0})))
          for name, fields in MONEY_FIELDS.items() for field in fields],
        migrations.RunPython(apply_normalized_money, migrations.RunPython.noop),
    ]
