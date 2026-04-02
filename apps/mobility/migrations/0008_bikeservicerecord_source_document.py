from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mobility", "0007_fuelrefilllog"),
    ]

    operations = [
        migrations.AddField(
            model_name="bikeservicerecord",
            name="source_document",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="imported_service_records",
                to="mobility.bikedocument",
            ),
        ),
    ]
