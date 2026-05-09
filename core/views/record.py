from __future__ import annotations

import re
import uuid

from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from core.auth.decorators import user_required
from core.models.bill_of_material import BillOfMaterial
from core.models.bill_of_material_item_master import BillOfMaterialItemMater
from core.models.defect_by_category import DefectByCategory
from core.models.defect_mode import DefectMode
from core.models.defect_stat import DefectStat
from core.models.item_line import ItemLine
from core.models.item_list import Item_list
from core.models.line import Line
from core.models.scrap_record import ScrapRecord
from core.services.auditlog import log_event


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
    except Exception:
        return False
    return True


@method_decorator(user_required, name="dispatch")
class RecordViews(TemplateView):
    template_name = "record.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        lines = list(Line.objects.all().order_by("line_name"))
        line_names = [l.code for l in lines]

        item_lines = list(
            ItemLine.objects.select_related("item", "line")
            .filter(line__line_name__in=line_names)
            .order_by("line__line_name", "item__sd_code", "item__part_number")
        )
        items_by_line: dict[str, list[Item_list]] = {ln: [] for ln in line_names}
        item_ids: set[str] = set()
        for il in item_lines:
            items_by_line.setdefault(il.line.code, []).append(il.item)
            item_ids.add(str(il.item_id))

        parts = list(Item_list.objects.filter(pk__in=list(item_ids)).order_by("sd_code", "part_number"))
        parts_by_id = {str(p.id): p for p in parts}

        # Defect mode dropdown is sourced strictly from DefectByCategory rows
        # whose `is_inlist=True`, scoped to the part's ItemCategory. No fallback
        # to "all defects" — if a category has no configured rows, the dropdown
        # is empty for parts in that category.
        category_ids = {str(p.category_id) for p in parts if getattr(p, "category_id", None)}
        cat_to_defects: dict[str, list[DefectMode]] = {}
        if category_ids:
            dbc_qs = (
                DefectByCategory.objects.filter(
                    category_id__in=list(category_ids),
                    is_inlist=True,
                )
                .select_related("defect_mode")
                .order_by("defect_mode__name_th", "defect_mode__name_en")
            )
            for dbc in dbc_qs:
                cat_key = str(dbc.category_id)
                cat_to_defects.setdefault(cat_key, []).append(dbc.defect_mode)
            # de-duplicate within each category, preserving order
            for cat_key, defects_for_cat in cat_to_defects.items():
                seen: set[str] = set()
                uniq: list[DefectMode] = []
                for dm in defects_for_cat:
                    dm_id = str(dm.id)
                    if dm_id in seen:
                        continue
                    seen.add(dm_id)
                    uniq.append(dm)
                cat_to_defects[cat_key] = uniq

        boms = list(
            BillOfMaterial.objects.filter(item__in=parts)
            .select_related("item")
            .prefetch_related(
                Prefetch(
                    "items_master",
                    queryset=BillOfMaterialItemMater.objects.select_related("component").order_by("sequence"),
                )
            )
            .order_by("-updated_at")
        )
        components_by_item_id: dict[str, list[dict]] = {}
        for bom in boms:
            key = str(bom.item_id)
            if key in components_by_item_id:
                continue  # keep newest bom
            comps: list[dict] = []
            for it in getattr(bom, "items_master", []).all():
                c = getattr(it, "component", None)
                if c is None:
                    continue
                child_image = ""
                try:
                    if getattr(c, "reference_image", None):
                        child_image = c.reference_image.url
                except Exception:
                    child_image = ""
                comps.append(
                    {
                        "id": str(c.id),
                        "name": (c.part_name or c.part_number or c.sku or "").strip(),
                        "sd_code": (c.sd_code or "").strip(),
                        "part_number": (c.part_number or "").strip(),
                        "image_url": child_image,
                    }
                )
            components_by_item_id[key] = comps

        production_lines_payload = []
        for line in lines:
            parts_payload = []
            for part_ref in items_by_line.get(line.code, []):
                part = parts_by_id.get(str(part_ref.id), part_ref)

                # Right-side component list = direct BOM children (one level deeper).
                # If the selected part has no BOM, the list is empty and the UI
                # shows an empty-state placeholder.
                component_parts_payload = components_by_item_id.get(str(part.id), [])

                defect_list = cat_to_defects.get(str(getattr(part, "category_id", "")), [])

                defects_payload = []
                for defect in defect_list:
                    defects_payload.append(
                        {
                            "id": str(defect.id),
                            "name": defect.name,
                            "component_parts": [
                                {
                                    **s,
                                    "defect_id": str(defect.id),
                                    "defect_name": defect.name,
                                }
                                for s in component_parts_payload
                            ],
                        }
                    )

                parts_payload.append(
                    {
                        "id": str(part.id),
                        "sd_number": (getattr(part, "sd_code", "") or "").strip(),
                        "part_number": (getattr(part, "part_number", "") or "").strip(),
                        "part_name": (getattr(part, "part_name", "") or "").strip(),
                        "has_components": bool(component_parts_payload),
                        "defects": defects_payload,
                        "component_parts": component_parts_payload,
                    }
                )
            production_lines_payload.append({"id": line.code, "parts": parts_payload})

        ctx["record_data"] = {"productionLines": production_lines_payload}
        return ctx

    def post(self, request, *args, **kwargs):
        default_line_code = (request.POST.get("production_line") or "").strip()
        default_part_ref = (request.POST.get("part_number") or "").strip()

        row_pattern = re.compile(r"^blocks\[(\d+)\]\[rows\]\[(\d+)\]\[enabled\]$")
        enabled_rows: list[tuple[int, int]] = []
        for key in request.POST.keys():
            m = row_pattern.match(key)
            if m and request.POST.get(key):
                enabled_rows.append((int(m.group(1)), int(m.group(2))))

        if not enabled_rows:
            messages.error(request, "ไม่พบแถวที่เลือกให้บันทึก (ต้องติ๊ก checkbox และกรอก Quantity)")
            log_event(
                request,
                action="record_scrap:create",
                status="failure",
                message="บันทึก ScrapRecord ไม่สำเร็จ: ไม่พบแถวที่เลือก",
                metadata={"created": 0},
            )
            return redirect("record")

        def group_line_part(gi: int) -> tuple[str, str]:
            if gi == 0:
                return default_line_code, default_part_ref
            line_code = (request.POST.get(f"blocks[{gi}][production_line]") or "").strip()
            part_ref = (request.POST.get(f"blocks[{gi}][part_number]") or "").strip()
            return line_code, part_ref

        created = 0
        skipped_missing_group = 0
        skipped_invalid = 0
        with transaction.atomic():
            line_cache: dict[str, Line] = {}
            part_cache: dict[tuple[str, str], Item_list] = {}
            component_cache: dict[str, Item_list] = {}

            for gi, ri in enabled_rows:
                line_code, part_ref = group_line_part(gi)
                if not line_code or not part_ref:
                    skipped_missing_group += 1
                    continue

                if line_code not in line_cache:
                    line_cache[line_code] = Line.objects.filter(line_name__iexact=line_code).first()  # type: ignore
                line = line_cache.get(line_code)
                if line is None:
                    skipped_invalid += 1
                    continue

                part_key = (line_code.lower(), part_ref.lower())
                if part_key not in part_cache:
                    if _is_uuid(part_ref):
                        part_obj = (
                            Item_list.objects.filter(pk=part_ref)
                            .filter(item_lines__line=line)
                            .distinct()
                            .first()
                        )
                    else:
                        # Accept part_number text or sd_code (barcode scan)
                        from django.db.models import Q
                        part_obj = (
                            Item_list.objects.filter(
                                Q(part_number__iexact=part_ref) | Q(sd_code__iexact=part_ref)
                            )
                            .filter(item_lines__line=line)
                            .distinct()
                            .first()
                        )
                    part_cache[part_key] = part_obj  # type: ignore
                part = part_cache.get(part_key)
                if part is None:
                    skipped_invalid += 1
                    continue

                defect_id = (request.POST.get(f"blocks[{gi}][rows][{ri}][defect_id]") or "").strip()
                component_part_id = (
                    request.POST.get(f"blocks[{gi}][rows][{ri}][component_part_id]") or ""
                ).strip()
                qty_raw = (request.POST.get(f"blocks[{gi}][rows][{ri}][quantity]") or "").strip()
                comment = (request.POST.get(f"blocks[{gi}][rows][{ri}][comment]") or "").strip()

                try:
                    qty = int(re.search(r"(\d+)", qty_raw).group(1)) if qty_raw else None  # type: ignore[union-attr]
                except Exception:
                    qty = None
                if qty is None or qty < 1:
                    skipped_invalid += 1
                    continue

                if not _is_uuid(defect_id):
                    skipped_invalid += 1
                    continue
                defect = DefectMode.objects.filter(pk=defect_id).first()
                if defect is None:
                    skipped_invalid += 1
                    continue

                component_part = None
                if _is_uuid(component_part_id):
                    if component_part_id not in component_cache:
                        component_cache[component_part_id] = Item_list.objects.filter(pk=component_part_id).first()  # type: ignore
                    component_part = component_cache.get(component_part_id)
                if component_part is None:
                    skipped_invalid += 1
                    continue

                ScrapRecord.objects.create(
                    production_line=line,
                    part_number=part,
                    defect_mode=defect,
                    component_part=component_part,
                    quantity=qty,
                    comment=comment or None,
                    photo=None,
                    created_by=request.user if getattr(request, "user", None) is not None and request.user.is_authenticated else None,
                )
                created += 1

            # ---- DefectStat: 1 row per submitted block (line, part, defect) ----
            # Counts how many produced units exhibited each defect, regardless
            # of how many of their components were scrapped. Used for %-defect.
            block_indices: set[int] = {0}
            for key in request.POST.keys():
                m = re.match(r"^blocks\[(\d+)\]", key)
                if m:
                    block_indices.add(int(m.group(1)))

            row_defect_re = {
                gi: re.compile(rf"^blocks\[{gi}\]\[rows\]\[\d+\]\[defect_id\]$")
                for gi in block_indices
            }

            def block_defect_id(gi: int) -> str:
                pattern = row_defect_re[gi]
                for key, val in request.POST.items():
                    if pattern.match(key):
                        s = (val or "").strip()
                        if s:
                            return s
                return ""

            defect_stat_created = 0
            for gi in sorted(block_indices):
                line_code, part_ref = group_line_part(gi)
                if not line_code or not part_ref:
                    continue
                d_id = block_defect_id(gi)
                if not _is_uuid(d_id):
                    continue

                if line_code not in line_cache:
                    line_cache[line_code] = Line.objects.filter(line_name__iexact=line_code).first()  # type: ignore
                line = line_cache.get(line_code)
                if line is None:
                    continue

                part_key = (line_code.lower(), part_ref.lower())
                if part_key not in part_cache:
                    if _is_uuid(part_ref):
                        part_obj = (
                            Item_list.objects.filter(pk=part_ref)
                            .filter(item_lines__line=line)
                            .distinct()
                            .first()
                        )
                    else:
                        from django.db.models import Q
                        part_obj = (
                            Item_list.objects.filter(
                                Q(part_number__iexact=part_ref) | Q(sd_code__iexact=part_ref)
                            )
                            .filter(item_lines__line=line)
                            .distinct()
                            .first()
                        )
                    part_cache[part_key] = part_obj  # type: ignore
                part = part_cache.get(part_key)
                if part is None:
                    continue

                defect = DefectMode.objects.filter(pk=d_id).first()
                if defect is None:
                    continue

                DefectStat.objects.create(
                    production_line=line,
                    part=part,
                    defect_mode=defect,
                    quantity=1,
                    created_by=request.user if request.user.is_authenticated else None,
                )
                defect_stat_created += 1

        if created:
            msg = f"บันทึกข้อมูลสำเร็จ {created} รายการ (สถิติของเสีย {defect_stat_created} รายการ)"
            if skipped_missing_group or skipped_invalid:
                msg += f" (ข้าม {skipped_missing_group + skipped_invalid} รายการ)"
            messages.success(request, msg)
            log_event(
                request,
                action="record_scrap:create",
                status="success",
                message="บันทึก ScrapRecord สำเร็จ",
                metadata={
                    "created": created,
                    "defect_stat_created": defect_stat_created,
                    "skipped_missing_group": skipped_missing_group,
                    "skipped_invalid": skipped_invalid,
                    "default_line_code": default_line_code,
                    "default_part_ref": default_part_ref,
                },
            )
        else:
            messages.error(request, "ไม่สามารถบันทึกได้ (กรุณากรอก Line/SD number ให้ครบ และกรอก Quantity)")
            log_event(
                request,
                action="record_scrap:create",
                status="failure",
                message="บันทึก ScrapRecord ไม่สำเร็จ: ข้อมูลไม่ครบ/ไม่ผ่านเงื่อนไข",
                metadata={
                    "created": 0,
                    "skipped_missing_group": skipped_missing_group,
                    "skipped_invalid": skipped_invalid,
                },
            )

        return redirect("record")
