from django.db import models
from core.models.base import BaseModel
from core.models.defect_by_category import DefectByCategory
from core.models.inspection.inspection_model import InspectionModels


class InspectionModelsDefect(BaseModel):

    inspection_model_id = models.ForeignKey(
        InspectionModels,
        on_delete=models.CASCADE,
        related_name="inspection_defects"
    )
    defect_mode_id = models.ForeignKey(
        DefectByCategory,
        on_delete=models.CASCADE,
        related_name="inspection_defects"
    )
    class_name = models.CharField(max_length=255)
    description_en = models.TextField(blank=True, null=True)
    description_th = models.TextField(blank=True, null=True)
    model_path = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.class_name