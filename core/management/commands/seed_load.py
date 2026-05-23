"""Replace the contents of the seed-managed tables with
``core/management/seeds/master_seed.json``.

What it does, in order, inside a single transaction:

1. Confirms the destructive action (unless ``--no-input``).
2. Deletes every row from the seed-managed tables in dependency-reverse
   order (children first) so PROTECT FKs don't fire.
3. Calls ``loaddata`` to restore the snapshot.
4. Reports before/after row counts per table.

Tables NOT touched: ``core.AuditLogEntry``, ``core.DefectStat``, Django's
``auth.Permission`` / ``contenttypes.*`` / ``sessions.*`` / ``admin.*``.

Server deployment:
    python manage.py migrate         # apply schema first
    python manage.py seed_load --no-input
"""
from __future__ import annotations

from pathlib import Path

from django.apps import apps
from django.core import management
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


DEFAULT_INPUT = Path("core/management/seeds/master_seed.json")


# Deletion order — children first. Reverse of the load order in seed_dump.SEED_MODELS.
# Each entry must be valid `apps.get_model(...)` syntax: `app_label.ModelName`
# (case-sensitive, exact class name).
DELETE_ORDER = [
    # Scrap & inspection
    "core.ScrapRecord",
    "core.MachineLine",
    "core.Machine",
    "core.InspectionResult",
    "core.InspectionError",
    "core.InspectionProducts",
    "core.InspectionModelsDefect",
    "core.InspectionItem",
    "core.InspectionModels",

    # Items' cross-tables
    "core.Routing",
    "core.BillOfMaterialItemMater",
    "core.BillOfMaterial",
    "core.ItemPrice",
    "core.ItemLine",
    "core.DefectByCategory",
    "core.Item_list",

    # Business partner family
    "core.Address",
    "core.Contact",
    "core.PartnerRole",
    "core.BusinessPartner",
    "core.Term",
    "core.Role",

    # Lookups
    "core.DefectMode",
    "core.Department",
    "core.Line",
    "core.LineProcess",
    "core.Process",
    "core.Plant",
    "core.InOut",
    "core.Side",
    "core.Portion",
    "core.Way",
    "core.ItemCategory",
    "core.ItemStage",

    # Auth / profile
    "core.UserProfile",
    "core.User",
    "auth.Group",
]


class Command(BaseCommand):
    help = (
        "Wipe seed-managed tables and reload them from the JSON fixture. "
        "This is destructive — intended for server deploys, not for "
        "incremental dev work."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--input", default=str(DEFAULT_INPUT),
            help=f"Fixture path (default: {DEFAULT_INPUT}).",
        )
        parser.add_argument(
            "--no-input", action="store_true",
            help="Skip the interactive confirmation prompt.",
        )

    def handle(self, *args, **options):
        path = Path(options["input"])
        if not path.exists():
            raise CommandError(f"Fixture not found: {path}")

        # ---- Before counts ------------------------------------------------
        before: dict[str, int] = {}
        for label in DELETE_ORDER:
            model = apps.get_model(label)
            before[label] = model.objects.count()

        total_before = sum(before.values())
        self.stdout.write(
            f"About to delete {total_before} row(s) across {len(DELETE_ORDER)} "
            f"table(s) and replay {path} ({path.stat().st_size / 1024:.1f} KB)."
        )

        if not options["no_input"]:
            answer = input("Type 'yes' to continue: ").strip().lower()
            if answer != "yes":
                self.stdout.write(self.style.WARNING("Aborted."))
                return

        # ---- Wipe + load --------------------------------------------------
        with transaction.atomic():
            # Delete in defined order; PROTECT FKs are safe because we walk
            # children -> parents.
            for label in DELETE_ORDER:
                model = apps.get_model(label)
                n, _ = model.objects.all().delete()
                if n:
                    self.stdout.write(f"  deleted {n:6d} from {label}")

            self.stdout.write(f"Loading {path} ...")
            management.call_command("loaddata", str(path))

        # ---- After counts -------------------------------------------------
        self.stdout.write(self.style.SUCCESS("Done. Per-table row counts:"))
        self.stdout.write(
            f"  {'table':40s} {'before':>10s} -> {'after':>10s}"
        )
        for label in DELETE_ORDER:
            model = apps.get_model(label)
            after = model.objects.count()
            self.stdout.write(
                f"  {label:40s} {before[label]:>10d} -> {after:>10d}"
            )
