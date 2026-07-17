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
from core.models.inspection.object_detection import KanbanItemMapping
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
class KanbanItemMappingView(TemplateView):
    template_name = "core/inspection/kanban_item_mapping.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request

        q = (request.GET.get("q") or "").strip()
        per_page_raw = (request.GET.get("per_page") or "").strip()
        page = (request.GET.get("page") or "1").strip() or "1"

        try:
            per_page = int(per_page_raw or 50)
        except Exception:
            per_page = 50
        if per_page not in {50, 100, 200, 500}:
            per_page = 50

        qs = KanbanItemMapping.objects.select_related("item")

        if q:
            qs = qs.filter(
                Q(kanban_qr__icontains=q)
                | Q(item_qr__icontains=q)
                | Q(item__part_name__icontains=q)
                | Q(item__part_number__icontains=q)
                | Q(item__sku__icontains=q)
                | Q(item__sd_code__icontains=q)
            )

        qs = qs.order_by("kanban_qr")

        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)

        rows = []
        for obj in page_obj.object_list:
            rows.append({
                "id": str(obj.id),
                "kanban_qr": obj.kanban_qr,
                "item_qr": obj.item_qr,
                "item_id": str(obj.item_id),
                "item_label": f"{obj.item.sd_code or obj.item.sku} — {obj.item.part_name}" if obj.item else "-",
            })

        ctx["rows"] = rows
        ctx["q"] = q
        ctx["page_obj"] = page_obj
        ctx["paginator"] = paginator
        ctx["per_page"] = per_page
        ctx["total_count"] = paginator.count
        ctx["page_items"] = _page_items(paginator.num_pages, page_obj.number)
        ctx["items_list"] = list(
            Item_list.objects.filter(item_lines__isnull=False)
            .exclude(part_name="")
            .distinct()
            .order_by("sd_code", "sku")
            .values("id", "sd_code", "sku", "part_name", "part_number")
        )
        return ctx

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip().lower()
        obj_id = (request.POST.get("id") or "").strip()
        kanban_qr = (request.POST.get("kanban_qr") or "").strip()
        item_qr = (request.POST.get("item_qr") or "").strip()
        item_id = (request.POST.get("item_id") or "").strip()

        item = Item_list.objects.filter(pk=item_id).first() if item_id else None

        if action == "create":
            if not kanban_qr:
                messages.error(request, "กรุณากรอก Kanban QR")
                return redirect(request.get_full_path())
            if not item_qr:
                messages.error(request, "กรุณากรอก Item QR")
                return redirect(request.get_full_path())
            if not item:
                messages.error(request, "กรุณาเลือกชิ้นงาน (Item)")
                return redirect(request.get_full_path())
            try:
                with transaction.atomic():
                    KanbanItemMapping.objects.create(
                        kanban_qr=kanban_qr,
                        item_qr=item_qr,
                        item=item,
                    )
                messages.success(request, "เพิ่ม Kanban Mapping สำเร็จ")
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
            return redirect(request.get_full_path())

        if action == "update":
            if not kanban_qr:
                messages.error(request, "กรุณากรอก Kanban QR")
                return redirect(request.get_full_path())
            if not item_qr:
                messages.error(request, "กรุณากรอก Item QR")
                return redirect(request.get_full_path())
            if not item:
                messages.error(request, "กรุณาเลือกชิ้นงาน (Item)")
                return redirect(request.get_full_path())
            try:
                with transaction.atomic():
                    obj = KanbanItemMapping.objects.get(pk=obj_id)
                    obj.kanban_qr = kanban_qr
                    obj.item_qr = item_qr
                    obj.item = item
                    obj.save()
                messages.success(request, "บันทึกการแก้ไขสำเร็จ")
            except KanbanItemMapping.DoesNotExist:
                messages.error(request, "ไม่พบรายการนี้")
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
            return redirect(request.get_full_path())

        if action == "delete":
            try:
                with transaction.atomic():
                    KanbanItemMapping.objects.get(pk=obj_id).delete()
                messages.success(request, "ลบสำเร็จ")
            except KanbanItemMapping.DoesNotExist:
                messages.error(request, "ไม่พบรายการนี้")
            except ProtectedError:
                messages.error(request, "ลบไม่ได้ มีข้อมูลอ้างอิงอยู่")
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
            return redirect(request.get_full_path())

        messages.error(request, "ไม่รู้จัก action")
        return redirect(request.get_full_path())
