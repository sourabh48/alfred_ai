"""FIN-15: record each bank account's and transaction's currency. Expand-only: existing rows stay null (not recorded), no backfill."""
from django.db import migrations, models


def preserve_currencies(apps, schema_editor):
    alias = schema_editor.connection.alias
    rows = apps.get_model('expenses', 'bankaccount').objects.using(alias)
    if rows.exclude(currency__isnull=True).exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing recorded expenses currencies.')
    rows = apps.get_model('expenses', 'expense').objects.using(alias)
    if rows.exclude(currency__isnull=True).exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing recorded expenses currencies.')


class Migration(migrations.Migration):

    dependencies = [('expenses', '0006_statement_transaction_evidence')]

    operations = [
        migrations.AddField(
            model_name='bankaccount',
            name='currency',
            field=models.CharField(blank=True, choices=[('INR', 'Indian rupee (INR)'), ('USD', 'US dollar (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'Pound sterling (GBP)')], default=None, max_length=3, null=True),
        ),
        migrations.AddField(
            model_name='expense',
            name='currency',
            field=models.CharField(blank=True, choices=[('INR', 'Indian rupee (INR)'), ('USD', 'US dollar (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'Pound sterling (GBP)')], default=None, max_length=3, null=True),
        ),
        # After AddField so that on reverse the guard runs first, while the columns still exist.
        migrations.RunPython(migrations.RunPython.noop, preserve_currencies),
    ]
