from django.db import models
from core.models.base import BaseModel


class Department(BaseModel):
    name = models.CharField(max_length=255, unique=True)        # ชื่อแผนก
    description = models.CharField(max_length=255, blank=True)  # คำอธิบาย

    def __str__(self):
        return self.name
