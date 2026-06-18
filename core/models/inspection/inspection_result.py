from django.db import models
from core.models.base import BaseModel
from core.models.item_list import Item_list
from core.models.line import Line


class InspectionResult(BaseModel):

    inspectionitem = models.ForeignKey(
        Item_list,
        on_delete=models.CASCADE,
        related_name="inspection_result"
    )

    inspection_line = models.ForeignKey(
        Line,
        on_delete=models.CASCADE,
        related_name="inspection_result"
    )

    qr_work = models.CharField(max_length=255, blank=True, default="")
    result = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return self.result
