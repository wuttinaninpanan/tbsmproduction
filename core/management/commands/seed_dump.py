"""Snapshot the current database into ``core/management/seeds/master_seed.json``.

The snapshot covers every "data" table needed to recreate a running app
from scratch — users, lookups, items, BoM. Operational/log tables
(AuditLogEntry, DefectStat) and Django internals (ContentType, Permission,
Sessions) are deliberately excluded.

The fixture is a Django JSON fixture, so it can be replayed with
``manage.py loaddata`` directly, but ``manage.py seed_load`` wraps that
with a "delete-then-load" step.

Usage:
    python manage.py seed_dump                       # default output path
    python manage.py seed_dump --output other.json   # custom path
"""
from __future__ import annotations

from pathlib import Path

from django.core import management
from django.core.management.base import BaseCommand


DEFAULT_OUTPUT = Path("core/management/seeds/master_seed.json")


# Order matches the LOAD order: dependencies first, dependents last.
# Django's `loaddata` does NOT enforce ordering between unrelated models,
# but the natural order here makes diffs in the JSON readable.
SEED_MODELS = [
    # Auth & profile
    "auth.Group",
    "core.User",
    "core.UserProfile",

    # Lookup tables (no FK except `user`)
    "core.ItemStage",
    "core.ItemCategory",
    "core.Way",
    "core.Portion",
    "core.Side",
    "core.InOut",
    "core.Plant",
    "core.Process",
    "core.LineProcess",
    "core.Line",
    "core.DefectMode",
    "core.Department",

    # Business partner family
    "core.Role",
    "core.Term",
    "core.BusinessPartner",
    "core.PartnerRole",
    "core.Contact",
    "core.Address",

    # Items & their cross-tables
    "core.Item_list",
    "core.DefectByCategory",
    "core.ItemLine",
    "core.ItemPrice",
    "core.BillOfMaterial",
    "core.BillOfMaterialItemMater",
    "core.Routing",

    # Inspection family
    "core.InspectionModels",
    "core.InspectionItem",
    "core.InspectionModelsDefect",
    "core.InspectionResult",
    "core.InspectionError",
    "core.InspectionProducts",

    # Inspection machine
    "core.Machine",
    "core.MachineLine",

    # Scrap (operational, but include for end-to-end seed)
    "core.ScrapRecord",
]


class Command(BaseCommand):
    help = (
        "Dump the curated set of core/auth tables to a Django JSON fixture "
        "for replay via `seed_load`."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output", default=str(DEFAULT_OUTPUT),
            help=f"Output path (default: {DEFAULT_OUTPUT}).",
        )
        parser.add_argument(
            "--indent", type=int, default=2,
            help="JSON indent level (default: 2). Use 0 for compact.",
        )

    def handle(self, *args, **options):
        output = Path(options["output"])
        output.parent.mkdir(parents=True, exist_ok=True)

        self.stdout.write(f"Dumping {len(SEED_MODELS)} model(s) -> {output}")
        for m in SEED_MODELS:
            self.stdout.write(f"  - {m}")

        management.call_command(
            "dumpdata",
            *SEED_MODELS,
            indent=options["indent"],
            output=str(output),
            use_natural_foreign_keys=False,
            use_natural_primary_keys=False,
        )

        size_kb = output.stat().st_size / 1024
        self.stdout.write(self.style.SUCCESS(
            f"Wrote {output} ({size_kb:.1f} KB)"
        ))
