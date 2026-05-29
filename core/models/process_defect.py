from django.conf import settings  # type: ignore
from django.db import models  # type: ignore

from core.models.base import BaseModel


class ProductionRecord(BaseModel):
    """One production event: a part produced on a line, with the quantity made.
    This is the new recording backbone (kept separate from the legacy
    ``core_scraprecord`` table, which stays as-is). Defect counts and the
    scrapped sub-parts hang off this row via ``ProcessDefect`` →
    ``ProcessDefectScrap``, so the defect rate (%) is always derived from those
    children, never stored.
    """

    line = models.ForeignKey(
        "Line",
        on_delete=models.PROTECT,
        related_name="production_records",
    )
    # Nullable: a "single part" scrap (a not-yet-assembled component thrown
    # away on the line) can't be tied to a produced product, so it has no item.
    item = models.ForeignKey(
        "Item_list",
        on_delete=models.PROTECT,
        related_name="production_records_as_part",
        null=True,
        blank=True,
    )
    products_quantity = models.PositiveIntegerField(default=1)
    # The window the operator says this lot was produced in. Recorded per
    # (line, part) row on the new Page 1 of /record/; nullable so legacy
    # rows (and rows entered without a clock) keep working.
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="production_records_created",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        item_label = self.item.sd_code if self.item_id else "Single part"
        return f"{self.line.line_name} · {item_label} × {self.products_quantity}"

    @property
    def total_defect_quantity(self) -> int:
        """Number of produced units flagged defective (sum of all ProcessDefect)."""
        return sum(d.quantity for d in self.defects.all())

    @property
    def defect_rate(self) -> float:
        """Defective units as a percentage of produced units (0 when none made)."""
        if not self.products_quantity:
            return 0.0
        return round(self.total_defect_quantity / self.products_quantity * 100, 2)


class ProcessDefect(BaseModel):
    """How many produced units of a ProductionRecord showed one defect mode."""

    production_record = models.ForeignKey(
        ProductionRecord,
        on_delete=models.CASCADE,
        related_name="defects",
    )
    defect_mode = models.ForeignKey(
        "DefectMode",
        on_delete=models.PROTECT,
        related_name="process_defects",
    )
    quantity = models.PositiveIntegerField(default=1)
    comment = models.TextField(blank=True, null=True)

    def __str__(self) -> str:
        return f"{self.defect_mode} × {self.quantity}"


class ProcessDefectScrap(BaseModel):
    """A sub-part (BOM component) scrapped as a result of a ProcessDefect."""

    process_defect = models.ForeignKey(
        ProcessDefect,
        on_delete=models.CASCADE,
        related_name="details",
    )
    component_part = models.ForeignKey(
        "Item_list",
        on_delete=models.PROTECT,
        related_name="process_defect_scraps",
    )
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.component_part} × {self.quantity}"
