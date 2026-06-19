from decimal import Decimal
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


    def save(self, *args, **kwargs):
        # พาร์ทลูก (component) ต้องใช้อย่างน้อย 1 ชิ้นเสมอ
        # หากจำนวนเป็นศูนย์ (หรือว่าง) ให้ใช้ค่า default = 1
        if self.quantity is None or self.quantity <= 0:
            self.quantity = Decimal("1")
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["sequence"]


