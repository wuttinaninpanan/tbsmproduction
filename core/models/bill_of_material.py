from django.db import models # type:ignore
from core.models.base import BaseModel
from .item_list import Item_list
from django.conf import settings

## Bom master สิ่งที่สามารถเห็นทั้งหมด
class BillOfMaterial(BaseModel):
    item = models.OneToOneField(
        Item_list,
        on_delete=models.CASCADE,
        related_name="bom_header",
    )
    revision = models.CharField(max_length=20, default="A")
    latest_eci = models.CharField(max_length=50)
    scrap_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bom_headers",
    )
    def __str__(self):
        return f"BOM-{self.item.sku}-Rev{self.revision}"