"""
Django management command: import_bom

Import BOM Master data from extraction output (scripts/bom_output/) into the database.

Usage:
  python manage.py import_bom                          # dry run (ไม่ write จริง)
  python manage.py import_bom --commit                 # write จริง
  python manage.py import_bom --commit --clear         # ล้างข้อมูลเก่าก่อน import
  python manage.py import_bom --commit --items-only    # import เฉพาะ Item_list
  python manage.py import_bom --commit --bom-only      # import เฉพาะ BOM (ต้องมี Item_list แล้ว)
  python manage.py import_bom --input /path/to/output  # ระบุ folder อื่น

Source files (จาก scripts/extract_bom.py):
  items.json         → Item_list
  relationships.json → BillOfMaterial + BillOfMaterialItemMaster
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models.bill_of_material import BillOfMaterial
from core.models.bill_of_material_item_master import BillOfMaterialItemMaster
from core.models.item_list import Item_list

logger = logging.getLogger(__name__)
User = get_user_model()

DEFAULT_INPUT = Path("scripts/bom_output")

# Note: import นี้จะ "ไม่" auto-infer item_type / process / unit
# ผู้ใช้จะกำหนดค่าเหล่านี้เองตามข้อมูลจริงของโรงงาน
# (Production flow: RAW → Stamping(WIP) → Sub-line(WIP) → Assembly(Semi-FG) → Inspection(FG))


class Command(BaseCommand):
    help = "Import BOM Master data from JSON extraction output into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit",
            action="store_true",
            default=False,
            help="บันทึกข้อมูลจริง (ถ้าไม่ระบุจะเป็น dry run)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            default=False,
            help="ลบข้อมูลเก่าทั้งหมดก่อน import (ต้องใช้ร่วมกับ --commit)",
        )
        parser.add_argument(
            "--items-only",
            action="store_true",
            default=False,
            help="import เฉพาะ Item_list",
        )
        parser.add_argument(
            "--bom-only",
            action="store_true",
            default=False,
            help="import เฉพาะ BOM (ต้องมี Item_list อยู่แล้ว)",
        )
        parser.add_argument(
            "--input",
            default=str(DEFAULT_INPUT),
            help=f"Folder ที่มีไฟล์ items.json และ relationships.json (default: {DEFAULT_INPUT})",
        )
        parser.add_argument(
            "--user",
            default=None,
            help="Username ที่จะใช้เป็น owner ของ records (default: superuser คนแรก)",
        )
        parser.add_argument(
            "--revision",
            default="A",
            help="Revision ของ BOM ที่จะสร้าง (default: A)",
        )

    def handle(self, *args, **options):
        commit: bool = options["commit"]
        do_clear: bool = options["clear"]
        items_only: bool = options["items_only"]
        bom_only: bool = options["bom_only"]
        input_dir = Path(options["input"])
        revision: str = options["revision"] or "A"

        # ─── Validate input ───
        if not input_dir.exists():
            raise CommandError(
                f"ไม่พบ folder: {input_dir}\n"
                f"กรุณารัน 'python scripts/extract_bom.py' ก่อน"
            )

        items_file = input_dir / "items.json"
        rels_file = input_dir / "relationships.json"

        if not items_file.exists():
            raise CommandError(f"ไม่พบ {items_file}")
        if not rels_file.exists() and not items_only:
            raise CommandError(f"ไม่พบ {rels_file}")

        # ─── Load system user ───
        if options["user"]:
            try:
                system_user = User.objects.get(username=options["user"])
            except User.DoesNotExist:
                raise CommandError(f"ไม่พบ user: {options['user']}")
        else:
            system_user = User.objects.filter(is_superuser=True).order_by("id").first()
            if system_user is None:
                raise CommandError("ไม่พบ superuser — กรุณาระบุ --user <username>")

        self.stdout.write(f"👤 System user: {system_user.username}")
        self.stdout.write(f"📂 Input: {input_dir.resolve()}")

        if not commit:
            self.stdout.write(self.style.WARNING(
                "\n⚠ DRY RUN — ไม่มีการบันทึกข้อมูลจริง (เพิ่ม --commit เพื่อ import จริง)\n"
            ))

        # ─── Load JSON ───
        with open(items_file, encoding="utf-8") as f:
            items_data: list[dict] = json.load(f)

        rels_data: list[dict] = []
        if not items_only and rels_file.exists():
            with open(rels_file, encoding="utf-8") as f:
                rels_data = json.load(f)

        self.stdout.write(
            f"\n📊 Items: {len(items_data)} | Relationships: {len(rels_data)}"
        )

        # ─── Stats counters ───
        stats = {
            "items_created": 0,
            "items_updated": 0,
            "items_skipped": 0,
            "bom_created": 0,
            "bom_updated": 0,
            "bom_items_created": 0,
            "bom_items_skipped": 0,
            "errors": [],
        }

        try:
            with transaction.atomic():
                # ─── Clear old data ───
                if do_clear and commit:
                    self.stdout.write(self.style.WARNING("\n🗑 Clearing existing BOM data..."))
                    BillOfMaterialItemMaster.objects.all().delete()
                    BillOfMaterial.objects.all().delete()
                    if not bom_only:
                        Item_list.objects.all().delete()
                    self.stdout.write("  Done.")

                # ─── Phase 1: Import Item_list ────────────────────────────────
                if not bom_only:
                    self.stdout.write("\n─── Phase 1: Import Items ───")
                    item_pk_map: dict[str, str] = {}  # unique_key → item.id (str)

                    for idx, item_data in enumerate(items_data, 1):
                        key = item_data.get("unique_key", "")
                        sd_code_raw = (item_data.get("sd_code") or "").strip()
                        part_no = (item_data.get("part_no") or "").strip()
                        part_name = (item_data.get("part_name") or "").strip()

                        if not key:
                            stats["items_skipped"] += 1
                            continue

                        # ─── Clean SD Code: "DUM"/ว่าง → ยังไม่มี SD Code ───
                        is_real_sd = bool(sd_code_raw) and sd_code_raw.upper() != "DUM"
                        clean_sd_code = sd_code_raw if is_real_sd else ""

                        # ต้องมี part_no อย่างน้อย (เป็นตัวแยก item)
                        if not part_no and not clean_sd_code:
                            stats["items_skipped"] += 1
                            continue

                        # Comment บอกว่ายังต้องกำหนด SD Code
                        comment = ""
                        if not is_real_sd:
                            comment = "ต้องกำหนด SD Code"
                            stats.setdefault("items_need_sd", 0)
                            stats["items_need_sd"] += 1

                        # หาก part_name ว่าง → placeholder
                        if not part_name:
                            label = clean_sd_code or part_no
                            part_name = f"[TO UPDATE] {label}"
                            stats.setdefault("items_placeholder", 0)
                            stats["items_placeholder"] += 1

                        level = item_data.get("min_level")

                        if commit:
                            # Lookup ด้วย (sd_code, part_number)
                            # item_type/unit เว้นว่าง — ผู้ใช้กำหนดเอง
                            obj, created = Item_list.objects.update_or_create(
                                sd_code=clean_sd_code,
                                part_number=part_no,
                                defaults={
                                    "part_name": part_name,
                                    "item_type": "",      # ← เว้นว่าง
                                    "unit": "",           # ← เว้นว่าง
                                    "level": level,
                                    "comment": comment,
                                    "sku": None,          # ← เว้นว่าง (ใช้เฉพาะ variant)
                                    "user": system_user,
                                },
                            )
                            item_pk_map[key] = str(obj.pk)
                            if created:
                                stats["items_created"] += 1
                            else:
                                stats["items_updated"] += 1
                        else:
                            item_pk_map[key] = f"<dry-{idx}>"
                            stats["items_created"] += 1

                        if idx % 100 == 0:
                            self.stdout.write(f"  ... {idx}/{len(items_data)}")

                    self.stdout.write(
                        f"  ✓ Created: {stats['items_created']} | "
                        f"Updated: {stats['items_updated']} | "
                        f"Skipped: {stats['items_skipped']}"
                    )

                else:
                    # bom_only: load existing items from DB by (sd_code, part_number)
                    self.stdout.write("\n⏩ Phase 1 skipped (--bom-only)")
                    item_pk_map: dict[str, str] = {}
                    for item_data in items_data:
                        key = item_data.get("unique_key", "")
                        sd_code_raw = (item_data.get("sd_code") or "").strip()
                        part_no = (item_data.get("part_no") or "").strip()
                        is_real_sd = bool(sd_code_raw) and sd_code_raw.upper() != "DUM"
                        clean_sd = sd_code_raw if is_real_sd else ""
                        if part_no or clean_sd:
                            obj = Item_list.objects.filter(
                                sd_code=clean_sd, part_number=part_no
                            ).first()
                            if obj:
                                item_pk_map[key] = str(obj.pk)

                # ─── Phase 2: Import BOM + BOMItemMaster ─────────────────────
                if not items_only and rels_data:
                    self.stdout.write("\n─── Phase 2: Import BOM Structure ───")

                    # หา FG items (unique parent keys)
                    parent_keys = {r["parent_key"] for r in rels_data}

                    for parent_key in sorted(parent_keys):
                        parent_item_id = item_pk_map.get(parent_key)
                        if not parent_item_id:
                            stats["errors"].append(f"Parent item ไม่พบ: {parent_key}")
                            continue

                        # หา children ของ parent นี้
                        children = [r for r in rels_data if r["parent_key"] == parent_key]
                        if not children:
                            continue

                        if commit:
                            parent_item = Item_list.objects.filter(pk=parent_item_id).first()
                            if not parent_item:
                                stats["errors"].append(f"Item not found in DB: {parent_key}")
                                continue

                            bom, bom_created = BillOfMaterial.objects.get_or_create(
                                item=parent_item,
                                revision=revision,
                                defaults={
                                    "lasted_eci": "",
                                    "scrap_percent": Decimal("0"),
                                    "user": system_user,
                                },
                            )
                            if bom_created:
                                stats["bom_created"] += 1
                            else:
                                stats["bom_updated"] += 1

                            # สร้าง BOMItemMaster สำหรับแต่ละ child
                            for seq, rel in enumerate(children, 1):
                                child_key = rel["child_key"]
                                child_item_id = item_pk_map.get(child_key)
                                if not child_item_id:
                                    stats["bom_items_skipped"] += 1
                                    continue

                                child_item = Item_list.objects.filter(pk=child_item_id).first()
                                if not child_item:
                                    stats["bom_items_skipped"] += 1
                                    continue

                                qty = Decimal(str(rel.get("quantity", 1))).quantize(
                                    Decimal("0.000001")
                                )

                                _, item_created = BillOfMaterialItemMaster.objects.update_or_create(
                                    bom=bom,
                                    component=child_item,
                                    defaults={
                                        "quantity": qty,
                                        "unit": "",          # ← เว้นว่าง
                                        "sequence": seq,
                                        "process": "",       # ← เว้นว่าง
                                        "scrap_percent": Decimal("0"),
                                        "user": system_user,
                                    },
                                )
                                if item_created:
                                    stats["bom_items_created"] += 1
                                else:
                                    stats["bom_items_skipped"] += 1
                        else:
                            stats["bom_created"] += 1
                            stats["bom_items_created"] += len(children)

                    self.stdout.write(
                        f"  ✓ BOM headers: {stats['bom_created']} new, {stats['bom_updated']} existing\n"
                        f"  ✓ BOM items: {stats['bom_items_created']} created, "
                        f"{stats['bom_items_skipped']} skipped"
                    )

                # ─── Rollback if dry run ───
                if not commit:
                    transaction.set_rollback(True)

        except Exception as e:
            raise CommandError(f"Import ล้มเหลว: {e}") from e

        # ─── Summary ───
        self.stdout.write("\n" + "=" * 60)
        if commit:
            self.stdout.write(self.style.SUCCESS("✅ IMPORT COMPLETE"))
        else:
            self.stdout.write(self.style.WARNING("✅ DRY RUN COMPLETE (ไม่มีการบันทึกจริง)"))

        placeholder = stats.get("items_placeholder", 0)
        need_sd = stats.get("items_need_sd", 0)
        self.stdout.write(f"""
  Items created  : {stats['items_created']}
  Items updated  : {stats['items_updated']}
  Items skipped  : {stats['items_skipped']}
  Items ต้องกำหนด SD Code : {need_sd}
  Items part_name ว่าง    : {placeholder}
  BOM headers    : {stats['bom_created']} new, {stats['bom_updated']} existing
  BOM items      : {stats['bom_items_created']} created, {stats['bom_items_skipped']} skipped
""")

        if need_sd:
            self.stdout.write(self.style.WARNING(
                f"ℹ {need_sd} items ยังไม่มี SD Code (เดิมเป็น DUM หรือเว้นว่าง) — "
                f"SKU ใช้ Part Number แทน, comment = 'ต้องกำหนด SD Code'\n"
                f"   → กรอง: Item_list.objects.filter(sd_code='')"
            ))
        if placeholder:
            self.stdout.write(self.style.WARNING(
                f"ℹ {placeholder} items มี part_name ว่าง — "
                f"ถูกตั้งเป็น '[TO UPDATE] <sku>' ให้ไปเติม Part Name ภายหลัง"
            ))

        if stats["errors"]:
            self.stdout.write(self.style.WARNING(f"⚠ Errors ({len(stats['errors'])}):"))
            for err in stats["errors"][:20]:
                self.stdout.write(f"  - {err}")

        if not commit:
            self.stdout.write(self.style.WARNING(
                "\n👉 รัน: python manage.py import_bom --commit\n"
                "   เพื่อ import จริง"
            ))
