from __future__ import annotations

import uuid

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.utils.timezone import localtime

from core.auth.decorators import staff_required
from core.models.inspection.inspection_error import InspectionError


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

    items = [1]

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

    compressed = []
    for it in items:
        if compressed and compressed[-1] == it:
            continue
        if it is None and compressed and compressed[-1] is None:
            continue
        compressed.append(it)

    return compressed


@method_decorator(staff_required, name="dispatch")
class InspectionErrorView(TemplateView):

    template_name = "core/inspection/inspection_error.html"

    # ================= GET =================
    def get_context_data(self, **kwargs):

        ctx = super().get_context_data(**kwargs)
        request = self.request

        q = (request.GET.get("q") or "").strip()
        page = request.GET.get("page", 1)

        per_page = 100

        qs = (
            InspectionError.objects
            .select_related("inspectionitem", "inspection_line")
            .order_by("-created_at")
        )

        # 🔍 search (รองรับ UUID)
        if q and _is_uuid(q):
            qs = qs.filter(
                Q(id=q)
                | Q(inspectionitem_id=q)
                | Q(inspection_line_id=q)
            )

        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)

        rows = []

        for obj in page_obj:

            photo_url = None
            if obj.photo:
                try:
                    photo_url = obj.photo.url
                except Exception:
                    photo_url = None

            rows.append({
                "id": str(obj.id),
                "inspectionitem_id": str(obj.inspectionitem_id),
                "inspection_line_id": str(obj.inspection_line_id),
                "sd_code": getattr(obj.inspectionitem, "sd_code", ""),
                "line_name": getattr(obj.inspection_line, "line_name", ""),
                "qr_work": obj.qr_work,
                "result": obj.result,
                "photo_url": photo_url,
                "created_at": localtime(obj.created_at).strftime("%d/%m/%Y %H:%M:%S"),
            })

        ctx.update({
            "rows": rows,
            "page_obj": page_obj,
            "paginator": paginator,
            "rows_total": paginator.count,
            "page_items": _page_items(paginator.num_pages, page_obj.number),
        })

        return ctx

    # ================= POST =================
    def post(self, request, *args, **kwargs):

        action = (request.POST.get("action") or "").strip().lower()
        obj_id = (request.POST.get("id") or "").strip()

        # ================= BULK DELETE =================
        if action == "bulk_delete":

            bulk_ids = request.POST.getlist("bulk_id")
            ids = [x for x in [b.strip() for b in bulk_ids] if _is_uuid(x)]

            if not ids:
                messages.error(request, "กรุณาเลือกรายการที่ต้องการลบ")
                return redirect(request.path)

            deleted = blocked = 0

            try:
                with transaction.atomic():
                    for pk in ids:
                        obj = InspectionError.objects.filter(pk=pk).first()
                        if obj is None:
                            continue
                        try:
                            obj.delete()
                            deleted += 1
                        except ProtectedError:
                            blocked += 1

            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return redirect(request.path)

            if blocked:
                messages.warning(request, f"ลบสำเร็จ {deleted} รายการ, ลบไม่ได้ {blocked}")
            else:
                messages.success(request, f"ลบสำเร็จ {deleted} รายการ")

            return redirect(request.path)

        # ================= DELETE (single) =================
        if action == "delete":

            if not _is_uuid(obj_id):
                messages.error(request, "ไม่พบรหัสรายการ")
                return redirect(request.path)

            try:
                with transaction.atomic():
                    obj = InspectionError.objects.get(pk=obj_id)
                    obj.delete()

                messages.success(request, "ลบสำเร็จ")

            except InspectionError.DoesNotExist:
                messages.warning(request, "รายการนี้ถูกลบไปแล้ว")

            except ProtectedError:
                messages.error(request, "ลบไม่ได้ มีข้อมูลอ้างอิงอยู่")

            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")

            return redirect(request.path)

        # ================= UNKNOWN ACTION =================
        messages.error(request, "ไม่รู้จัก action")
        return redirect(request.path)