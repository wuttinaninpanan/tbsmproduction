from django.db import models  # type:ignore
from core.models.base import BaseModel
from .item_list import Item_list
from .line import Line
from .bill_of_material import BillOfMaterial
from django.conf import settings

## รายละเอียด Material ว่าประกอบตัวงานตัวใหนบ้าง
class BillOfMaterialItemMater(BaseModel):
    bom = models.ForeignKey(
        BillOfMaterial,
        on_delete=models.CASCADE,
        related_name="items_master"
    )

    component = models.ForeignKey(
        Item_list,
        on_delete=models.PROTECT,
        related_name="used_in_boms"
    )

    quantity = models.DecimalField(max_digits=12, decimal_places=4)
    unit = models.CharField(max_length=20)
    sequence = models.IntegerField(default=1)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="used_in_boms"
    )


    class Meta:
        ordering = ["sequence"]


