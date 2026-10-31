"""Add the income period without touching any stored amount.

Rows that exist before this migration have no stated period, so they start as
unconfirmed. New rows default to monthly. Reversing it drops only the new column.
"""
from django.db import migrations, models

CHOICES = [("monthly", "Per month"), ("annual", "Per year"), ("unconfirmed", "Not confirmed")]


class Migration(migrations.Migration):
    dependencies = [("users", "0003_user_money_decimal")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="monthly_income_basis",
            field=models.CharField(choices=CHOICES, default="unconfirmed", max_length=12),
        ),
        migrations.AlterField(
            model_name="user",
            name="monthly_income_basis",
            field=models.CharField(choices=CHOICES, default="monthly", max_length=12),
        ),
    ]
