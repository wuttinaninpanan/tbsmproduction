from __future__ import annotations

import uuid

from django.contrib import messages
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.timezone import localtime
from django.views.generic import TemplateView

from core.auth.decorators import staff_required, user_required
from core.models.manual import Manual
from core.services.html_sanitize import sanitize_manual_html


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
    except Exception:
        return False
    return True


def _can_manage(user) -> bool:
    return bool(user.is_authenticated and (user.is_staff or user.is_superuser))


def readable_qs(user):
    """คู่มือที่ผู้ใช้คนนี้เปิดอ่านได้.

    - ผู้จัดการ (staff/admin): เห็นทั้งหมด (รวมที่ปิดใช้งาน) เพื่อจัดการ
    - ผู้ใช้ทั่วไป: เฉพาะที่ active และ usefor เป็น ALL หรือ USER
    """
    if _can_manage(user):
        return Manual.objects.all()
    return Manual.objects.filter(
        is_active=True,
        usefor__in=[Manual.UseFor.ALL, Manual.UseFor.USER],
    )


@method_decorator(user_required, name="dispatch")
class ManualListView(TemplateView):
    """หน้ารวมคู่มือ — ทุกคนอ่านได้ (กรองตาม role); staff เห็นปุ่มเพิ่ม/แก้ไข/ลบ."""

    template_name = "core/manual_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        q = (self.request.GET.get("q") or "").strip()

        qs = readable_qs(user)
        if q:
            qs = qs.filter(title__icontains=q)
        qs = qs.order_by("usefor", "title")

        rows = []
        for m in qs:
            rows.append({
                "id": str(m.id),
                "title": m.title,
                "description": m.description,
                "usefor": m.usefor,
                "usefor_label": m.get_usefor_display(),
                "is_active": m.is_active,
                "created_at": localtime(m.created_at).strftime("%d/%m/%Y") if m.created_at else "",
            })

        ctx["rows"] = rows
        ctx["q"] = q
        ctx["total_count"] = len(rows)
        ctx["can_manage"] = _can_manage(user)
        return ctx

    def post(self, request, *args, **kwargs):
        # ลบ — staff/admin เท่านั้น
        if not _can_manage(request.user):
            messages.error(request, "คุณไม่มีสิทธิ์ดำเนินการนี้")
            return redirect(reverse("manual_list"))

        action = (request.POST.get("action") or "").strip().lower()
        obj_id = (request.POST.get("id") or "").strip()
        if action == "delete" and _is_uuid(obj_id):
            with transaction.atomic():
                Manual.objects.filter(pk=obj_id).delete()
            messages.success(request, "ลบคู่มือสำเร็จ")
        else:
            messages.error(request, "ไม่รู้จัก action หรือไม่พบรายการ")
        return redirect(reverse("manual_list"))


@method_decorator(user_required, name="dispatch")
class ManualDetailView(TemplateView):
    """อ่านคู่มือ 1 เรื่อง + ปุ่ม Export PDF (client-side)."""

    template_name = "core/manual_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        manual_id = self.kwargs.get("id")

        manual = readable_qs(user).filter(pk=manual_id).first()
        if manual is None:
            raise Http404("ไม่พบคู่มือ หรือคุณไม่มีสิทธิ์เข้าถึง")

        # Sanitize at render too, so manuals stored before on-save sanitization
        # was introduced are also safe. Not persisted — just the value shown.
        manual.detail = sanitize_manual_html(manual.detail)
        ctx["manual"] = manual
        ctx["can_manage"] = _can_manage(user)
        return ctx


@method_decorator(staff_required, name="dispatch")
class ManualFormView(TemplateView):
    """สร้าง/แก้ไขคู่มือด้วย WYSIWYG — staff/admin เท่านั้น."""

    template_name = "core/manual_form.html"

    def _get_object(self):
        manual_id = self.kwargs.get("id")
        if manual_id is None:
            return None
        manual = Manual.objects.filter(pk=manual_id).first()
        if manual is None:
            raise Http404("ไม่พบคู่มือ")
        return manual

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["manual"] = self._get_object()
        ctx["usefor_choices"] = Manual.UseFor.choices
        return ctx

    def post(self, request, *args, **kwargs):
        manual = self._get_object()

        title = (request.POST.get("title") or "").strip()
        description = (request.POST.get("description") or "").strip()
        raw_detail = request.POST.get("detail") or ""   # HTML ดิบจาก WYSIWYG
        usefor = (request.POST.get("usefor") or "").strip().upper()
        is_active = str(request.POST.get("is_active")).lower() == "true"

        valid = {c[0] for c in Manual.UseFor.choices}
        if usefor not in valid:
            usefor = Manual.UseFor.ALL

        if not title:
            messages.error(request, "กรุณากรอกหัวข้อคู่มือ")
            return redirect(request.get_full_path())

        # ตรวจ blob: บน HTML ดิบก่อน (sanitize จะตัด blob: ทิ้ง ทำให้ตรวจไม่เจอ)
        if "blob:" in raw_detail:
            messages.error(
                request,
                "บันทึกรูปภาพไม่สำเร็จ: กรุณาแทรกรูปใหม่อีกครั้ง แล้วกดบันทึก",
            )
            return redirect(request.get_full_path())

        # staff เป็นผู้เขียน แต่ยัง sanitize กัน stored XSS
        detail = sanitize_manual_html(raw_detail)

        try:
            with transaction.atomic():
                if manual is None:
                    manual = Manual.objects.create(
                        title=title,
                        description=description,
                        detail=detail,
                        usefor=usefor,
                        is_active=is_active,
                        created_by=request.user if request.user.is_authenticated else None,
                    )
                    messages.success(request, "สร้างคู่มือสำเร็จ")
                else:
                    manual.title = title
                    manual.description = description
                    manual.detail = detail
                    manual.usefor = usefor
                    manual.is_active = is_active
                    manual.save()
                    messages.success(request, "บันทึกการแก้ไขสำเร็จ")
        except Exception as e:
            messages.error(request, f"เกิดข้อผิดพลาด: {e}")
            return redirect(request.get_full_path())

        return redirect(reverse("manual_detail", kwargs={"id": manual.id}))
