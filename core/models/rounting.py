from django.db import models
from core.models.base import BaseModel
from .item_list import Item_list
from .line import Line
from django.conf import settings

class Routing(BaseModel):
    product = models.ForeignKey(
        Item_list,
        on_delete=models.CASCADE,
        related_name="routings"
    )

    line = models.ForeignKey(
        Line,
        on_delete=models.CASCADE,
        related_name="routings"
    )

    cycle_time = models.FloatField(help_text="Cycle time in seconds")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="routings"
    )


    def __str__(self):
        return f"{self.product.sku} - {self.line.line_name} ({self.cycle_time}s)"