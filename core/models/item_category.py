from django.db import models
from core.models.base import BaseModel
from django.conf import settings

class ItemCategory(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    description = models.CharField(max_length=255)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="itemcates"
    )


    def __str__(self):
        return self.name