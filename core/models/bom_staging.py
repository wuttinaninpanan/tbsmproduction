"""
BomStaging (ชั่วคราว)
──────────────────────────
Staging table สำหรับเก็บข้อมูล BOM ที่รวมจากหลายไฟล์ Excel
ก่อนที่จะทำความสะอาดและ import เข้า model จริง (Item_list / BillOfMaterial / BOMItemMaster)

Fields มาจาก header ของ BOM Update sheet ตามรูป:
  Level(1/2/3/4/*) | SD Code | Part No. | Part Name | Usage RM | Process |
  Line No. | Supplier Name | Model | Coil Press | Weight | SD_FG |
  SD Code_Component | Supplier | Line No.
"""

from django.db import models  # type:ignore
from django.conf import settings

from core.models.base import BaseModel


class BomStaging(BaseModel):
    # ─── Level marker (เก็บเลข level จริง เช่น "0", "1", "5", "10") ───
    lv_star = models.CharField(
        max_length=10, blank=True,
        help_text="Level marker (ค่าเลข level เป็น string)",
    )

    # Computed level — ใช้ใน query/filter
    level = models.IntegerField(
        null=True, blank=True,
        help_text="0=FG, 1..N=sub-levels",
    )

    # ─── Main columns ───
    sd_code = models.CharField(max_length=50, blank=True, db_index=True)
    part_no = models.CharField(max_length=100, blank=True, db_index=True)
    part_name = models.CharField(max_length=255, blank=True)
    usage_rm = models.DecimalField(
        max_digits=14, decimal_places=6, null=True, blank=True,
        help_text="Usage Raw Material (ปริมาณที่ใช้)",
    )
    process = models.CharField(max_length=50, blank=True)
    line_no = models.CharField(max_length=50, blank=True)
    supplier_name = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True, help_text="รุ่นรถ/โมเดล")

    # ─── Derived / lookup columns (ขวามือในภาพ — ไฮไลท์น้ำเงิน/เหลือง) ───
    coil_press = models.CharField(max_length=50, blank=True)
    weight = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True,
    )
    sd_fg = models.CharField(
        max_length=50, blank=True, db_index=True,
        help_text="SD Code ของ FG ที่ row นี้สังกัด (derived)",
    )
    sd_code_component = models.CharField(
        max_length=50, blank=True,
        help_text="SD Code ของ component (duplicate/lookup ref)",
    )
    supplier = models.CharField(
        max_length=100, blank=True,
        help_text="Supplier (derived/lookup ref)",
    )
    line_no_final = models.CharField(
        max_length=50, blank=True,
        help_text="Line No. final (derived/lookup ref)",
    )

    # ─── Metadata ───
    source_file = models.CharField(
        max_length=255, blank=True,
        help_text="ไฟล์ Excel ต้นทาง",
    )
    source_sheet = models.CharField(max_length=100, blank=True)
    row_index = models.IntegerField(default=0, help_text="ลำดับแถวต้นฉบับ")

    # ─── Cleanup flags ───
    is_reviewed = models.BooleanField(
        default=False,
        help_text="ทำความสะอาด/ตรวจแล้ว",
    )
    is_ready_to_import = models.BooleanField(
        default=False,
        help_text="พร้อม import เข้า master table",
    )
    note = models.CharField(max_length=500, blank=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bom_staging_rows",
        null=True, blank=True,
    )

    class Meta:
        ordering = ["source_file", "row_index"]
        indexes = [
            models.Index(fields=["sd_fg", "level"]),
            models.Index(fields=["source_file", "row_index"]),
        ]

    def __str__(self):
        parts = []
        if self.sd_code:
            parts.append(self.sd_code)
        if self.part_no:
            parts.append(self.part_no)
        head = " / ".join(parts) if parts else f"row-{self.row_index}"
        lvl = f"L{self.level}" if self.level is not None else "L?"
        return f"[{lvl}] {head}"
