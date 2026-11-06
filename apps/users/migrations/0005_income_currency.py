"""FIN-15: record the currency of entered income, variable income and housing cost. Expand-only: existing rows stay null (not recorded), no backfill."""
from django.db import migrations, models


def preserve_currencies(apps, schema_editor):
    alias = schema_editor.connection.alias
    rows = apps.get_model('users', 'user').objects.using(alias)
    if rows.exclude(income_currency__isnull=True).exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing recorded users currencies.')
    if rows.exclude(rent_currency__isnull=True).exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing recorded users currencies.')
    if rows.exclude(variable_income_currency__isnull=True).exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing recorded users currencies.')


class Migration(migrations.Migration):

    dependencies = [('users', '0004_user_monthly_income_basis')]

    operations = [
        migrations.AddField(
            model_name='user',
            name='income_currency',
            field=models.CharField(blank=True, choices=[('INR', 'Indian rupee (INR)'), ('USD', 'US dollar (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'Pound sterling (GBP)')], default=None, max_length=3, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='rent_currency',
            field=models.CharField(blank=True, choices=[('INR', 'Indian rupee (INR)'), ('USD', 'US dollar (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'Pound sterling (GBP)')], default=None, max_length=3, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='variable_income_currency',
            field=models.CharField(blank=True, choices=[('INR', 'Indian rupee (INR)'), ('USD', 'US dollar (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'Pound sterling (GBP)')], default=None, max_length=3, null=True),
        ),
        # After AddField so that on reverse the guard runs first, while the columns still exist.
        migrations.RunPython(migrations.RunPython.noop, preserve_currencies),
    ]
