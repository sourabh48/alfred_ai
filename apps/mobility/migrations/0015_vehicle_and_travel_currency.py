"""FIN-15: record the currency of vehicle values, running costs, documents and travel-plan budgets. Expand-only: existing rows stay null (not recorded), no backfill."""
from django.db import migrations, models


def preserve_currencies(apps, schema_editor):
    alias = schema_editor.connection.alias
    rows = apps.get_model('mobility', 'bikedocument').objects.using(alias)
    if rows.exclude(currency__isnull=True).exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing recorded mobility currencies.')
    rows = apps.get_model('mobility', 'bikeissuereport').objects.using(alias)
    if rows.exclude(currency__isnull=True).exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing recorded mobility currencies.')
    rows = apps.get_model('mobility', 'bikeprofile').objects.using(alias)
    if rows.exclude(income_support_currency__isnull=True).exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing recorded mobility currencies.')
    if rows.exclude(value_currency__isnull=True).exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing recorded mobility currencies.')
    rows = apps.get_model('mobility', 'bikeservicerecord').objects.using(alias)
    if rows.exclude(currency__isnull=True).exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing recorded mobility currencies.')
    rows = apps.get_model('mobility', 'fuelrefilllog').objects.using(alias)
    if rows.exclude(currency__isnull=True).exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing recorded mobility currencies.')
    rows = apps.get_model('mobility', 'travelplan').objects.using(alias)
    if rows.exclude(budget_currency__isnull=True).exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing recorded mobility currencies.')
    rows = apps.get_model('mobility', 'triplog').objects.using(alias)
    if rows.exclude(currency__isnull=True).exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing recorded mobility currencies.')


class Migration(migrations.Migration):

    dependencies = [('mobility', '0014_trip_video')]

    operations = [
        migrations.AddField(
            model_name='bikedocument',
            name='currency',
            field=models.CharField(blank=True, choices=[('INR', 'Indian rupee (INR)'), ('USD', 'US dollar (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'Pound sterling (GBP)')], default=None, max_length=3, null=True),
        ),
        migrations.AddField(
            model_name='bikeissuereport',
            name='currency',
            field=models.CharField(blank=True, choices=[('INR', 'Indian rupee (INR)'), ('USD', 'US dollar (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'Pound sterling (GBP)')], default=None, max_length=3, null=True),
        ),
        migrations.AddField(
            model_name='bikeprofile',
            name='income_support_currency',
            field=models.CharField(blank=True, choices=[('INR', 'Indian rupee (INR)'), ('USD', 'US dollar (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'Pound sterling (GBP)')], default=None, max_length=3, null=True),
        ),
        migrations.AddField(
            model_name='bikeprofile',
            name='value_currency',
            field=models.CharField(blank=True, choices=[('INR', 'Indian rupee (INR)'), ('USD', 'US dollar (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'Pound sterling (GBP)')], default=None, max_length=3, null=True),
        ),
        migrations.AddField(
            model_name='bikeservicerecord',
            name='currency',
            field=models.CharField(blank=True, choices=[('INR', 'Indian rupee (INR)'), ('USD', 'US dollar (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'Pound sterling (GBP)')], default=None, max_length=3, null=True),
        ),
        migrations.AddField(
            model_name='fuelrefilllog',
            name='currency',
            field=models.CharField(blank=True, choices=[('INR', 'Indian rupee (INR)'), ('USD', 'US dollar (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'Pound sterling (GBP)')], default=None, max_length=3, null=True),
        ),
        migrations.AddField(
            model_name='travelplan',
            name='budget_currency',
            field=models.CharField(blank=True, choices=[('INR', 'Indian rupee (INR)'), ('USD', 'US dollar (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'Pound sterling (GBP)')], default=None, max_length=3, null=True),
        ),
        migrations.AddField(
            model_name='triplog',
            name='currency',
            field=models.CharField(blank=True, choices=[('INR', 'Indian rupee (INR)'), ('USD', 'US dollar (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'Pound sterling (GBP)')], default=None, max_length=3, null=True),
        ),
        # After AddField so that on reverse the guard runs first, while the columns still exist.
        migrations.RunPython(migrations.RunPython.noop, preserve_currencies),
    ]
