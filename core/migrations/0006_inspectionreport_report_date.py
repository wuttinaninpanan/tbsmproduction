import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_inspectionreport"),
    ]

    operations = [
        migrations.AddField(
            model_name="inspectionreport",
            name="report_date",
            field=models.DateField(default=django.utils.timezone.localdate),
        ),
    ]
