from __future__ import annotations

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.views.generic import TemplateView
from django.shortcuts import redirect

from core.models.inspection.object_detection import DetectionObject


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


class DetectionObjectView(TemplateView):
    template_name = "core/inspection/detection_object.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = (self.request.GET.get("q") or "").strip()
        per_page_raw = (self.request.GET.get("per_page") or "").strip()
        page = (self.request.GET.get("page") or "1").strip() or "1"

        try:
            per_page = int(per_page_raw or 50)
        except Exception:
            per_page = 50
        if per_page not in {50, 100, 200}:
            per_page = 50

        qs = DetectionObject.objects.all()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        qs = qs.order_by("name")

        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)

        ctx["rows"] = [
            {"id": str(o.id), "name": o.name, "description": o.description or ""}
            for o in page_obj.object_list
        ]
        ctx.update(q=q, page_obj=page_obj, paginator=paginator,
                   per_page=per_page, total_count=paginator.count,
                   page_items=_page_items(paginator.num_pages, page_obj.number))
        return ctx

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip().lower()
        obj_id = (request.POST.get("id") or "").strip()
        name = (request.POST.get("name") or "").strip()
        description = (request.POST.get("description") or "").strip()

        if action == "create":
            if not name:
                messages.error(request, "กรุณากรอกชื่อ Object")
                return redirect(request.get_full_path())
            try:
                with transaction.atomic():
                    DetectionObject.objects.create(name=name, description=description or None)
                messages.success(request, "เพิ่ม Detection Object สำเร็จ")
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
            return redirect(request.get_full_path())

        if action == "update":
            if not name:
                messages.error(request, "กรุณากรอกชื่อ Object")
                return redirect(request.get_full_path())
            try:
                with transaction.atomic():
                    obj = DetectionObject.objects.get(pk=obj_id)
                    obj.name = name
                    obj.description = description or None
                    obj.save()
                messages.success(request, "บันทึกการแก้ไขสำเร็จ")
            except DetectionObject.DoesNotExist:
                messages.error(request, "ไม่พบรายการนี้")
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
            return redirect(request.get_full_path())

        if action == "delete":
            try:
                with transaction.atomic():
                    DetectionObject.objects.get(pk=obj_id).delete()
                messages.success(request, "ลบสำเร็จ")
            except DetectionObject.DoesNotExist:
                messages.error(request, "ไม่พบรายการนี้")
            except ProtectedError:
                messages.error(request, "ลบไม่ได้ มีข้อมูลอ้างอิงอยู่")
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
            return redirect(request.get_full_path())

        messages.error(request, "ไม่รู้จัก action")
        return redirect(request.get_full_path())
