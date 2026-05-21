"""Merge duplicate Item_list rows that share the same (sd_code, part_number).

Background: a two-pass import produced two Item_list rows per part — one
created during the BOM import (owns a BOM, no ItemLine) and one created
during the line/master import (linked to ItemLine, usually no BOM). Record
view picks the line-linked row, so its empty BOM hides the real BOM data.

This command merges each duplicate group: it keeps the OLDER row (the one
that owns the BOM) and moves every FK that points at the newer row over to
the older one, then deletes the newer row.

Run with --dry-run first to inspect; re-run without it to commit.
"""
from __future__ import annotations

from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from core.models.bill_of_material import BillOfMaterial
from core.models.bill_of_material_item_master import BillOfMaterialItemMater
from core.models.defect_stat import DefectStat
from core.models.item_line import ItemLine
from core.models.item_list import Item_list
from core.models.item_price import ItemPrice
from core.models.rounting import Routing
from core.models.scrap_record import ScrapRecord

try:
    from core.models.inspection.inspection_error import InspectionError
except Exception:
    InspectionError = None
try:
    from core.models.inspection.inspection_result import InspectionResult
except Exception:
    InspectionResult = None


class Command(BaseCommand):
    help = "Merge duplicate Item_list rows (same sd_code + part_number)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show planned changes without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be saved"))

        dup_groups = (
            Item_list.objects.values("sd_code", "part_number")
            .annotate(c=Count("id"))
            .filter(c__gt=1)
            .order_by("sd_code")
        )
        total_groups = dup_groups.count()
        self.stdout.write(f"Found {total_groups} duplicate (sd_code, part_number) groups")

        summary = defaultdict(int)
        try:
            with transaction.atomic():
                for d in dup_groups:
                    self._merge_group(
                        sd_code=d["sd_code"],
                        part_number=d["part_number"],
                        summary=summary,
                        dry_run=dry_run,
                    )
                if dry_run:
                    raise _DryRunRollback()
        except _DryRunRollback:
            pass

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== Summary ==="))
        for k, v in sorted(summary.items()):
            self.stdout.write(f"  {k}: {v}")

    def _merge_group(self, *, sd_code, part_number, summary, dry_run):
        rows = list(
            Item_list.objects.filter(
                sd_code=sd_code, part_number=part_number
            ).order_by("created_at")
        )
        if len(rows) < 2:
            return

        keeper = rows[0]  # oldest — typically owns the BOM
        losers = rows[1:]

        self.stdout.write("")
        self.stdout.write(
            f"-- sd={sd_code!r} pn={part_number!r}: keep {keeper.id} "
            f"({keeper.created_at:%Y-%m-%d}), merge {len(losers)} other(s)"
        )

        for loser in losers:
            self._merge_one(keeper=keeper, loser=loser, summary=summary, dry_run=dry_run)

        summary["groups_processed"] += 1

    def _merge_one(self, *, keeper, loser, summary, dry_run):
        # 1) BOM header: OneToOne — if both keeper & loser have a BOM, delete
        #    the loser's BOM (after verifying its children are a subset).
        loser_bom = BillOfMaterial.objects.filter(item=loser).first()
        keeper_bom = BillOfMaterial.objects.filter(item=keeper).first()
        if loser_bom is not None:
            if keeper_bom is None:
                # Reassign loser's BOM to keeper.
                self.stdout.write(
                    f"   move BOM {loser_bom.id} → keeper {keeper.id}"
                )
                if not dry_run:
                    loser_bom.item = keeper
                    loser_bom.save(update_fields=["item", "updated_at"])
                summary["bom_reassigned"] += 1
            else:
                # Both have BOMs — verify children match, then drop loser's.
                keeper_children = set(
                    BillOfMaterialItemMater.objects.filter(bom=keeper_bom).values_list(
                        "component_id", flat=True
                    )
                )
                loser_children = set(
                    BillOfMaterialItemMater.objects.filter(bom=loser_bom).values_list(
                        "component_id", flat=True
                    )
                )
                if loser_children <= keeper_children:
                    n = BillOfMaterialItemMater.objects.filter(bom=loser_bom).count()
                    self.stdout.write(
                        f"   delete duplicate BOM {loser_bom.id} "
                        f"({n} children, all already in keeper BOM)"
                    )
                    if not dry_run:
                        loser_bom.delete()  # CASCADE deletes its items_master
                    summary["bom_deleted_duplicate"] += 1
                else:
                    # Loser has unique children → import them into keeper BOM.
                    missing = loser_children - keeper_children
                    self.stdout.write(
                        f"   migrate {len(missing)} unique child(ren) "
                        f"from BOM {loser_bom.id} → keeper BOM {keeper_bom.id}, "
                        f"then delete loser BOM"
                    )
                    if not dry_run:
                        next_seq = (
                            (BillOfMaterialItemMater.objects.filter(bom=keeper_bom)
                             .order_by("-sequence")
                             .values_list("sequence", flat=True)
                             .first()) or 0
                        )
                        for child in BillOfMaterialItemMater.objects.filter(
                            bom=loser_bom, component_id__in=list(missing)
                        ):
                            next_seq += 1
                            BillOfMaterialItemMater.objects.create(
                                bom=keeper_bom,
                                component=child.component,
                                quantity=child.quantity,
                                unit=child.unit,
                                sequence=next_seq,
                                user=child.user,
                            )
                        loser_bom.delete()
                    summary["bom_merged_children"] += 1

        # 2) BillOfMaterialItemMater.component (other BOMs using loser as child)
        cnt = BillOfMaterialItemMater.objects.filter(component=loser).count()
        if cnt:
            self.stdout.write(f"   reassign {cnt} BOM child link(s) → keeper")
            if not dry_run:
                BillOfMaterialItemMater.objects.filter(component=loser).update(
                    component=keeper
                )
            summary["bom_child_links_reassigned"] += cnt

        # 3) ItemLine — beware unique_together(item, line). Skip if keeper
        #    already on the same line; otherwise move.
        keeper_lines = set(
            ItemLine.objects.filter(item=keeper).values_list("line_id", flat=True)
        )
        for il in ItemLine.objects.filter(item=loser):
            if il.line_id in keeper_lines:
                self.stdout.write(
                    f"   delete duplicate ItemLine line_id={il.line_id} "
                    f"(keeper already on this line)"
                )
                if not dry_run:
                    il.delete()
                summary["itemline_duplicate_deleted"] += 1
            else:
                self.stdout.write(
                    f"   move ItemLine line_id={il.line_id} → keeper"
                )
                if not dry_run:
                    il.item = keeper
                    il.save(update_fields=["item", "updated_at"])
                summary["itemline_moved"] += 1
                keeper_lines.add(il.line_id)

        # 4) Other FK references
        cnt = ItemPrice.objects.filter(item=loser).count()
        if cnt:
            self.stdout.write(f"   move {cnt} ItemPrice row(s) → keeper")
            if not dry_run:
                ItemPrice.objects.filter(item=loser).update(item=keeper)
            summary["item_price_moved"] += cnt

        cnt = ScrapRecord.objects.filter(part_number=loser).count()
        if cnt:
            self.stdout.write(f"   move {cnt} ScrapRecord.part_number → keeper")
            if not dry_run:
                ScrapRecord.objects.filter(part_number=loser).update(part_number=keeper)
            summary["scrap_part_moved"] += cnt

        cnt = ScrapRecord.objects.filter(component_part=loser).count()
        if cnt:
            self.stdout.write(f"   move {cnt} ScrapRecord.component_part → keeper")
            if not dry_run:
                ScrapRecord.objects.filter(component_part=loser).update(
                    component_part=keeper
                )
            summary["scrap_component_moved"] += cnt

        cnt = DefectStat.objects.filter(part=loser).count()
        if cnt:
            self.stdout.write(f"   move {cnt} DefectStat row(s) → keeper")
            if not dry_run:
                DefectStat.objects.filter(part=loser).update(part=keeper)
            summary["defect_stat_moved"] += cnt

        cnt = Routing.objects.filter(product=loser).count()
        if cnt:
            self.stdout.write(f"   move {cnt} Routing row(s) → keeper")
            if not dry_run:
                Routing.objects.filter(product=loser).update(product=keeper)
            summary["routing_moved"] += cnt

        if InspectionError is not None:
            cnt = InspectionError.objects.filter(inspectionitem=loser).count()
            if cnt:
                self.stdout.write(
                    f"   move {cnt} InspectionError row(s) → keeper"
                )
                if not dry_run:
                    InspectionError.objects.filter(inspectionitem=loser).update(
                        inspectionitem=keeper
                    )
                summary["inspection_error_moved"] += cnt

        if InspectionResult is not None:
            cnt = InspectionResult.objects.filter(inspectionitem=loser).count()
            if cnt:
                self.stdout.write(
                    f"   move {cnt} InspectionResult row(s) → keeper"
                )
                if not dry_run:
                    InspectionResult.objects.filter(inspectionitem=loser).update(
                        inspectionitem=keeper
                    )
                summary["inspection_result_moved"] += cnt

        # 5) Finally delete loser
        self.stdout.write(f"   delete loser Item_list {loser.id}")
        if not dry_run:
            loser.delete()
        summary["item_list_deleted"] += 1


class _DryRunRollback(Exception):
    pass
