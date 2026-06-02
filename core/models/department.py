from django.db import models
from core.models.base import BaseModel


class Department(BaseModel):
    division = models.ForeignKey(
        "core.Division",
        on_delete=models.PROTECT,
        related_name="departments",
        null=True,
        blank=True,
    )
    code = models.CharField(max_length=20, unique=True, null=True, blank=True, db_index=True)
    short_name = models.CharField(max_length=10, blank=True)
    name = models.CharField(max_length=255, unique=True)
    name_en = models.CharField(max_length=200, blank=True)
    name_ja = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    description_ja = models.TextField(blank=True)

    def __str__(self):
        return self.name
