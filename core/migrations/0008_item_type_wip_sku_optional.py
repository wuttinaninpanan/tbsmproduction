"""
Migration: ปรับ ItemType ให้สอดคล้องกับ production flow จริง + ทำให้ sku optional

Changes:
  - ItemType choices: เพิ่ม WIP, เปลี่ยน SEMI → SEMI_FG, เปลี่ยนรหัส COMPONENT → COMP
    (flow: RAW → Stamping(WIP) → Sub-line(WIP) → Assembly(Semi-FG) → Inspection(FG))
  - sku: เปลี่ยนเป็น blank+null (ใช้เฉพาะแยก variant — พาร์ทผลิตไม่จำเป็น)
  - sd_code: อนุญาตให้ blank (items ที่ยังไม่มี SD Code)
  - part_number: เพิ่ม index เพื่อ lookup เร็ว
  - Data migration: แปลง item_type 'SEMI' เก่า → 'SEMI_FG'
"""

from django.db import migrations, models


NEW_CHOICES = [
    ("FG", "Finished Good (ผ่าน Inspection)"),
    ("SEMI_FG", "Semi-FG (ผ่าน Assembly)"),
    ("WIP", "WIP (หลัง Stamping หรือ Sub-line)"),
    ("COMP", "Purchased Component (ซื้อจาก supplier)"),
    ("RAW", "Raw Material / Coil"),
    ("CONS", "Consumable (Oil / Paint / Welding Wire)"),
]


def migrate_semi_to_semi_fg(apps, schema_editor):
    """รหัส 'SEMI' เก่า → 'SEMI_FG' ใหม่"""
    Item_list = apps.get_model("core", "item_list")
    Item_list.objects.filter(item_type="SEMI").update(item_type="SEMI_FG")


def reverse_semi_fg(apps, schema_editor):
    Item_list = apps.get_model("core", "item_list")
    Item_list.objects.filter(item_type="SEMI_FG").update(item_type="SEMI")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_bom_item_enhancements"),
    ]

    operations = [
        # 1. Alter item_type choices + blank=True, default=""
        migrations.AlterField(
            model_name="item_list",
            name="item_type",
            field=models.CharField(
                choices=NEW_CHOICES,
                blank=True,
                default="",
                help_text="ประเภท item — ผู้ใช้กำหนดเอง (ตาม production flow)",
                max_length=10,
            ),
        ),

        # 2. Data migration: rename SEMI → SEMI_FG
        migrations.RunPython(migrate_semi_to_semi_fg, reverse_semi_fg),

        # 3. sku: optional (blank+null)
        migrations.AlterField(
            model_name="item_list",
            name="sku",
            field=models.CharField(
                blank=True, null=True, max_length=100, unique=True
            ),
        ),

        # 4. sd_code: blank=True
        migrations.AlterField(
            model_name="item_list",
            name="sd_code",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),

        # 5. part_number: add db_index
        migrations.AlterField(
            model_name="item_list",
            name="part_number",
            field=models.CharField(db_index=True, max_length=255),
        ),

        # 6. BOMItemMaster.process: default ว่าง (เดิมเป็น COMP)
        migrations.AlterField(
            model_name="billofmaterialitemmaster",
            name="process",
            field=models.CharField(
                blank=True,
                choices=[
                    ("FG", "Finish Good"),
                    ("500T", "Press 500T"),
                    ("600T", "Press 600T"),
                    ("1000T", "Press 1000T"),
                    ("COIL", "Coil (Raw Coil Input)"),
                    ("COMP", "Purchased Component"),
                    ("WELD", "Welding"),
                    ("SURF", "Surface Treatment"),
                    ("OTHER", "Other"),
                ],
                default="",
                max_length=10,
            ),
        ),
    ]
