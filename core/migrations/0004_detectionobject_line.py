import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_scraprecord_machine_fk_drop_created_by"),
    ]

    operations = [
        migrations.AddField(
            model_name="detectionobject",
            name="line",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="detection_objects",
                to="core.line",
            ),
        ),
    ]
