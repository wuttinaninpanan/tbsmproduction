from __future__ import annotations

import uuid
from datetime import datetime, time

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.views.generic import TemplateView

from core.models.inspection.inspection_defect_image import InspectionDefectImage


def _image_url(path: str) -> str:
    """Convert stored image_path string to a browser-loadable URL.

    Absolute URLs (http://, https://) and root-absolute paths (/...) are
    returned as-is; everything else is treated as a path relative to
    MEDIA_ROOT and prefixed with MEDIA_URL.
    """
    p = (path or "").strip()
    if not p:
        return ""
    if p.startswith(("http://", "https://", "/")):
        return p
    media = (settings.MEDIA_URL or "/media/").rstrip("/") + "/"
    return media + p.lstrip("/")


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
    except Exception:
        return False
    return True


def _parse_date(value: str):
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


class InspectionDefectImageView(TemplateView):
    template_name = "core/inspection/inspection_defect_image.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request

        q_sd = (request.GET.get("sd_code") or "").strip()
        q_qr = (request.GET.get("qr_work") or "").strip()
        q_caption = (request.GET.get("caption") or "").strip()
        q_defect = (request.GET.get("defect_id") or "").strip()
        q_from_raw = (request.GET.get("date_from") or "").strip()
        q_to_raw = (request.GET.get("date_to") or "").strip()
        per_page_raw = (request.GET.get("per_page") or "").strip()
        page = (request.GET.get("page") or "1").strip() or "1"

        allowed_per_page = {50, 100, 200, 500}
        try:
            per_page = int(per_page_raw or 100)
        except Exception:
            per_page = 100
        if per_page not in allowed_per_page:
            per_page = 100

        qs = InspectionDefectImage.objects.select_related(
            "defect",
            "defect__scrap_record__part_number",
            "defect__scrap_record__component_part",
            "defect__scrap_record__defect_mode",
        )

        if q_defect and _is_uuid(q_defect):
            qs = qs.filter(defect_id=q_defect)
        if q_sd:
            qs = qs.filter(
                Q(defect__scrap_record__part_number__sd_code__icontains=q_sd)
                | Q(defect__scrap_record__component_part__sd_code__icontains=q_sd)
            )
        if q_qr:
            qs = qs.filter(defect__qr_work__icontains=q_qr)
        if q_caption:
            qs = qs.filter(caption__icontains=q_caption)

        date_from = _parse_date(q_from_raw)
        date_to = _parse_date(q_to_raw)
        if date_from is not None:
            dt_from = timezone.make_aware(datetime.combine(date_from, time.min))
            qs = qs.filter(created_at__gte=dt_from)
        if date_to is not None:
            dt_to = timezone.make_aware(datetime.combine(date_to, time.max))
            qs = qs.filter(created_at__lte=dt_to)

        qs = qs.order_by("-created_at", "order")

        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)

        rows = []
        for obj in page_obj.object_list:
            defect = obj.defect
            sr = getattr(defect, "scrap_record", None) if defect else None
            part = getattr(sr, "part_number", None) if sr else None
            defect_mode = getattr(sr, "defect_mode", None) if sr else None
            rows.append({
                "id": str(obj.id),
                "defect_id": str(obj.defect_id) if obj.defect_id else "",
                "image_path": obj.image_path or "",
                "image_url": _image_url(obj.image_path or ""),
                "caption": obj.caption or "",
                "order": obj.order,
                "created_at": obj.created_at.strftime("%Y-%m-%d %H:%M") if obj.created_at else "",
                "qr_work": (defect.qr_work or "") if defect else "",
                "result": (defect.result or "") if defect else "",
                "sd_code": (getattr(part, "sd_code", "") or "") if part else "",
                "defect_name": (
                    getattr(defect_mode, "name_en", "")
                    or getattr(defect_mode, "name_th", "")
                    or ""
                ) if defect_mode else "",
            })

        ctx["rows"] = rows
        ctx["q_sd"] = q_sd
        ctx["q_qr"] = q_qr
        ctx["q_caption"] = q_caption
        ctx["q_defect"] = q_defect
        ctx["q_date_from"] = q_from_raw
        ctx["q_date_to"] = q_to_raw
        ctx["page_obj"] = page_obj
        ctx["paginator"] = paginator
        ctx["per_page"] = per_page
        ctx["rows_total"] = paginator.count
        ctx["page_items"] = _page_items(paginator.num_pages, page_obj.number)
        ctx["total_count"] = paginator.count
        return ctx
