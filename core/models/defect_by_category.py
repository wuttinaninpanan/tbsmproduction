from django.db import models # type:ignore
from core.models.base import BaseModel  # type:ignore
from django.conf import settings # type:ignore
from .item_category import ItemCategory
from .defect_mode import DefectMode


"""
อกกแบบให้Fetch categoryทั้งหมด
for rows in Category:
    rows.category_name

    for dm in defect_mode:
        <inpuy type="checkbox" dm.ชื่อDefect />

Category ['Round recline','Lower arm','Seat track','Loop handle','Hinge']
 """

class DefectByCategory(BaseModel):
    title = models.CharField(max_length=255)
    category = models.ForeignKey(
        ItemCategory,
        on_delete=models.PROTECT,
        related_name='category_defects'
    )

    defect_mode = models.ForeignKey(
        DefectMode,
        on_delete=models.PROTECT,
        related_name='category_defects'
    )

    is_inlist = models.BooleanField(default=False)
    description = models.CharField(max_length=100)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.CASCADE,
        related_name="category_defects"
    )

    def __str__(self):
        return self.title

