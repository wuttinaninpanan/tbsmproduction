"""
Migration: BOM & Item enhancements for BOM Master system.

Changes:
  ItemPrice     : rename field customer → partner (pre-existing rename, no prior migration)
  Item_list     : add item_type, unit, supplier; adjust decimal precision for weight/cost/price
  BillOfMaterial: add vehicle_model, eci_date; lasted_eci blank=True; unique_together
  BillOfMaterialItemMater: rename class → BillOfMaterialItemMaster;
                           add process, scrap_percent; adjust quantity precision
"""

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_scraprecord_comment"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ─── 1. ItemPrice: rename customer → partner ───────────────────────────
        migrations.RenameField(
            model_name="itemprice",
            old_name="customer",
            new_name="partner",
        ),
        migrations.AlterField(
            model_name="itemprice",
            name="partner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="item_prices",
                to="core.businesspartner",
            ),
        ),

        # ─── 2. Item_list: add item_type ───────────────────────────────────────
        migrations.AddField(
            model_name="item_list",
            name="item_type",
            field=models.CharField(
                choices=[
                    ("FG", "Finished Good"),
                    ("SEMI", "Semi-Finished / Sub-Assembly"),
                    ("COMP", "Purchased Component"),
                    ("RAW", "Raw Material / Coil"),
                    ("CONS", "Consumable (Oil / Paint / Wire)"),
                ],
                default="COMP",
                help_text="ประเภท item สำหรับระบบต้นทุนและ inventory",
                max_length=10,
            ),
        ),

        # ─── 3. Item_list: add unit ────────────────────────────────────────────
        migrations.AddField(
            model_name="item_list",
            name="unit",
            field=models.CharField(
                choices=[
                    ("PCS", "Piece"),
                    ("KG", "Kilogram"),
                    ("L", "Liter"),
                    ("M", "Meter"),
                    ("SET", "Set"),
                ],
                default="PCS",
                help_text="หน่วยนับ",
                max_length=5,
            ),
        ),

        # ─── 4. Item_list: add supplier FK ────────────────────────────────────
        migrations.AddField(
            model_name="item_list",
            name="supplier",
            field=models.ForeignKey(
                blank=True,
                help_text="Supplier หลัก (ซื้อจากใคร)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="supplied_items",
                to="core.businesspartner",
            ),
        ),

        # ─── 5. Item_list: adjust decimal precision ────────────────────────────
        migrations.AlterField(
            model_name="item_list",
            name="weight",
            field=models.DecimalField(
                decimal_places=4, default=0, help_text="kg", max_digits=10
            ),
        ),
        migrations.AlterField(
            model_name="item_list",
            name="purchased_price",
            field=models.DecimalField(decimal_places=4, default=0, max_digits=12),
        ),
        migrations.AlterField(
            model_name="item_list",
            name="cost",
            field=models.DecimalField(decimal_places=4, default=0, max_digits=12),
        ),

        # ─── 6. BillOfMaterial: add vehicle_model ─────────────────────────────
        migrations.AddField(
            model_name="billofmaterial",
            name="vehicle_model",
            field=models.CharField(
                blank=True, max_length=50, help_text="รุ่นรถยนต์ เช่น 578W, CAMRY"
            ),
        ),

        # ─── 7. BillOfMaterial: add eci_date ──────────────────────────────────
        migrations.AddField(
            model_name="billofmaterial",
            name="eci_date",
            field=models.DateField(blank=True, null=True, help_text="วันที่ ECI มีผล"),
        ),

        # ─── 8. BillOfMaterial: lasted_eci allow blank ────────────────────────
        migrations.AlterField(
            model_name="billofmaterial",
            name="lasted_eci",
            field=models.CharField(blank=True, max_length=50),
        ),

        # ─── 9. BillOfMaterial: unique_together ───────────────────────────────
        migrations.AlterUniqueTogether(
            name="billofmaterial",
            unique_together={("item", "revision")},
        ),

        # ─── 10. BillOfMaterialItemMater: rename class ────────────────────────
        migrations.RenameModel(
            old_name="BillOfMaterialItemMater",
            new_name="BillOfMaterialItemMaster",
        ),

        # ─── 11. BillOfMaterialItemMaster: add process field ──────────────────
        migrations.AddField(
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
                default="COMP",
                max_length=10,
            ),
        ),

        # ─── 12. BillOfMaterialItemMaster: add scrap_percent per component ────
        migrations.AddField(
            model_name="billofmaterialitemmaster",
            name="scrap_percent",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="% scrap เฉพาะ component นี้ (0 = ใช้ค่าจาก BOM header)",
                max_digits=5,
            ),
        ),

        # ─── 13. BillOfMaterialItemMaster: adjust quantity precision ──────────
        migrations.AlterField(
            model_name="billofmaterialitemmaster",
            name="quantity",
            field=models.DecimalField(decimal_places=6, max_digits=12),
        ),

        # ─── 14. BillOfMaterialItemMaster: unique_together (bom, component) ───
        migrations.AlterUniqueTogether(
            name="billofmaterialitemmaster",
            unique_together={("bom", "component")},
        ),
    ]
