"""FIN-15: record the career salary currency. Expand-only: existing rows stay null (not recorded), no backfill."""
from django.db import migrations, models


def preserve_currencies(apps, schema_editor):
    alias = schema_editor.connection.alias
    rows = apps.get_model('career', 'careerprofile').objects.using(alias)
    if rows.exclude(salary_currency__isnull=True).exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing recorded career currencies.')


class Migration(migrations.Migration):

    dependencies = [('career', '0005_career_salary_decimal')]

    operations = [
        migrations.AddField(
            model_name='careerprofile',
            name='salary_currency',
            field=models.CharField(blank=True, choices=[('INR', 'Indian rupee (INR)'), ('USD', 'US dollar (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'Pound sterling (GBP)')], default=None, max_length=3, null=True),
        ),
        # After AddField so that on reverse the guard runs first, while the columns still exist.
        migrations.RunPython(migrations.RunPython.noop, preserve_currencies),
    ]
