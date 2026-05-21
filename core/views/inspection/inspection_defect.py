from __future__ import annotations

from datetime import datetime, time

from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.views.generic import TemplateView

from core.models.inspection.inspection_defect import InspectionDefect


def _parse_date(value: str):
    """Parse YYYY-MM-DD; return naive date or None."""
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


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


def _scrap_label(sr) -> str:
    part = getattr(sr, "part_number", None)
    sd = getattr(part, "sd_code", "") or "" if part else ""
    pn = getattr(part, "part_number", "") or "" if part else ""
    defect = getattr(sr, "defect_mode", None)
    defect_name = ""
    if defect is not None:
        defect_name = (
            getattr(defect, "name_en", "")
            or getattr(defect, "name_th", "")
            or getattr(defect, "name_jp", "")
            or ""
        )
    created = sr.created_at.strftime("%Y-%m-%d") if sr.created_at else ""
    bits = [b for b in [sd, pn, defect_name, created] if b]
    return " / ".join(bits) or str(sr.id)


class InspectionDefectView(TemplateView):
    template_name = "inspection/inspection_defect.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request

        q_sd = (request.GET.get("sd_code") or "").strip()
        q_qr = (request.GET.get("qr_work") or "").strip()
        q_from_raw = (request.GET.get("date_from") or "").strip()
        q_to_raw = (request.GET.get("date_to") or "").strip()
        per_page_raw = (request.GET.get("per_page") or "").strip()
        page = (request.GET.get("page") or "1").strip() or "1"

        allowed_per_page = {100, 200, 500, 1000}
        try:
            per_page = int(per_page_raw or 100)
        except Exception:
            per_page = 100
        if per_page not in allowed_per_page:
            per_page = 100

        qs = InspectionDefect.objects.select_related(
            "scrap_record__part_number",
            "scrap_record__component_part",
            "scrap_record__defect_mode",
            "scrap_record__production_line",
        )

        if q_sd:
            qs = qs.filter(
                Q(scrap_record__part_number__sd_code__icontains=q_sd)
                | Q(scrap_record__component_part__sd_code__icontains=q_sd)
            )
        if q_qr:
            qs = qs.filter(qr_work__icontains=q_qr)

        date_from = _parse_date(q_from_raw)
        date_to = _parse_date(q_to_raw)
        if date_from is not None:
            dt_from = timezone.make_aware(datetime.combine(date_from, time.min))
            qs = qs.filter(created_at__gte=dt_from)
        if date_to is not None:
            dt_to = timezone.make_aware(datetime.combine(date_to, time.max))
            qs = qs.filter(created_at__lte=dt_to)

        qs = qs.order_by("-created_at")

        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)

        rows = []
        for obj in page_obj.object_list:
            sr = obj.scrap_record
            part = getattr(sr, "part_number", None) if sr else None
            comp = getattr(sr, "component_part", None) if sr else None
            defect = getattr(sr, "defect_mode", None) if sr else None
            photo_url = ""
            try:
                if obj.photo:
                    photo_url = obj.photo.url
            except Exception:
                photo_url = ""
            rows.append({
                "id": str(obj.id),
                "scrap_record_id": str(sr.id) if sr else "",
                "scrap_label": _scrap_label(sr) if sr else "-",
                "sd_code": (getattr(part, "sd_code", "") or "") if part else "",
                "component_sd_code": (getattr(comp, "sd_code", "") or "") if comp else "",
                "defect_name": (
                    getattr(defect, "name_en", "")
                    or getattr(defect, "name_th", "")
                    or ""
                ) if defect else "",
                "qr_work": obj.qr_work or "",
                "result": obj.result or "",
                "photo_url": photo_url,
                "created_at": obj.created_at.strftime("%Y-%m-%d %H:%M") if obj.created_at else "",
            })

        ctx["rows"] = rows
        ctx["q_sd"] = q_sd
        ctx["q_qr"] = q_qr
        ctx["q_date_from"] = q_from_raw
        ctx["q_date_to"] = q_to_raw
        ctx["page_obj"] = page_obj
        ctx["paginator"] = paginator
        ctx["per_page"] = per_page
        ctx["rows_total"] = paginator.count
        ctx["page_items"] = _page_items(paginator.num_pages, page_obj.number)
        ctx["total_count"] = paginator.count
        return ctx
