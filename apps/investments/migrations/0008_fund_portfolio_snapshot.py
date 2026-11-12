"""WEALTH2-001: saved fund portfolios for look-through. Additive: no existing table or row changes."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def preserve_saved_portfolios(apps, schema_editor):
    rows = apps.get_model('investments', 'FundPortfolioSnapshot').objects.using(schema_editor.connection.alias)
    if rows.exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing saved fund portfolios.')


class Migration(migrations.Migration):

    dependencies = [
        ('investments', '0007_research_decision'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FundPortfolioSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scheme', models.CharField(blank=True, max_length=160)),
                ('as_of', models.DateField(blank=True, null=True)),
                ('source_sha256', models.CharField(max_length=64)),
                ('securities', models.JSONField(default=list)),
                ('opaque', models.JSONField(default=list)),
                ('parser_version', models.PositiveSmallIntegerField(default=1)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('investment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='portfolio_snapshots', to='investments.investment')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fund_portfolio_snapshots', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': [models.OrderBy(models.F('as_of'), descending=True, nulls_last=True), '-uploaded_at', '-id'],
                'constraints': [models.UniqueConstraint(fields=('investment', 'source_sha256'), name='unique_fund_portfolio_file')],
            },
        ),
        # After CreateModel so that on reverse the guard runs first, while the table still exists.
        migrations.RunPython(migrations.RunPython.noop, preserve_saved_portfolios),
    ]
