from django.conf import settings
from django.db import models  # type: ignore

from core.models.base import BaseModel


class InOut(BaseModel):
    """inner/outer classification used by Item_list as a product type."""

    title = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inouts",
    )

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title
