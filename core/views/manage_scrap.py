from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator

from core.services.auditlog import log_event
from core.models import DefectMode, PartNumber, ProductionLine, ComponentPart, ComponentPartRecord
from core.auth.decorators import staff_required


@method_decorator(staff_required, name='dispatch')
class ManageComponentPartViews(TemplateView):
    template_name = "manage_scrap.html"

    def get(self, request, *args, **kwargs):
        # Handle Excel export
        export_action = (request.GET.get("action") or "").strip().lower()
        if export_action == "export_excel":
            return self._export_excel(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        q = (self.request.GET.get("q") or "").strip()
        date_from_raw = (self.request.GET.get("date_from") or "").strip()
        date_to_raw = (self.request.GET.get("date_to") or "").strip()
        per_page_raw = (self.request.GET.get("per_page") or "").strip()
        page = (self.request.GET.get("page") or "1").strip() or "1"
        date_from = parse_date(date_from_raw) if date_from_raw else None
        date_to = parse_date(date_to_raw) if date_to_raw else None

        qs = ComponentPartRecord.objects.select_related(
            "production_line",
            "part_number",
            "defect_mode",
            "component_part",
            "created_by",
            "created_by__profile",
        ).all()

        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        if q:
            qs = qs.filter(
                Q(production_line__code__icontains=q)
                | Q(part_number__number__icontains=q)
                | Q(defect_mode__name__icontains=q)
                | Q(component_part__name__icontains=q)
                | Q(created_by__username__icontains=q)
                | Q(created_by__profile__shift__icontains=q)
            )

        allowed_per_page = {20, 50, 100, 200}
        try:
            per_page = int(per_page_raw or 20)
        except Exception:
            per_page = 20
        if per_page not in allowed_per_page:
            per_page = 20

        qs = qs.order_by("-created_at")
        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)
        ctx["component_part_records"] = list(page_obj.object_list)
        ctx["production_lines"] = list(ProductionLine.objects.order_by("code").values_list("code", flat=True))

        def _page_items(num_pages: int, current: int) -> list[int | None]:
            if num_pages <= 0:
                return []
            if num_pages <= 10:
                return list(range(1, num_pages + 1))
            items: list[int | None] = [1]
            if current > 4:
                items.append(None)
            start = max(2, current - 1)
            end = min(num_pages - 1, current + 1)
            if current <= 4:
                start, end = 2, 4
            if current >= num_pages - 3:
                start, end = num_pages - 3, num_pages - 1
            for n in range(start, end + 1):
                if 1 < n < num_pages:
                    items.append(n)
            if current < num_pages - 3:
                items.append(None)
            items.append(num_pages)
            compressed: list[int | None] = []
            for it in items:
                if compressed and compressed[-1] == it:
                    continue
                if it is None and compressed and compressed[-1] is None:
                    continue
                compressed.append(it)
            return compressed

        # Provide full master-data for edit modal dropdowns (bulk-loaded to avoid N+1).
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
            .only("id", "name", "part_number_id")
            .order_by("part_number__production_line__code", "part_number__number", "name")
        ):
            component_parts_by_part.setdefault(component_part.part_number_id, []).append(
                {"id": str(component_part.pk), "name": component_part.name}
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
                defects_payload = []
                defects = defects_by_part.get(part.id, []) + global_defects
                component_parts = component_parts_by_part.get(part.id, [])
                if not component_parts:
                    component_parts = [{"id": "", "name": "Component part"}]
                for defect in defects:
                    defects_payload.append(
                        {
                            "id": str(defect.pk),
                            "name": defect.name,
                            "component_parts": component_parts,
                        }
                    )
                parts_payload.append({"number": part.number, "defects": defects_payload})
            production_lines_payload.append({"code": line.code, "parts": parts_payload})

        ctx["record_data"] = {"productionLines": production_lines_payload}
        ctx["q"] = q
        ctx["date_from"] = date_from_raw
        ctx["date_to"] = date_to_raw
        ctx["page_obj"] = page_obj
        ctx["paginator"] = paginator
        ctx["per_page"] = per_page
        ctx["rows_total"] = paginator.count
        ctx["page_items"] = _page_items(paginator.num_pages, page_obj.number)
        ctx["total_count"] = paginator.count
        ctx.setdefault("delete_action", "")
        return ctx

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip().lower()
        rec_id = (request.POST.get("id") or "").strip()

        if action == "bulk_delete":
            raw_ids = request.POST.getlist("bulk_id")
            ids = []
            for raw in raw_ids:
                raw = (raw or "").strip()
                if raw.isdigit():
                    ids.append(int(raw))

            if not ids:
                messages.error(request, "กรุณาเลือกรายการที่ต้องการลบ")
                return self.get(request, *args, **kwargs)

            with transaction.atomic():
                deleted, _ = ComponentPartRecord.objects.filter(pk__in=ids).delete()
            messages.success(request, f"ลบสำเร็จ {deleted} รายการ")
            transaction.on_commit(
                lambda: log_event(
                    request,
                    action="scrap:bulk_delete",
                    message="ลบ ComponentPartRecord แบบ bulk",
                    metadata={"selected": len(ids), "deleted": deleted, "ids": ids[:50]},
                )
            )
            return self.get(request, *args, **kwargs)

        if action in {"delete", "update"}:
            if not rec_id.isdigit():
                messages.error(request, "ไม่พบรหัสรายการ")
                return self.get(request, *args, **kwargs)

        if action == "delete":
            obj = (
                ComponentPartRecord.objects.select_related(
                    "production_line",
                    "part_number",
                    "defect_mode",
                    "component_part",
                )
                .filter(pk=int(rec_id))
                .first()
            )
            deleted, _ = ComponentPartRecord.objects.filter(pk=int(rec_id)).delete()
            if deleted:
                messages.success(request, "ลบรายการสำเร็จ")
                meta = {"record_id": int(rec_id)}
                if obj is not None:
                    meta.update(
                        {
                            "line_code": getattr(obj.production_line, "code", ""),
                            "part_number": getattr(obj.part_number, "number", ""),
                            "defect": getattr(obj.defect_mode, "name", ""),
                            "component_part": getattr(obj.component_part, "name", ""),
                            "quantity": obj.quantity,
                        }
                    )
                transaction.on_commit(
                    lambda: log_event(
                        request,
                        action="scrap:delete",
                        message="ลบ ComponentPartRecord",
                        metadata=meta,
                    )
                )
            else:
                messages.error(request, "ไม่พบรายการ")
            return self.get(request, *args, **kwargs)

        if action == "update":
            line_code = (request.POST.get("line_code") or "").strip().upper()
            part_number = (request.POST.get("part_number") or "").strip()
            defect_id = (request.POST.get("defect_id") or "").strip()
            component_part_id = (request.POST.get("component_part_id") or "").strip()

            qty_raw = (request.POST.get("quantity") or "").strip()
            clear_photo = (request.POST.get("clear_photo") or "").strip() in {"1", "true", "on", "yes"}
            photo = request.FILES.get("photo")

            try:
                quantity = int(qty_raw)
            except Exception:
                quantity = None

            if quantity is None or quantity < 1:
                messages.error(request, "กรุณาระบุ Quantity เป็นตัวเลข (>= 1)")
                return self.get(request, *args, **kwargs)

            if not line_code or not part_number or not defect_id.isdigit() or not component_part_id.isdigit():
                messages.error(request, "กรุณาเลือก Line / Part / Defect / Component Part ให้ครบ")
                return self.get(request, *args, **kwargs)

            rec = ComponentPartRecord.objects.filter(pk=int(rec_id)).first()
            if rec is None:
                messages.error(request, "ไม่พบรายการ")
                return self.get(request, *args, **kwargs)

            old_snapshot = {
                "line_id": rec.production_line_id,
                "part_id": rec.part_number_id,
                "defect_id": rec.defect_mode_id,
                "component_part_id": rec.component_part_id,
                "quantity": rec.quantity,
                "had_photo": bool(rec.photo),
            }

            line = ProductionLine.objects.filter(code=line_code).first()
            if line is None:
                messages.error(request, "ไม่พบ Production line")
                return self.get(request, *args, **kwargs)
            part = PartNumber.objects.filter(production_line=line, number=part_number).first()
            if part is None:
                messages.error(request, "ไม่พบ Part number ใน Production line ที่เลือก")
                return self.get(request, *args, **kwargs)
            defect = DefectMode.objects.filter(pk=int(defect_id)).filter(
                Q(part=part) | Q(part__isnull=True)
            ).first()
            if defect is None:
                messages.error(request, "ไม่พบ Defect mode ใน Part ที่เลือก")
                return self.get(request, *args, **kwargs)
            component_part = ComponentPart.objects.filter(pk=int(component_part_id), part_number=part).first()
            if component_part is None:
                messages.error(request, "ไม่พบ Component Part ใน Part ที่เลือก")
                return self.get(request, *args, **kwargs)

            with transaction.atomic():
                updated_fields = []

                if rec.production_line_id != line.id:
                    rec.production_line = line
                    updated_fields.append("production_line")
                if rec.part_number_id != part.id:
                    rec.part_number = part
                    updated_fields.append("part_number")
                if rec.defect_mode_id != defect.id:
                    rec.defect_mode = defect
                    updated_fields.append("defect_mode")
                if rec.component_part_id != component_part.id:
                    rec.component_part = component_part
                    updated_fields.append("component_part")

                if rec.quantity != quantity:
                    rec.quantity = quantity
                    updated_fields.append("quantity")

                if clear_photo:
                    if rec.photo:
                        rec.photo.delete(save=False)
                    rec.photo = None
                    updated_fields.append("photo")
                elif photo is not None:
                    rec.photo = photo
                    updated_fields.append("photo")

                if updated_fields:
                    rec.save(update_fields=updated_fields)
                    messages.success(request, "แก้ไขรายการสำเร็จ")

                    new_snapshot = {
                        "line_id": rec.production_line_id,
                        "part_id": rec.part_number_id,
                        "defect_id": rec.defect_mode_id,
                        "component_part_id": rec.component_part_id,
                        "quantity": rec.quantity,
                        "had_photo": bool(rec.photo),
                    }
                    changed = [f for f in updated_fields if f not in {"updated_at"}]
                    transaction.on_commit(
                        lambda: log_event(
                            request,
                            action="scrap:update",
                            message="แก้ไข ComponentPartRecord",
                            metadata={
                                "record_id": int(rec_id),
                                "changed_fields": changed,
                                "old": old_snapshot,
                                "new": new_snapshot,
                                "clear_photo": clear_photo,
                                "photo_uploaded": photo is not None,
                            },
                        )
                    )
                else:
                    messages.info(request, "ไม่มีการเปลี่ยนแปลง")

            return self.get(request, *args, **kwargs)

        return self.get(request, *args, **kwargs)

    def _export_excel(self, request):
        """Export Component Part records to Excel file"""
        try:
            from openpyxl import Workbook
        except ImportError:
            messages.error(request, "ไม่สามารถ export Excel ได้เนื่องจากไม่มี openpyxl")
            return self.get(request, *args, **kwargs)

        q = (request.GET.get("q") or "").strip()
        date_from_raw = (request.GET.get("date_from") or "").strip()
        date_to_raw = (request.GET.get("date_to") or "").strip()
        date_from = parse_date(date_from_raw) if date_from_raw else None
        date_to = parse_date(date_to_raw) if date_to_raw else None

        qs = ComponentPartRecord.objects.select_related(
            "production_line",
            "part_number",
            "defect_mode",
            "component_part",
            "created_by",
            "created_by__profile",
        ).all()

        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        if q:
            qs = qs.filter(
                Q(production_line__code__icontains=q)
                | Q(part_number__number__icontains=q)
                | Q(defect_mode__name__icontains=q)
                | Q(component_part__name__icontains=q)
                | Q(created_by__username__icontains=q)
                | Q(created_by__profile__shift__icontains=q)
            )

        qs = qs.order_by("-created_at")

        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Component Part Records"

        # Headers
        headers = ["วันที่/เวลา", "ผู้ใช้งาน", "กะ", "Production line", "Part number", "Defect mode", "Component Part", "Quantity"]
        ws.append(headers)

        # Style header row
        from openpyxl.styles import Font, PatternFill
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font

        # Add data rows
        for r in qs:
            shift_display = "-"
            if r.created_by and hasattr(r.created_by, 'profile') and r.created_by.profile:
                shift_value = r.created_by.profile.shift
                if shift_value == 'shift_a':
                    shift_display = "กะ A"
                elif shift_value == 'shift_b':
                    shift_display = "กะ B"
                else:
                    shift_display = "กะ Day"

            created_at_local = timezone.localtime(r.created_at) if r.created_at else None

            row_data = [
                created_at_local.strftime("%d/%m/%Y %H:%M") if created_at_local else "-",
                r.created_by.username if r.created_by else "-",
                shift_display,
                r.production_line.code if r.production_line else "-",
                r.part_number.number if r.part_number else "-",
                r.defect_mode.name if r.defect_mode else "-",
                r.component_part.name if r.component_part else "-",
                r.quantity if r.quantity else 0,
            ]
            ws.append(row_data)

        # Adjust column widths
        ws.column_dimensions['A'].width = 18
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 12
        ws.column_dimensions['D'].width = 18
        ws.column_dimensions['E'].width = 15
        ws.column_dimensions['F'].width = 18
        ws.column_dimensions['G'].width = 15
        ws.column_dimensions['H'].width = 12

        # Prepare response
        from django.http import HttpResponse
        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        filename_ts = timezone.localtime(timezone.now()).strftime("%Y%m%d_%H%M%S")
        response['Content-Disposition'] = f'attachment; filename="ComponentPartRecords_{filename_ts}.xlsx"'
        wb.save(response)
        return response
