from django.db import models  # type:ignore
from core.models.base import BaseModel
from .item_list import Item_list
from .line import Line
from .item_stage import ItemStage
from django.conf import settings

class ItemLine(BaseModel):
    item = models.ForeignKey(
        Item_list,
        on_delete=models.CASCADE,
        related_name="item_lines"
    )

    line = models.ForeignKey(
        Line,
        on_delete=models.CASCADE,
        related_name="item_lines"
    )

    item_stage = models.ForeignKey(
        ItemStage,
        on_delete=models.CASCADE,
        related_name="item_lines"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="item_lines"
    )


    class Meta:
        unique_together = ("item", "line")
    