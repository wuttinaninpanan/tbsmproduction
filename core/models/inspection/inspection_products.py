from django.db import models
from core.models.base import BaseModel


class InspectionProducts(BaseModel):
    sd_code = models.CharField(max_length=255)
    work_qr = models.CharField(max_length=255)
    qtt_box = models.IntegerField(default=0)
    products_path_image = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.sd_code