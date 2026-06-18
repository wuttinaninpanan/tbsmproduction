from __future__ import annotations

import uuid

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from core.auth.decorators import staff_required
from core.models.bill_of_material_item_master import BillOfMaterialItemMater
from core.models.contact_request import ContactMessage, PartRequest
from core.models.item_line import ItemLine
from core.services.auditlog import log_event


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
    except Exception:
        return False
    return True


@method_decorator(staff_required, name="dispatch")
class ManageRequestsViews(TemplateView):
    template_name = "core/manage_requests.html"

    VALID_TABS = {"bom", "line", "messages"}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request

        tab = (request.GET.get("tab") or "bom").strip().lower()
        if tab not in self.VALID_TABS:
            tab = "bom"
        status = (request.GET.get("status") or "PENDING").strip().upper()
        page = (request.GET.get("page") or "1").strip() or "1"

        if tab == "messages":
            qs = ContactMessage.objects.select_related("created_by").all()
            if status in {"NEW", "READ"}:
                qs = qs.filter(status=status)
            paginator = Paginator(qs, 50)
            page_obj = paginator.get_page(page)
            rows = [
                {
                    "id": str(m.id),
                    "name": m.name,
                    "email": m.email,
                    "message": m.message,
                    "status": m.status,
                    "status_label": m.get_status_display(),
                    "created_at": m.created_at,
                    "by": (m.created_by.get_full_name() or m.created_by.username) if m.created_by else "",
                }
                for m in page_obj.object_list
            ]
        else:
            rtype = PartRequest.Type.BOM_COMPONENT if tab == "bom" else PartRequest.Type.LINE_ITEM
            qs = PartRequest.objects.select_related(
                "requester", "bom", "bom__item", "component", "item", "line", "item_stage", "reviewed_by"
            ).filter(request_type=rtype)
            if status in {"PENDING", "APPROVED", "REJECTED"}:
                qs = qs.filter(status=status)
            paginator = Paginator(qs, 50)
            page_obj = paginator.get_page(page)
            rows = []
            for r in page_obj.object_list:
                row = {
                    "id": str(r.id),
                    "status": r.status,
                    "status_label": r.get_status_display(),
                    "note": r.note,
                    "review_note": r.review_note,
                    "created_at": r.created_at,
                    "requester": (r.requester.get_full_name() or r.requester.username) if r.requester else "",
                    "reviewed_by": (r.reviewed_by.get_full_name() or r.reviewed_by.username) if r.reviewed_by else "",
                    "reviewed_at": r.reviewed_at,
                }
                if tab == "bom":
                    row["bom"] = f"{r.bom.item.part_number} (Rev {r.bom.revision})" if r.bom else "(ถูกลบ)"
                    row["component"] = str(r.component) if r.component else "(ถูกลบ)"
                    row["quantity"] = r.quantity
                    row["unit"] = r.unit
                    row["sequence"] = r.sequence
                else:
                    row["item"] = str(r.item) if r.item else "(ถูกลบ)"
                    row["line"] = r.line.line_name if r.line else "(ถูกลบ)"
                    row["stage"] = r.item_stage.display_name if r.item_stage else "(ถูกลบ)"
                rows.append(row)

        ctx["tab"] = tab
        ctx["status"] = status
        ctx["rows"] = rows
        ctx["page_obj"] = page_obj
        ctx["paginator"] = paginator
        ctx["total_count"] = paginator.count
        ctx["pending_bom"] = PartRequest.objects.filter(
            request_type=PartRequest.Type.BOM_COMPONENT, status=PartRequest.Status.PENDING
        ).count()
        ctx["pending_line"] = PartRequest.objects.filter(
            request_type=PartRequest.Type.LINE_ITEM, status=PartRequest.Status.PENDING
        ).count()
        ctx["new_messages"] = ContactMessage.objects.filter(status=ContactMessage.Status.NEW).count()
        return ctx

    # ------------------------------------------------------------------
    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip().lower()
        obj_id = (request.POST.get("id") or "").strip()

        if action == "approve":
            return self._approve(request, obj_id)
        if action == "reject":
            return self._reject(request, obj_id)
        if action == "mark_read":
            return self._mark_read(request, obj_id)

        messages.error(request, "ไม่รู้จัก action")
        return redirect(request.get_full_path())

    # ------------------------------------------------------------------
    def _approve(self, request, obj_id):
        if not _is_uuid(obj_id):
            messages.error(request, "ไม่พบรหัสคำขอ")
            return redirect(request.get_full_path())

        req = PartRequest.objects.filter(pk=obj_id).first()
        if req is None:
            messages.error(request, "ไม่พบคำขอ")
            return redirect(request.get_full_path())
        if req.status != PartRequest.Status.PENDING:
            messages.warning(request, "คำขอนี้ถูกพิจารณาไปแล้ว")
            return redirect(request.get_full_path())

        try:
            with transaction.atomic():
                if req.request_type == PartRequest.Type.BOM_COMPONENT:
                    if req.bom is None or req.component is None:
                        messages.error(request, "BoM หรือพาร์ทถูกลบไปแล้ว ไม่สามารถอนุมัติได้")
                        return redirect(request.get_full_path())
                    if BillOfMaterialItemMater.objects.filter(bom=req.bom, component=req.component).exists():
                        messages.error(request, "พาร์ทนี้มีอยู่ใน BoM นี้แล้ว")
                        return redirect(request.get_full_path())
                    BillOfMaterialItemMater.objects.create(
                        bom=req.bom,
                        component=req.component,
                        quantity=req.quantity or 0,
                        unit=req.unit,
                        sequence=req.sequence or 1,
                        user=request.user,
                    )
                else:  # LINE_ITEM
                    if req.item is None or req.line is None or req.item_stage is None:
                        messages.error(request, "พาร์ท/ไลน์/Stage ถูกลบไปแล้ว ไม่สามารถอนุมัติได้")
                        return redirect(request.get_full_path())
                    if ItemLine.objects.filter(item=req.item, line=req.line).exists():
                        messages.error(request, "พาร์ทนี้ถูกผูกกับไลน์นี้อยู่แล้ว")
                        return redirect(request.get_full_path())
                    ItemLine.objects.create(
                        item=req.item,
                        line=req.line,
                        item_stage=req.item_stage,
                        user=request.user,
                    )

                req.status = PartRequest.Status.APPROVED
                req.reviewed_by = request.user
                req.reviewed_at = timezone.now()
                req.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])

            messages.success(request, "อนุมัติคำขอและเพิ่มข้อมูลเข้าระบบแล้ว")
            log_event(
                request,
                action="part_request:approve",
                message="อนุมัติคำขอ",
                metadata={"id": str(req.pk), "type": req.request_type},
            )
        except IntegrityError as e:
            messages.error(request, f"ข้อมูลซ้ำหรือไม่ถูกต้อง: {e}")
        except Exception as e:
            messages.error(request, f"เกิดข้อผิดพลาด: {e}")
        return redirect(request.get_full_path())

    # ------------------------------------------------------------------
    def _reject(self, request, obj_id):
        if not _is_uuid(obj_id):
            messages.error(request, "ไม่พบรหัสคำขอ")
            return redirect(request.get_full_path())
        review_note = (request.POST.get("review_note") or "").strip()

        req = PartRequest.objects.filter(pk=obj_id).first()
        if req is None:
            messages.error(request, "ไม่พบคำขอ")
            return redirect(request.get_full_path())
        if req.status != PartRequest.Status.PENDING:
            messages.warning(request, "คำขอนี้ถูกพิจารณาไปแล้ว")
            return redirect(request.get_full_path())

        try:
            req.status = PartRequest.Status.REJECTED
            req.review_note = review_note
            req.reviewed_by = request.user
            req.reviewed_at = timezone.now()
            req.save(update_fields=["status", "review_note", "reviewed_by", "reviewed_at", "updated_at"])
            messages.success(request, "ปฏิเสธคำขอแล้ว")
            log_event(
                request,
                action="part_request:reject",
                message="ปฏิเสธคำขอ",
                metadata={"id": str(req.pk), "type": req.request_type},
            )
        except Exception as e:
            messages.error(request, f"เกิดข้อผิดพลาด: {e}")
        return redirect(request.get_full_path())

    # ------------------------------------------------------------------
    def _mark_read(self, request, obj_id):
        if not _is_uuid(obj_id):
            messages.error(request, "ไม่พบรหัสข้อความ")
            return redirect(request.get_full_path())
        msg = ContactMessage.objects.filter(pk=obj_id).first()
        if msg is None:
            messages.error(request, "ไม่พบข้อความ")
            return redirect(request.get_full_path())
        new_status = (
            ContactMessage.Status.READ
            if msg.status == ContactMessage.Status.NEW
            else ContactMessage.Status.NEW
        )
        msg.status = new_status
        msg.save(update_fields=["status", "updated_at"])
        messages.success(request, "อัปเดตสถานะข้อความแล้ว")
        return redirect(request.get_full_path())
