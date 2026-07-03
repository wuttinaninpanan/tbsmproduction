from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_inspectionreport_report_type_maxlen"),
    ]

    operations = [
        migrations.AddField(
            model_name="inspectionreport",
            name="note",
            field=models.TextField(blank=True, default=""),
        ),
    ]
