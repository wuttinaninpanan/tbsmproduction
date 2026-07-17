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
from core.models.defect_mode import DefectMode
from core.models.inspection.inspection_model import InspectionModels
from core.models import User


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
class DefectModeView(TemplateView):
    template_name = "core/inspection/defect_mode.html"

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

        qs = DefectMode.objects.select_related("inspection_model")
        if q:
            qs = qs.filter(
                Q(name_th__icontains=q)
                | Q(name_en__icontains=q)
                | Q(name_jp__icontains=q)
                | Q(class_name__icontains=q)
                | Q(inspection_model__class_name__icontains=q)
            )
        qs = qs.order_by("name_th")

        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)

        ctx["rows"] = [
            {
                "id": str(o.id),
                "name_th": o.name_th,
                "name_en": o.name_en,
                "name_jp": o.name_jp,
                "defect_type": o.defect_type or "",
                "defect_type_display": o.get_defect_type_display() if o.defect_type else "-",
                "class_name": o.class_name,
                "model_id": str(o.inspection_model_id) if o.inspection_model_id else "",
                "model_class": o.inspection_model.class_name if o.inspection_model_id else "-",
            }
            for o in page_obj.object_list
        ]
        ctx.update(q=q, page_obj=page_obj, paginator=paginator,
                   per_page=per_page, total_count=paginator.count,
                   page_items=_page_items(paginator.num_pages, page_obj.number))
        ctx["models_list"] = list(InspectionModels.objects.order_by("class_name").values("id", "class_name"))
        ctx["defect_type_choices"] = DefectMode.DefectType.choices
        return ctx

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip().lower()
        obj_id = (request.POST.get("id") or "").strip()
        name_th = (request.POST.get("name_th") or "").strip()
        name_en = (request.POST.get("name_en") or "").strip()
        name_jp = (request.POST.get("name_jp") or "").strip()
        defect_type = (request.POST.get("defect_type") or "").strip() or None
        class_name = (request.POST.get("class_name") or "").strip()
        model_id = (request.POST.get("model_id") or "").strip()

        insp_model = InspectionModels.objects.filter(pk=model_id).first() if model_id else None

        if action == "create":
            if not name_th:
                messages.error(request, "กรุณากรอกชื่อภาษาไทย")
                return redirect(request.get_full_path())
            if not name_en:
                messages.error(request, "กรุณากรอกชื่อภาษาอังกฤษ")
                return redirect(request.get_full_path())
            try:
                with transaction.atomic():
                    DefectMode.objects.create(
                        name_th=name_th, name_en=name_en, name_jp=name_jp,
                        defect_type=defect_type, class_name=class_name,
                        inspection_model=insp_model, user=request.user,
                    )
                messages.success(request, "เพิ่ม Defect Mode สำเร็จ")
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
            return redirect(request.get_full_path())

        if action == "update":
            if not name_th:
                messages.error(request, "กรุณากรอกชื่อภาษาไทย")
                return redirect(request.get_full_path())
            if not name_en:
                messages.error(request, "กรุณากรอกชื่อภาษาอังกฤษ")
                return redirect(request.get_full_path())
            try:
                with transaction.atomic():
                    o = DefectMode.objects.get(pk=obj_id)
                    o.name_th = name_th
                    o.name_en = name_en
                    o.name_jp = name_jp
                    o.defect_type = defect_type
                    o.class_name = class_name
                    o.inspection_model = insp_model
                    o.save()
                messages.success(request, "บันทึกการแก้ไขสำเร็จ")
            except DefectMode.DoesNotExist:
                messages.error(request, "ไม่พบรายการนี้")
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
            return redirect(request.get_full_path())

        if action == "delete":
            try:
                with transaction.atomic():
                    DefectMode.objects.get(pk=obj_id).delete()
                messages.success(request, "ลบสำเร็จ")
            except DefectMode.DoesNotExist:
                messages.error(request, "ไม่พบรายการนี้")
            except ProtectedError:
                messages.error(request, "ลบไม่ได้ มีข้อมูลอ้างอิงอยู่")
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
            return redirect(request.get_full_path())

        messages.error(request, "ไม่รู้จัก action")
        return redirect(request.get_full_path())
