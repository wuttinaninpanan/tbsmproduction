from django.db import models # type:ignore
from core.models.base import BaseModel
from .item_list import Item_list
from .businesspartner import BusinessPartner
from django.conf import settings

class ItemPrice(BaseModel):
    item = models.ForeignKey(
        Item_list,
        on_delete=models.CASCADE,
        related_name="item_prices"
    )

    partner = models.ForeignKey(
        BusinessPartner,
        on_delete=models.CASCADE,
        related_name="item_prices",
        null=True,
        blank=True
    )

    price = models.DecimalField(max_digits=12, decimal_places=2)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="item_prices"
    )


    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['item', 'partner'],
                name='unique_product_partner_price'
            )
        ]

    def __str__(self):
        return f"{self.partner.name} - {self.item.part_name}"