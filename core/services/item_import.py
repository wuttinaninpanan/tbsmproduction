"""Shared rules for importing/updating ``Item_list`` from the Export/Import
spreadsheet (used by both the Item-list bulk import and the BoM Master import,
which share one column format).

Policy — keyed on ``sd_code``, fill-only / non-destructive:

1. New sd_code -> insert, but first flag near-duplicates (same normalized key,
   e.g. hyphen difference or O/0 swap) so they aren't silently created.
2. Blank sd_code -> never insert or update.
3-6. For an existing sd_code, only FILL fields that are empty in the system and
   have a value in the spreadsheet. A non-empty system value is never
   overwritten (so a blank cell can't wipe data, and a changed value is ignored
   here — real value changes need a separate versioning flow).
"""
from __future__ import annotations

from core.models.item_list import normalize_sd_code

# Item_list fields an import may FILL. Excludes the sd_code key itself, the
# auto-managed item_code, and stage (owned by the BoM reclassify step).
DECIMAL_FIELDS = ("weight", "cost", "purchased_price")
FK_FIELDS = ("category", "stage", "portion", "side", "inout", "way")
# Everything else passed in is treated as a text field.


def _text_empty(value) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def fill_only_update(item, incoming: dict) -> list[str]:
    """Apply the fill-only merge (rules 4/5/6) to an existing ``Item_list``.

    ``incoming`` maps a field name to its parsed spreadsheet value: ``str`` for
    text, ``Decimal`` for numbers, a model instance for FKs, or ``None`` (or
    ``""``) when the cell was blank. Only empty fields are filled; existing
    non-empty values are left untouched. Returns the changed field names (the
    caller is responsible for ``item.save(update_fields=...)``).
    """
    changed: list[str] = []
    for field, new_value in incoming.items():
        if field in FK_FIELDS:
            if new_value is None:
                continue  # rule 5/2: blank in Excel -> skip
            if getattr(item, f"{field}_id") is None:  # rule 4: system empty -> fill
                setattr(item, field, new_value)
                changed.append(field)
            # rule 6: system already set -> skip
        elif field in DECIMAL_FIELDS:
            if new_value is None:
                continue
            if not getattr(item, field):  # 0 / None counts as unset -> fill
                setattr(item, field, new_value)
                changed.append(field)
        else:  # text field
            if _text_empty(new_value):
                continue
            if _text_empty(getattr(item, field)):
                setattr(item, field, new_value)
                changed.append(field)
    return changed


class SimilarSdIndex:
    """Tracks normalized sd_codes to flag near-duplicates during an import.

    Seed it with the sd_codes already in the database; as the importer inserts
    new rows it should ``add()`` them so two similar NEW rows in the same file
    are caught too.
    """

    def __init__(self):
        self._by_norm: dict[str, str] = {}  # normalized key -> first raw sd_code seen

    def seed(self, sd_codes) -> None:
        for sd in sd_codes:
            self.add(sd)

    def add(self, sd_code: str) -> None:
        norm = normalize_sd_code(sd_code)
        if norm and norm not in self._by_norm:
            self._by_norm[norm] = sd_code

    def has_exact(self, sd_code: str) -> bool:
        return normalize_sd_code(sd_code) in self._by_norm

    def similar_to(self, sd_code: str) -> str | None:
        """Return an existing sd_code that is *similar but not identical* to
        ``sd_code`` (same normalized key, different raw text), else ``None``."""
        norm = normalize_sd_code(sd_code)
        existing = self._by_norm.get(norm)
        if existing is not None and existing.strip().upper() != (sd_code or "").strip().upper():
            return existing
        return None
