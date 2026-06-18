from django.conf import settings  # type: ignore
from django.db import models  # type: ignore

from core.models.base import BaseModel
from core.models.defect_mode import DefectMode
from core.models.item_list import Item_list
from core.models.line import Line


class DefectStat(BaseModel):
    """Counts each defect occurrence on a produced part (line × part × defect).

    Distinct from ScrapRecord: ScrapRecord counts how many *components* were
    physically scrapped, whereas DefectStat counts how many *units of the
    produced part* exhibited the defect — needed to compute defect-rate (%).
    """

    production_line = models.ForeignKey(
        Line,
        on_delete=models.PROTECT,
        related_name="defect_stats",
    )
    part = models.ForeignKey(
        Item_list,
        on_delete=models.PROTECT,
        related_name="defect_stats",
    )
    defect_mode = models.ForeignKey(
        DefectMode,
        on_delete=models.PROTECT,
        related_name="defect_stats",
    )
    quantity = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="defect_stats_created",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["production_line", "created_at"], name="defstat_line_created_idx"),
            models.Index(fields=["defect_mode", "created_at"], name="defstat_defect_created_idx"),
            models.Index(fields=["part", "created_at"], name="defstat_part_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.production_line.line_name} · {self.part.sd_code} · {self.defect_mode.name} × {self.quantity}"
