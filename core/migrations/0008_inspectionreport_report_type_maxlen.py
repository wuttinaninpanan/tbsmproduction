from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_inspectionreport_target_count"),
    ]

    operations = [
        migrations.AlterField(
            model_name="inspectionreport",
            name="report_type",
            field=models.CharField(
                choices=[("NORMAL", "ปกติ"), ("OIL", "แบบทาน้ำมัน")],
                default="NORMAL",
                max_length=50,
            ),
        ),
    ]
