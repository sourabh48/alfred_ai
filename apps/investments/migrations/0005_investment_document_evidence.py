"""Add owner field receipts without rewriting money or inventing historical evidence."""
from django.db import migrations, models
import django.db.models.deletion


def preserve_receipts(apps, schema_editor):
    if apps.get_model('investments', 'InvestmentDocumentEvidence').objects.using(schema_editor.connection.alias).exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing investment evidence.')


class Migration(migrations.Migration):
    dependencies = [('investments', '0004_investment_money_decimal')]
    operations = [
        migrations.CreateModel(
            name='InvestmentDocumentEvidence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_investment_id', models.PositiveBigIntegerField()),
                ('source_values', models.JSONField(default=dict)),
                ('reviewed_fields', models.JSONField(default=dict)),
                ('review_generation', models.PositiveBigIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='field_evidence', to='investments.investmentimportdocument')),
                ('investment', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='document_evidence', to='investments.investment')),
            ],
            options={'constraints':[models.UniqueConstraint(fields=('document','original_investment_id'),name='investment_source_record_once')]},
        ),
        migrations.RunPython(migrations.RunPython.noop, preserve_receipts),
    ]
