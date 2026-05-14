"""Import item-line mapping + sync Item_list (part_number/part_name) from itemline.xlsx.

Sheet `main-part` columns:
    SD_code | part number | part name | Line

Phases:
  1. UPSERT Item_list using the FIRST row seen per sd_code.
     - Existing rows: update part_number, and part_name when xlsx value is non-empty.
     - Missing rows : create with stage = --default-stage (default: semi_fg).
  2. UPSERT Line: create any line_name from the xlsx that does not exist.
  3. REBUILD ItemLine: delete all existing rows, then create from the xlsx pairs.
     - item_stage is inherited from Item_list.stage.

Defaults to dry-run; pass --commit to write to the database.

Usage:
    python manage.py import_itemline_xlsx                            # dry-run
    python manage.py import_itemline_xlsx --commit                   # apply
    python manage.py import_itemline_xlsx --file path/to/other.xlsx
    python manage.py import_itemline_xlsx --default-stage wip --commit
"""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import openpyxl  # type: ignore
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models.item_line import ItemLine
from core.models.item_list import Item_list
from core.models.item_stage import ItemStage
from core.models.line import Line
from core.models.line_process import LineProcess


DEFAULT_PATH = Path("core/management/itemline.xlsx")
DEFAULT_STAGE = "semi_fg"
DEFAULT_LINE_PROCESS = "assy"


def _s(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


class Command(BaseCommand):
    help = "Import ItemLine + upsert Item_list/Line from itemline.xlsx (default dry-run)."

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(DEFAULT_PATH),
                            help=f"Path to xlsx (default: {DEFAULT_PATH}).")
        parser.add_argument("--commit", action="store_true",
                            help="Persist changes. Without this flag the command is a dry-run.")
        parser.add_argument("--user",
                            help="Username to set as user FK (default: first superuser, then first staff).")
        parser.add_argument("--default-stage", default=DEFAULT_STAGE,
                            help=f"ItemStage.name to use for new Item_list rows (default: {DEFAULT_STAGE}).")
        parser.add_argument("--default-line-process", default=DEFAULT_LINE_PROCESS,
                            help=f"LineProcess.name to use for new Line rows (default: {DEFAULT_LINE_PROCESS}).")

    def handle(self, *args, **opts):
        path = Path(opts["file"])
        commit = bool(opts["commit"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        owner = self._resolve_owner(opts.get("user"))
        default_stage = self._resolve_stage(opts["default_stage"])
        default_line_process = self._resolve_line_process(opts["default_line_process"])
        self.stdout.write(f"Reading {path} ...")
        self.stdout.write(f"  default stage for new items: {default_stage.name} ({default_stage.display_name})")
        self.stdout.write(f"  default line process       : {default_line_process.name}")
        rows = list(self._read_rows(path))
        self.stdout.write(f"  data rows: {len(rows)}")

        first_seen: "OrderedDict[str, tuple[str, str]]" = OrderedDict()
        conflicts: list[tuple[str, str, str]] = []
        pair_seen: set[tuple[str, str]] = set()
        pairs: list[tuple[str, str]] = []
        bad_rows: list[tuple[int, tuple]] = []

        for idx, raw in enumerate(rows, start=2):  # row 1 is header
            sd = _s(raw[0])
            pn = _s(raw[1])
            name = _s(raw[2])
            line = _s(raw[3])
            if not sd or not line:
                bad_rows.append((idx, raw))
                continue
            if sd not in first_seen:
                first_seen[sd] = (pn, name)
            else:
                kept_pn, _ = first_seen[sd]
                if pn and pn != kept_pn:
                    conflicts.append((sd, kept_pn, pn))
            key = (sd, line)
            if key in pair_seen:
                continue
            pair_seen.add(key)
            pairs.append(key)

        self.stdout.write(f"  unique sd_code: {len(first_seen)}")
        self.stdout.write(f"  unique (sd_code, line) pairs: {len(pairs)}")
        if bad_rows:
            self.stdout.write(self.style.WARNING(f"  rows with empty sd_code/line: {len(bad_rows)} (skipped)"))
        if conflicts:
            self.stdout.write(self.style.WARNING(
                f"  part_number conflicts (kept first, ignored others): {len(conflicts)}"
            ))
            for sd, kept, ignored in conflicts[:20]:
                self.stdout.write(f"    {sd}: kept={kept!r}  ignored={ignored!r}")

        items_by_sd = {it.sd_code: it for it in Item_list.objects.all() if it.sd_code}
        lines_by_name = {ln.line_name: ln for ln in Line.objects.all()}

        new_items = [sd for sd in first_seen if sd not in items_by_sd]
        new_lines = sorted({ln for _, ln in pairs if ln not in lines_by_name})

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("=== Phase 1: Item_list ==="))
        plan_pn = plan_name = plan_unchanged = 0
        for sd, (pn, name) in first_seen.items():
            it = items_by_sd.get(sd)
            if it is None:
                continue
            if pn and pn != (it.part_number or ""):
                plan_pn += 1
            if name and name != (it.part_name or ""):
                plan_name += 1
            if not (pn and pn != (it.part_number or "")) and not (name and name != (it.part_name or "")):
                plan_unchanged += 1

        self.stdout.write(f"  existing items found      : {len(first_seen) - len(new_items)} / {len(first_seen)}")
        self.stdout.write(f"  part_number to update     : {plan_pn}")
        self.stdout.write(f"  part_name   to update     : {plan_name} (empty xlsx values are skipped)")
        self.stdout.write(f"  unchanged                 : {plan_unchanged}")
        self.stdout.write(f"  NEW Item_list to create   : {len(new_items)} (stage={default_stage.name})")
        if new_items:
            for sd in new_items[:20]:
                pn, name = first_seen[sd]
                self.stdout.write(f"    + {sd}  pn={pn!r}  name={name!r}")
            if len(new_items) > 20:
                self.stdout.write(f"    ... and {len(new_items) - 20} more")

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("=== Phase 2: Line ==="))
        self.stdout.write(f"  existing lines           : {len(lines_by_name)}")
        self.stdout.write(f"  NEW Line to create       : {len(new_lines)}")
        for ln in new_lines:
            self.stdout.write(f"    + {ln!r}")

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("=== Phase 3: ItemLine rebuild ==="))
        existing_il = ItemLine.objects.count()
        self.stdout.write(f"  existing ItemLine rows (to be deleted): {existing_il}")
        self.stdout.write(f"  pairs to create                       : {len(pairs)}")
        self.stdout.write("")

        if not commit:
            self.stdout.write(self.style.NOTICE(
                "DRY-RUN — no changes written. Re-run with --commit to apply."
            ))
            return

        # ---- Apply ----
        created_items = updated_items = 0
        created_lines = 0
        created_item_lines = 0
        deleted_count = 0
        try:
            with transaction.atomic():
                # Phase 1
                for sd, (pn, name) in first_seen.items():
                    it = items_by_sd.get(sd)
                    if it is None:
                        it = Item_list(
                            sd_code=sd,
                            part_number=pn,
                            part_name=name,
                            sku="",
                            stage=default_stage,
                            user=owner,
                        )
                        it.save()
                        items_by_sd[sd] = it
                        created_items += 1
                    else:
                        update_fields: list[str] = []
                        if pn and pn != (it.part_number or ""):
                            it.part_number = pn
                            update_fields.append("part_number")
                        if name and name != (it.part_name or ""):
                            it.part_name = name
                            update_fields.append("part_name")
                        if update_fields:
                            update_fields.append("updated_at")
                            it.save(update_fields=update_fields)
                            updated_items += 1

                # Phase 2
                for ln_name in new_lines:
                    new_line = Line.objects.create(
                        line_name=ln_name,
                        line_process=default_line_process,
                        user=owner,
                    )
                    lines_by_name[ln_name] = new_line
                    created_lines += 1

                # Phase 3
                deleted_count, _ = ItemLine.objects.all().delete()
                for sd, ln_name in pairs:
                    it = items_by_sd[sd]
                    line = lines_by_name[ln_name]
                    ItemLine.objects.create(
                        item=it,
                        line=line,
                        item_stage_id=it.stage_id or default_stage.id,
                        user=owner,
                    )
                    created_item_lines += 1
        except Exception as e:
            raise CommandError(f"Failed to apply changes: {e}")

        self.stdout.write(self.style.SUCCESS(
            f"Applied. Item_list created: {created_items}, updated: {updated_items}. "
            f"Line created: {created_lines}. "
            f"ItemLine deleted: {deleted_count}, created: {created_item_lines}."
        ))

    # ------------------------------------------------------------------
    def _read_rows(self, path: Path):
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        rows = ws.iter_rows(values_only=True)
        try:
            next(rows)  # header
        except StopIteration:
            return
        for row in rows:
            yield row

    def _resolve_owner(self, username: str | None):
        User = get_user_model()
        if username:
            u = User.objects.filter(username=username).first()
            if u is None:
                raise CommandError(f"User not found: {username}")
            return u
        u = User.objects.filter(is_superuser=True).order_by("id").first()
        if u is None:
            u = User.objects.filter(is_staff=True).order_by("id").first()
        if u is None:
            raise CommandError("No superuser or staff user available; pass --user explicitly.")
        return u

    def _resolve_stage(self, name: str) -> ItemStage:
        stage = (
            ItemStage.objects.filter(name__iexact=name).first()
            or ItemStage.objects.filter(display_name__iexact=name).first()
        )
        if stage is None:
            available = ", ".join(ItemStage.objects.values_list("name", flat=True).order_by("name"))
            raise CommandError(f"ItemStage not found: {name!r}. Available: {available}")
        return stage

    def _resolve_line_process(self, name: str) -> LineProcess:
        lp = (
            LineProcess.objects.filter(name__iexact=name).first()
            or LineProcess.objects.filter(display_name__iexact=name).first()
        )
        if lp is None:
            available = ", ".join(LineProcess.objects.values_list("name", flat=True).order_by("name"))
            raise CommandError(f"LineProcess not found: {name!r}. Available: {available}")
        return lp
