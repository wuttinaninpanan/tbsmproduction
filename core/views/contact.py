from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView

from core.auth.decorators import user_required
from core.models.bill_of_material import BillOfMaterial
from core.models.contact_request import ContactMessage, PartRequest
from core.models.item_list import Item_list
from core.models.item_stage import ItemStage
from core.models.line import Line
from core.services.auditlog import log_event


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
    except Exception:
        return False
    return True


class ContactViews(TemplateView):
    template_name = "core/contact.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Items, BoMs and lines are searched on-demand via the autocomplete
        # endpoint, so we only ship the small stage lookup here.
        if self.request.user.is_authenticated:
            ctx["stages"] = list(
                ItemStage.objects.order_by("display_name").values("id", "display_name")
            )
        return ctx

    # ------------------------------------------------------------------
    def post(self, request, *args, **kwargs):
        form_type = (request.POST.get("form_type") or "general").strip().lower()

        if form_type == "general":
            return self._handle_general(request)
        if form_type == "bom_component":
            return self._handle_bom_component(request)
        if form_type == "line_item":
            return self._handle_line_item(request)

        messages.error(request, "ไม่รู้จักประเภทฟอร์ม")
        return redirect("/contact/")

    # ------------------------------------------------------------------
    def _handle_general(self, request):
        name = (request.POST.get("name") or "").strip()
        email = (request.POST.get("email") or "").strip()
        message = (request.POST.get("message") or "").strip()

        if not name or not message:
            messages.error(request, "กรุณากรอกชื่อและข้อความ")
            return redirect("/contact/")

        try:
            obj = ContactMessage.objects.create(
                name=name,
                email=email,
                message=message,
                created_by=request.user if request.user.is_authenticated else None,
            )
            messages.success(request, "ส่งข้อความเรียบร้อย ทางทีมจะติดต่อกลับโดยเร็ว")
            log_event(
                request,
                action="contact:message",
                message="ส่งข้อความติดต่อทั่วไป",
                metadata={"id": str(obj.pk)},
            )
        except Exception as e:
            messages.error(request, f"เกิดข้อผิดพลาด: {e}")
        return redirect("/contact/")

    # ------------------------------------------------------------------
    def _handle_bom_component(self, request):
        if not request.user.is_authenticated:
            messages.error(request, "กรุณาเข้าสู่ระบบก่อนส่งคำขอ")
            return redirect("/login/")

        bom_id = (request.POST.get("bom_id") or "").strip()
        component_id = (request.POST.get("component_id") or "").strip()
        quantity_raw = (request.POST.get("quantity") or "").strip()
        unit = (request.POST.get("unit") or "").strip()
        sequence_raw = (request.POST.get("sequence") or "").strip()
        note = (request.POST.get("note") or "").strip()

        if not _is_uuid(bom_id) or not _is_uuid(component_id) or not quantity_raw or not unit:
            messages.error(request, "กรุณากรอกข้อมูลคำขอ BoM ให้ครบ (BoM, พาร์ท, จำนวน, หน่วย)")
            return redirect("/contact/")

        try:
            quantity = Decimal(quantity_raw)
        except (InvalidOperation, ValueError):
            messages.error(request, "จำนวนไม่ถูกต้อง")
            return redirect("/contact/")

        try:
            sequence = int(sequence_raw) if sequence_raw else 1
        except ValueError:
            sequence = 1

        bom = BillOfMaterial.objects.filter(pk=bom_id).first()
        component = Item_list.objects.filter(pk=component_id).first()
        if bom is None or component is None:
            messages.error(request, "ไม่พบ BoM หรือพาร์ทที่เลือก")
            return redirect("/contact/")

        try:
            obj = PartRequest.objects.create(
                request_type=PartRequest.Type.BOM_COMPONENT,
                requester=request.user,
                note=note,
                bom=bom,
                component=component,
                quantity=quantity,
                unit=unit,
                sequence=sequence,
            )
            messages.success(request, "ส่งคำขอเพิ่ม component เข้า BoM แล้ว รอ Admin อนุมัติ")
            log_event(
                request,
                action="part_request:bom",
                message="ส่งคำขอเพิ่ม component BoM",
                metadata={"id": str(obj.pk)},
            )
        except Exception as e:
            messages.error(request, f"เกิดข้อผิดพลาด: {e}")
        return redirect("/contact/")

    # ------------------------------------------------------------------
    def _handle_line_item(self, request):
        if not request.user.is_authenticated:
            messages.error(request, "กรุณาเข้าสู่ระบบก่อนส่งคำขอ")
            return redirect("/login/")

        item_id = (request.POST.get("item_id") or "").strip()
        line_id = (request.POST.get("line_id") or "").strip()
        stage_id = (request.POST.get("stage_id") or "").strip()
        note = (request.POST.get("note") or "").strip()

        if not _is_uuid(item_id) or not _is_uuid(line_id) or not _is_uuid(stage_id):
            messages.error(request, "กรุณาเลือกพาร์ท, ไลน์ และ Stage ให้ครบ")
            return redirect("/contact/")

        item = Item_list.objects.filter(pk=item_id).first()
        line = Line.objects.filter(pk=line_id).first()
        stage = ItemStage.objects.filter(pk=stage_id).first()
        if item is None or line is None or stage is None:
            messages.error(request, "ไม่พบพาร์ท/ไลน์/Stage ที่เลือก")
            return redirect("/contact/")

        try:
            obj = PartRequest.objects.create(
                request_type=PartRequest.Type.LINE_ITEM,
                requester=request.user,
                note=note,
                item=item,
                line=line,
                item_stage=stage,
            )
            messages.success(request, "ส่งคำขอผูกพาร์ทเข้าไลน์แล้ว รอ Admin อนุมัติ")
            log_event(
                request,
                action="part_request:line",
                message="ส่งคำขอผูกพาร์ทเข้าไลน์",
                metadata={"id": str(obj.pk)},
            )
        except Exception as e:
            messages.error(request, f"เกิดข้อผิดพลาด: {e}")
        return redirect("/contact/")


@method_decorator(user_required, name="dispatch")
class ContactSearchView(View):
    """AJAX autocomplete สำหรับฟอร์มคำขอในหน้า /contact/ — เปิดให้ผู้ใช้ที่
    ล็อกอินทุกคน (ต่างจาก LineItemSearchView ที่เป็น staff-only).

    ``?type=item`` (ค่าเริ่มต้น) ค้น Item_list, ``?type=bom`` ค้น BillOfMaterial,
    ``?type=line`` ค้น Line.
    """

    def get(self, request, *args, **kwargs):
        q = (request.GET.get("q") or "").strip()
        search_type = (request.GET.get("type") or "item").strip().lower()
        if not q:
            return JsonResponse({"results": []})

        if search_type == "line":
            qs = Line.objects.filter(line_name__icontains=q).order_by("line_name")[:20]
            results = [
                {
                    "id": str(line.id),
                    "line_name": line.line_name or "",
                }
                for line in qs
            ]
            return JsonResponse({"results": results})

        if search_type == "bom":
            qs = (
                BillOfMaterial.objects.select_related("item").filter(
                    Q(item__part_number__icontains=q)
                    | Q(item__part_name__icontains=q)
                    | Q(item__sku__icontains=q)
                    | Q(item__item_code__icontains=q)
                    | Q(item__sd_code__icontains=q)
                )
                .order_by("item__part_number")[:20]
            )
            results = [
                {
                    "id": str(b.id),
                    "sd_code": b.item.sd_code or "",
                    "part_number": b.item.part_number or "",
                    "part_name": b.item.part_name or "",
                    "item_code": f"Rev {b.revision}",
                }
                for b in qs
            ]
            return JsonResponse({"results": results})

        qs = (
            Item_list.objects.filter(
                Q(sd_code__icontains=q)
                | Q(part_number__icontains=q)
                | Q(part_name__icontains=q)
                | Q(item_code__icontains=q)
            )
            .order_by("sd_code", "part_number")[:20]
        )
        results = [
            {
                "id": str(it.id),
                "sd_code": it.sd_code or "",
                "part_number": it.part_number or "",
                "part_name": it.part_name or "",
                "item_code": it.item_code or "",
            }
            for it in qs
        ]
        return JsonResponse({"results": results})
