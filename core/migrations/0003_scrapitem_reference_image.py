from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_defectmode_code_reference_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="scrapitem",
            name="reference_image",
            field=models.ImageField(blank=True, null=True, upload_to="scrap_reference/"),
        ),
    ]
