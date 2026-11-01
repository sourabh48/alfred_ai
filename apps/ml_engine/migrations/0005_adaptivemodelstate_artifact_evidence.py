from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ml_engine", "0004_documentparserlearningmemory_retry_tracking"),
    ]

    operations = [
        migrations.AddField(
            model_name="adaptivemodelstate",
            name="artifact_evidence",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
