from __future__ import annotations

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.shortcuts import redirect

from core.auth.decorators import staff_required
from core.models.inspection.object_detection import ItemObject, DetectionObject
from core.models.item_list import Item_list


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
class ItemObjectView(TemplateView):
    template_name = "core/inspection/item_object.html"

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

        qs = ItemObject.objects.select_related("item", "object")
        if q:
            qs = qs.filter(
                Q(item__part_name__icontains=q)
                | Q(item__sd_code__icontains=q)
                | Q(item__sku__icontains=q)
                | Q(object__name__icontains=q)
            )
        qs = qs.order_by("object__name", "item__sd_code")

        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)

        ctx["rows"] = [
            {
                "id": str(o.id),
                "object_id": str(o.object_id),
                "object_name": o.object.name,
                "item_id": str(o.item_id),
                "item_label": f"{o.item.sd_code or o.item.sku} — {o.item.part_name}",
                "quantity": o.quantity,
            }
            for o in page_obj.object_list
        ]
        ctx.update(q=q, page_obj=page_obj, paginator=paginator,
                   per_page=per_page, total_count=paginator.count,
                   page_items=_page_items(paginator.num_pages, page_obj.number))
        ctx["objects_list"] = list(DetectionObject.objects.order_by("name").values("id", "name"))
        ctx["items_list"] = list(
            Item_list.objects.exclude(part_name="")
            .order_by("sd_code", "sku")
            .values("id", "sd_code", "sku", "part_name")
        )
        return ctx

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip().lower()
        obj_id = (request.POST.get("id") or "").strip()
        object_id = (request.POST.get("object_id") or "").strip()
        item_id = (request.POST.get("item_id") or "").strip()
        try:
            quantity = int(request.POST.get("quantity") or 1)
        except Exception:
            quantity = 1

        det_obj = DetectionObject.objects.filter(pk=object_id).first() if object_id else None
        item = Item_list.objects.filter(pk=item_id).first() if item_id else None

        if action == "create":
            if not det_obj:
                messages.error(request, "กรุณาเลือก Detection Object")
                return redirect(request.get_full_path())
            if not item:
                messages.error(request, "กรุณาเลือกชิ้นงาน (Item)")
                return redirect(request.get_full_path())
            try:
                with transaction.atomic():
                    ItemObject.objects.create(object=det_obj, item=item, quantity=quantity)
                messages.success(request, "เพิ่ม Item Object สำเร็จ")
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
            return redirect(request.get_full_path())

        if action == "update":
            if not det_obj:
                messages.error(request, "กรุณาเลือก Detection Object")
                return redirect(request.get_full_path())
            if not item:
                messages.error(request, "กรุณาเลือกชิ้นงาน (Item)")
                return redirect(request.get_full_path())
            try:
                with transaction.atomic():
                    o = ItemObject.objects.get(pk=obj_id)
                    o.object = det_obj
                    o.item = item
                    o.quantity = quantity
                    o.save()
                messages.success(request, "บันทึกการแก้ไขสำเร็จ")
            except ItemObject.DoesNotExist:
                messages.error(request, "ไม่พบรายการนี้")
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
            return redirect(request.get_full_path())

        if action == "delete":
            try:
                with transaction.atomic():
                    ItemObject.objects.get(pk=obj_id).delete()
                messages.success(request, "ลบสำเร็จ")
            except ItemObject.DoesNotExist:
                messages.error(request, "ไม่พบรายการนี้")
            except ProtectedError:
                messages.error(request, "ลบไม่ได้ มีข้อมูลอ้างอิงอยู่")
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
            return redirect(request.get_full_path())

        messages.error(request, "ไม่รู้จัก action")
        return redirect(request.get_full_path())
