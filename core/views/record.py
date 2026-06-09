"""Two-step Record flow.

Page 1 (``RecordProductionView`` — ``/record/``)
    Operator picks a production line via a typeahead, sees every part
    configured on that line, enters the line's start/end time, and enters
    the produced quantity per part. Multiple lines can be filled in on the
    same page.
    "Next" stores the draft in ``sessionStorage`` and navigates to Page 2.

Page 2 (``RecordDefectsView`` — ``/record/defects/``)
    Reads the draft, renders one defect block per (line, part) — same UI as
    the previous single-page ``/record/`` — and on POST persists into the
    new ``ProductionRecord`` → ``ProcessDefect`` → ``ProcessDefectScrap``
    trio (the legacy ``ScrapRecord`` / ``DefectStat`` tables are
    intentionally not written; the inspection-machine pipeline still owns
    ``ScrapRecord``).
"""
from __future__ import annotations

import re
import uuid

from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch, Q
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
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
from core.models.shift import Shift
from core.services.auditlog import log_event


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
    except Exception:
        return False
    return True


def _build_record_payload() -> dict:
    """Shape used by both pages: lines → parts → defects → component scraps.

    Page 1 only needs ``id``, ``parts[].{id,sd_number,part_number,part_name,image_url}``
    but we keep the same structure as Page 2 so a single payload feeds both
    JS files without duplicating queries.
    """
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
    # whose `is_inlist=True`, scoped to the part's ItemCategory.
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
                    "bom_qty": float(it.quantity) if it.quantity is not None else 0,
                }
            )
        components_by_item_id[key] = comps

    production_lines_payload = []
    for line in lines:
        parts_payload = []
        for part_ref in items_by_line.get(line.code, []):
            part = parts_by_id.get(str(part_ref.id), part_ref)
            component_parts_payload = components_by_item_id.get(str(part.id), [])
            defect_list = cat_to_defects.get(str(getattr(part, "category_id", "")), [])

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

    return {"productionLines": production_lines_payload}


@method_decorator(user_required, name="dispatch")
class RecordProductionView(TemplateView):
    """Page 1 — line time window & production quantity per part."""

    template_name = "record_production.html"

    # Map the employee's standing UserProfile.shift to the matching Shift row's
    # display_number, so the right checkbox is pre-ticked (gp A→1, B→2, Day→3).
    _PROFILE_SHIFT_TO_DISPLAY = {"shift_a": 1, "shift_b": 2, "shift_day": 3}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["record_data"] = _build_record_payload()
        # Shift options for the checkbox selector at the top of the page.
        shifts = list(Shift.objects.all().order_by("display_number", "name"))
        ctx["shifts"] = shifts
        # Default-tick the shift that matches the logged-in user's profile shift,
        # to save the operator a click. Draft (sessionStorage) still wins on the
        # client; this is only the fresh-load default.
        default_shift_id = ""
        profile = getattr(self.request.user, "profile", None)
        if profile is not None:
            dn = self._PROFILE_SHIFT_TO_DISPLAY.get(getattr(profile, "shift", None))
            match = next((s for s in shifts if s.display_number == dn), None) if dn else None
            if match is not None:
                default_shift_id = str(match.id)
        ctx["default_shift_id"] = default_shift_id
        return ctx


@method_decorator(user_required, name="dispatch")
class RecordDefectsView(TemplateView):
    """Page 2 — defect & scrap entry, persists the whole submission."""

    template_name = "record_defects.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["record_data"] = _build_record_payload()
        return ctx

    # ----------------------------------------------------------- POST helpers
    def _parse_dt(self, raw: str):
        """Accept either ``YYYY-MM-DDTHH:MM`` (datetime-local) or full ISO.

        ``<input type="datetime-local">`` submits naive strings — promote
        them to aware (using the current TIME_ZONE) so Django doesn't warn.
        """
        raw = (raw or "").strip()
        if not raw:
            return None
        dt = parse_datetime(raw)
        if dt is None:
            return None
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    def _parse_int(self, raw: str, default: int = 0) -> int:
        try:
            return int(re.search(r"(\d+)", raw or "").group(1))  # type: ignore[union-attr]
        except Exception:
            return default

    # Frontend sentinel for the "อื่นๆ" defect option.
    OTHER_SENTINEL = "__other__"
    OTHER_NAME_EN = "Other"

    def _other_defect(self, user=None):
        """The catch-all "Other" DefectMode used when the operator scraps a
        workpiece for a reason outside the listed process defects.

        Seeded by migration 0013; recreated lazily here (keyed on name_en) in
        case it was removed or the DB had no users when the migration ran. The
        specific reason lives in ``ProcessDefect.comment``, not here.
        """
        other = DefectMode.objects.filter(name_en__iexact=self.OTHER_NAME_EN).first()
        if other is not None:
            return other
        from django.contrib.auth import get_user_model

        User = get_user_model()
        creator = user if (user is not None and getattr(user, "pk", None)) else None
        creator = creator or User.objects.filter(is_superuser=True).order_by("pk").first() or User.objects.order_by("pk").first()
        if creator is None:
            return None
        return DefectMode.objects.create(
            name_th="อื่นๆ",
            name_en=self.OTHER_NAME_EN,
            name_jp="その他",
            user=creator,
        )

    def post(self, request, *args, **kwargs):
        """Persist Page 1 + Page 2 data into the new model trio.

        Hidden fields the JS submits (per defect block, indexed by ``gi``):

        - ``blocks[gi][production_line]``    line code (e.g. "L1")
        - ``blocks[gi][part_number]``        part UUID, sd_code or part_number
        - ``blocks[gi][production_quantity]``
        - ``blocks[gi][start_time]``         ``YYYY-MM-DDTHH:MM`` (optional)
        - ``blocks[gi][end_time]``           ``YYYY-MM-DDTHH:MM`` (optional)
        - ``blocks[gi][defect_quantity]``
        - ``blocks[gi][rows][ri][...]``      scrap rows (defect_id, qty, ...)

        Blocks that share the same (line, part) collapse into ONE
        ``ProductionRecord`` (products_quantity = the largest qty entered;
        start/end = the earliest start and latest end across blocks).
        """
        # One shift applies to the whole submission (chosen once on Page 1).
        shift = None
        shift_id = (request.POST.get("shift") or "").strip()
        if _is_uuid(shift_id):
            shift = Shift.objects.filter(pk=shift_id).first()

        # The working day (วันทำการ) chosen once at the top of Page 1 — fixed for
        # the whole submission, never derived from the (possibly cross-midnight)
        # start/end times below.
        production_date = parse_date((request.POST.get("production_date") or "").strip())

        # Every block index present in the submission.
        block_indices: set[int] = set()
        for key in request.POST.keys():
            m = re.match(r"^blocks\[(\d+)\]", key)
            if m:
                block_indices.add(int(m.group(1)))

        def block_field(gi: int, field: str) -> str:
            return (request.POST.get(f"blocks[{gi}][{field}]") or "").strip()

        def row_field(gi: int, ri: int, field: str) -> str:
            return (request.POST.get(f"blocks[{gi}][rows][{ri}][{field}]") or "").strip()

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
            line_code = block_field(gi, "production_line")
            line = resolve_line(line_code)
            if line is None:
                continue

            # "Single part" block: a not-yet-assembled component scrapped on the
            # line that can't be tied to any produced product. Recorded under a
            # productless ProductionRecord (item=None) with NG mode = Other and
            # comment "Single part"; its ProcessDefect.quantity is the sum of the
            # scrapped part quantities.
            is_single = bool(block_field(gi, "single_part"))
            if is_single:
                part = None
            else:
                part = resolve_part(line, line_code, block_field(gi, "part_number"))
                if part is None:
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
                qty = self._parse_int(row_field(gi, ri, "quantity"), 0)
                comp = resolve_item(row_field(gi, ri, "component_part_id"))
                if enabled and qty >= 1 and comp is not None:
                    scraps.append((comp, qty))

            if is_single:
                # NG mode is always the catch-all "Other"; the reason is fixed.
                # Only an actually-used block (≥1 scrap) is recorded — an empty
                # one stays inert so it isn't counted as a skipped attempt.
                if scraps:
                    defect = self._other_defect(getattr(request, "user", None))
                    defect_id = self.OTHER_SENTINEL
                    # Operator-entered reason wins; fall back to the fixed label.
                    comment = comment or "Single part"
                    defect_qty = sum(qty for _comp, qty in scraps)
                else:
                    defect = None
                    defect_id = ""
                    comment = ""
                    defect_qty = 0
            else:
                if _is_uuid(defect_id):
                    defect = DefectMode.objects.filter(pk=defect_id).first()
                elif defect_id == self.OTHER_SENTINEL:
                    # "อื่นๆ" → the catch-all DefectMode; reason is in `comment`.
                    defect = self._other_defect(getattr(request, "user", None))
                else:
                    defect = None
                defect_qty = self._parse_int(block_field(gi, "defect_quantity"), 0)

            parsed_blocks.append(
                {
                    "line": line,
                    "part": part,
                    "is_single": is_single,
                    "defect": defect,
                    "defect_id_raw": defect_id,
                    "prod_qty": self._parse_int(block_field(gi, "production_quantity"), 0),
                    "defect_qty": defect_qty,
                    "start_time": self._parse_dt(block_field(gi, "start_time")),
                    "end_time": self._parse_dt(block_field(gi, "end_time")),
                    "comment": comment,
                    "scraps": scraps,
                }
            )

        # ---- Group by (line, part) → ProductionRecord ----
        groups: dict[tuple[str, str], dict] = {}
        for b in parsed_blocks:
            # Single-part blocks have no product → collapse per line under a
            # sentinel so they don't merge with any real (line, part) record.
            part_key = str(b["part"].id) if b["part"] is not None else "__single__"
            key = (str(b["line"].id), part_key)
            g = groups.setdefault(
                key,
                {
                    "line": b["line"],
                    "part": b["part"],
                    "prod_qty": 0,
                    "start_time": None,
                    "end_time": None,
                    "blocks": [],
                },
            )
            g["prod_qty"] = max(g["prod_qty"], b["prod_qty"])
            # earliest start wins, latest end wins
            if b["start_time"] and (g["start_time"] is None or b["start_time"] < g["start_time"]):
                g["start_time"] = b["start_time"]
            if b["end_time"] and (g["end_time"] is None or b["end_time"] > g["end_time"]):
                g["end_time"] = b["end_time"]
            g["blocks"].append(b)

        production_created = defect_created = scrap_created = skipped = 0
        user = request.user if getattr(request, "user", None) is not None and request.user.is_authenticated else None

        missing_lot_time = False
        for g in groups.values():
            has_useful_record = g["prod_qty"] >= 1 or any(
                b["defect"] is not None and b["defect_qty"] >= 1 for b in g["blocks"]
            )
            if not has_useful_record:
                continue
            if production_date is None or g["start_time"] is None or g["end_time"] is None:
                missing_lot_time = True
                break

        if missing_lot_time:
            messages.error(request, "บันทึกไม่สำเร็จ: ต้องมีวันทำการและเวลาเริ่ม/จบของไลน์ เพื่อสร้างเลขล็อตให้ถูกต้อง")
            return redirect("record")

        with transaction.atomic():
            for g in groups.values():
                valid = [b for b in g["blocks"] if b["defect"] is not None and b["defect_qty"] >= 1]
                for b in g["blocks"]:
                    attempted = bool(b["defect_id_raw"]) or b["defect_qty"] >= 1 or bool(b["scraps"])
                    if attempted and b not in valid:
                        skipped += 1
                if not valid and g["prod_qty"] < 1:
                    # Nothing useful to record at all.
                    continue

                lot_number = ProductionRecord.build_lot_number(
                    g["line"].line_name,
                    getattr(g["part"], "sd_code", None),
                    production_date,
                    g["start_time"],
                    g["end_time"],
                )
                pr = ProductionRecord.objects.create(
                    line=g["line"],
                    item=g["part"],
                    products_quantity=g["prod_qty"],
                    production_date=production_date,
                    start_time=g["start_time"],
                    end_time=g["end_time"],
                    lot_number=lot_number,
                    shift=shift,
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
                "บันทึกไม่สำเร็จ: ต้องกรอก Line/SD number, จำนวนการผลิต ≥ 1 (หรือกรอก Defect mode + จำนวนของเสีย ≥ 1)",
            )

        # After save, send the user back to Page 1 to start a new lot.
        return redirect("record")


# Backwards-compat alias — some imports still reference ``RecordViews``.
RecordViews = RecordProductionView
