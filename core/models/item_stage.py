from django.db import models  # type:ignore
from core.models.base import BaseModel
from django.conf import settings

class ItemStage(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(max_length=255)
    code_prefix = models.CharField(max_length=4, blank=True, default="")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="itemstage"
    )


    def __str__(self):
        return self.name
