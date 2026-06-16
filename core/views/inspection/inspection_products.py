from __future__ import annotations

import uuid

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.views.generic import TemplateView
from django.shortcuts import redirect

from core.models.inspection.inspection_products import InspectionProducts


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


class InspectionProductsView(TemplateView):
    template_name = "core/inspection/inspection_products.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request

        q = (request.GET.get("q") or "").strip()
        per_page_raw = (request.GET.get("per_page") or "").strip()
        page = (request.GET.get("page") or "1").strip() or "1"

        allowed_per_page = {100, 200, 500, 1000}

        try:
            per_page = int(per_page_raw or 100)
        except Exception:
            per_page = 100

        if per_page not in allowed_per_page:
            per_page = 100

        qs = InspectionProducts.objects.all()

        if q:
            qs = qs.filter(
                Q(sd_code__icontains=q) |
                Q(work_qr__icontains=q)
            )

        qs = qs.order_by("-created_at")

        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)

        rows = []

        for obj in page_obj.object_list:
            rows.append({
                "id": str(obj.id),
                "sd_code": obj.sd_code,
                "work_qr": obj.work_qr,
                "qtt_box": obj.qtt_box,
                "products_path_image": obj.products_path_image,
            })

        ctx["rows"] = rows
        ctx["q"] = q
        ctx["page_obj"] = page_obj
        ctx["paginator"] = paginator
        ctx["per_page"] = per_page
        ctx["rows_total"] = paginator.count
        ctx["page_items"] = _page_items(paginator.num_pages, page_obj.number)
        ctx["total_count"] = paginator.count

        return ctx

    def post(self, request, *args, **kwargs):

        action = (request.POST.get("action") or "").strip().lower()

        obj_id = (request.POST.get("id") or "").strip()
        sd_code = (request.POST.get("sd_code") or "").strip()
        work_qr = (request.POST.get("work_qr") or "").strip()
        qtt_box = (request.POST.get("qtt_box") or "0").strip()
        products_path_image = (request.POST.get("products_path_image") or "").strip()

        try:
            qtt_box = int(qtt_box)
        except Exception:
            qtt_box = 0

        # ================= CREATE =================
        if action == "create":

            if not sd_code:
                messages.error(request, "กรุณากรอก SD Code")
                return redirect(request.get_full_path())
            try:
                with transaction.atomic():

                    InspectionProducts.objects.create(
                        sd_code=sd_code,
                        work_qr=work_qr,
                        qtt_box=qtt_box,
                        products_path_image=products_path_image,
                    )

                messages.success(request, "เพิ่มข้อมูลสำเร็จ")

            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")

            return redirect(request.get_full_path())
        # ================= UPDATE =================
        if action == "update":

            if not _is_uuid(obj_id):
                messages.error(request, "ไม่พบรหัสรายการ")
                return redirect(request.get_full_path())
            try:
                with transaction.atomic():

                    obj = InspectionProducts.objects.get(pk=obj_id)

                    obj.sd_code = sd_code
                    obj.work_qr = work_qr
                    obj.qtt_box = qtt_box
                    obj.products_path_image = products_path_image  # ✅ เพิ่ม

                    obj.save()

                messages.success(request, "แก้ไขสำเร็จ")

            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")

            return redirect(request.get_full_path())
        # ================= DELETE =================
        if action == "delete":

            if not _is_uuid(obj_id):
                messages.error(request, "ไม่พบรหัสรายการ")
                return redirect(request.get_full_path())
            try:
                with transaction.atomic():

                    obj = InspectionProducts.objects.get(pk=obj_id)
                    obj.delete()

                messages.success(request, "ลบสำเร็จ")

            except ProtectedError:
                messages.error(request, "ลบไม่ได้ มีข้อมูลอ้างอิงอยู่")

            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")

            return redirect(request.get_full_path())
        messages.error(request, "ไม่รู้จัก action")
        return redirect(request.get_full_path())