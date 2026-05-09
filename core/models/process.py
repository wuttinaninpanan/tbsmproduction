from django.conf import settings
from django.db import models  # type: ignore

from core.models.base import BaseModel
from core.models.plant import Plant


class Process(BaseModel):
    """Production process step (e.g. Press, Sub-assembly, Final inspection)."""

    title = models.CharField(max_length=100, unique=True)
    plant = models.ForeignKey(
        Plant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processes",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="production_processes",
    )

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title
