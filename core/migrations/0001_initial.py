from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductionLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=32, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["code"],
            },
        ),
        migrations.CreateModel(
            name="PartNumber",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("number", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "production_line",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="parts",
                        to="core.productionline",
                    ),
                ),
            ],
            options={
                "ordering": ["production_line__code", "number"],
            },
        ),
        migrations.CreateModel(
            name="DefectMode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "part",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="defects",
                        to="core.partnumber",
                    ),
                ),
            ],
            options={
                "ordering": ["part__production_line__code", "part__number", "name"],
            },
        ),
        migrations.CreateModel(
            name="ScrapItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "defect_mode",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scraps",
                        to="core.defectmode",
                    ),
                ),
            ],
            options={
                "ordering": ["defect_mode__name", "name"],
            },
        ),
        migrations.CreateModel(
            name="ScrapRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("photo", models.ImageField(blank=True, null=True, upload_to="scrap_photos/")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scrap_records",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "defect_mode",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scrap_records",
                        to="core.defectmode",
                    ),
                ),
                (
                    "part_number",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scrap_records",
                        to="core.partnumber",
                    ),
                ),
                (
                    "production_line",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scrap_records",
                        to="core.productionline",
                    ),
                ),
                (
                    "scrap_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scrap_records",
                        to="core.scrapitem",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="partnumber",
            constraint=models.UniqueConstraint(
                fields=("production_line", "number"),
                name="uniq_part_per_line",
            ),
        ),
        migrations.AddConstraint(
            model_name="defectmode",
            constraint=models.UniqueConstraint(
                fields=("part", "name"),
                name="uniq_defect_per_part",
            ),
        ),
        migrations.AddConstraint(
            model_name="scrapitem",
            constraint=models.UniqueConstraint(
                fields=("defect_mode", "name"),
                name="uniq_scrap_per_defect",
            ),
        ),
    ]
