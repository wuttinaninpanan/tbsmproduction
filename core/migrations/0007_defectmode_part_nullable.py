from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_scrapitem_part_to_partnumber"),
    ]

    operations = [
        migrations.AlterField(
            model_name="defectmode",
            name="part",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name="defects",
                to="core.partnumber",
            ),
        ),
    ]
