from django.db import models  # type:ignore
from core.models.base import BaseModel
from .item_category import ItemCategory
from django.conf import settings

class Item_list(BaseModel):
    sd_code = models.CharField(max_length=255)
    part_number = models.CharField(max_length=255)
    part_name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True)
    weight = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="kg")

    reference_image = models.FileField(
        upload_to="component_part_reference/",
        blank=True,
        null=True,
    )

    category = models.ForeignKey(
        ItemCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items"
    )

    purchased_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    level = models.IntegerField(blank=True, null=True)
    comment = models.CharField(max_length=255, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="items"
    )


    def __str__(self):
        return f"{self.sku} - {self.part_name}"

    @property
    def number(self) -> str:
        return (self.part_number or "").strip()

    @property
    def name(self) -> str:
        return (self.part_name or "").strip()

