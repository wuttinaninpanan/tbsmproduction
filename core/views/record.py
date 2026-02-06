import re

from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator

from core.models import DefectMode, PartNumber, ProductionLine, ScrapItem, ScrapRecord
from core.decorators import user_required


@method_decorator(user_required, name='dispatch')
class RecordViews(TemplateView):
    template_name = "record.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lines = list(ProductionLine.objects.all().order_by("code"))

        # Record page pulls master data from DB (Line -> Part -> Defect -> Scrap).
        # Each scrap item provides its own reference image.
        production_lines_payload = []
        for line in lines:
            parts_payload = []
            parts = list(PartNumber.objects.filter(production_line=line).order_by("number"))
            for part in parts:

                defects_payload = []
                scraps_payload = []

                defects = list(
                    DefectMode.objects.filter(part=part)
                    .prefetch_related("scraps")
                    .order_by("name")
                )

                for defect in defects:
                    defect_scraps = []
                    for scrap in defect.scraps.all().order_by("name"):
                        scrap_payload = {
                            "id": str(scrap.pk),
                            "name": scrap.name,
                            "defect_id": str(defect.pk),
                            "defect_name": defect.name,
                            "image_url": scrap.reference_image.url if getattr(scrap, "reference_image", None) else "",
                        }
                        defect_scraps.append(scrap_payload)
                        scraps_payload.append(scrap_payload)

                    defects_payload.append(
                        {
                            "id": str(defect.pk),
                            "name": defect.name,
                            "scraps": defect_scraps,
                        }
                    )

                if not scraps_payload:
                    # Keep UI functional even if master data is incomplete
                    first_defect = DefectMode.objects.filter(part=part).order_by("name").first()
                    scraps_payload = [
                        {
                            "id": "",
                            "name": "Component part",
                            "defect_id": str(first_defect.pk) if first_defect else "",
                            "defect_name": first_defect.name if first_defect else "",
                            "image_url": "",
                        }
                    ]

                if not defects_payload:
                    # Allow Defect Mode dropdown to still render
                    if scraps_payload and scraps_payload[0].get("defect_id"):
                        defects_payload = [
                            {
                                "id": scraps_payload[0].get("defect_id") or "",
                                "name": scraps_payload[0].get("defect_name") or "",
                                "scraps": scraps_payload,
                            }
                        ]

                parts_payload.append({"id": part.number, "defects": defects_payload, "scraps": scraps_payload})
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

                scrap_id = (request.POST.get(f"blocks[{gi}][rows][{ri}][scrap_id]") or "").strip()
                defect_id = (request.POST.get(f"blocks[{gi}][rows][{ri}][defect_id]") or "").strip()
                scrap_name = (request.POST.get(f"blocks[{gi}][rows][{ri}][scrap_name]") or "").strip()
                qty_raw = (request.POST.get(f"blocks[{gi}][rows][{ri}][quantity]") or "").strip()

                qty = 1
                m_qty = re.search(r"(\d+)", qty_raw)
                if m_qty:
                    qty = max(1, int(m_qty.group(1)))

                scrap_item = None
                defect = None

                # Prefer scrap_id (from master data)
                if scrap_id.isdigit():
                    scrap_item = (
                        ScrapItem.objects.select_related("defect_mode", "defect_mode__part")
                        .filter(pk=int(scrap_id))
                        .first()
                    )
                    if scrap_item is None:
                        continue
                    defect = scrap_item.defect_mode
                    if defect is None or defect.part_id != part.id:
                        continue
                else:
                    # Fallback: "Component part" case
                    if not defect_id.isdigit() or not scrap_name:
                        continue
                    defect = DefectMode.objects.filter(pk=int(defect_id), part=part).first()
                    if defect is None:
                        continue
                    scrap_item, _ = ScrapItem.objects.get_or_create(defect_mode=defect, name=scrap_name)

                ScrapRecord.objects.create(
                    production_line=line,
                    part_number=part,
                    defect_mode=defect,
                    scrap_item=scrap_item,
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
        else:
            messages.error(request, "ไม่สามารถบันทึกได้ (กรุณากรอก Line/Part ให้ครบ และเลือก Quantity)")

        return redirect("record")