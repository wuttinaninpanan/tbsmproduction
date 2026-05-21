from django.db import models
from core.models.base import BaseModel
from core.models.scrap_record import ScrapRecord


class InspectionDefect(BaseModel):
    scrap_record = models.ForeignKey(
        ScrapRecord,
        on_delete=models.CASCADE,
        related_name="inspection_defects",
    )

    qr_work = models.CharField(max_length=255, blank=True, default="")
    result = models.CharField(max_length=255, blank=True, default="")
    photo = models.FileField(
        upload_to="inspection_defect_photos/",
        blank=True,
        null=True,
    )

    def __str__(self) -> str:
        return f"{self.qr_work} — {self.result}".strip(" —")
