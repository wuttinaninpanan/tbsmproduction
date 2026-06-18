from django.db import models

from core.models.base import BaseModel


class Shift(BaseModel):
    """กะการทำงานขององค์กร (Shift A / Shift B / Shift D).

    Seeded with 3 default rows by migration. ``display_number`` controls the
    order shown in the Record page (and any report) — lower number first.
    """

    name = models.CharField(max_length=50, unique=True)
    display_number = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_number", "name"]

    def __str__(self) -> str:
        return self.name
