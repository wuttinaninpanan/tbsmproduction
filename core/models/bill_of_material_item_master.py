from django.db import models  # type:ignore
from core.models.base import BaseModel
from .item_list import Item_list
from .line import Line
from .bill_of_material import BillOfMaterial
from django.conf import settings


class BillOfMaterialItemMaster(BaseModel):
    """
    1 record = 1 component ใน BOM
    bom  → parent item ที่กำลังประกอบ
    component → child item ที่ใช้ประกอบ
    """

    class ProcessType(models.TextChoices):
        FINISH_GOOD = "FG", "Finish Good"
        PRESS_500T = "500T", "Press 500T"
        PRESS_600T = "600T", "Press 600T"
        PRESS_1000T = "1000T", "Press 1000T"
        COIL = "COIL", "Coil (Raw Coil Input)"
        COMPONENT = "COMP", "Purchased Component"
        WELDING = "WELD", "Welding"
        SURFACE = "SURF", "Surface Treatment"
        OTHER = "OTHER", "Other"

    bom = models.ForeignKey(
        BillOfMaterial,
        on_delete=models.CASCADE,
        related_name="items_master",
    )

    component = models.ForeignKey(
        Item_list,
        on_delete=models.PROTECT,
        related_name="used_in_boms",
    )

    quantity = models.DecimalField(max_digits=12, decimal_places=6)
    unit = models.CharField(max_length=5, default="PCS")
    sequence = models.IntegerField(default=1)

    # กระบวนการที่ใช้ผลิต/รับ component นี้ (สำหรับ routing และ production planning)
    process = models.CharField(
        max_length=10,
        choices=ProcessType.choices,
        default="",
        blank=True,
    )

    # scrap ต่อ component (override BOM-level scrap_percent ถ้าระบุ)
    scrap_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="% scrap เฉพาะ component นี้ (0 = ใช้ค่าจาก BOM header)",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="used_in_boms",
    )

    class Meta:
        ordering = ["sequence"]
        unique_together = ("bom", "component")

    def __str__(self):
        return f"{self.bom} → {self.component.sku} x{self.quantity}"

    @property
    def effective_scrap(self) -> float:
        """ใช้ scrap ของ component เอง ถ้าระบุ ไม่งั้นใช้ BOM header"""
        if self.scrap_percent:
            return float(self.scrap_percent)
        return float(self.bom.scrap_percent)

    @property
    def quantity_with_scrap(self):
        """ปริมาณที่ต้องใช้จริง รวม scrap แล้ว"""
        return self.quantity * (1 + self.effective_scrap / 100)


