"""Clean up Item_list rows whose sd_code is the legacy "{SD}-{part_number}" composite.

Background: an earlier version of seed_data wrote COL_SDPN (column N, the
composite "SD-PartNumber" join key) into Item_list.sd_code instead of COL_SD
(column P, the bare SD code). This created duplicate items — one with the
correct sd_code (e.g. "DAR-56") and another with the composite form
(e.g. "DAR-56-72503-X7V73"). Both reference the same physical part.

This command merges every composite row into the canonical SD-only row of the
same part_number, transferring BOM headers/components and ItemLine rows, then
deletes the composite. If no canonical row exists, it just rewrites sd_code
in place.

Usage:
    python manage.py dedupe_combined_items                # apply
    python manage.py dedupe_combined_items --dry-run      # report only
"""
from __future__ import annotations

import re
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F

from core.models.bill_of_material import BillOfMaterial
from core.models.bill_of_material_item_master import BillOfMaterialItemMater
from core.models.item_line import ItemLine
from core.models.item_list import Item_list


# Matches "{SD-prefix}-{rest}" where rest is the part_number.
COMPOSITE_RE = re.compile(r"^([A-Za-z]+-\d+)-(.+)$")


class Command(BaseCommand):
    help = "Merge composite-sd_code Item_list rows into canonical SD-only rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Print what would happen without modifying the database.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))

        composite_rows = self._find_composites()
        self.stdout.write(f"Found {len(composite_rows)} composite-sd_code rows.")

        merged = renamed = skipped = 0
        bom_headers_dropped = 0
        bom_items_moved = 0
        bom_items_dropped_dup = 0
        item_lines_moved = 0
        item_lines_dropped_dup = 0

        with transaction.atomic():
            for combined, sd_prefix in composite_rows:
                canonical = (
                    Item_list.objects
                    .filter(sd_code=sd_prefix, part_number__iexact=combined.part_number)
                    .exclude(pk=combined.pk)
                    .first()
                )

                if canonical is None:
                    if dry_run:
                        self.stdout.write(
                            f"  [rename] {combined.sd_code} -> {sd_prefix} "
                            f"(no canonical row exists)"
                        )
                    else:
                        combined.sd_code = sd_prefix
                        combined.save(update_fields=["sd_code", "updated_at"])
                    renamed += 1
                    continue

                # ---- Merge combined into canonical ----
                stats = self._merge(combined, canonical, dry_run=dry_run)
                bom_headers_dropped += stats["bom_headers_dropped"]
                bom_items_moved += stats["bom_items_moved"]
                bom_items_dropped_dup += stats["bom_items_dropped_dup"]
                item_lines_moved += stats["item_lines_moved"]
                item_lines_dropped_dup += stats["item_lines_dropped_dup"]
                merged += 1

                if dry_run:
                    self.stdout.write(
                        f"  [merge]  {combined.sd_code} -> {canonical.sd_code} "
                        f"(bom_items moved={stats['bom_items_moved']}, "
                        f"dup={stats['bom_items_dropped_dup']}, "
                        f"item_lines moved={stats['item_lines_moved']}, "
                        f"dup={stats['item_lines_dropped_dup']})"
                    )

            if dry_run:
                self.stdout.write(self.style.WARNING("Dry run — rolling back."))
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f"Done. merged={merged} renamed={renamed} skipped={skipped} "
            f"bom_headers_dropped={bom_headers_dropped} "
            f"bom_items_moved={bom_items_moved} "
            f"bom_items_dropped_dup={bom_items_dropped_dup} "
            f"item_lines_moved={item_lines_moved} "
            f"item_lines_dropped_dup={item_lines_dropped_dup}"
        ))

    # ------------------------------------------------------------------

    def _find_composites(self) -> list[tuple[Item_list, str]]:
        """Return [(item, sd_prefix), ...] for every row whose sd_code is the
        composite "{prefix}-{part_number}" form."""
        out: list[tuple[Item_list, str]] = []
        qs = Item_list.objects.exclude(sd_code="").exclude(part_number="")
        for item in qs.iterator():
            m = COMPOSITE_RE.match(item.sd_code or "")
            if not m:
                continue
            prefix, suffix = m.group(1), m.group(2)
            if (item.part_number or "").strip().upper() == suffix.strip().upper():
                out.append((item, prefix))
        return out

    def _merge(self, combined: Item_list, canonical: Item_list, *, dry_run: bool) -> dict:
        """Move FK references from `combined` to `canonical`, then delete combined."""
        stats = defaultdict(int)

        # --- BOM headers (OneToOne on item) ---
        combined_bom = BillOfMaterial.objects.filter(item=combined).first()
        canonical_bom = BillOfMaterial.objects.filter(item=canonical).first()
        if combined_bom is not None:
            if canonical_bom is None:
                # Re-point the BOM to canonical.
                if not dry_run:
                    combined_bom.item = canonical
                    combined_bom.save(update_fields=["item", "updated_at"])
            else:
                # Both have headers. Move components from combined_bom to
                # canonical_bom (skipping duplicates), then delete combined_bom.
                existing_components = set(
                    BillOfMaterialItemMater.objects
                    .filter(bom=canonical_bom)
                    .values_list("component_id", flat=True)
                )
                next_seq = (
                    BillOfMaterialItemMater.objects.filter(bom=canonical_bom)
                    .order_by("-sequence").values_list("sequence", flat=True).first()
                ) or 0
                for child in BillOfMaterialItemMater.objects.filter(bom=combined_bom):
                    if child.component_id in existing_components:
                        stats["bom_items_dropped_dup"] += 1
                        if not dry_run:
                            child.delete()
                    else:
                        next_seq += 1
                        if not dry_run:
                            child.bom = canonical_bom
                            child.sequence = next_seq
                            child.save(update_fields=["bom", "sequence", "updated_at"])
                        existing_components.add(child.component_id)
                        stats["bom_items_moved"] += 1
                if not dry_run:
                    combined_bom.delete()
                stats["bom_headers_dropped"] += 1

        # --- BOM components (combined used as a component elsewhere) ---
        for parent_link in BillOfMaterialItemMater.objects.filter(component=combined):
            dup = (
                BillOfMaterialItemMater.objects
                .filter(bom=parent_link.bom, component=canonical)
                .exclude(pk=parent_link.pk)
                .first()
            )
            if dup is not None:
                stats["bom_items_dropped_dup"] += 1
                if not dry_run:
                    parent_link.delete()
            else:
                if not dry_run:
                    parent_link.component = canonical
                    parent_link.save(update_fields=["component", "updated_at"])
                stats["bom_items_moved"] += 1

        # --- ItemLine (unique_together item, line) ---
        for il in ItemLine.objects.filter(item=combined):
            dup = ItemLine.objects.filter(item=canonical, line_id=il.line_id).first()
            if dup is not None:
                stats["item_lines_dropped_dup"] += 1
                if not dry_run:
                    il.delete()
            else:
                if not dry_run:
                    il.item = canonical
                    il.save(update_fields=["item", "updated_at"])
                stats["item_lines_moved"] += 1

        # Other FKs (item_price, routing, scrap_record) are 0 for these rows
        # per the audit; if any appear in the future, add transfer logic here.

        if not dry_run:
            combined.delete()

        return stats
