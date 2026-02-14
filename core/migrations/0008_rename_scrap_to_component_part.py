from django.db import migrations, models


class Migration(migrations.Migration):
	dependencies = [
		("core", "0007_defectmode_part_nullable"),
	]

	operations = [
		migrations.RenameModel(
			old_name="ScrapItem",
			new_name="ComponentPart",
		),
		migrations.RenameModel(
			old_name="ScrapRecord",
			new_name="ComponentPartRecord",
		),
		migrations.RenameField(
			model_name="componentpartrecord",
			old_name="scrap_item",
			new_name="component_part",
		),
		migrations.RemoveConstraint(
			model_name="componentpart",
			name="uniq_scrap_per_part",
		),
		migrations.AddConstraint(
			model_name="componentpart",
			constraint=models.UniqueConstraint(
				fields=("part_number", "name"),
				name="uniq_component_part_per_part",
			),
		),
	]
