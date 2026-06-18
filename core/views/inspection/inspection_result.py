from __future__ import annotations

import uuid
from datetime import datetime, time

from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.utils.timezone import localtime
from django.views.generic import TemplateView

from core.models.inspection.inspection_result import InspectionResult


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except Exception:
        return False


def _parse_date(value: str):
    """Parse YYYY-MM-DD; return date or None."""
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


class InspectionResultView(TemplateView):

    template_name = "core/inspection/inspection_result.html"

    def get_context_data(self, **kwargs):

        ctx = super().get_context_data(**kwargs)
        request = self.request

        q_sd = (request.GET.get("sd_code") or "").strip()
        q_line = (request.GET.get("line") or "").strip()
        q_qr = (request.GET.get("qr_work") or "").strip()
        q_result = (request.GET.get("result") or "").strip()
        q_from_raw = (request.GET.get("date_from") or "").strip()
        q_to_raw = (request.GET.get("date_to") or "").strip()
        per_page_raw = (request.GET.get("per_page") or "").strip()
        page = request.GET.get("page", 1)

        allowed_per_page = {50, 100, 200, 500, 1000}
        try:
            per_page = int(per_page_raw or 100)
        except Exception:
            per_page = 100
        if per_page not in allowed_per_page:
            per_page = 100

        qs = (
            InspectionResult.objects
            .select_related("inspectionitem", "inspection_line")
            .order_by("-created_at")
        )

        if q_sd:
            qs = qs.filter(inspectionitem__sd_code__icontains=q_sd)
        if q_line:
            qs = qs.filter(inspection_line__line_name__icontains=q_line)
        if q_qr:
            qs = qs.filter(qr_work__icontains=q_qr)
        if q_result:
            qs = qs.filter(result__icontains=q_result)

        date_from = _parse_date(q_from_raw)
        date_to = _parse_date(q_to_raw)
        if date_from is not None:
            dt_from = timezone.make_aware(datetime.combine(date_from, time.min))
            qs = qs.filter(created_at__gte=dt_from)
        if date_to is not None:
            dt_to = timezone.make_aware(datetime.combine(date_to, time.max))
            qs = qs.filter(created_at__lte=dt_to)

        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)

        rows = [
            {
                "id": str(obj.id),
                "inspectionitem_id": str(obj.inspectionitem_id),
                "inspection_line_id": str(obj.inspection_line_id),

                "sd_code": getattr(obj.inspectionitem, "sd_code", ""),
                "line_name": getattr(obj.inspection_line, "line_name", ""),

                "qr_work": obj.qr_work,
                "result": obj.result,

                "created_at": localtime(obj.created_at).strftime("%d/%m/%Y %H:%M:%S"),
            }
            for obj in page_obj
        ]

        ctx.update({
            "rows": rows,
            "page_obj": page_obj,
            "paginator": paginator,
            "per_page": per_page,
            "rows_total": paginator.count,
            "page_items": _page_items(paginator.num_pages, page_obj.number),
            "q_sd": q_sd,
            "q_line": q_line,
            "q_qr": q_qr,
            "q_result": q_result,
            "q_date_from": q_from_raw,
            "q_date_to": q_to_raw,
            "total_count": paginator.count,
        })

        return ctx