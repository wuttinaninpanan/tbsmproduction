from __future__ import annotations

import uuid

from django.core.paginator import Paginator
from django.db.models import Q
from django.views.generic import TemplateView
from django.utils.timezone import localtime

from core.models.inspection.inspection_result import InspectionResult


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except Exception:
        return False


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

    template_name = "inspection/inspection_result.html"

    def get_context_data(self, **kwargs):

        ctx = super().get_context_data(**kwargs)
        request = self.request

        q = (request.GET.get("q") or "").strip()
        page = request.GET.get("page", 1)

        per_page = 100

        qs = (
            InspectionResult.objects
            .select_related("inspectionitem", "inspection_line")
            .order_by("-created_at")
        )

        if q and _is_uuid(q):
            qs = qs.filter(
                Q(id=q)
                | Q(inspectionitem_id=q)
                | Q(inspection_line_id=q)
            )

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

                # ✅ ดึงจาก DB แล้ว format เลย
                "created_at": localtime(obj.created_at).strftime("%d/%m/%Y %H:%M:%S"),
            }
            for obj in page_obj
        ]

        ctx.update({
            "rows": rows,
            "page_obj": page_obj,
            "paginator": paginator,
            "rows_total": paginator.count,
            "page_items": _page_items(paginator.num_pages, page_obj.number),
        })

        return ctx