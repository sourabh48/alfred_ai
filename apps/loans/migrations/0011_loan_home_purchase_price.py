from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("loans", "0010_loan_home_cash_inputs"),
    ]

    operations = [
        migrations.AddField(
            model_name="loan",
            name="home_purchase_price",
            field=models.FloatField(default=0),
        ),
    ]
