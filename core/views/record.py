import re

from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.db.models import Q

from core.models import DefectMode, PartNumber, ProductionLine, ComponentPart, ComponentPartRecord
from core.auth.decorators import user_required
from core.services.auditlog import log_event


@method_decorator(user_required, name='dispatch')
class RecordViews(TemplateView):
    template_name = "record.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Bulk-load master data to avoid N+1 queries.
        lines = list(ProductionLine.objects.all().order_by("code"))
        parts = list(
            PartNumber.objects.select_related("production_line")
            .filter(production_line__in=lines)
            .order_by("production_line__code", "number")
        )
        part_ids = [p.id for p in parts]

        component_parts_by_part: dict[int, list[dict]] = {pid: [] for pid in part_ids}
        for component_part in (
            ComponentPart.objects.filter(part_number_id__in=part_ids)
            .only("id", "name", "reference_image", "part_number_id")
            .order_by("part_number__production_line__code", "part_number__number", "name")
        ):
            component_parts_by_part.setdefault(component_part.part_number_id, []).append(
                {
                    "id": str(component_part.pk),
                    "name": component_part.name,
                    "image_url": component_part.reference_image.url
                    if getattr(component_part, "reference_image", None)
                    else "",
                }
            )

        global_defects = list(
            DefectMode.objects.filter(part__isnull=True)
            .only("id", "name")
            .order_by("name")
        )
        defects_by_part: dict[int, list[DefectMode]] = {pid: [] for pid in part_ids}
        for defect in (
            DefectMode.objects.filter(part_id__in=part_ids)
            .only("id", "name", "part_id")
            .order_by("name")
        ):
            defects_by_part.setdefault(defect.part_id, []).append(defect)

        parts_by_line_id: dict[int, list[PartNumber]] = {}
        for p in parts:
            parts_by_line_id.setdefault(p.production_line_id, []).append(p)

        production_lines_payload = []
        for line in lines:
            parts_payload = []
            for part in parts_by_line_id.get(line.id, []):
                component_parts_payload = component_parts_by_part.get(part.id, [])
                if not component_parts_payload:
                    component_parts_payload = [{"id": "", "name": "Component part", "image_url": ""}]

                defects_payload = []
                defects = defects_by_part.get(part.id, []) + global_defects
                for defect in defects:
                    defects_payload.append(
                        {
                            "id": str(defect.pk),
                            "name": defect.name,
                            "component_parts": [
                                {
                                    **s,
                                    "defect_id": str(defect.pk),
                                    "defect_name": defect.name,
                                }
                                for s in component_parts_payload
                            ],
                        }
                    )

                if not defects_payload:
                    defects_payload = [{"id": "", "name": "", "component_parts": component_parts_payload}]

                parts_payload.append(
                    {
                        "id": part.number,
                        "defects": defects_payload,
                        "component_parts": component_parts_payload,
                    }
                )
            production_lines_payload.append({"id": line.code, "parts": parts_payload})

        # Always provide record_data so the page uses real DB data (no fallback demo data)
        ctx["record_data"] = {"productionLines": production_lines_payload}
        return ctx

    def post(self, request, *args, **kwargs):
        default_line_code = (request.POST.get("production_line") or "").strip().upper()
        default_part_number = (request.POST.get("part_number") or "").strip()

        # Collect enabled rows from submitted fields
        row_pattern = re.compile(r"^blocks\[(\d+)\]\[rows\]\[(\d+)\]\[enabled\]$")
        enabled_rows = []
        for key in request.POST.keys():
            m = row_pattern.match(key)
            if m:
                gi = int(m.group(1))
                ri = int(m.group(2))
                if request.POST.get(key):
                    enabled_rows.append((gi, ri))

        if not enabled_rows:
            messages.error(request, "ไม่พบแถวที่เลือกให้บันทึก (ต้องติ๊ก checkbox และเลือก Quantity)")
            log_event(
                request,
                action="record_create",
                status="failure",
                message="Record save failed: no enabled rows",
                metadata={"created": 0, "skipped_missing_group": 0},
            )
            return redirect("record")

        def group_line_part(gi: int) -> tuple[str, str]:
            if gi == 0:
                return default_line_code, default_part_number
            line_code = (request.POST.get(f"blocks[{gi}][production_line]") or "").strip().upper()
            part_number = (request.POST.get(f"blocks[{gi}][part_number]") or "").strip()
            return line_code, part_number

        created = 0
        skipped_missing_group = 0
        with transaction.atomic():
            line_cache: dict[str, ProductionLine] = {}
            part_cache: dict[tuple[str, str], PartNumber] = {}

            for gi, ri in enabled_rows:
                line_code, part_number = group_line_part(gi)
                if not line_code or not part_number:
                    skipped_missing_group += 1
                    continue

                if line_code not in line_cache:
                    line_cache[line_code], _ = ProductionLine.objects.get_or_create(code=line_code)
                line = line_cache[line_code]

                part_key = (line_code, part_number)
                if part_key not in part_cache:
                    part_cache[part_key], _ = PartNumber.objects.get_or_create(production_line=line, number=part_number)
                part = part_cache[part_key]

                component_part_id = (
                    request.POST.get(f"blocks[{gi}][rows][{ri}][component_part_id]") or ""
                ).strip()
                defect_id = (request.POST.get(f"blocks[{gi}][rows][{ri}][defect_id]") or "").strip()
                component_part_name = (
                    request.POST.get(f"blocks[{gi}][rows][{ri}][component_part_name]") or ""
                ).strip()
                qty_raw = (request.POST.get(f"blocks[{gi}][rows][{ri}][quantity]") or "").strip()

                qty = 1
                m_qty = re.search(r"(\d+)", qty_raw)
                if m_qty:
                    qty = max(1, int(m_qty.group(1)))

                component_part = None
                defect = None

                # Defect is still required on records
                if not defect_id.isdigit():
                    continue
                defect = DefectMode.objects.filter(pk=int(defect_id)).filter(
                    Q(part=part) | Q(part__isnull=True)
                ).first()
                if defect is None:
                    continue

                # Prefer component_part_id (from master data)
                if component_part_id.isdigit():
                    component_part = (
                        ComponentPart.objects.select_related("part_number")
                        .filter(pk=int(component_part_id), part_number=part)
                        .first()
                    )
                    if component_part is None:
                        continue
                else:
                    # Fallback: "Component part" case
                    if not component_part_name:
                        continue
                    component_part, _ = ComponentPart.objects.get_or_create(
                        part_number=part,
                        name=component_part_name,
                    )

                ComponentPartRecord.objects.create(
                    production_line=line,
                    part_number=part,
                    defect_mode=defect,
                    component_part=component_part,
                    quantity=qty,
                    photo=None,  # Record page no longer uploads photos; use master images instead
                    created_by=request.user if getattr(request, "user", None) is not None and request.user.is_authenticated else None,
                )
                created += 1

        if created:
            if skipped_missing_group:
                messages.warning(request, f"บันทึกข้อมูลสำเร็จ {created} รายการ (ข้าม {skipped_missing_group} รายการ: ยังไม่กรอก Line/Part ในบางกรอบ)")
            else:
                messages.success(request, f"บันทึกข้อมูลสำเร็จ {created} รายการ")

            log_event(
                request,
                action="record_create",
                status="success",
                message=f"Created {created} component part record(s)",
                metadata={
                    "created": created,
                    "skipped_missing_group": skipped_missing_group,
                    "default_line_code": default_line_code,
                    "default_part_number": default_part_number,
                },
            )
        else:
            messages.error(request, "ไม่สามารถบันทึกได้ (กรุณากรอก Line/Part ให้ครบ และเลือก Quantity)")
            log_event(
                request,
                action="record_create",
                status="failure",
                message="Record save failed: validation/missing fields",
                metadata={
                    "created": 0,
                    "skipped_missing_group": skipped_missing_group,
                    "default_line_code": default_line_code,
                    "default_part_number": default_part_number,
                },
            )

        return redirect("record")