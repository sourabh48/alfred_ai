from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ml_engine", "0003_documentparserlearningmemory_correction_count"),
    ]

    operations = [
        migrations.AddField(
            model_name="documentparserlearningmemory",
            name="accepted_field_hints",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="documentparserlearningmemory",
            name="last_resolution",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="documentparserlearningmemory",
            name="retry_failure_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="documentparserlearningmemory",
            name="retry_success_count",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
