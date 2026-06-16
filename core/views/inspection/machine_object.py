from __future__ import annotations

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.views.generic import TemplateView
from django.shortcuts import redirect

from core.models.inspection.object_detection import MachineObject, DetectionObject
from core.models.inspection.machine import Machine


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


class MachineObjectView(TemplateView):
    template_name = "core/inspection/machine_object.html"

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

        qs = MachineObject.objects.select_related("machine", "object")
        if q:
            qs = qs.filter(
                Q(machine__machine_no__icontains=q)
                | Q(machine__machine_name__icontains=q)
                | Q(object__name__icontains=q)
            )
        qs = qs.order_by("machine__machine_no", "object__name")

        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)

        ctx["rows"] = [
            {
                "id": str(o.id),
                "machine_id": str(o.machine_id),
                "machine_label": f"{o.machine.machine_no} — {o.machine.machine_name}",
                "object_id": str(o.object_id),
                "object_name": o.object.name,
            }
            for o in page_obj.object_list
        ]
        ctx.update(q=q, page_obj=page_obj, paginator=paginator,
                   per_page=per_page, total_count=paginator.count,
                   page_items=_page_items(paginator.num_pages, page_obj.number))
        ctx["machines_list"] = list(
            Machine.objects.order_by("machine_no").values("id", "machine_no", "machine_name")
        )
        ctx["objects_list"] = list(DetectionObject.objects.order_by("name").values("id", "name"))
        return ctx

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip().lower()
        obj_id = (request.POST.get("id") or "").strip()
        machine_id = (request.POST.get("machine_id") or "").strip()
        object_id = (request.POST.get("object_id") or "").strip()

        machine = Machine.objects.filter(pk=machine_id).first() if machine_id else None
        det_obj = DetectionObject.objects.filter(pk=object_id).first() if object_id else None

        if action == "create":
            if not machine:
                messages.error(request, "กรุณาเลือกเครื่อง (Machine)")
                return redirect(request.get_full_path())
            if not det_obj:
                messages.error(request, "กรุณาเลือก Detection Object")
                return redirect(request.get_full_path())
            try:
                with transaction.atomic():
                    MachineObject.objects.create(machine=machine, object=det_obj)
                messages.success(request, "เพิ่ม Machine Object สำเร็จ")
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
            return redirect(request.get_full_path())

        if action == "update":
            if not machine:
                messages.error(request, "กรุณาเลือกเครื่อง (Machine)")
                return redirect(request.get_full_path())
            if not det_obj:
                messages.error(request, "กรุณาเลือก Detection Object")
                return redirect(request.get_full_path())
            try:
                with transaction.atomic():
                    o = MachineObject.objects.get(pk=obj_id)
                    o.machine = machine
                    o.object = det_obj
                    o.save()
                messages.success(request, "บันทึกการแก้ไขสำเร็จ")
            except MachineObject.DoesNotExist:
                messages.error(request, "ไม่พบรายการนี้")
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
            return redirect(request.get_full_path())

        if action == "delete":
            try:
                with transaction.atomic():
                    MachineObject.objects.get(pk=obj_id).delete()
                messages.success(request, "ลบสำเร็จ")
            except MachineObject.DoesNotExist:
                messages.error(request, "ไม่พบรายการนี้")
            except ProtectedError:
                messages.error(request, "ลบไม่ได้ มีข้อมูลอ้างอิงอยู่")
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
            return redirect(request.get_full_path())

        messages.error(request, "ไม่รู้จัก action")
        return redirect(request.get_full_path())
