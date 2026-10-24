"""Retain import receipts without changing financial values or historical currency."""
from django.db import migrations, models
import django.db.models.deletion


def preserve_receipts(apps, schema_editor):
    if apps.get_model('loans', 'LoanDocumentEvidence').objects.using(schema_editor.connection.alias).exists():
        raise RuntimeError('Restore the verified pre-migration backup before removing loan evidence.')


class Migration(migrations.Migration):
    dependencies = [('loans', '0015_related_loan_money_decimal')]
    operations = [
        migrations.CreateModel(
            name='LoanDocumentEvidence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_loan_id', models.PositiveBigIntegerField()),
                ('source_values', models.JSONField(default=dict)),
                ('reviewed_fields', models.JSONField(default=dict)),
                ('review_generation', models.PositiveBigIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='field_evidence', to='loans.loanimportdocument')),
                ('loan', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='document_evidence', to='loans.loan')),
            ],
            options={'constraints':[models.UniqueConstraint(fields=('document','original_loan_id'),name='loan_source_record_once')]},
        ),
        migrations.RunPython(migrations.RunPython.noop, preserve_receipts),
    ]
