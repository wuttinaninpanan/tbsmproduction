from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_inspectionreport_report_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="inspectionreport",
            name="target_count",
            field=models.PositiveIntegerField(default=30),
        ),
    ]
