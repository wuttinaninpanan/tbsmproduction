from __future__ import annotations

import uuid

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.views.generic import TemplateView
from django.shortcuts import redirect

from core.models import User
from core.models.department import Department
from core.models.inspection.machine import Machine
from core.models.item_category import ItemCategory
from core.models.line import Line


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
    except Exception:
        return False
    return True


def _user_label(user) -> str:
    if user is None:
        return ""
    full = (f"{user.first_name} {user.last_name}").strip()
    if full:
        return f"{full} ({user.username})"
    return user.username


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


class MachineLineView(TemplateView):
    template_name = "inspection/machine_line.html"

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

        qs = Machine.objects.select_related(
            "res_dept", "responsible1", "responsible2", "line", "category"
        )

        if q:
            qs = qs.filter(
                Q(machine_no__icontains=q)
                | Q(machine_name__icontains=q)
                | Q(machine_type__icontains=q)
                | Q(category__name__icontains=q)
                | Q(res_dept__name__icontains=q)
                | Q(responsible1__first_name__icontains=q)
                | Q(responsible1__username__icontains=q)
                | Q(responsible2__first_name__icontains=q)
                | Q(responsible2__username__icontains=q)
            )

        qs = qs.order_by("machine_no")

        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)

        rows = []
        for obj in page_obj.object_list:
            rows.append({
                "id": str(obj.id),
                "machine_no": obj.machine_no,
                "machine_name": obj.machine_name,
                "machine_detail": obj.machine_detail or "",
                "res_dept_id": str(obj.res_dept_id) if obj.res_dept_id else "",
                "res_dept_name": obj.res_dept.name if obj.res_dept_id else "",
                "responsible1_id": str(obj.responsible1_id) if obj.responsible1_id else "",
                "responsible1_name": _user_label(obj.responsible1) if obj.responsible1_id else "",
                "responsible2_id": str(obj.responsible2_id) if obj.responsible2_id else "",
                "responsible2_name": _user_label(obj.responsible2) if obj.responsible2_id else "",
                "is_approved": obj.is_approved,
                "line_id": str(obj.line_id) if obj.line_id else "",
                "line_name": obj.line.line_name if obj.line_id else "",
                "machine_type": obj.machine_type or "",
                "category_id": str(obj.category_id) if obj.category_id else "",
                "category_name": obj.category.name if obj.category_id else "",
            })

        ctx["rows"] = rows
        ctx["q"] = q
        ctx["page_obj"] = page_obj
        ctx["paginator"] = paginator
        ctx["per_page"] = per_page
        ctx["rows_total"] = paginator.count
        ctx["page_items"] = _page_items(paginator.num_pages, page_obj.number)
        ctx["total_count"] = paginator.count

        ctx["lines_list"] = list(
            Line.objects.order_by("line_name").values("id", "line_name")
        )
        ctx["departments_list"] = list(
            Department.objects.order_by("name").values("id", "name")
        )
        ctx["categories_list"] = list(
            ItemCategory.objects.order_by("name").values("id", "name")
        )
        ctx["users_list"] = [
            {"id": str(u.id), "label": _user_label(u)}
            for u in User.objects.order_by("first_name", "username")
        ]

        return ctx

    def _resolve_fk(self, raw: str, model):
        """แปลง id (string) -> instance หรือ None"""
        raw = (raw or "").strip()
        if not _is_uuid(raw):
            return None
        return model.objects.filter(pk=raw).first()

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip().lower()

        obj_id = (request.POST.get("id") or "").strip()
        machine_no = (request.POST.get("machine_no") or "").strip()
        machine_name = (request.POST.get("machine_name") or "").strip()
        machine_detail = (request.POST.get("machine_detail") or "").strip()
        res_dept = self._resolve_fk(request.POST.get("res_dept"), Department)
        responsible1 = self._resolve_fk(request.POST.get("responsible1"), User)
        responsible2 = self._resolve_fk(request.POST.get("responsible2"), User)
        is_approved = str(request.POST.get("is_approved")).lower() == "true"
        line = self._resolve_fk(request.POST.get("line_id"), Line)
        machine_type = (request.POST.get("machine_type") or "").strip()
        category = self._resolve_fk(request.POST.get("category"), ItemCategory)

        # ================= CREATE =================
        if action == "create":
            if not machine_no:
                messages.error(request, "กรุณากรอกรหัสเครื่อง (Machine No)")
                return redirect(request.get_full_path())
            if not machine_name:
                messages.error(request, "กรุณากรอกชื่อเครื่อง (Machine Name)")
                return redirect(request.get_full_path())
            try:
                with transaction.atomic():
                    Machine.objects.create(
                        machine_no=machine_no,
                        machine_name=machine_name,
                        machine_detail=machine_detail,
                        res_dept=res_dept,
                        responsible1=responsible1,
                        responsible2=responsible2,
                        is_approved=is_approved,
                        line=line,
                        machine_type=machine_type,
                        category=category,
                    )

                messages.success(request, "เพิ่มเครื่องสำเร็จ")

            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")

            return redirect(request.get_full_path())
        # ================= UPDATE =================
        if action == "update":
            if not _is_uuid(obj_id):
                messages.error(request, "ไม่พบรหัสรายการ")
                return redirect(request.get_full_path())
            if not machine_no:
                messages.error(request, "กรุณากรอกรหัสเครื่อง (Machine No)")
                return redirect(request.get_full_path())
            if not machine_name:
                messages.error(request, "กรุณากรอกชื่อเครื่อง (Machine Name)")
                return redirect(request.get_full_path())
            try:
                with transaction.atomic():
                    machine = Machine.objects.get(pk=obj_id)
                    machine.machine_no = machine_no
                    machine.machine_name = machine_name
                    machine.machine_detail = machine_detail
                    machine.res_dept = res_dept
                    machine.responsible1 = responsible1
                    machine.responsible2 = responsible2
                    machine.is_approved = is_approved
                    machine.line = line
                    machine.machine_type = machine_type
                    machine.category = category
                    machine.save()

                messages.success(request, "บันทึกการแก้ไขสำเร็จ")

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
                    obj = Machine.objects.get(pk=obj_id)
                    obj.delete()

                messages.success(request, "ลบสำเร็จ")

            except ProtectedError:
                messages.error(request, "ลบไม่ได้ มีข้อมูลอ้างอิงอยู่")

            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")

            return redirect(request.get_full_path())

        messages.error(request, "ไม่รู้จัก action")
        return redirect(request.get_full_path())
