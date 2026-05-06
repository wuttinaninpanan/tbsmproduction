"""
Migration: สร้าง BomStaging table
────────────────────────────────────
Staging table สำหรับเก็บข้อมูล BOM ที่รวมจากหลาย Excel ก่อนทำความสะอาด
Fields ตาม header ของ BOM Update sheet
"""

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_item_type_wip_sku_optional"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BomStaging",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False,
                                        primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),

                # Level markers
                ("lv1", models.CharField(blank=True, help_text="Level 1 marker", max_length=10)),
                ("lv2", models.CharField(blank=True, help_text="Level 2 marker", max_length=10)),
                ("lv3", models.CharField(blank=True, help_text="Level 3 marker", max_length=10)),
                ("lv4", models.CharField(blank=True, help_text="Level 4 marker", max_length=10)),
                ("lv_star", models.CharField(blank=True, help_text="Level * marker (level 5+)", max_length=10)),
                ("level", models.IntegerField(blank=True, null=True,
                                              help_text="0=FG, 1-4=sub-levels, 5=*")),

                # Main columns
                ("sd_code", models.CharField(blank=True, db_index=True, max_length=50)),
                ("part_no", models.CharField(blank=True, db_index=True, max_length=100)),
                ("part_name", models.CharField(blank=True, max_length=255)),
                ("usage_rm", models.DecimalField(blank=True, decimal_places=6,
                                                 help_text="Usage Raw Material (ปริมาณที่ใช้)",
                                                 max_digits=14, null=True)),
                ("process", models.CharField(blank=True, max_length=50)),
                ("line_no", models.CharField(blank=True, max_length=50)),
                ("supplier_name", models.CharField(blank=True, max_length=100)),
                ("model", models.CharField(blank=True, help_text="รุ่นรถ/โมเดล", max_length=100)),

                # Derived / lookup
                ("coil_press", models.CharField(blank=True, max_length=50)),
                ("weight", models.DecimalField(blank=True, decimal_places=4,
                                               max_digits=12, null=True)),
                ("sd_fg", models.CharField(blank=True, db_index=True,
                                           help_text="SD Code ของ FG ที่ row นี้สังกัด (derived)",
                                           max_length=50)),
                ("sd_code_component", models.CharField(blank=True,
                                                       help_text="SD Code ของ component (duplicate/lookup ref)",
                                                       max_length=50)),
                ("supplier", models.CharField(blank=True,
                                              help_text="Supplier (derived/lookup ref)",
                                              max_length=100)),
                ("line_no_final", models.CharField(blank=True,
                                                   help_text="Line No. final (derived/lookup ref)",
                                                   max_length=50)),

                # Metadata
                ("source_file", models.CharField(blank=True,
                                                 help_text="ไฟล์ Excel ต้นทาง",
                                                 max_length=255)),
                ("source_sheet", models.CharField(blank=True, max_length=100)),
                ("row_index", models.IntegerField(default=0, help_text="ลำดับแถวต้นฉบับ")),

                # Cleanup flags
                ("is_reviewed", models.BooleanField(default=False,
                                                    help_text="ทำความสะอาด/ตรวจแล้ว")),
                ("is_ready_to_import", models.BooleanField(default=False,
                                                            help_text="พร้อม import เข้า master table")),
                ("note", models.CharField(blank=True, max_length=500)),

                ("user", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="bom_staging_rows",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "ordering": ["source_file", "row_index"],
            },
        ),
        migrations.AddIndex(
            model_name="bomstaging",
            index=models.Index(fields=["sd_fg", "level"], name="core_bomsta_sd_fg_idx"),
        ),
        migrations.AddIndex(
            model_name="bomstaging",
            index=models.Index(fields=["source_file", "row_index"],
                               name="core_bomsta_source_idx"),
        ),
    ]
