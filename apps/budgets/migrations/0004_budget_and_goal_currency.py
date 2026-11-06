"""FIN-15: record each budget plan's and savings goal's currency. Expand-only: existing rows stay null (not recorded), no backfill."""
from django.db import migrations, models


def preserve_currencies(apps, schema_editor):
    alias = schema_editor.connection.alias
    rows = apps.get_model('budgets', 'budget').objects.using(alias)
    if rows.exclude(currency__isnull=True).exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing recorded budgets currencies.')
    rows = apps.get_model('budgets', 'savingsgoal').objects.using(alias)
    if rows.exclude(currency__isnull=True).exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing recorded budgets currencies.')


class Migration(migrations.Migration):

    dependencies = [('budgets', '0003_savings_goal')]

    operations = [
        migrations.AddField(
            model_name='budget',
            name='currency',
            field=models.CharField(blank=True, choices=[('INR', 'Indian rupee (INR)'), ('USD', 'US dollar (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'Pound sterling (GBP)')], default=None, max_length=3, null=True),
        ),
        migrations.AddField(
            model_name='savingsgoal',
            name='currency',
            field=models.CharField(blank=True, choices=[('INR', 'Indian rupee (INR)'), ('USD', 'US dollar (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'Pound sterling (GBP)')], default=None, max_length=3, null=True),
        ),
        # After AddField so that on reverse the guard runs first, while the columns still exist.
        migrations.RunPython(migrations.RunPython.noop, preserve_currencies),
    ]
