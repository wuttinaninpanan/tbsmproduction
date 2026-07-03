import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_bom_item_quantity_min_one"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="scraprecord",
            name="created_by",
        ),
        # machine_id column already exists in DB (added outside Django migrations).
        # SeparateDatabaseAndState skips the ALTER TABLE but keeps Django's state correct.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="scraprecord",
                    name="machine",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scrap_records",
                        to="core.machine",
                    ),
                ),
            ],
        ),
    ]
