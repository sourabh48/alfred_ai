"""Owner decision 2026-11-12 (FIN-17 OWNER_DESCOPED): credit scores and bureau reports are removed.

Apply only after the owner has taken a backup. Uploaded report files under media/credit_reports/ stay on
disk; this migration never deletes files.
"""
from django.db import migrations


def refuse_to_lose_card_limits(apps, schema_editor):
    # total_credit_limit lives only on CreditScore; the owner asked to keep it, so a non-zero value stops the drop.
    CreditScore = apps.get_model("integrations", "CreditScore")
    kept = CreditScore.objects.using(schema_editor.connection.alias).exclude(total_credit_limit=0).count()
    if kept:
        raise RuntimeError(
            f"{kept} credit score row(s) hold a non-zero total_credit_limit. Record those card limits "
            "elsewhere first; nothing was changed."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("integrations", "0006_verifiedexternalinsight_refresh_observability"),
        # 0013 reads CreditReportUpload during its backfill, so it must run first.
        ("loans", "0013_loan_verification"),
    ]

    operations = [
        migrations.RunPython(refuse_to_lose_card_limits, migrations.RunPython.noop),
        migrations.DeleteModel(name="CreditReportUpload"),
        migrations.DeleteModel(name="CreditScoreFactor"),
        migrations.DeleteModel(name="CreditScore"),
    ]
