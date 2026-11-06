"""FIN-15: record each loan's contract currency. Expand-only: existing rows stay null (not recorded), no backfill."""
from django.db import migrations, models


def preserve_currencies(apps, schema_editor):
    rows = apps.get_model('loans', 'Loan').objects.using(schema_editor.connection.alias)
    if rows.exclude(currency__isnull=True).exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing recorded loan currencies.')


class Migration(migrations.Migration):

    dependencies = [
        ('loans', '0016_loan_document_evidence'),
    ]

    operations = [
        migrations.AddField(
            model_name='loan',
            name='currency',
            field=models.CharField(blank=True, choices=[('INR', 'Indian rupee (INR)'), ('USD', 'US dollar (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'Pound sterling (GBP)')], default=None, max_length=3, null=True),
        ),
        # After AddField so that on reverse the guard runs first, while the column still exists.
        migrations.RunPython(migrations.RunPython.noop, preserve_currencies),
    ]
