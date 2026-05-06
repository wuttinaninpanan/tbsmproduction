"""
Migration: ลบ columns lv1..lv4 ออกจาก BomStaging
─────────────────────────────────────────────────
เหลือเฉพาะ lv_star (เก็บเลข level เป็น string สำหรับทุก level)
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_bom_staging"),
    ]

    operations = [
        migrations.RemoveField(model_name="bomstaging", name="lv1"),
        migrations.RemoveField(model_name="bomstaging", name="lv2"),
        migrations.RemoveField(model_name="bomstaging", name="lv3"),
        migrations.RemoveField(model_name="bomstaging", name="lv4"),
        migrations.AlterField(
            model_name="bomstaging",
            name="lv_star",
            field=models.CharField(
                blank=True,
                help_text="Level marker (ค่าเลข level เป็น string)",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="bomstaging",
            name="level",
            field=models.IntegerField(
                blank=True,
                null=True,
                help_text="0=FG, 1..N=sub-levels",
            ),
        ),
    ]
