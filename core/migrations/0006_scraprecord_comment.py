from django.db import migrations, models


class Migration(migrations.Migration):
	dependencies = [
		("core", "0005_item_list_reference_image"),
	]

	operations = [
		migrations.AddField(
			model_name="scraprecord",
			name="comment",
			field=models.TextField(blank=True, null=True),
		),
	]
