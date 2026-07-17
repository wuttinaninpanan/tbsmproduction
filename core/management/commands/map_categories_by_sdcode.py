"""Assign Item_list.category from the SECOND character of sd_code.

Rule (owner-defined):
    sd_code[1]   F -> Side frame
                 T -> Seat track
                 A -> Lower arm
                 H -> Hinge

Only these four letters are mapped; any other 2nd character is left completely
untouched (its current category is preserved). The 2nd char is uppercased before
matching, so 'f' and 'F' both count. Rows are skipped when:
  * sd_code is shorter than 2 characters, or
  * sd_code is a spreadsheet-error literal (#REF! etc.).

The four target categories must already exist (they do); this command never
creates or deletes categories, and never touches any field other than category.

Defaults to a DRY RUN. Pass --commit to apply (one transaction, bulk_update).
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models.item_category import ItemCategory
from core.models.item_list import Item_list, is_spreadsheet_error

# 2nd character of sd_code -> ItemCategory.name
LETTER_TO_CATEGORY = {
    "F": "Side frame",
    "T": "Seat track",
    "A": "Lower arm",
    "H": "Hinge",
}


class Command(BaseCommand):
    help = "Assign Item_list.category from the 2nd character of sd_code (F/T/A/H)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Apply changes. Without it the command only reports (dry run).",
        )
        parser.add_argument(
            "--show",
            type=int,
            default=20,
            help="How many rows of each detail list to print (default 20).",
        )

    def handle(self, *args, **opts):
        commit = opts["commit"]
        show = opts["show"]

        # Resolve the four target categories up front (must all exist).
        cats = {}
        missing = []
        for letter, name in LETTER_TO_CATEGORY.items():
            c = ItemCategory.objects.filter(name=name).first()
            if c is None:
                missing.append(name)
            else:
                cats[letter] = c
        if missing:
            raise CommandError(
                "These categories do not exist (create them first): "
                + ", ".join(sorted(set(missing)))
            )

        # Names of ALL categories, so we can print readable "old -> new".
        cat_name = dict(ItemCategory.objects.values_list("id", "name"))

        rows = list(
            Item_list.objects.all().values_list("id", "sd_code", "category_id")
        )

        to_update = []       # (id, sd, letter, old_cat_id, new_cat)
        unchanged = 0        # 2nd char is a target and category already correct
        skipped_short = 0    # sd_code shorter than 2 chars (incl. blank)
        skipped_error = 0    # sd_code is a spreadsheet-error literal
        untouched_other = 0  # 2nd char not one of F/T/A/H -> left as-is
        per_letter = {L: 0 for L in LETTER_TO_CATEGORY}   # matched rows per letter
        overwrites = []      # (id, sd, old_name, new_name) where a *different* category is replaced

        for pk, sd, cat_id in rows:
            sd = (sd or "").strip()
            if len(sd) < 2:
                skipped_short += 1
                continue
            if is_spreadsheet_error(sd):
                skipped_error += 1
                continue
            letter = sd[1].upper()
            cat = cats.get(letter)
            if cat is None:
                untouched_other += 1
                continue
            per_letter[letter] += 1
            if cat_id == cat.id:
                unchanged += 1
                continue
            to_update.append((pk, sd, letter, cat_id, cat))
            if cat_id is not None:
                overwrites.append((pk, sd, cat_name.get(cat_id, "?"), cat.name))

        # ---- report -----------------------------------------------------
        h = self.style.MIGRATE_HEADING
        self.stdout.write(h("=== RULE (sd_code 2nd char -> category) ==="))
        for letter, name in LETTER_TO_CATEGORY.items():
            self.stdout.write(f"    {letter} -> {name:12} matched rows: {per_letter[letter]}")

        self.stdout.write(h("\n=== SUMMARY ==="))
        self.stdout.write(
            f"Item_list rows total              : {len(rows)}\n"
            f"category WILL CHANGE              : {len(to_update)}\n"
            f"   of which overwrite existing    : {len(overwrites)}\n"
            f"already correct (no change)       : {unchanged}\n"
            f"untouched (2nd char not F/T/A/H)  : {untouched_other}\n"
            f"skipped (sd_code < 2 chars)       : {skipped_short}\n"
            f"skipped (spreadsheet error)       : {skipped_error}"
        )

        if to_update:
            self.stdout.write(h(f"\n--- changes (first {show}) ---"))
            for pk, sd, letter, old_id, cat in to_update[:show]:
                old = cat_name.get(old_id, "(none)") if old_id else "(none)"
                self.stdout.write(f"    {sd:12} [{letter}] {old!r} -> {cat.name!r}")
            if len(to_update) > show:
                self.stdout.write(f"    ... and {len(to_update) - show} more")

        if overwrites:
            self.stdout.write(
                self.style.WARNING(
                    f"\n--- {len(overwrites)} rows already had a DIFFERENT category "
                    f"(will be replaced; first {show}) ---"
                )
            )
            for pk, sd, old_name, new_name in overwrites[:show]:
                self.stdout.write(f"    {sd:12} {old_name!r} -> {new_name!r}")
            if len(overwrites) > show:
                self.stdout.write(f"    ... and {len(overwrites) - show} more")

        if not commit:
            self.stdout.write(
                self.style.WARNING(
                    "\nDRY RUN — no changes. Re-run with --commit to apply."
                )
            )
            return

        if not to_update:
            self.stdout.write(
                self.style.SUCCESS("\nNothing to update — categories already match.")
            )
            return

        with transaction.atomic():
            objs = [Item_list(id=pk, category=cat) for pk, _sd, _l, _old, cat in to_update]
            Item_list.objects.bulk_update(objs, ["category"], batch_size=1000)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDONE (committed) — set category on {len(to_update)} items."
            )
        )
