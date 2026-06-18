from django.db import models
from core.models.base import BaseModel
from core.models.item_list import Item_list
from core.models.line import Line


class InspectionError(BaseModel):

    inspectionitem = models.ForeignKey(
        Item_list,
        on_delete=models.CASCADE,
        related_name="inspection_error"
    )

    inspection_line = models.ForeignKey(
        Line,
        on_delete=models.CASCADE,
        related_name="inspection_error"
    )

    qr_work = models.CharField(max_length=255, blank=True, default="")
    photo = models.FileField(upload_to="inspection_photos/", blank=True, null=True)
    result = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return self.result