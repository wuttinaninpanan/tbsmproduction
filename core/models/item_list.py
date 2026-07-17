from django.db import models, transaction  # type:ignore
from core.models.base import BaseModel
from .item_category import ItemCategory
from .item_stage import ItemStage
from .portion import Portion
from .side import Side
from .inout import InOut
from .way import Way
from django.conf import settings

ITEM_CODE_PADDING = 6


def extract_item_number(item_code) -> int | None:
    """Pull the numeric portion out of an item_code (e.g. 'G000005' -> 5).

    Returns None if no digits are found or the string can't be parsed.
    """
    if not item_code:
        return None
    digits = "".join(c for c in str(item_code) if c.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except (ValueError, TypeError):
        return None


def format_item_code(prefix: str, number: int) -> str:
    return f"{prefix}{number:0{ITEM_CODE_PADDING}d}"


# Excel/Sheets error literals. When a spreadsheet formula breaks (e.g. a deleted
# referenced cell), openpyxl with data_only=True reads the cached value as one of
# these strings. They must never be imported as real data — a bad import on
# 2026-06-09 created 379 duplicate items with sd_code "#REF!" exactly this way.
SPREADSHEET_ERROR_VALUES = frozenset(
    {"#REF!", "#N/A", "#VALUE!", "#DIV/0!", "#NAME?", "#NULL!", "#NUM!", "#GETTING_DATA"}
)


def is_spreadsheet_error(value) -> bool:
    """True if ``value`` is a spreadsheet error literal (e.g. ``#REF!``)."""
    if value is None:
        return False
    return str(value).strip().upper() in SPREADSHEET_ERROR_VALUES


# Characters that are visually/typographically confusable and have caused
# duplicate sd_codes in real data (e.g. "A0Y006" vs "AOY006", "MIT-186" vs
# "MIT186"). Map each to a single canonical form for *comparison only* — the
# stored sd_code is never altered.
_SD_CONFUSABLES = str.maketrans({"O": "0", "I": "1"})


def normalize_sd_code(value) -> str:
    """Comparison key for detecting near-duplicate sd_codes.

    Upper-cases, drops separators/punctuation and whitespace, then folds the
    confusable characters above. Two sd_codes with the same normalized key are
    "similar" (likely the same part entered two ways) even if their raw text
    differs. Used only to warn/skip on import — never written back.

    Examples (all collapse together): ``BTS-141`` / ``BTS141`` -> ``BTS141``;
    ``A0Y006`` / ``AOY006`` -> ``A0Y006``.
    """
    if not value:
        return ""
    s = "".join(ch for ch in str(value).upper() if ch.isalnum())
    return s.translate(_SD_CONFUSABLES)


def next_global_item_number() -> int:
    """Compute the next number to use across ALL prefixes.

    Each Item_list owns one stable number; only the prefix changes when stage
    is reclassified. So we look at every existing item_code, take the highest
    numeric portion, and add 1.
    """
    codes = (
        Item_list.objects
        .exclude(item_code__isnull=True)
        .exclude(item_code="")
        .values_list("item_code", flat=True)
    )
    max_num = 0
    for code in codes:
        num = extract_item_number(code)
        if num is not None and num > max_num:
            max_num = num
    return max_num + 1


class Item_list(BaseModel):
    sd_code = models.CharField(max_length=32, blank=True, default="", db_index=True)
    part_number = models.CharField(max_length=255, db_index=True)
    part_name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100)
    weight = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="kg")

    item_code = models.CharField(max_length=16, unique=True, blank=True, null=True)

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

    stage = models.ForeignKey(
        ItemStage,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="items",
    )

    portion = models.ForeignKey(
        Portion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )

    side = models.ForeignKey(
        Side,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )

    inout = models.ForeignKey(
        InOut,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )

    way = models.ForeignKey(
        Way,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )

    purchased_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
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

    def save(self, *args, **kwargs):
        if not self.item_code and self.stage_id:
            prefix = (self.stage.code_prefix or "").strip()
            if prefix:
                with transaction.atomic():
                    self.item_code = format_item_code(prefix, next_global_item_number())
                    super().save(*args, **kwargs)
                    return
        super().save(*args, **kwargs)
