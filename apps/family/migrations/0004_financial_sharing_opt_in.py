from django.db import migrations, models


def disable_financial_sharing(apps, schema_editor):
    # Historical True defaults cannot establish consent. Reversal must not revive it.
    apps.get_model("family", "FamilyAccountLink").objects.using(schema_editor.connection.alias).update(
        share_financial_summary=False, linked_user_share_financial_summary=False)


class Migration(migrations.Migration):
    dependencies = [("family", "0003_familyaccountlink_share_financial_summary")]

    operations = [
        migrations.AlterField(
            model_name="familyaccountlink", name="share_financial_summary",
            field=models.BooleanField(default=False, help_text="Creator shares their own financial summary.")),
        migrations.AddField(
            model_name="familyaccountlink", name="linked_user_share_financial_summary",
            field=models.BooleanField(default=False, help_text="Linked user shares their own financial summary.")),
        migrations.RunPython(disable_financial_sharing, disable_financial_sharing),
    ]
