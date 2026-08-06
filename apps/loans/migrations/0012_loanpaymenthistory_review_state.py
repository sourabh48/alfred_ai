from django.db import migrations, models


def mark_existing_payment_effects_applied(apps, schema_editor):
    LoanPaymentHistory = apps.get_model("loans", "LoanPaymentHistory")
    LoanPaymentHistory.objects.filter(match_status__in=["matched", "review"]).update(loan_effect_applied=True)


def reset_existing_payment_effects(apps, schema_editor):
    LoanPaymentHistory = apps.get_model("loans", "LoanPaymentHistory")
    LoanPaymentHistory.objects.update(loan_effect_applied=False)


class Migration(migrations.Migration):

    dependencies = [
        ("loans", "0011_loan_home_purchase_price"),
    ]

    operations = [
        migrations.AlterField(
            model_name="loanpaymenthistory",
            name="match_status",
            field=models.CharField(
                choices=[("matched", "Matched"), ("review", "Needs Review"), ("rejected", "Rejected")],
                default="matched",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="loanpaymenthistory",
            name="loan_effect_applied",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(mark_existing_payment_effects_applied, reset_existing_payment_effects),
    ]
