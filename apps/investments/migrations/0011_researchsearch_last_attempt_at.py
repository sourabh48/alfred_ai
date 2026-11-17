from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("investments", "0010_researchsearch")]

    operations = [
        migrations.AddField(
            model_name="researchsearch",
            name="last_attempt_at",
            field=models.DateTimeField(null=True),
        ),
    ]
