from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("loans", "0004_loanimportdocument"),
    ]

    operations = [
        migrations.AddField(
            model_name="loanclosuredocument",
            name="parser_status",
            field=models.CharField(choices=[("pending", "Pending"), ("parsed", "Parsed"), ("needs_review", "Needs Review"), ("failed", "Failed")], default="pending", max_length=20),
        ),
        migrations.AddField(
            model_name="loanclosuredocument",
            name="parse_confidence",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="loanclosuredocument",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AlterModelOptions(
            name="loanclosuredocument",
            options={"ordering": ["-updated_at", "-id"]},
        ),
        migrations.AddIndex(
            model_name="loanclosuredocument",
            index=models.Index(fields=["loan", "parser_status", "updated_at"], name="loans_loanc_loan_id_6cf4a5_idx"),
        ),
    ]
