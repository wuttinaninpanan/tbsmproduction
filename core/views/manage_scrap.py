from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator

from core.models import DefectMode, PartNumber, ProductionLine, ScrapItem, ScrapRecord
from core.decorators import staff_required


@method_decorator(staff_required, name='dispatch')
class ManageScrapViews(TemplateView):
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
        date_from = parse_date(date_from_raw) if date_from_raw else None
        date_to = parse_date(date_to_raw) if date_to_raw else None

        qs = ScrapRecord.objects.select_related(
            "production_line",
            "part_number",
            "defect_mode",
            "scrap_item",
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
                | Q(scrap_item__name__icontains=q)
                | Q(created_by__username__icontains=q)
                | Q(created_by__profile__shift__icontains=q)
            )

        total_count = qs.count()
        ctx["scrap_records"] = list(qs.order_by("-created_at")[:1000])
        ctx["production_lines"] = list(ProductionLine.objects.order_by("code").values_list("code", flat=True))

        # Provide full master-data for edit modal dropdowns (similar to record page)
        lines = list(ProductionLine.objects.all().order_by("code"))
        production_lines_payload = []
        for line in lines:
            parts_payload = []
            parts = list(PartNumber.objects.filter(production_line=line).order_by("number"))
            for part in parts:
                defects_payload = []
                defects = list(DefectMode.objects.filter(part=part).order_by("name"))
                for defect in defects:
                    scraps = list(
                        ScrapItem.objects.filter(defect_mode=defect)
                        .order_by("name")
                        .values("id", "name")
                    )
                    if not scraps:
                        scraps = [{"id": "", "name": "Component part"}]
                    defects_payload.append(
                        {
                            "id": str(defect.pk),
                            "name": defect.name,
                            "scraps": scraps,
                        }
                    )
                parts_payload.append(
                    {
                        "number": part.number,
                        "defects": defects_payload,
                    }
                )
            production_lines_payload.append({"code": line.code, "parts": parts_payload})

        ctx["record_data"] = {"productionLines": production_lines_payload}
        ctx["q"] = q
        ctx["date_from"] = date_from_raw
        ctx["date_to"] = date_to_raw
        ctx["total_count"] = total_count
        ctx.setdefault("delete_action", "")
        return ctx

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip().lower()
        rec_id = (request.POST.get("id") or "").strip()

        if action in {"delete", "update"}:
            if not rec_id.isdigit():
                messages.error(request, "ไม่พบรหัสรายการ")
                return self.get(request, *args, **kwargs)

        if action == "delete":
            deleted, _ = ScrapRecord.objects.filter(pk=int(rec_id)).delete()
            if deleted:
                messages.success(request, "ลบรายการสำเร็จ")
            else:
                messages.error(request, "ไม่พบรายการ")
            return self.get(request, *args, **kwargs)

        if action == "update":
            line_code = (request.POST.get("line_code") or "").strip().upper()
            part_number = (request.POST.get("part_number") or "").strip()
            defect_id = (request.POST.get("defect_id") or "").strip()
            scrap_id = (request.POST.get("scrap_id") or "").strip()

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

            if not line_code or not part_number or not defect_id.isdigit() or not scrap_id.isdigit():
                messages.error(request, "กรุณาเลือก Line / Part / Defect / Scrap ให้ครบ")
                return self.get(request, *args, **kwargs)

            rec = ScrapRecord.objects.filter(pk=int(rec_id)).first()
            if rec is None:
                messages.error(request, "ไม่พบรายการ")
                return self.get(request, *args, **kwargs)

            line = ProductionLine.objects.filter(code=line_code).first()
            if line is None:
                messages.error(request, "ไม่พบ Production line")
                return self.get(request, *args, **kwargs)
            part = PartNumber.objects.filter(production_line=line, number=part_number).first()
            if part is None:
                messages.error(request, "ไม่พบ Part number ใน Production line ที่เลือก")
                return self.get(request, *args, **kwargs)
            defect = DefectMode.objects.filter(pk=int(defect_id), part=part).first()
            if defect is None:
                messages.error(request, "ไม่พบ Defect mode ใน Part ที่เลือก")
                return self.get(request, *args, **kwargs)
            scrap = ScrapItem.objects.filter(pk=int(scrap_id), defect_mode=defect).first()
            if scrap is None:
                messages.error(request, "ไม่พบ Scrap ใน Defect ที่เลือก")
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
                if rec.scrap_item_id != scrap.id:
                    rec.scrap_item = scrap
                    updated_fields.append("scrap_item")

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
                else:
                    messages.info(request, "ไม่มีการเปลี่ยนแปลง")

            return self.get(request, *args, **kwargs)

        return self.get(request, *args, **kwargs)

    def _export_excel(self, request):
        """Export scrap records to Excel file"""
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

        qs = ScrapRecord.objects.select_related(
            "production_line",
            "part_number",
            "defect_mode",
            "scrap_item",
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
                | Q(scrap_item__name__icontains=q)
                | Q(created_by__username__icontains=q)
                | Q(created_by__profile__shift__icontains=q)
            )

        qs = qs.order_by("-created_at")

        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Scrap Records"

        # Headers
        headers = ["วันที่/เวลา", "ผู้ใช้งาน", "กะ", "Production line", "Part number", "Defect mode", "Scrap", "Quantity"]
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
                r.scrap_item.name if r.scrap_item else "-",
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
        response['Content-Disposition'] = f'attachment; filename="ScrapRecords_{filename_ts}.xlsx"'
        wb.save(response)
        return response
