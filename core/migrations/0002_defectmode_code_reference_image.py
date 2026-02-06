from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		("core", "0001_initial"),
	]

	operations = [
		migrations.AddField(
			model_name="defectmode",
			name="code",
			field=models.CharField(blank=True, max_length=64, null=True),
		),
		migrations.AddField(
			model_name="defectmode",
			name="reference_image",
			field=models.ImageField(blank=True, null=True, upload_to="defect_reference/"),
		),
	]
