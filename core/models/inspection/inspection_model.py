from django.db import models
from core.models.base import BaseModel


class InspectionModels(BaseModel):
    class_name = models.CharField(max_length=255)
    description_en = models.TextField(blank=True, null=True)
    description_th = models.TextField(blank=True, null=True)
    model_path = models.TextField(blank=True, null=True)
    count_detect = models.IntegerField(default=0)

    def __str__(self):
        return self.class_name