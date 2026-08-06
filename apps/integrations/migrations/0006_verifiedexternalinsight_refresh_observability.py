from django.db import migrations, models
from django.db.models import F


def backfill_refresh_observability(apps, schema_editor):
    verified_external_insight = apps.get_model("integrations", "VerifiedExternalInsight")
    verified_external_insight.objects.filter(last_refresh_attempt_at__isnull=True).update(
        last_refresh_attempt_at=F("verified_at"),
        last_refresh_status=F("status"),
    )
    verified_external_insight.objects.filter(status="fresh", last_refresh_success_at__isnull=True).update(
        last_refresh_success_at=F("verified_at"),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0005_encrypt_emailconnection_tokens"),
    ]

    operations = [
        migrations.AddField(
            model_name="verifiedexternalinsight",
            name="last_refresh_attempt_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="verifiedexternalinsight",
            name="last_refresh_success_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="verifiedexternalinsight",
            name="last_refresh_status",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="verifiedexternalinsight",
            name="last_refresh_error",
            field=models.TextField(blank=True),
        ),
        migrations.AddIndex(
            model_name="verifiedexternalinsight",
            index=models.Index(fields=["last_refresh_attempt_at", "last_refresh_status"], name="integration_last_re_8c70a1_idx"),
        ),
        migrations.RunPython(backfill_refresh_observability, migrations.RunPython.noop),
    ]
