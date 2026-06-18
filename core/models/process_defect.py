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
    # The working day (วันทำการ) this lot belongs to — chosen once at the top of
    # /record/. Stays FIXED even when the shift crosses midnight, so reports can
    # group output by the business day it was produced for. Unlike start_time /
    # end_time below, it carries no clock. Nullable for legacy rows.
    production_date = models.DateField(null=True, blank=True)
    # The REAL wall-clock window the lot was produced in — full date + time, so
    # a night shift that crosses midnight keeps its true timestamps (and you can
    # tell a day shift from a night shift). Recorded once per line on Page 1 of
    # /record/ and applied to each produced part on that line; nullable so
    # legacy rows (and rows without a clock) work.
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    # Human-readable lot identifier, auto-built at /record/ save time so reports
    # can group every defect back to the lot it came from. Shape:
    #   L{LineName}{SD code}{prodYYMMDD}{startHHMM}{endHHMM}
    #   ("-" stripped from line name & SD code). The YYMMDD is the working day
    #   (production_date); start/end contribute only their local clock times.
    #   e.g. LDTA1DTI0926053008101000 for (DTA-1, DTI-09, prod 2026-05-30,
    #   08:10-10:00). Nullable: "single part" scraps have no product/time, and
    #   legacy rows predate this field.
    lot_number = models.CharField(max_length=80, null=True, blank=True, db_index=True)
    # The work shift this lot was produced in, chosen by the operator on Page 1
    # of /record/. Nullable: legacy rows predate the field, and a shift may not
    # always be picked. PROTECT so a shift in use can't be deleted out from
    # under its records.
    shift = models.ForeignKey(
        "Shift",
        on_delete=models.PROTECT,
        related_name="production_records",
        null=True,
        blank=True,
    )
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

    @staticmethod
    def build_lot_number(line_name, sd_code, production_date, start, end) -> str | None:
        """Compose the lot number from a (line, part, working day, window).

        ``L{LineName}{SD code}{prodYYMMDD}{startHHMM}{endHHMM}`` with every ``-``
        stripped from the line name and SD code. The YYMMDD is the working day
        (``production_date``); start/end only contribute their local clock time.
        Returns ``None`` when any piece is missing (e.g. a single-part scrap has
        no SD code/time), so the caller can store NULL rather than a malformed
        lot.
        """
        from django.utils import timezone

        if not line_name or not sd_code or production_date is None or start is None or end is None:
            return None
        ln = str(line_name).replace("-", "").strip()
        sd = str(sd_code).replace("-", "").strip()
        s = timezone.localtime(start)
        e = timezone.localtime(end)
        return f"L{ln}{sd}{production_date:%y%m%d}{s:%H%M}{e:%H%M}"

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
