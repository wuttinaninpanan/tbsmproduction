import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_detectionobject_line"),
    ]

    operations = [
        migrations.CreateModel(
            name="InspectionReport",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                ("report_type", models.CharField(choices=[("NORMAL", "ปกติ"), ("OIL", "แบบทาน้ำมัน")], default="NORMAL", max_length=20)),
                ("count", models.PositiveIntegerField(default=1)),
                ("line", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="inspection_reports", to="core.line")),
                ("object", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="inspection_reports", to="core.detectionobject")),
                ("defect_mode", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="inspection_reports", to="core.defectmode")),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
