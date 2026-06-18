from django.conf import settings
from django.db import models  # type: ignore

from core.models.base import BaseModel


class Plant(BaseModel):
    """Production plant (e.g. In-house, Out source)."""

    title = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="plants",
    )

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title
