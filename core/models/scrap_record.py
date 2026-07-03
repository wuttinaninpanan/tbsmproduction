from django.db import models  # type: ignore

from core.models.base import BaseModel
from core.models.defect_mode import DefectMode
from core.models.item_list import Item_list
from core.models.line import Line
from core.models.inspection.machine import Machine


class ScrapRecord(BaseModel):
    production_line = models.ForeignKey(
        Line,
        on_delete=models.PROTECT,
        related_name="scrap_records",
    )
    part_number = models.ForeignKey(
        Item_list,
        on_delete=models.PROTECT,
        related_name="scrap_records_as_part",
    )
    defect_mode = models.ForeignKey(
        DefectMode,
        on_delete=models.PROTECT,
        related_name="scrap_records",
    )
    component_part = models.ForeignKey(
        Item_list,
        on_delete=models.PROTECT,
        related_name="scrap_records_as_component",
    )
    quantity = models.PositiveIntegerField(default=1)

    comment = models.TextField(blank=True, null=True)

    photo = models.FileField(upload_to="scrap_photos/", blank=True, null=True)

    machine = models.ForeignKey(
        Machine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scrap_records",
    )

    class Meta:
        ordering = ["-created_at"]

