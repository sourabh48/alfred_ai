from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ml_engine", "0002_documentparserlearningmemory"),
    ]

    operations = [
        migrations.AddField(
            model_name="documentparserlearningmemory",
            name="correction_count",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
