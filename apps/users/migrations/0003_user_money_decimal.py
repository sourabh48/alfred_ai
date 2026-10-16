"""Retain profile money originals before independent HALF_UP cent conversion."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext

import apps.users.money
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models, transaction
from django.utils import timezone

FIELDS = ("monthly_income", "variable_income", "rent_or_emi")


def normalized_amount(value):
    # Historical policy must not depend on evolving runtime input validation.
    try:
        amount = Decimal(str(value))
        if isinstance(value, bool) or not amount.is_finite() or amount < 0 or amount > Decimal("1000000000000"):
            raise ValueError("Invalid profile amount.")
        with localcontext() as context:
            context.prec = 30
            amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if amount > Decimal("999999999999.99"):
            raise ValueError("Invalid profile amount.")
        return amount
    except (InvalidOperation, TypeError, OverflowError):
        raise ValueError("Invalid profile amount.") from None


def capture_legacy_money(apps, schema_editor):
    alias = schema_editor.connection.alias
    User = apps.get_model("users", "User")
    Snapshot = apps.get_model("users", "UserMoneySnapshot")
    recorded = Snapshot.objects.using(alias).values_list("original_user_id", flat=True)
    pending = User.objects.using(alias).exclude(pk__in=recorded).order_by("pk")
    for user in pending.iterator(chunk_size=500):
        for field in FIELDS:
            try:
                normalized_amount(getattr(user, field))
            except ValueError:
                raise ValueError(f"User {user.pk}: invalid money field {field}.") from None
    for user in pending.iterator(chunk_size=500):
        Snapshot.objects.using(alias).get_or_create(original_user_id=user.pk, defaults={
            "user_id": user.pk, "source_values": {field: repr(float(getattr(user, field))) for field in FIELDS},
            "normalized_values": {field: format(normalized_amount(getattr(user, field)), ".2f") for field in FIELDS},
        })


def apply_normalized_money(apps, schema_editor):
    alias = schema_editor.connection.alias
    User = apps.get_model("users", "User")
    Snapshot = apps.get_model("users", "UserMoneySnapshot")
    with transaction.atomic(using=alias):
        for snapshot in Snapshot.objects.using(alias).select_for_update().filter(applied_at__isnull=True).iterator(chunk_size=500):
            if snapshot.user_id != snapshot.original_user_id:
                continue
            values = {field: Decimal(snapshot.normalized_values[field]) for field in FIELDS}
            if User.objects.using(alias).filter(pk=snapshot.user_id).update(**values):
                Snapshot.objects.using(alias).filter(pk=snapshot.pk).update(applied_at=timezone.now())


def restore_legacy_money(apps, schema_editor):
    alias = schema_editor.connection.alias
    User = apps.get_model("users", "User")
    Snapshot = apps.get_model("users", "UserMoneySnapshot")
    for snapshot in Snapshot.objects.using(alias).filter(applied_at__isnull=False).iterator(chunk_size=500):
        if snapshot.user_id != snapshot.original_user_id:
            continue
        user = User.objects.using(alias).filter(pk=snapshot.user_id).first()
        if user is None:
            continue
        restored = {}
        for field in FIELDS:
            try:
                if normalized_amount(getattr(user, field)) == Decimal(snapshot.normalized_values[field]):
                    restored[field] = float(snapshot.source_values[field])
            except ValueError:
                continue
        if restored:
            User.objects.using(alias).filter(pk=user.pk).update(**restored)


class Migration(migrations.Migration):
    atomic = True
    dependencies = [("users", "0002_user_ml_training_consent")]
    operations = [
        migrations.CreateModel(name="UserMoneySnapshot", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("original_user_id", models.PositiveBigIntegerField(unique=True)),
            ("source_values", models.JSONField()),
            ("normalized_values", models.JSONField()),
            ("policy", models.CharField(default="user-money-v1", max_length=30)),
            ("applied_at", models.DateTimeField(blank=True, null=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="money_snapshot", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.RunPython(capture_legacy_money, migrations.RunPython.noop),
        migrations.RunPython(migrations.RunPython.noop, restore_legacy_money),
        *[migrations.AlterField(model_name="user", name=field,
            field=apps.users.money.ProfileMoneyField(max_digits=14, decimal_places=2, default=0)) for field in FIELDS],
        migrations.RunPython(apply_normalized_money, migrations.RunPython.noop),
    ]
