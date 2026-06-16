from __future__ import annotations

from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from django.views.generic import TemplateView

from core.models.inspection.inspection_log import (
    InspectionOKLog, InspectionOKLogDetail,
    InspectionNGLog, InspectionNGLogDetail,
)
from core.models.inspection.machine import Machine


TABS = ("ok", "ng")


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


class InspectionLogsView(TemplateView):
    template_name = "core/inspection/inspection_logs.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request

        tab = (request.GET.get("tab") or "ok").strip().lower()
        if tab not in TABS:
            tab = "ok"

        q = (request.GET.get("q") or "").strip()
        machine_id = (request.GET.get("machine_id") or "").strip()
        date_from = (request.GET.get("date_from") or "").strip()
        date_to = (request.GET.get("date_to") or "").strip()
        page = (request.GET.get("page") or "1").strip() or "1"

        try:
            per_page = int(request.GET.get("per_page") or 50)
        except Exception:
            per_page = 50
        if per_page not in {25, 50, 100, 200}:
            per_page = 50

        if tab == "ok":
            qs = InspectionOKLog.objects.select_related(
                "machine", "item"
            ).prefetch_related(
                Prefetch(
                    "details",
                    queryset=InspectionOKLogDetail.objects.select_related("detection_object"),
                )
            )
            if q:
                qs = qs.filter(
                    Q(kanban_qr__icontains=q)
                    | Q(item_qr__icontains=q)
                    | Q(item__part_name__icontains=q)
                    | Q(item__sd_code__icontains=q)
                    | Q(machine__machine_no__icontains=q)
                    | Q(machine__machine_name__icontains=q)
                )
            if machine_id:
                qs = qs.filter(machine_id=machine_id)
            if date_from:
                qs = qs.filter(inspected_at__date__gte=date_from)
            if date_to:
                qs = qs.filter(inspected_at__date__lte=date_to)

            qs = qs.order_by("-inspected_at")
            paginator = Paginator(qs, per_page)
            page_obj = paginator.get_page(page)

            rows = []
            for log in page_obj.object_list:
                rows.append({
                    "id": str(log.id),
                    "inspected_at": log.inspected_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "machine_no": log.machine.machine_no,
                    "machine_name": log.machine.machine_name,
                    "sd_code": log.item.sd_code or "",
                    "part_name": log.item.part_name or "",
                    "kanban_qr": log.kanban_qr,
                    "item_qr": log.item_qr,
                    "photo_path": log.photo_path or "",
                    "details": [
                        {
                            "object_name": d.detection_object.name,
                            "camera_number": d.camera_number,
                            "object_found": d.object_found,
                            "object_count": d.object_count,
                            "expected_count": d.expected_count,
                            "confidence": f"{d.confidence:.2f}" if d.confidence is not None else "-",
                            "photo_path": d.photo_path or "",
                        }
                        for d in log.details.all()
                    ],
                })

        else:  # ng
            qs = InspectionNGLog.objects.select_related(
                "machine", "item"
            ).prefetch_related(
                Prefetch(
                    "details",
                    queryset=InspectionNGLogDetail.objects.select_related(
                        "detection_object", "defect_mode"
                    ),
                )
            )
            if q:
                qs = qs.filter(
                    Q(kanban_qr__icontains=q)
                    | Q(item_qr__icontains=q)
                    | Q(item__part_name__icontains=q)
                    | Q(item__sd_code__icontains=q)
                    | Q(machine__machine_no__icontains=q)
                    | Q(machine__machine_name__icontains=q)
                )
            if machine_id:
                qs = qs.filter(machine_id=machine_id)
            if date_from:
                qs = qs.filter(inspected_at__date__gte=date_from)
            if date_to:
                qs = qs.filter(inspected_at__date__lte=date_to)

            qs = qs.order_by("-inspected_at")
            paginator = Paginator(qs, per_page)
            page_obj = paginator.get_page(page)

            rows = []
            for log in page_obj.object_list:
                rows.append({
                    "id": str(log.id),
                    "inspected_at": log.inspected_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "machine_no": log.machine.machine_no,
                    "machine_name": log.machine.machine_name,
                    "sd_code": log.item.sd_code or "",
                    "part_name": log.item.part_name or "",
                    "kanban_qr": log.kanban_qr,
                    "item_qr": log.item_qr,
                    "photo_path": log.photo_path or "",
                    "details": [
                        {
                            "object_name": d.detection_object.name,
                            "camera_number": d.camera_number,
                            "object_found": d.object_found,
                            "object_count": d.object_count,
                            "expected_count": d.expected_count,
                            "defect_mode": d.defect_mode.name_th if d.defect_mode else "-",
                            "confidence": f"{d.confidence:.2f}" if d.confidence is not None else "-",
                            "photo_path": d.photo_path or "",
                        }
                        for d in log.details.all()
                    ],
                })

        ctx["tab"] = tab
        ctx["q"] = q
        ctx["machine_id"] = machine_id
        ctx["date_from"] = date_from
        ctx["date_to"] = date_to
        ctx["rows"] = rows
        ctx["page_obj"] = page_obj
        ctx["paginator"] = paginator
        ctx["per_page"] = per_page
        ctx["page_items"] = _page_items(paginator.num_pages, page_obj.number)
        ctx["total_count"] = paginator.count
        ctx["machines_list"] = list(
            Machine.objects.order_by("machine_no").values("id", "machine_no", "machine_name")
        )
        ctx["nav_counts"] = {
            "ok": InspectionOKLog.objects.count(),
            "ng": InspectionNGLog.objects.count(),
        }
        return ctx
