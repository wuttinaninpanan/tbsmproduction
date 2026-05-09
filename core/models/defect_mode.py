from django.db import models  # type: ignore
from django.conf import settings  # type: ignore
from core.models.base import BaseModel
from core.models.inspection.inspection_model import InspectionModels


class DefectMode(BaseModel):
    class DefectType(models.TextChoices):
        ASSY_NG = "ASSY_NG", "Assembly NG"
        PROCESS_NG = "PROCESS_NG", "Process NG"

    name_th = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    name_jp = models.CharField(max_length=100)
    description_th = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    description_jp = models.TextField(blank=True)
    defect_type = models.CharField(
        max_length=20,
        choices=DefectType.choices,
        null=True,
        blank=True
    )
    inspection_model = models.ForeignKey(
        InspectionModels,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="defect_modes",
    )
    class_name = models.CharField(max_length=255, blank=True, default="")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="defects"
    )

    def __str__(self):
        return self.name_en

    @property
    def name(self) -> str:
        return (self.name_th or self.name_en or self.name_jp or "").strip()

