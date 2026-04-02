from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("investments", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="InvestmentImportDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uploaded_file", models.FileField(upload_to="investment_imports/%Y/%m/")),
                ("file_name", models.CharField(max_length=255)),
                ("broker_name", models.CharField(blank=True, max_length=120)),
                ("parser_status", models.CharField(choices=[("pending", "Pending"), ("parsed", "Parsed"), ("needs_review", "Needs Review"), ("failed", "Failed")], default="pending", max_length=20)),
                ("parse_confidence", models.FloatField(default=0)),
                ("extracted_text", models.TextField(blank=True)),
                ("extracted_payload", models.JSONField(blank=True, default=dict)),
                ("summary", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("linked_investments", models.ManyToManyField(blank=True, related_name="source_documents", to="investments.investment")),
                ("user", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="investment_import_documents", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-updated_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="investmentimportdocument",
            index=models.Index(fields=["user", "parser_status", "updated_at"], name="investmenti_user_id_a9ad33_idx"),
        ),
        migrations.AddIndex(
            model_name="investmentimportdocument",
            index=models.Index(fields=["user", "broker_name", "updated_at"], name="investmenti_user_id_359302_idx"),
        ),
    ]
