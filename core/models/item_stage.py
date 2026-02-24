from django.db import models  # type:ignore
from core.models.base import BaseModel
from django.conf import settings

class ItemStage(BaseModel):
    name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="itemstage"
    )

    
    def __str__(self):
        return self.name
    
        # RAW_MATERIAL = "raw_mat", "Raw material"
        # WIP = "wip", "Work in process"
        # SEMI_FG = "semi_fg", "Semi finished goods"
        # FG = "fg", "Finished goods"
        # DEL = "delivery","Delivery"