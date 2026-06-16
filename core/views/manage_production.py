from __future__ import annotations

import uuid

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Prefetch, Q
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from core.auth.decorators import staff_required
from core.models.process_defect import ProcessDefect, ProcessDefectScrap, ProductionRecord
from core.services.auditlog import log_event
from core.services.scrap_export import build_scrap_workbook


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
    except Exception:
        return False
    return True


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


@method_decorator(staff_required, name="dispatch")
class ManageProductionViews(TemplateView):
    """View + delete management for the ProductionRecord → ProcessDefect →
    ProcessDefectScrap trio. Each list row is one ProductionRecord; its defect
    modes and scrapped sub-parts are shown as an expandable detail block.
    Deleting a record cascades to its defects and scraps (FK on_delete=CASCADE).
    """

    template_name = "core/manage_production.html"

    TAB_PRODUCTION = "production"
    TAB_DEFECT = "defect"
    TAB_SCRAP = "scrap"
    ALLOWED_TABS = {TAB_PRODUCTION, TAB_DEFECT, TAB_SCRAP}

    # target → (model, audit-log key, human label, cascades?)
    DELETE_TARGETS = {
        TAB_PRODUCTION: (ProductionRecord, "production_record", "ProductionRecord", True),
        TAB_DEFECT: (ProcessDefect, "process_defect", "ProcessDefect", True),
        TAB_SCRAP: (ProcessDefectScrap, "process_defect_scrap", "ProcessDefectScrap", False),
    }

    def get(self, request, *args, **kwargs):
        action = (request.GET.get("action") or "").strip().lower()
        if action == "export_excel":
            return self._export_excel(request)
        return super().get(request, *args, **kwargs)

    def _filtered_queryset(self, q: str, date_from=None, date_to=None):
        """ProductionRecord queryset (newest first) with defects + scraps
        prefetched, optionally filtered by the free-text search `q` and a
        working-day date range. Shared by the list view and the Excel export so
        both honor the same filter."""
        qs = (
            ProductionRecord.objects.select_related("line", "item", "shift", "created_by", "created_by__profile")
            .prefetch_related(
                Prefetch(
                    "defects",
                    queryset=ProcessDefect.objects.select_related("defect_mode").prefetch_related(
                        Prefetch(
                            "details",
                            queryset=ProcessDefectScrap.objects.select_related("component_part"),
                        )
                    ),
                )
            )
        )
        if date_from:
            qs = qs.filter(Q(production_date__gte=date_from) | Q(production_date__isnull=True, created_at__date__gte=date_from))
        if date_to:
            qs = qs.filter(Q(production_date__lte=date_to) | Q(production_date__isnull=True, created_at__date__lte=date_to))
        if q:
            qs = qs.filter(
                Q(line__line_name__icontains=q)
                | Q(lot_number__icontains=q)
                | Q(item__sd_code__icontains=q)
                | Q(item__part_number__icontains=q)
                | Q(item__part_name__icontains=q)
                | Q(defects__defect_mode__name_th__icontains=q)
                | Q(defects__defect_mode__name_en__icontains=q)
            ).distinct()
        return qs.order_by("-created_at")

    def _defect_queryset(self, q: str, date_from=None, date_to=None):
        """ProcessDefect queryset (one defect mode per row), newest first."""
        pr = "production_record__"
        qs = ProcessDefect.objects.select_related(
            f"{pr}line",
            f"{pr}item",
            f"{pr}shift",
            f"{pr}created_by",
            f"{pr}created_by__profile",
            "defect_mode",
        ).prefetch_related("details")
        if date_from:
            qs = qs.filter(Q(**{f"{pr}production_date__gte": date_from}) | Q(**{f"{pr}production_date__isnull": True, f"{pr}created_at__date__gte": date_from}))
        if date_to:
            qs = qs.filter(Q(**{f"{pr}production_date__lte": date_to}) | Q(**{f"{pr}production_date__isnull": True, f"{pr}created_at__date__lte": date_to}))
        if q:
            qs = qs.filter(
                Q(**{f"{pr}line__line_name__icontains": q})
                | Q(**{f"{pr}lot_number__icontains": q})
                | Q(**{f"{pr}item__sd_code__icontains": q})
                | Q(**{f"{pr}item__part_number__icontains": q})
                | Q(**{f"{pr}item__part_name__icontains": q})
                | Q(defect_mode__name_th__icontains=q)
                | Q(defect_mode__name_en__icontains=q)
            )
        return qs.order_by("-production_record__created_at")

    def _scrap_queryset(self, q: str, date_from=None, date_to=None):
        """ProcessDefectScrap queryset (one scrapped sub-part per row), newest first."""
        pr = "process_defect__production_record__"
        qs = ProcessDefectScrap.objects.select_related(
            f"{pr}line",
            f"{pr}item",
            f"{pr}shift",
            f"{pr}created_by",
            f"{pr}created_by__profile",
            "process_defect__defect_mode",
            "component_part",
        )
        if date_from:
            qs = qs.filter(Q(**{f"{pr}production_date__gte": date_from}) | Q(**{f"{pr}production_date__isnull": True, f"{pr}created_at__date__gte": date_from}))
        if date_to:
            qs = qs.filter(Q(**{f"{pr}production_date__lte": date_to}) | Q(**{f"{pr}production_date__isnull": True, f"{pr}created_at__date__lte": date_to}))
        if q:
            qs = qs.filter(
                Q(**{f"{pr}line__line_name__icontains": q})
                | Q(**{f"{pr}lot_number__icontains": q})
                | Q(**{f"{pr}item__sd_code__icontains": q})
                | Q(component_part__sd_code__icontains=q)
                | Q(component_part__part_number__icontains=q)
                | Q(component_part__part_name__icontains=q)
                | Q(process_defect__defect_mode__name_th__icontains=q)
                | Q(process_defect__defect_mode__name_en__icontains=q)
            )
        return qs.order_by(f"-{pr}created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request

        q = (request.GET.get("q") or "").strip()
        date_from_raw = (request.GET.get("date_from") or "").strip()
        date_to_raw = (request.GET.get("date_to") or "").strip()
        date_from = parse_date(date_from_raw) if date_from_raw else None
        date_to = parse_date(date_to_raw) if date_to_raw else None
        per_page_raw = (request.GET.get("per_page") or "").strip()
        page = (request.GET.get("page") or "1").strip() or "1"

        tab = (request.GET.get("tab") or self.TAB_PRODUCTION).strip().lower()
        if tab not in self.ALLOWED_TABS:
            tab = self.TAB_PRODUCTION

        allowed_per_page = {100, 200, 500, 1000}
        try:
            per_page = int(per_page_raw or 100)
        except Exception:
            per_page = 100
        if per_page not in allowed_per_page:
            per_page = 100

        if tab == self.TAB_DEFECT:
            qs = self._defect_queryset(q, date_from, date_to)
        elif tab == self.TAB_SCRAP:
            qs = self._scrap_queryset(q, date_from, date_to)
        else:
            qs = self._filtered_queryset(q, date_from, date_to)

        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)

        if tab == self.TAB_DEFECT:
            ctx["defect_rows"] = self._build_defect_rows(page_obj.object_list)
        elif tab == self.TAB_SCRAP:
            ctx["scrap_rows"] = self._build_scrap_rows(page_obj.object_list)
        else:
            ctx["rows"] = self._build_production_rows(page_obj.object_list)

        ctx["tab"] = tab
        ctx["q"] = q
        ctx["date_from"] = date_from_raw
        ctx["date_to"] = date_to_raw
        ctx["page_obj"] = page_obj
        ctx["paginator"] = paginator
        ctx["per_page"] = per_page
        ctx["rows_total"] = paginator.count
        ctx["total_count"] = paginator.count
        ctx["page_items"] = _page_items(paginator.num_pages, page_obj.number)
        return ctx

    def _build_production_rows(self, records):
        rows = []
        for pr in records:
            defects = []
            for d in pr.defects.all():
                scraps = [
                    {
                        "part_name": (getattr(s.component_part, "part_name", "") or "").strip(),
                        "sd_code": (getattr(s.component_part, "sd_code", "") or "").strip(),
                        "quantity": s.quantity,
                    }
                    for s in d.details.all()
                ]
                defects.append(
                    {
                        "defect_name": d.defect_mode.name if d.defect_mode_id else "-",
                        "quantity": d.quantity,
                        "comment": (d.comment or "").strip(),
                        "scraps": scraps,
                    }
                )
            rows.append(
                {
                    "id": str(pr.id),
                    "created_at": pr.created_at,
                    "production_date": pr.production_date,
                    "lot_number": pr.lot_number,
                    "created_by_name": pr.created_by.get_short_name() if pr.created_by_id else "",
                    "shift": self._shift_display(pr.created_by if pr.created_by_id else None, pr),
                    "line_name": pr.line.line_name if pr.line_id else "-",
                    "sd_code": (getattr(pr.item, "sd_code", "") or "").strip() if pr.item_id else "",
                    "part_number": (getattr(pr.item, "part_number", "") or "").strip() if pr.item_id else "",
                    "part_name": (getattr(pr.item, "part_name", "") or "").strip() if pr.item_id else "",
                    "products_quantity": pr.products_quantity,
                    "total_defect_quantity": pr.total_defect_quantity,
                    "defect_rate": pr.defect_rate,
                    "defect_count": len(defects),
                    "defects": defects,
                }
            )
        return rows

    def _build_defect_rows(self, defects):
        rows = []
        for d in defects:
            pr = d.production_record
            user = pr.created_by if pr.created_by_id else None
            rows.append(
                {
                    "id": str(d.id),
                    "created_at": pr.created_at,
                    "production_date": pr.production_date,
                    "lot_number": pr.lot_number,
                    "created_by_name": user.get_short_name() if user else "",
                    "shift": self._shift_display(user, pr),
                    "line_name": pr.line.line_name if pr.line_id else "-",
                    "sd_code": (getattr(pr.item, "sd_code", "") or "").strip() if pr.item_id else "",
                    "part_name": (getattr(pr.item, "part_name", "") or "").strip() if pr.item_id else "",
                    "defect_name": d.defect_mode.name if d.defect_mode_id else "-",
                    "quantity": d.quantity,
                    "comment": (d.comment or "").strip(),
                    "scrap_count": d.details.count(),
                }
            )
        return rows

    def _build_scrap_rows(self, scraps):
        rows = []
        for s in scraps:
            pd = s.process_defect
            pr = pd.production_record
            user = pr.created_by if pr.created_by_id else None
            comp = s.component_part
            rows.append(
                {
                    "id": str(s.id),
                    "created_at": pr.created_at,
                    "production_date": pr.production_date,
                    "lot_number": pr.lot_number,
                    "created_by_name": user.get_short_name() if user else "",
                    "shift": self._shift_display(user, pr),
                    "line_name": pr.line.line_name if pr.line_id else "-",
                    "comp_sd_code": (getattr(comp, "sd_code", "") or "").strip(),
                    "comp_part_number": (getattr(comp, "part_number", "") or "").strip(),
                    "comp_part_name": (getattr(comp, "part_name", "") or "").strip(),
                    "quantity": s.quantity,
                    "defect_name": pd.defect_mode.name if pd.defect_mode_id else "-",
                }
            )
        return rows

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip().lower()
        target = (request.POST.get("target") or self.TAB_PRODUCTION).strip().lower()
        model, log_key, label, cascades = self.DELETE_TARGETS.get(
            target, self.DELETE_TARGETS[self.TAB_PRODUCTION]
        )
        cascade_note = " (รวม Defect/Scrap ที่เกี่ยวข้อง)" if cascades else ""

        if action == "bulk_delete":
            bulk_ids = request.POST.getlist("bulk_id")
            ids = [pk for pk in bulk_ids if _is_uuid((pk or "").strip())]
            if not ids:
                messages.error(request, "กรุณาเลือกรายการที่ต้องการลบ")
                return redirect(request.get_full_path())
            try:
                with transaction.atomic():
                    deleted, _ = model.objects.filter(pk__in=ids).delete()
            except Exception as e:
                log_event(
                    request,
                    action=f"{log_key}:bulk_delete",
                    status="failure",
                    message=f"ลบ {label} แบบ bulk ไม่สำเร็จ",
                    metadata={"selected": len(ids), "error": str(e)},
                )
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return redirect(request.get_full_path())

            transaction.on_commit(
                lambda: log_event(
                    request,
                    action=f"{log_key}:bulk_delete",
                    message=f"ลบ {label} แบบ bulk",
                    metadata={"selected": len(ids), "deleted": deleted},
                )
            )
            messages.success(request, f"ลบสำเร็จ {len(ids)} รายการ{cascade_note}")
            return redirect(request.get_full_path())

        if action == "delete":
            obj_id = (request.POST.get("id") or "").strip()
            if not _is_uuid(obj_id):
                messages.error(request, "ไม่พบรหัสรายการ")
                return redirect(request.get_full_path())
            obj = model.objects.filter(pk=obj_id).first()
            if obj is None:
                messages.error(request, "ไม่พบรายการ")
                return redirect(request.get_full_path())
            try:
                obj.delete()
            except ProtectedError:
                messages.error(request, "ไม่สามารถลบได้: รายการนี้ถูกใช้งานอยู่")
                return redirect(request.get_full_path())

            transaction.on_commit(
                lambda: log_event(
                    request,
                    action=f"{log_key}:delete",
                    message=f"ลบ {label}",
                    metadata={"id": obj_id},
                )
            )
            messages.success(request, f"ลบรายการสำเร็จ{cascade_note}")
            return redirect(request.get_full_path())

        messages.error(request, "ไม่รองรับการทำงานนี้")
        return redirect(request.get_full_path())

    @staticmethod
    def _shift_display(user, record=None) -> str:
        """กะของรายการ.

        Prefer the shift explicitly chosen on /record/ (``ProductionRecord.shift``)
        — that's the authoritative value going forward. Fall back to the
        recorder's profile shift for legacy rows saved before the field existed,
        then '-' when neither is available.
        """
        if record is not None and getattr(record, "shift_id", None):
            return record.shift.name
        profile = getattr(user, "profile", None) if user is not None else None
        if profile is None:
            return "-"
        return profile.get_shift_display()

    def _export_excel(self, request):
        """Export the filtered ProductionRecord data to the shared 4-sheet
        workbook (Production Record / Scrap / สรุปตาม Line / สรุปตาม Defect mode),
        honoring the same `q` + date-range filter as the list."""
        q = (request.GET.get("q") or "").strip()
        date_from_raw = (request.GET.get("date_from") or "").strip()
        date_to_raw = (request.GET.get("date_to") or "").strip()
        date_from = parse_date(date_from_raw) if date_from_raw else None
        date_to = parse_date(date_to_raw) if date_to_raw else None
        records = list(self._filtered_queryset(q, date_from, date_to))

        record_rows = []
        scrap_rows = []
        line_totals: dict[str, int] = {}
        defect_totals: dict[str, int] = {}

        for pr in records:
            created = timezone.localtime(pr.created_at) if pr.created_at else None
            created_str = created.strftime("%d/%m/%Y %H:%M") if created else "-"
            prod_date_str = pr.production_date.strftime("%d/%m/%Y") if pr.production_date else "-"
            user = pr.created_by if pr.created_by_id else None
            user_str = user.get_short_name() if user else "-"
            shift_str = self._shift_display(user, pr)
            line_name = pr.line.line_name if pr.line_id else "-"

            record_rows.append(
                [
                    created_str,
                    prod_date_str,
                    user_str,
                    shift_str,
                    line_name,
                    pr.lot_number or "-",
                    (getattr(pr.item, "sd_code", "") or "-") if pr.item_id else "-",
                    (getattr(pr.item, "part_name", "") or "-") if pr.item_id else "-",
                    pr.products_quantity,
                    pr.total_defect_quantity,
                    (pr.defect_rate or 0) / 100.0,  # fraction → rendered as %
                ]
            )
            line_totals[line_name] = line_totals.get(line_name, 0) + pr.total_defect_quantity

            for d in pr.defects.all():
                dm_name = d.defect_mode.name if d.defect_mode_id else "-"
                defect_totals[dm_name] = defect_totals.get(dm_name, 0) + d.quantity
                for s in d.details.all():
                    comp = s.component_part
                    scrap_rows.append(
                        [
                            created_str,
                            prod_date_str,
                            user_str,
                            shift_str,
                            line_name,
                            pr.lot_number or "-",
                            (getattr(comp, "sd_code", "") or "-") or "-",
                            (getattr(comp, "part_number", "") or "-") or "-",
                            (getattr(comp, "part_name", "") or "-") or "-",
                            s.quantity,
                        ]
                    )

        try:
            wb = build_scrap_workbook(record_rows, scrap_rows, line_totals, defect_totals)
        except ImportError:
            messages.error(request, "ไม่สามารถ export Excel ได้เนื่องจากไม่มี openpyxl")
            return redirect(request.get_full_path())

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        filename_ts = timezone.localtime(timezone.now()).strftime("%Y%m%d_%H%M%S")
        response["Content-Disposition"] = f'attachment; filename="ProductionRecords_{filename_ts}.xlsx"'
        wb.save(response)
        return response
