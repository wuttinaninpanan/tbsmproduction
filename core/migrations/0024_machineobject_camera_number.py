from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0023_add_model_type_to_inspection_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="machineobject",
            name="camera_number",
            field=models.PositiveSmallIntegerField(default=1),
        ),
    ]
