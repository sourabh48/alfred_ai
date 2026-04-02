from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("relationship", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="relationshipprofile",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name="relationshipprofile",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AlterModelOptions(
            name="relationshipprofile",
            options={"ordering": ["-updated_at", "-id"]},
        ),
    ]
