from __future__ import annotations

import uuid

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.timezone import localtime
from django.views.generic import TemplateView

from core.auth.decorators import staff_required
from core.models.email_receiver import EmailReceiver
from core.services.report_email import send_report_to_receiver


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


@method_decorator(staff_required, name="dispatch")
class EmailReceiverView(TemplateView):
    """ตั้งค่าผู้รับอีเมลรายงานอัตโนมัติ (CRUD) + ปุ่มส่งทดสอบทันที."""

    template_name = "core/email_receiver.html"

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

        qs = EmailReceiver.objects.all()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q))
        qs = qs.order_by("name")

        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)

        rows = []
        for obj in page_obj.object_list:
            rows.append({
                "id": str(obj.id),
                "name": obj.name,
                "email": obj.email,
                "frequency": obj.frequency,
                "frequency_label": obj.get_frequency_display(),
                "send_production_report": obj.send_production_report,
                "send_inspection_report": obj.send_inspection_report,
                "is_active": obj.is_active,
                "last_sent_at": localtime(obj.last_sent_at).strftime("%d/%m/%Y %H:%M") if obj.last_sent_at else "",
            })

        ctx["rows"] = rows
        ctx["q"] = q
        ctx["page_obj"] = page_obj
        ctx["paginator"] = paginator
        ctx["per_page"] = per_page
        ctx["rows_total"] = paginator.count
        ctx["total_count"] = paginator.count
        ctx["page_items"] = _page_items(paginator.num_pages, page_obj.number)
        ctx["frequency_choices"] = EmailReceiver.Frequency.choices
        return ctx

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip().lower()

        obj_id = (request.POST.get("id") or "").strip()
        name = (request.POST.get("name") or "").strip()
        email = (request.POST.get("email") or "").strip()
        frequency = (request.POST.get("frequency") or "").strip().upper()
        send_production = str(request.POST.get("send_production_report")).lower() == "true"
        send_inspection = str(request.POST.get("send_inspection_report")).lower() == "true"
        is_active = str(request.POST.get("is_active")).lower() == "true"

        valid_freqs = {c[0] for c in EmailReceiver.Frequency.choices}
        if action in {"create", "update"} and frequency not in valid_freqs:
            frequency = EmailReceiver.Frequency.DAILY

        # ================= CREATE =================
        if action == "create":
            if not name:
                messages.error(request, "กรุณากรอกชื่อผู้รับ")
                return redirect(request.get_full_path())
            if not email:
                messages.error(request, "กรุณากรอกอีเมล")
                return redirect(request.get_full_path())
            if not (send_production or send_inspection):
                messages.error(request, "กรุณาเลือกข้อมูลที่จะส่งอย่างน้อย 1 อย่าง")
                return redirect(request.get_full_path())
            try:
                with transaction.atomic():
                    EmailReceiver.objects.create(
                        name=name,
                        email=email,
                        frequency=frequency,
                        send_production_report=send_production,
                        send_inspection_report=send_inspection,
                        is_active=is_active,
                        created_by=request.user if request.user.is_authenticated else None,
                    )
                messages.success(request, "เพิ่มผู้รับอีเมลสำเร็จ")
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
            return redirect(request.get_full_path())

        # ================= UPDATE =================
        if action == "update":
            if not _is_uuid(obj_id):
                messages.error(request, "ไม่พบรหัสรายการ")
                return redirect(request.get_full_path())
            if not name:
                messages.error(request, "กรุณากรอกชื่อผู้รับ")
                return redirect(request.get_full_path())
            if not email:
                messages.error(request, "กรุณากรอกอีเมล")
                return redirect(request.get_full_path())
            if not (send_production or send_inspection):
                messages.error(request, "กรุณาเลือกข้อมูลที่จะส่งอย่างน้อย 1 อย่าง")
                return redirect(request.get_full_path())
            try:
                with transaction.atomic():
                    obj = EmailReceiver.objects.get(pk=obj_id)
                    obj.name = name
                    obj.email = email
                    obj.frequency = frequency
                    obj.send_production_report = send_production
                    obj.send_inspection_report = send_inspection
                    obj.is_active = is_active
                    obj.save()
                messages.success(request, "บันทึกการแก้ไขสำเร็จ")
            except EmailReceiver.DoesNotExist:
                messages.error(request, "ไม่พบรายการ")
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
                    EmailReceiver.objects.filter(pk=obj_id).delete()
                messages.success(request, "ลบสำเร็จ")
            except ProtectedError:
                messages.error(request, "ลบไม่ได้ มีข้อมูลอ้างอิงอยู่")
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
            return redirect(request.get_full_path())

        # ================= SEND NOW (ทดสอบ) =================
        if action == "send_now":
            if not _is_uuid(obj_id):
                messages.error(request, "ไม่พบรหัสรายการ")
                return redirect(request.get_full_path())
            obj = EmailReceiver.objects.filter(pk=obj_id).first()
            if obj is None:
                messages.error(request, "ไม่พบรายการ")
                return redirect(request.get_full_path())
            try:
                # ปุ่ม "ส่งทดสอบ" — ไม่อัปเดต last_sent_at เพื่อไม่ให้บังรอบส่งอัตโนมัติของวันนั้น
                res = send_report_to_receiver(obj, ref_date=timezone.localdate(), mark_sent=False)
                messages.success(
                    request,
                    f"ส่งอีเมลให้ {res['email']} สำเร็จ ({', '.join(res['attachments'])})",
                )
            except Exception as e:
                messages.error(request, f"ส่งไม่สำเร็จ: {e}")
            return redirect(request.get_full_path())

        messages.error(request, "ไม่รู้จัก action")
        return redirect(request.get_full_path())
