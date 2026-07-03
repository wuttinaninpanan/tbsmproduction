"""Delete self-referencing BOM lines (a part listed as its own component).

The 2026-07-01 BOM rebuild (import_bom_master.py) imported ~359 rows from
BoM_Master.xlsx where Parent Parts No. == Child Parts No.. Each became a
BillOfMaterialItemMater whose ``component`` is the same Item_list as its BOM's
own ``item`` — so the item edit page shows the assembly listed inside its own
BOM (e.g. W001657 / 72533-X7V10-00 appears twice under itself).

A part can never be a component of itself, so these lines are always wrong.
This command finds every BillOfMaterialItemMater where component_id == the
owning BOM's item_id and deletes it. Nothing else is touched.

Defaults to a DRY RUN. Pass --commit to actually delete (inside one transaction).
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F

from core.models.bill_of_material_item_master import BillOfMaterialItemMater


class Command(BaseCommand):
    help = "Delete BOM lines whose component is the assembly itself (parent == child)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Apply the deletion. Without it the command only reports (dry run).",
        )
        parser.add_argument(
            "--show",
            type=int,
            default=30,
            help="How many offending rows to print (default 30).",
        )

    def handle(self, *args, **opts):
        commit = opts["commit"]
        show = opts["show"]

        # component_id == bom.item_id  -> the line points a part at itself.
        qs = (
            BillOfMaterialItemMater.objects
            .filter(component_id=F("bom__item_id"))
            .select_related("component", "bom", "bom__item")
            .order_by("bom__item__item_code", "sequence")
        )

        rows = list(qs)
        self.stdout.write(self.style.MIGRATE_HEADING("=== SELF-REFERENCING BOM LINES ==="))
        self.stdout.write(f"found: {len(rows)}")

        distinct_items = {r.bom.item_id for r in rows}
        self.stdout.write(f"distinct assemblies affected: {len(distinct_items)}")

        for r in rows[:show]:
            item = r.bom.item
            self.stdout.write(
                f"    seq {r.sequence}: {getattr(item, 'item_code', '') or '-'} "
                f"{item.sd_code} {item.part_number} — {item.part_name}"
            )
        if len(rows) > show:
            self.stdout.write(f"    ... and {len(rows) - show} more")

        if not commit:
            self.stdout.write(self.style.WARNING(
                "\nDRY RUN — no changes. Re-run with --commit to delete."))
            return

        if not rows:
            self.stdout.write(self.style.SUCCESS("\nNothing to delete."))
            return

        ids = [r.id for r in rows]
        with transaction.atomic():
            deleted, _ = BillOfMaterialItemMater.objects.filter(id__in=ids).delete()
        self.stdout.write(self.style.SUCCESS(f"\nDONE (committed) — deleted {deleted} rows."))
