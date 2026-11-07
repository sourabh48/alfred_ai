"""Display-only currency preference. Expand-only: existing rows stay null (automatic), no backfill."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('users', '0005_income_currency')]

    operations = [
        migrations.AddField(
            model_name='user',
            name='display_currency',
            field=models.CharField(blank=True, default=None, max_length=3, null=True),
        ),
    ]
