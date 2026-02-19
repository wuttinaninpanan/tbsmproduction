from django.db import migrations, models


class Migration(migrations.Migration):
	dependencies = [
		("core", "0004_rename_line_process_field"),
	]

	operations = [
		migrations.AddField(
			model_name="item_list",
			name="reference_image",
			field=models.FileField(blank=True, null=True, upload_to="component_part_reference/"),
		),
	]
