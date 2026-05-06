from django.db import models  # type:ignore
from core.models.base import BaseModel
from .item_list import Item_list
from django.conf import settings


class BillOfMaterial(BaseModel):
    item = models.ForeignKey(
        Item_list,
        on_delete=models.CASCADE,
        related_name="bom_headers",
    )

    revision = models.CharField(max_length=20, default="A")

    # ECI (Engineering Change Instruction) tracking
    lasted_eci = models.CharField(max_length=50, blank=True)
    eci_date = models.DateField(
        null=True,
        blank=True,
        help_text="วันที่ ECI มีผล",
    )

    # รุ่นรถยนต์ที่ใช้ BOM นี้ เช่น '578W', 'CAMRY'
    vehicle_model = models.CharField(max_length=50, blank=True)

    # scrap_percent ระดับ BOM header (ค่า default ถ้าไม่ได้ระบุต่อ component)
    scrap_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bom_headers",
    )

    class Meta:
        # item หนึ่งตัวมีได้หลาย revision แต่ revision เดียวกันซ้ำไม่ได้
        unique_together = ("item", "revision")

    def __str__(self):
        return f"BOM-{self.item.sku}-Rev{self.revision}"