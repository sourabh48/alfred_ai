"""INVEST2-002: a new owner research journal table. Additive: no existing table or row changes."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def preserve_journal(apps, schema_editor):
    rows = apps.get_model('investments', 'ResearchDecision').objects.using(schema_editor.connection.alias)
    if rows.exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing recorded research decisions.')


class Migration(migrations.Migration):

    dependencies = [
        ('investments', '0006_investment_currency'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ResearchDecision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('instrument', models.CharField(max_length=120)),
                ('rating', models.CharField(choices=[('buy', 'Buy'), ('overweight', 'Overweight'), ('hold', 'Hold'), ('underweight', 'Underweight'), ('sell', 'Sell')], max_length=12)),
                ('thesis', models.TextField(max_length=4000)),
                ('decided_on', models.DateField()),
                ('review_on', models.DateField()),
                ('currency', models.CharField(blank=True, choices=[('INR', 'Indian rupee (INR)'), ('USD', 'US dollar (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'Pound sterling (GBP)')], default=None, max_length=3, null=True)),
                ('entry_price', models.DecimalField(decimal_places=4, max_digits=18)),
                ('benchmark', models.CharField(blank=True, max_length=60)),
                ('benchmark_entry', models.DecimalField(blank=True, decimal_places=4, max_digits=18, null=True)),
                ('settled_on', models.DateField(blank=True, null=True)),
                ('exit_price', models.DecimalField(blank=True, decimal_places=4, max_digits=18, null=True)),
                ('benchmark_exit', models.DecimalField(blank=True, decimal_places=4, max_digits=18, null=True)),
                ('lesson', models.TextField(blank=True, max_length=2000)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='research_decisions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-decided_on', '-id'],
                'indexes': [models.Index(fields=['user', 'instrument', 'decided_on'], name='investments_user_id_fdc34e_idx')],
            },
        ),
        # After CreateModel so that on reverse the guard runs first, while the table still exists.
        migrations.RunPython(migrations.RunPython.noop, preserve_journal),
    ]
