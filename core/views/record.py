from __future__ import annotations

import re
import uuid

from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch, Q
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from core.auth.decorators import user_required
from core.models.bill_of_material import BillOfMaterial
from core.models.bill_of_material_item_master import BillOfMaterialItemMater
from core.models.defect_by_category import DefectByCategory
from core.models.defect_mode import DefectMode
from core.models.item_line import ItemLine
from core.models.item_list import Item_list
from core.models.line import Line
from core.models.process_defect import ProcessDefect, ProcessDefectScrap, ProductionRecord
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
                        # qty of this component used per product (BoM) — drives the
                        # auto-filled scrap Qtty (defect qty × bom_qty).
                        "bom_qty": float(it.quantity) if it.quantity is not None else 0,
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

                # The product's own photo — shown on the FG (whole-product) scrap row.
                part_image = ""
                try:
                    if getattr(part, "reference_image", None):
                        part_image = part.reference_image.url
                except Exception:
                    part_image = ""

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
                        "image_url": part_image,
                        "has_components": bool(component_parts_payload),
                        "defects": defects_payload,
                        "component_parts": component_parts_payload,
                    }
                )
            production_lines_payload.append({"id": line.code, "parts": parts_payload})

        ctx["record_data"] = {"productionLines": production_lines_payload}
        return ctx

    def post(self, request, *args, **kwargs):
        """Persist the board into the new model trio.

        One block = (line, part, defect, production qty, defect qty, scrap rows).
        Blocks sharing the same (line, part) collapse into ONE ``ProductionRecord``
        (products_quantity = the largest qty entered across them); each block then
        becomes one ``ProcessDefect``, and every ticked scrap row a
        ``ProcessDefectScrap`` (the first row is the FG = the product itself).
        The legacy ScrapRecord/DefectStat tables are intentionally no longer written.
        """
        default_line_code = (request.POST.get("production_line") or "").strip()
        default_part_ref = (request.POST.get("part_number") or "").strip()

        # Every block index present in the submission (0 is the header block).
        block_indices: set[int] = {0}
        for key in request.POST.keys():
            m = re.match(r"^blocks\[(\d+)\]", key)
            if m:
                block_indices.add(int(m.group(1)))

        def group_line_part(gi: int) -> tuple[str, str]:
            if gi == 0:
                return default_line_code, default_part_ref
            return (
                (request.POST.get(f"blocks[{gi}][production_line]") or "").strip(),
                (request.POST.get(f"blocks[{gi}][part_number]") or "").strip(),
            )

        def block_field(gi: int, field: str) -> str:
            key = field if gi == 0 else f"blocks[{gi}][{field}]"
            return (request.POST.get(key) or "").strip()

        def row_field(gi: int, ri: int, field: str) -> str:
            return (request.POST.get(f"blocks[{gi}][rows][{ri}][{field}]") or "").strip()

        def parse_int(raw: str, default: int = 0) -> int:
            try:
                return int(re.search(r"(\d+)", raw).group(1))  # type: ignore[union-attr]
            except Exception:
                return default

        def row_indices(gi: int) -> list[int]:
            rx = re.compile(rf"^blocks\[{gi}\]\[rows\]\[(\d+)\]\[")
            idxs: set[int] = set()
            for key in request.POST.keys():
                m = rx.match(key)
                if m:
                    idxs.add(int(m.group(1)))
            return sorted(idxs)

        line_cache: dict[str, Line] = {}
        part_cache: dict[tuple[str, str], Item_list] = {}
        item_cache: dict[str, Item_list] = {}

        def resolve_line(line_code: str):
            if not line_code:
                return None
            if line_code not in line_cache:
                line_cache[line_code] = Line.objects.filter(line_name__iexact=line_code).first()  # type: ignore
            return line_cache.get(line_code)

        def resolve_part(line, line_code: str, part_ref: str):
            if line is None or not part_ref:
                return None
            key = (line_code.lower(), part_ref.lower())
            if key not in part_cache:
                base = Item_list.objects.filter(item_lines__line=line).distinct()
                if _is_uuid(part_ref):
                    part_cache[key] = base.filter(pk=part_ref).first()  # type: ignore
                else:
                    # part_number text or sd_code (barcode scan)
                    part_cache[key] = base.filter(
                        Q(part_number__iexact=part_ref) | Q(sd_code__iexact=part_ref)
                    ).first()  # type: ignore
            return part_cache.get(key)

        def resolve_item(item_id: str):
            if not _is_uuid(item_id):
                return None
            if item_id not in item_cache:
                item_cache[item_id] = Item_list.objects.filter(pk=item_id).first()  # type: ignore
            return item_cache.get(item_id)

        # ---- Parse each block into a normalized structure ----
        parsed_blocks: list[dict] = []
        for gi in sorted(block_indices):
            line_code, part_ref = group_line_part(gi)
            line = resolve_line(line_code)
            part = resolve_part(line, line_code, part_ref)
            if line is None or part is None:
                continue

            defect_id = ""
            comment = ""
            scraps: list[tuple[Item_list, int]] = []
            for ri in row_indices(gi):
                d = row_field(gi, ri, "defect_id")
                if not defect_id and d:
                    defect_id = d
                c = row_field(gi, ri, "comment")
                if not comment and c:
                    comment = c
                enabled = bool(request.POST.get(f"blocks[{gi}][rows][{ri}][enabled]"))
                qty = parse_int(row_field(gi, ri, "quantity"), 0)
                comp = resolve_item(row_field(gi, ri, "component_part_id"))
                if enabled and qty >= 1 and comp is not None:
                    scraps.append((comp, qty))

            defect = DefectMode.objects.filter(pk=defect_id).first() if _is_uuid(defect_id) else None
            parsed_blocks.append(
                {
                    "line": line,
                    "part": part,
                    "defect": defect,
                    "defect_id_raw": defect_id,
                    "prod_qty": parse_int(block_field(gi, "production_quantity"), 0),
                    "defect_qty": parse_int(block_field(gi, "defect_quantity"), 0),
                    "comment": comment,
                    "scraps": scraps,
                }
            )

        # ---- Group by (line, part) → ProductionRecord ----
        groups: dict[tuple[str, str], dict] = {}
        for b in parsed_blocks:
            key = (str(b["line"].id), str(b["part"].id))
            g = groups.setdefault(key, {"line": b["line"], "part": b["part"], "prod_qty": 0, "blocks": []})
            g["prod_qty"] = max(g["prod_qty"], b["prod_qty"])
            g["blocks"].append(b)

        production_created = defect_created = scrap_created = skipped = 0
        user = request.user if getattr(request, "user", None) is not None and request.user.is_authenticated else None

        with transaction.atomic():
            for g in groups.values():
                # A block yields a ProcessDefect only with a real defect + qty ≥ 1.
                valid = [b for b in g["blocks"] if b["defect"] is not None and b["defect_qty"] >= 1]
                # Count blocks the user clearly attempted but that can't be saved
                # (e.g. defect 'อื่นๆ', or a defect/scrap left with qty 0).
                for b in g["blocks"]:
                    attempted = bool(b["defect_id_raw"]) or b["defect_qty"] >= 1 or bool(b["scraps"])
                    if attempted and b not in valid:
                        skipped += 1
                if not valid:
                    continue

                pr = ProductionRecord.objects.create(
                    line=g["line"],
                    item=g["part"],
                    products_quantity=g["prod_qty"],
                    created_by=user,
                )
                production_created += 1
                for b in valid:
                    pd = ProcessDefect.objects.create(
                        production_record=pr,
                        defect_mode=b["defect"],
                        quantity=b["defect_qty"],
                        comment=b["comment"] or None,
                    )
                    defect_created += 1
                    for comp, qty in b["scraps"]:
                        ProcessDefectScrap.objects.create(
                            process_defect=pd,
                            component_part=comp,
                            quantity=qty,
                        )
                        scrap_created += 1

            transaction.on_commit(
                lambda: log_event(
                    request,
                    action="production_record:create",
                    status="success" if production_created else "failure",
                    message="บันทึก ProductionRecord",
                    metadata={
                        "production_created": production_created,
                        "defect_created": defect_created,
                        "scrap_created": scrap_created,
                        "skipped": skipped,
                    },
                )
            )

        if production_created:
            msg = (
                f"บันทึกสำเร็จ: ผลิตภัณฑ์ {production_created} รายการ, "
                f"ของเสีย {defect_created} ประเภท, ทิ้งชิ้นส่วน {scrap_created} รายการ"
            )
            if skipped:
                msg += f" (ข้าม {skipped} รายการ)"
            messages.success(request, msg)
        else:
            messages.error(
                request,
                "บันทึกไม่สำเร็จ: ต้องกรอก Line/SD number, เลือก Defect mode และกรอกจำนวนของเสีย ≥ 1",
            )

        return redirect("record")
