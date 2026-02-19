from django.db import models  # type: ignore
from django.conf import settings  # type: ignore
from core.models.base import BaseModel


class DefectMode(BaseModel):
    name_th = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    name_jp = models.CharField(max_length=100)

    description_th = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    description_jp = models.TextField(blank=True)

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

