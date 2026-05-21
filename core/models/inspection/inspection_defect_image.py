from django.db import models
from core.models.base import BaseModel
from core.models.inspection.inspection_defect import InspectionDefect


class InspectionDefectImage(BaseModel):
    defect = models.ForeignKey(
        InspectionDefect,
        on_delete=models.CASCADE,
        related_name="images",
    )

    image_path = models.TextField(blank=True, default="")
    caption = models.CharField(max_length=255, blank=True, default="")
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self) -> str:
        return f"{self.defect_id} · {self.image_path}"
