from __future__ import annotations

import json
import uuid

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Prefetch, Q
from django.db.models.deletion import ProtectedError
from django.views.generic import TemplateView
from django.shortcuts import redirect

from core.models import User
from core.models.department import Department
from core.models.inspection.machine import Machine
from core.models.inspection.inspection_model import InspectionModels
from core.models.item_category import ItemCategory
from core.models.line import Line
from core.models.inspection.object_detection import (
    DetectionObject, ItemObject, MachineObject,
    ObjectDetectionModel, DefectDetectionInModels, KanbanItemMapping,
)
from core.models.defect_mode import DefectMode
from core.models.item_list import Item_list
from core.models.inspection.inspection_log import (
    InspectionOKLog, InspectionOKLogDetail, InspectionOKLogDetailPhoto,
    InspectionNGLog, InspectionNGLogDetail, InspectionNGLogDetailPhoto,
)


INSPECTION_TABS = (
    "machine",
    "detection_object",
    "item_object",
    "machine_object",
    "object_detection_model",
    "defect_detection_models",
    "defect_mode",
    "kanban_mapping",
    "ok_log",
    "ng_log",
)


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
    template_name = "core/inspection/machine_line.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request

        tab = (request.GET.get("tab") or "machine").strip().lower()
        if tab not in INSPECTION_TABS:
            tab = "machine"

        q = (request.GET.get("q") or "").strip()
        per_page_raw = (request.GET.get("per_page") or "").strip()
        page = (request.GET.get("page") or "1").strip() or "1"

        allowed_per_page = {50, 100, 200, 500, 1000}

        try:
            per_page = int(per_page_raw or 100)
        except Exception:
            per_page = 100

        if per_page not in allowed_per_page:
            per_page = 100

        # ------------------------------------------------------------------ machine
        if tab == "machine":
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

        # ------------------------------------------------------------------ detection_object
        elif tab == "detection_object":
            qs = DetectionObject.objects.all()
            if q:
                qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
            qs = qs.order_by("name")
            paginator = Paginator(qs, per_page)
            page_obj = paginator.get_page(page)
            rows = [
                {"id": str(o.id), "name": o.name, "description": o.description or ""}
                for o in page_obj.object_list
            ]

        # ------------------------------------------------------------------ item_object
        elif tab == "item_object":
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
            rows = [
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
            ctx["objects_list"] = list(DetectionObject.objects.order_by("name").values("id", "name"))
            ctx["items_list"] = list(
                Item_list.objects.exclude(part_name="")
                .order_by("sd_code", "sku")
                .values("id", "sd_code", "sku", "part_name")
            )

        # ------------------------------------------------------------------ machine_object
        elif tab == "machine_object":
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
            rows = [
                {
                    "id": str(o.id),
                    "machine_id": str(o.machine_id),
                    "machine_label": f"{o.machine.machine_no} — {o.machine.machine_name}",
                    "object_id": str(o.object_id),
                    "object_name": o.object.name,
                    "camera_number": o.camera_number,
                }
                for o in page_obj.object_list
            ]
            ctx["machines_list"] = list(
                Machine.objects.order_by("machine_no").values("id", "machine_no", "machine_name")
            )
            ctx["objects_list"] = list(DetectionObject.objects.order_by("name").values("id", "name"))

        # ------------------------------------------------------------------ object_detection_model
        elif tab == "object_detection_model":
            qs = ObjectDetectionModel.objects.select_related("object", "inspection_model")
            if q:
                qs = qs.filter(
                    Q(object__name__icontains=q)
                    | Q(inspection_model__class_name__icontains=q)
                )
            qs = qs.order_by("object__name", "inspection_model__class_name")
            paginator = Paginator(qs, per_page)
            page_obj = paginator.get_page(page)
            rows = [
                {
                    "id": str(o.id),
                    "object_id": str(o.object_id),
                    "object_name": o.object.name,
                    "model_id": str(o.inspection_model_id),
                    "model_class": o.inspection_model.class_name,
                }
                for o in page_obj.object_list
            ]
            ctx["objects_list"] = list(DetectionObject.objects.order_by("name").values("id", "name"))
            ctx["models_list"] = list(
                InspectionModels.objects.filter(model_type="OBJECT")
                .order_by("class_name")
                .values("id", "class_name")
            )

        # ------------------------------------------------------------------ defect_detection_models
        elif tab == "defect_detection_models":
            qs = DefectDetectionInModels.objects.select_related("object", "defect_mode", "inspection_model")
            if q:
                qs = qs.filter(
                    Q(object__name__icontains=q)
                    | Q(defect_mode__name_th__icontains=q)
                    | Q(defect_mode__name_en__icontains=q)
                    | Q(inspection_model__class_name__icontains=q)
                )
            qs = qs.order_by("object__name", "defect_mode__name_en")
            paginator = Paginator(qs, per_page)
            page_obj = paginator.get_page(page)
            rows = [
                {
                    "id": str(o.id),
                    "object_id": str(o.object_id),
                    "object_name": o.object.name,
                    "defect_mode_id": str(o.defect_mode_id),
                    "defect_mode_label": f"{o.defect_mode.name_th} / {o.defect_mode.name_en}",
                    "model_id": str(o.inspection_model_id),
                    "model_class": o.inspection_model.class_name,
                }
                for o in page_obj.object_list
            ]
            ctx["objects_list"] = list(DetectionObject.objects.order_by("name").values("id", "name"))
            ctx["defect_modes_list"] = list(
                DefectMode.objects.order_by("name_th").values("id", "name_th", "name_en")
            )
            ctx["models_list"] = list(
                InspectionModels.objects.filter(model_type="DEFECT")
                .order_by("class_name")
                .values("id", "class_name")
            )

        # ------------------------------------------------------------------ defect_mode
        elif tab == "defect_mode":
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
            rows = [
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
            ctx["insp_models_list"] = list(
                InspectionModels.objects.order_by("class_name").values("id", "class_name")
            )
            ctx["defect_type_choices"] = DefectMode.DefectType.choices

        # ------------------------------------------------------------------ ok_log
        elif tab == "ok_log":
            machine_id_filter = (request.GET.get("machine_id") or "").strip()
            date_from = (request.GET.get("date_from") or "").strip()
            date_to = (request.GET.get("date_to") or "").strip()
            qs = InspectionOKLog.objects.select_related("machine", "item").prefetch_related(
                Prefetch(
                    "details",
                    queryset=InspectionOKLogDetail.objects.select_related("detection_object").prefetch_related(
                        Prefetch("photos", queryset=InspectionOKLogDetailPhoto.objects.order_by("photo_order"))
                    ),
                )
            )
            if q:
                qs = qs.filter(
                    Q(kanban_qr__icontains=q)
                    | Q(item_qr__icontains=q)
                    | Q(item__part_name__icontains=q)
                    | Q(item__sd_code__icontains=q)
                    | Q(machine__machine_no__icontains=q)
                )
            if machine_id_filter:
                qs = qs.filter(machine_id=machine_id_filter)
            if date_from:
                qs = qs.filter(inspected_at__date__gte=date_from)
            if date_to:
                qs = qs.filter(inspected_at__date__lte=date_to)
            qs = qs.order_by("-inspected_at")
            paginator = Paginator(qs, per_page)
            page_obj = paginator.get_page(page)
            rows = []
            for log in page_obj.object_list:
                details_list = []
                for d in log.details.all():
                    photos = list(d.photos.all())
                    details_list.append({
                        "object_name": d.detection_object.name,
                        "camera_number": d.camera_number,
                        "object_found": d.object_found,
                        "object_count": d.object_count,
                        "expected_count": d.expected_count,
                        "confidence": f"{d.confidence:.2f}" if d.confidence is not None else "-",
                        "photos_json": json.dumps([{"path": p.image_path, "caption": p.caption} for p in photos]),
                        "photo_count": len(photos),
                    })
                rows.append({
                    "id": str(log.id),
                    "inspected_at": log.inspected_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "machine_no": log.machine.machine_no,
                    "machine_name": log.machine.machine_name,
                    "sd_code": log.item.sd_code or "",
                    "part_name": log.item.part_name or "",
                    "kanban_qr": log.kanban_qr,
                    "item_qr": log.item_qr,
                    "details": details_list,
                })
            ctx["log_machine_id"] = machine_id_filter
            ctx["date_from"] = date_from
            ctx["date_to"] = date_to
            ctx["machines_list"] = list(
                Machine.objects.order_by("machine_no").values("id", "machine_no", "machine_name")
            )

        # ------------------------------------------------------------------ ng_log
        elif tab == "ng_log":
            machine_id_filter = (request.GET.get("machine_id") or "").strip()
            date_from = (request.GET.get("date_from") or "").strip()
            date_to = (request.GET.get("date_to") or "").strip()
            qs = InspectionNGLog.objects.select_related("machine", "item").prefetch_related(
                Prefetch(
                    "details",
                    queryset=InspectionNGLogDetail.objects.select_related("detection_object", "defect_mode").prefetch_related(
                        Prefetch("photos", queryset=InspectionNGLogDetailPhoto.objects.order_by("photo_order"))
                    ),
                )
            )
            if q:
                qs = qs.filter(
                    Q(kanban_qr__icontains=q)
                    | Q(item_qr__icontains=q)
                    | Q(item__part_name__icontains=q)
                    | Q(item__sd_code__icontains=q)
                    | Q(machine__machine_no__icontains=q)
                )
            if machine_id_filter:
                qs = qs.filter(machine_id=machine_id_filter)
            if date_from:
                qs = qs.filter(inspected_at__date__gte=date_from)
            if date_to:
                qs = qs.filter(inspected_at__date__lte=date_to)
            qs = qs.order_by("-inspected_at")
            paginator = Paginator(qs, per_page)
            page_obj = paginator.get_page(page)
            rows = []
            for log in page_obj.object_list:
                details_list = []
                for d in log.details.all():
                    photos = list(d.photos.all())
                    details_list.append({
                        "object_name": d.detection_object.name,
                        "camera_number": d.camera_number,
                        "object_found": d.object_found,
                        "object_count": d.object_count,
                        "expected_count": d.expected_count,
                        "defect_mode": d.defect_mode.name_th if d.defect_mode else "-",
                        "confidence": f"{d.confidence:.2f}" if d.confidence is not None else "-",
                        "photos_json": json.dumps([{"path": p.image_path, "caption": p.caption} for p in photos]),
                        "photo_count": len(photos),
                    })
                rows.append({
                    "id": str(log.id),
                    "inspected_at": log.inspected_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "machine_no": log.machine.machine_no,
                    "machine_name": log.machine.machine_name,
                    "sd_code": log.item.sd_code or "",
                    "part_name": log.item.part_name or "",
                    "kanban_qr": log.kanban_qr,
                    "item_qr": log.item_qr,
                    "details": details_list,
                })
            ctx["log_machine_id"] = machine_id_filter
            ctx["date_from"] = date_from
            ctx["date_to"] = date_to
            ctx["machines_list"] = list(
                Machine.objects.order_by("machine_no").values("id", "machine_no", "machine_name")
            )

        # ------------------------------------------------------------------ kanban_mapping
        else:  # kanban_mapping
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
            rows = [
                {
                    "id": str(obj.id),
                    "kanban_qr": obj.kanban_qr,
                    "item_qr": obj.item_qr,
                    "item_id": str(obj.item_id),
                    "item_label": f"{obj.item.sd_code or obj.item.sku} — {obj.item.part_name}" if obj.item else "-",
                }
                for obj in page_obj.object_list
            ]
            ctx["items_list"] = list(
                Item_list.objects.filter(item_lines__isnull=False)
                .exclude(part_name="")
                .distinct()
                .order_by("sd_code", "sku")
                .values("id", "sd_code", "sku", "part_name", "part_number")
            )

        ctx["tab"] = tab
        ctx["q"] = q
        ctx["rows"] = rows
        ctx["page_obj"] = page_obj
        ctx["paginator"] = paginator
        ctx["per_page"] = per_page
        ctx["rows_total"] = paginator.count
        ctx["total_count"] = paginator.count
        ctx["page_items"] = _page_items(paginator.num_pages, page_obj.number)

        ctx["nav_counts"] = {
            "machine":             Machine.objects.count(),
            "detection_object":    DetectionObject.objects.count(),
            "item_object":         ItemObject.objects.count(),
            "machine_object":      MachineObject.objects.count(),
            "object_detect_model": ObjectDetectionModel.objects.count(),
            "defect_detect_model": DefectDetectionInModels.objects.count(),
            "defect_mode":         DefectMode.objects.count(),
            "kanban_mapping":      KanbanItemMapping.objects.count(),
            "ok_log":              InspectionOKLog.objects.count(),
            "ng_log":              InspectionNGLog.objects.count(),
        }

        return ctx

    # ---------------------------------------------------------------------- helpers

    def _resolve_fk(self, raw: str, model):
        """แปลง id (string) -> instance หรือ None"""
        raw = (raw or "").strip()
        if not _is_uuid(raw):
            return None
        return model.objects.filter(pk=raw).first()

    def _redirect_tab(self, request, tab):
        return redirect(f"/inspection/machine/?tab={tab}")

    # ---------------------------------------------------------------------- POST

    def post(self, request, *args, **kwargs):
        tab = (request.POST.get("tab") or "machine").strip().lower()
        if tab not in INSPECTION_TABS:
            tab = "machine"

        action = (request.POST.get("action") or "").strip().lower()
        obj_id = (request.POST.get("id") or "").strip()

        # ============================================================= machine
        if tab == "machine":
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

            if action == "create":
                if not machine_no:
                    messages.error(request, "กรุณากรอกรหัสเครื่อง (Machine No)")
                    return self._redirect_tab(request, tab)
                if not machine_name:
                    messages.error(request, "กรุณากรอกชื่อเครื่อง (Machine Name)")
                    return self._redirect_tab(request, tab)
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
                return self._redirect_tab(request, tab)

            if action == "update":
                if not _is_uuid(obj_id):
                    messages.error(request, "ไม่พบรหัสรายการ")
                    return self._redirect_tab(request, tab)
                if not machine_no:
                    messages.error(request, "กรุณากรอกรหัสเครื่อง (Machine No)")
                    return self._redirect_tab(request, tab)
                if not machine_name:
                    messages.error(request, "กรุณากรอกชื่อเครื่อง (Machine Name)")
                    return self._redirect_tab(request, tab)
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
                return self._redirect_tab(request, tab)

            if action == "delete":
                if not _is_uuid(obj_id):
                    messages.error(request, "ไม่พบรหัสรายการ")
                    return self._redirect_tab(request, tab)
                try:
                    with transaction.atomic():
                        obj = Machine.objects.get(pk=obj_id)
                        obj.delete()
                    messages.success(request, "ลบสำเร็จ")
                except ProtectedError:
                    messages.error(request, "ลบไม่ได้ มีข้อมูลอ้างอิงอยู่")
                except Exception as e:
                    messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return self._redirect_tab(request, tab)

        # ============================================================= detection_object
        elif tab == "detection_object":
            name = (request.POST.get("name") or "").strip()
            description = (request.POST.get("description") or "").strip()

            if action == "create":
                if not name:
                    messages.error(request, "กรุณากรอกชื่อ Object")
                    return self._redirect_tab(request, tab)
                try:
                    with transaction.atomic():
                        DetectionObject.objects.create(name=name, description=description or None)
                    messages.success(request, "เพิ่ม Detection Object สำเร็จ")
                except Exception as e:
                    messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return self._redirect_tab(request, tab)

            if action == "update":
                if not name:
                    messages.error(request, "กรุณากรอกชื่อ Object")
                    return self._redirect_tab(request, tab)
                try:
                    with transaction.atomic():
                        obj = DetectionObject.objects.get(pk=obj_id)
                        obj.name = name
                        obj.description = description or None
                        obj.save()
                    messages.success(request, "บันทึกการแก้ไขสำเร็จ")
                except DetectionObject.DoesNotExist:
                    messages.error(request, "ไม่พบรายการนี้")
                except Exception as e:
                    messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return self._redirect_tab(request, tab)

            if action == "delete":
                try:
                    with transaction.atomic():
                        DetectionObject.objects.get(pk=obj_id).delete()
                    messages.success(request, "ลบสำเร็จ")
                except DetectionObject.DoesNotExist:
                    messages.error(request, "ไม่พบรายการนี้")
                except ProtectedError:
                    messages.error(request, "ลบไม่ได้ มีข้อมูลอ้างอิงอยู่")
                except Exception as e:
                    messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return self._redirect_tab(request, tab)

        # ============================================================= item_object
        elif tab == "item_object":
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
                    return self._redirect_tab(request, tab)
                if not item:
                    messages.error(request, "กรุณาเลือกชิ้นงาน (Item)")
                    return self._redirect_tab(request, tab)
                try:
                    with transaction.atomic():
                        ItemObject.objects.create(object=det_obj, item=item, quantity=quantity)
                    messages.success(request, "เพิ่ม Item Object สำเร็จ")
                except Exception as e:
                    messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return self._redirect_tab(request, tab)

            if action == "update":
                if not det_obj:
                    messages.error(request, "กรุณาเลือก Detection Object")
                    return self._redirect_tab(request, tab)
                if not item:
                    messages.error(request, "กรุณาเลือกชิ้นงาน (Item)")
                    return self._redirect_tab(request, tab)
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
                return self._redirect_tab(request, tab)

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
                return self._redirect_tab(request, tab)

        # ============================================================= machine_object
        elif tab == "machine_object":
            machine_id = (request.POST.get("machine_id") or "").strip()
            object_id = (request.POST.get("object_id") or "").strip()
            try:
                camera_number = int(request.POST.get("camera_number") or 1)
                if camera_number < 1:
                    camera_number = 1
            except Exception:
                camera_number = 1

            machine = Machine.objects.filter(pk=machine_id).first() if machine_id else None
            det_obj = DetectionObject.objects.filter(pk=object_id).first() if object_id else None

            if action == "create":
                if not machine:
                    messages.error(request, "กรุณาเลือกเครื่อง (Machine)")
                    return self._redirect_tab(request, tab)
                if not det_obj:
                    messages.error(request, "กรุณาเลือก Detection Object")
                    return self._redirect_tab(request, tab)
                try:
                    with transaction.atomic():
                        MachineObject.objects.create(machine=machine, object=det_obj, camera_number=camera_number)
                    messages.success(request, "เพิ่ม Machine Object สำเร็จ")
                except Exception as e:
                    messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return self._redirect_tab(request, tab)

            if action == "update":
                if not machine:
                    messages.error(request, "กรุณาเลือกเครื่อง (Machine)")
                    return self._redirect_tab(request, tab)
                if not det_obj:
                    messages.error(request, "กรุณาเลือก Detection Object")
                    return self._redirect_tab(request, tab)
                try:
                    with transaction.atomic():
                        o = MachineObject.objects.get(pk=obj_id)
                        o.machine = machine
                        o.object = det_obj
                        o.camera_number = camera_number
                        o.save()
                    messages.success(request, "บันทึกการแก้ไขสำเร็จ")
                except MachineObject.DoesNotExist:
                    messages.error(request, "ไม่พบรายการนี้")
                except Exception as e:
                    messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return self._redirect_tab(request, tab)

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
                return self._redirect_tab(request, tab)

        # ============================================================= object_detection_model
        elif tab == "object_detection_model":
            object_id = (request.POST.get("object_id") or "").strip()
            model_id = (request.POST.get("model_id") or "").strip()

            det_obj = DetectionObject.objects.filter(pk=object_id).first() if object_id else None
            insp_model = InspectionModels.objects.filter(pk=model_id).first() if model_id else None

            if action == "create":
                if not det_obj:
                    messages.error(request, "กรุณาเลือก Detection Object")
                    return self._redirect_tab(request, tab)
                if not insp_model:
                    messages.error(request, "กรุณาเลือก Inspection Model")
                    return self._redirect_tab(request, tab)
                try:
                    with transaction.atomic():
                        ObjectDetectionModel.objects.create(object=det_obj, inspection_model=insp_model)
                    messages.success(request, "เพิ่ม Object Detection Model สำเร็จ")
                except Exception as e:
                    messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return self._redirect_tab(request, tab)

            if action == "update":
                if not det_obj:
                    messages.error(request, "กรุณาเลือก Detection Object")
                    return self._redirect_tab(request, tab)
                if not insp_model:
                    messages.error(request, "กรุณาเลือก Inspection Model")
                    return self._redirect_tab(request, tab)
                try:
                    with transaction.atomic():
                        o = ObjectDetectionModel.objects.get(pk=obj_id)
                        o.object = det_obj
                        o.inspection_model = insp_model
                        o.save()
                    messages.success(request, "บันทึกการแก้ไขสำเร็จ")
                except ObjectDetectionModel.DoesNotExist:
                    messages.error(request, "ไม่พบรายการนี้")
                except Exception as e:
                    messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return self._redirect_tab(request, tab)

            if action == "delete":
                try:
                    with transaction.atomic():
                        ObjectDetectionModel.objects.get(pk=obj_id).delete()
                    messages.success(request, "ลบสำเร็จ")
                except ObjectDetectionModel.DoesNotExist:
                    messages.error(request, "ไม่พบรายการนี้")
                except ProtectedError:
                    messages.error(request, "ลบไม่ได้ มีข้อมูลอ้างอิงอยู่")
                except Exception as e:
                    messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return self._redirect_tab(request, tab)

        # ============================================================= defect_detection_models
        elif tab == "defect_detection_models":
            object_id = (request.POST.get("object_id") or "").strip()
            defect_mode_id = (request.POST.get("defect_mode_id") or "").strip()
            model_id = (request.POST.get("model_id") or "").strip()

            det_obj = DetectionObject.objects.filter(pk=object_id).first() if object_id else None
            defect_mode = DefectMode.objects.filter(pk=defect_mode_id).first() if defect_mode_id else None
            insp_model = InspectionModels.objects.filter(pk=model_id).first() if model_id else None

            if action == "create":
                if not det_obj:
                    messages.error(request, "กรุณาเลือก Detection Object")
                    return self._redirect_tab(request, tab)
                if not defect_mode:
                    messages.error(request, "กรุณาเลือก Defect Mode")
                    return self._redirect_tab(request, tab)
                if not insp_model:
                    messages.error(request, "กรุณาเลือก Inspection Model")
                    return self._redirect_tab(request, tab)
                try:
                    with transaction.atomic():
                        DefectDetectionInModels.objects.create(
                            object=det_obj, defect_mode=defect_mode, inspection_model=insp_model
                        )
                    messages.success(request, "เพิ่ม Defect Detection In Models สำเร็จ")
                except Exception as e:
                    messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return self._redirect_tab(request, tab)

            if action == "update":
                if not det_obj:
                    messages.error(request, "กรุณาเลือก Detection Object")
                    return self._redirect_tab(request, tab)
                if not defect_mode:
                    messages.error(request, "กรุณาเลือก Defect Mode")
                    return self._redirect_tab(request, tab)
                if not insp_model:
                    messages.error(request, "กรุณาเลือก Inspection Model")
                    return self._redirect_tab(request, tab)
                try:
                    with transaction.atomic():
                        o = DefectDetectionInModels.objects.get(pk=obj_id)
                        o.object = det_obj
                        o.defect_mode = defect_mode
                        o.inspection_model = insp_model
                        o.save()
                    messages.success(request, "บันทึกการแก้ไขสำเร็จ")
                except DefectDetectionInModels.DoesNotExist:
                    messages.error(request, "ไม่พบรายการนี้")
                except Exception as e:
                    messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return self._redirect_tab(request, tab)

            if action == "delete":
                try:
                    with transaction.atomic():
                        DefectDetectionInModels.objects.get(pk=obj_id).delete()
                    messages.success(request, "ลบสำเร็จ")
                except DefectDetectionInModels.DoesNotExist:
                    messages.error(request, "ไม่พบรายการนี้")
                except ProtectedError:
                    messages.error(request, "ลบไม่ได้ มีข้อมูลอ้างอิงอยู่")
                except Exception as e:
                    messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return self._redirect_tab(request, tab)

        # ============================================================= defect_mode
        elif tab == "defect_mode":
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
                    return self._redirect_tab(request, tab)
                if not name_en:
                    messages.error(request, "กรุณากรอกชื่อภาษาอังกฤษ")
                    return self._redirect_tab(request, tab)
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
                return self._redirect_tab(request, tab)

            if action == "update":
                if not name_th:
                    messages.error(request, "กรุณากรอกชื่อภาษาไทย")
                    return self._redirect_tab(request, tab)
                if not name_en:
                    messages.error(request, "กรุณากรอกชื่อภาษาอังกฤษ")
                    return self._redirect_tab(request, tab)
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
                return self._redirect_tab(request, tab)

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
                return self._redirect_tab(request, tab)

        # ============================================================= kanban_mapping
        elif tab == "kanban_mapping":
            kanban_qr = (request.POST.get("kanban_qr") or "").strip()
            item_qr = (request.POST.get("item_qr") or "").strip()
            item_id = (request.POST.get("item_id") or "").strip()
            item = Item_list.objects.filter(pk=item_id).first() if item_id else None

            if action == "create":
                if not kanban_qr:
                    messages.error(request, "กรุณากรอก Kanban QR")
                    return self._redirect_tab(request, tab)
                if not item_qr:
                    messages.error(request, "กรุณากรอก Item QR")
                    return self._redirect_tab(request, tab)
                if not item:
                    messages.error(request, "กรุณาเลือกชิ้นงาน (Item)")
                    return self._redirect_tab(request, tab)
                try:
                    with transaction.atomic():
                        KanbanItemMapping.objects.create(
                            kanban_qr=kanban_qr, item_qr=item_qr, item=item,
                        )
                    messages.success(request, "เพิ่ม Kanban Mapping สำเร็จ")
                except Exception as e:
                    messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return self._redirect_tab(request, tab)

            if action == "update":
                if not kanban_qr:
                    messages.error(request, "กรุณากรอก Kanban QR")
                    return self._redirect_tab(request, tab)
                if not item_qr:
                    messages.error(request, "กรุณากรอก Item QR")
                    return self._redirect_tab(request, tab)
                if not item:
                    messages.error(request, "กรุณาเลือกชิ้นงาน (Item)")
                    return self._redirect_tab(request, tab)
                try:
                    with transaction.atomic():
                        o = KanbanItemMapping.objects.get(pk=obj_id)
                        o.kanban_qr = kanban_qr
                        o.item_qr = item_qr
                        o.item = item
                        o.save()
                    messages.success(request, "บันทึกการแก้ไขสำเร็จ")
                except KanbanItemMapping.DoesNotExist:
                    messages.error(request, "ไม่พบรายการนี้")
                except Exception as e:
                    messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return self._redirect_tab(request, tab)

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
                return self._redirect_tab(request, tab)

        messages.error(request, "ไม่รู้จัก action")
        return self._redirect_tab(request, tab)
