# Generated for ProductionRecord start_time/end_time fields.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_detectionobject_defectdetection_kanbanpartmapping_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="productionrecord",
            name="start_time",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="productionrecord",
            name="end_time",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
