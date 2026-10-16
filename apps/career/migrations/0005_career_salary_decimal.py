"""Retain salary originals; experience, scores and extracted evidence are unchanged."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext

import apps.expenses.money
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models, transaction
from django.utils import timezone


def normalized_amount(value):
    # Preserve the existing signed register policy independently of runtime helpers.
    try:
        amount = Decimal(str(value))
        if isinstance(value, bool) or not amount.is_finite() or abs(amount) > Decimal("1000000000000"):
            raise ValueError("Invalid career amount.")
        with localcontext() as context:
            context.prec = 30
            amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if abs(amount) > Decimal("999999999999.99"):
            raise ValueError("Invalid career amount.")
        return amount
    except (InvalidOperation, TypeError, OverflowError):
        raise ValueError("Invalid career amount.") from None


def capture_legacy_money(apps, schema_editor):
    alias = schema_editor.connection.alias
    Profile, Snapshot = apps.get_model("career", "CareerProfile"), apps.get_model("career", "CareerProfileMoneySnapshot")
    recorded = Snapshot.objects.using(alias).values_list("original_career_profile_id", flat=True)
    pending = Profile.objects.using(alias).exclude(pk__in=recorded).order_by("pk")
    for row in pending.iterator(chunk_size=500):
        try:
            normalized_amount(row.last_salary)
        except ValueError:
            raise ValueError(f"Career profile {row.pk}: invalid salary.") from None
    for row in pending.iterator(chunk_size=500):
        Snapshot.objects.using(alias).get_or_create(original_career_profile_id=row.pk, defaults={
            "career_profile_id": row.pk, "user_id": row.user_id,
            "source_values": {"last_salary": repr(float(row.last_salary))},
            "normalized_values": {"last_salary": format(normalized_amount(row.last_salary), ".2f")},
        })


def apply_normalized_money(apps, schema_editor):
    alias = schema_editor.connection.alias
    Profile, Snapshot = apps.get_model("career", "CareerProfile"), apps.get_model("career", "CareerProfileMoneySnapshot")
    with transaction.atomic(using=alias):
        for snapshot in Snapshot.objects.using(alias).select_for_update().filter(
            career_profile_id__isnull=False, applied_at__isnull=True,
        ).iterator(chunk_size=500):
            changed = Profile.objects.using(alias).filter(pk=snapshot.career_profile_id, user_id=snapshot.user_id).update(
                last_salary=Decimal(snapshot.normalized_values["last_salary"]))
            if changed:
                Snapshot.objects.using(alias).filter(pk=snapshot.pk).update(applied_at=timezone.now())


def restore_legacy_money(apps, schema_editor):
    alias = schema_editor.connection.alias
    Profile, Snapshot = apps.get_model("career", "CareerProfile"), apps.get_model("career", "CareerProfileMoneySnapshot")
    for snapshot in Snapshot.objects.using(alias).filter(career_profile_id__isnull=False, applied_at__isnull=False).iterator(chunk_size=500):
        row = Profile.objects.using(alias).filter(pk=snapshot.career_profile_id, user_id=snapshot.user_id).first()
        if row is None:
            continue
        try:
            matches = normalized_amount(row.last_salary) == Decimal(snapshot.normalized_values["last_salary"])
        except ValueError:
            continue
        if matches:
            Profile.objects.using(alias).filter(pk=row.pk, user_id=snapshot.user_id).update(last_salary=float(snapshot.source_values["last_salary"]))


class Migration(migrations.Migration):
    atomic = True
    dependencies = [("career", "0004_alter_careerjobanalysis_options_and_more"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="CareerProfileMoneySnapshot", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("original_career_profile_id", models.PositiveBigIntegerField(unique=True)),
            ("source_values", models.JSONField()),
            ("normalized_values", models.JSONField()),
            ("policy", models.CharField(default="career-money-v1", max_length=30)),
            ("applied_at", models.DateTimeField(blank=True, null=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("career_profile", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="money_snapshots", to="career.careerprofile")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="career_money_snapshots", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.RunPython(capture_legacy_money, migrations.RunPython.noop),
        migrations.RunPython(migrations.RunPython.noop, restore_legacy_money),
        migrations.AlterField(model_name="careerprofile", name="last_salary", field=apps.expenses.money.ExpenseMoneyField(max_digits=14, decimal_places=2, default=0)),
        migrations.RunPython(apply_normalized_money, migrations.RunPython.noop),
    ]
