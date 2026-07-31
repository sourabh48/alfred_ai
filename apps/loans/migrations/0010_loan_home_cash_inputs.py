from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("loans", "0009_loanpaymenthistory_settlement_components"),
    ]

    operations = [
        migrations.AddField(
            model_name="loan",
            name="home_down_payment",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="loan",
            name="home_other_upfront_payments",
            field=models.FloatField(default=0),
        ),
    ]
