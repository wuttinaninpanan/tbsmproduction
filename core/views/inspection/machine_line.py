from __future__ import annotations

import json
import os
import pathlib
import uuid

from datetime import timezone as _utc
from zoneinfo import ZoneInfo

from django.conf import settings as _django_settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Prefetch, Q
from django.db.models.deletion import ProtectedError
from django.utils import timezone as _django_timezone
from django.utils.dateparse import parse_date
from django.views.generic import TemplateView
from django.shortcuts import redirect

_BANGKOK = ZoneInfo("Asia/Bangkok")


def _fmt_dt(dt) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_BANGKOK)
    return dt.astimezone(_BANGKOK).strftime("%Y-%m-%d %H:%M:%S")


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
from core.models.inspection.inspection_report import InspectionReport


INSPECTION_TABS = (
    "machine",
    "detection_object",
    "item_object",
    "machine_object",
    "inspection_modelss",
    "object_detection_model",
    "defect_detection_models",
    "defect_mode",
    "inspection_report",
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
            qs = DetectionObject.objects.select_related("line").all()
            if q:
                qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
            qs = qs.order_by("line__line_name", "name")
            all_objs = list(qs)
            groups = []
            group_map: dict = {}
            for o in all_objs:
                key = str(o.line_id) if o.line_id else "__none__"
                if key not in group_map:
                    entry: dict = {
                        "line_id": str(o.line_id) if o.line_id else "",
                        "line_name": o.line.line_name if o.line_id else "ไม่ระบุ Line",
                        "objects": [],
                    }
                    group_map[key] = entry
                    groups.append(entry)
                group_map[key]["objects"].append({
                    "id": str(o.id),
                    "name": o.name,
                    "description": o.description or "",
                    "line_id": str(o.line_id) if o.line_id else "",
                    "line_name": o.line.line_name if o.line_id else "",
                })
            paginator = Paginator(all_objs, max(len(all_objs), 1))
            page_obj = paginator.get_page(1)
            rows = []
            ctx["groups"] = groups
            ctx["lines_list"] = list(
                Line.objects.order_by("line_name").values("id", "line_name")
            )

        # ------------------------------------------------------------------ item_object
        elif tab == "item_object":
            from core.models.item_line import ItemLine as _ItemLine
            base_qs = ItemObject.objects.select_related("item", "object")
            if q:
                base_qs = base_qs.filter(
                    Q(item__part_name__icontains=q)
                    | Q(item__sd_code__icontains=q)
                    | Q(item__sku__icontains=q)
                    | Q(object__name__icontains=q)
                )
            all_io = list(base_qs.order_by("item__sd_code", "item__sku", "object__name"))

            # Build item_id → {label, objects} map
            item_io_map: dict = {}
            for o in all_io:
                key = str(o.item_id)
                if key not in item_io_map:
                    item_io_map[key] = {
                        "item_id": key,
                        "item_label": f"{o.item.sd_code or o.item.sku} — {o.item.part_name}",
                        "objects": [],
                    }
                item_io_map[key]["objects"].append({
                    "id": str(o.id),
                    "object_id": str(o.object_id),
                    "object_name": o.object.name,
                    "item_id": key,
                    "item_label": item_io_map[key]["item_label"],
                    "quantity": o.quantity,
                })

            # Build line → items map via ItemLine
            item_lines = (
                _ItemLine.objects
                .filter(item_id__in=set(item_io_map.keys()))
                .select_related("line")
                .order_by("line__line_name", "item__sd_code")
            )
            line_map: dict = {}
            line_order: list = []
            assigned_items: set = set()
            for il in item_lines:
                lk = str(il.line_id)
                ik = str(il.item_id)
                if ik not in item_io_map:
                    continue
                if lk not in line_map:
                    line_map[lk] = {
                        "line_id": lk,
                        "line_name": il.line.line_name,
                        "items": [],
                        "_seen": set(),
                    }
                    line_order.append(lk)
                if ik not in line_map[lk]["_seen"]:
                    line_map[lk]["items"].append(item_io_map[ik])
                    line_map[lk]["_seen"].add(ik)
                assigned_items.add(ik)

            line_groups: list = []
            for lk in line_order:
                g = line_map[lk]
                del g["_seen"]
                line_groups.append(g)

            unassigned = [v for k, v in item_io_map.items() if k not in assigned_items]
            if unassigned:
                line_groups.append({"line_id": "", "line_name": "ไม่ระบุ Line", "items": unassigned})

            paginator = Paginator(all_io, max(len(all_io), 1))
            page_obj = paginator.get_page(1)
            rows = []
            ctx["line_groups"] = line_groups
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
            all_mo = list(qs.order_by("machine__machine_no", "object__name"))
            mo_groups: list = []
            mo_group_map: dict = {}
            for o in all_mo:
                key = str(o.machine_id)
                if key not in mo_group_map:
                    entry: dict = {
                        "machine_id": key,
                        "machine_label": f"{o.machine.machine_no} — {o.machine.machine_name}",
                        "objects": [],
                    }
                    mo_group_map[key] = entry
                    mo_groups.append(entry)
                mo_group_map[key]["objects"].append({
                    "id": str(o.id),
                    "machine_id": key,
                    "machine_label": mo_group_map[key]["machine_label"],
                    "object_id": str(o.object_id),
                    "object_name": o.object.name,
                    "camera_number": o.camera_number,
                })
            paginator = Paginator(all_mo, max(len(all_mo), 1))
            page_obj = paginator.get_page(1)
            rows = []
            ctx["mo_groups"] = mo_groups
            ctx["machines_list"] = list(
                Machine.objects.order_by("machine_no").values("id", "machine_no", "machine_name")
            )
            ctx["objects_list"] = list(DetectionObject.objects.order_by("name").values("id", "name"))

        # ------------------------------------------------------------------ inspection_modelss
        elif tab == "inspection_modelss":
            qs = InspectionModels.objects.all()
            if q:
                qs = qs.filter(
                    Q(class_name__icontains=q)
                    | Q(description_en__icontains=q)
                    | Q(description_th__icontains=q)
                )
            qs = qs.order_by("class_name")
            paginator = Paginator(qs, per_page)
            page_obj = paginator.get_page(page)
            rows = []
            for obj in page_obj.object_list:
                rows.append({
                    "id": str(obj.id),
                    "class_name": obj.class_name,
                    "description_en": obj.description_en or "",
                    "description_th": obj.description_th or "",
                    "model_path": obj.model_path or "",
                    "model_type": obj.model_type or "OBJECT",
                    "count_detect": obj.count_detect,
                })
            ctx["windows_app_base"] = _django_settings.WINDOWS_APP_BASE

        # ------------------------------------------------------------------ object_detection_model
        elif tab == "object_detection_model":
            qs = ObjectDetectionModel.objects.select_related("object", "object__line", "inspection_model")
            if q:
                qs = qs.filter(
                    Q(object__name__icontains=q)
                    | Q(inspection_model__class_name__icontains=q)
                )
            all_odm = list(qs.order_by("object__line__line_name", "object__name", "inspection_model__class_name"))
            odm_groups: list = []
            odm_group_map: dict = {}
            for o in all_odm:
                ln = o.object.line
                key = str(ln.id) if ln else "__none__"
                if key not in odm_group_map:
                    entry: dict = {
                        "line_id": str(ln.id) if ln else "",
                        "line_name": ln.line_name if ln else "ไม่ระบุ Line",
                        "items": [],
                    }
                    odm_group_map[key] = entry
                    odm_groups.append(entry)
                odm_group_map[key]["items"].append({
                    "id": str(o.id),
                    "object_id": str(o.object_id),
                    "object_name": o.object.name,
                    "model_id": str(o.inspection_model_id),
                    "model_class": o.inspection_model.class_name,
                })
            paginator = Paginator(all_odm, max(len(all_odm), 1))
            page_obj = paginator.get_page(1)
            rows = []
            ctx["odm_groups"] = odm_groups
            ctx["objects_list"] = list(DetectionObject.objects.select_related("line").order_by("line__line_name", "name").values("id", "name"))
            ctx["models_list"] = list(
                InspectionModels.objects.filter(model_type="OBJECT")
                .order_by("class_name")
                .values("id", "class_name")
            )

        # ------------------------------------------------------------------ defect_detection_models
        elif tab == "defect_detection_models":
            qs = DefectDetectionInModels.objects.select_related("object", "object__line", "defect_mode", "inspection_model")
            if q:
                qs = qs.filter(
                    Q(object__name__icontains=q)
                    | Q(defect_mode__name_th__icontains=q)
                    | Q(defect_mode__name_en__icontains=q)
                    | Q(inspection_model__class_name__icontains=q)
                )
            all_ddm = list(qs.order_by("object__line__line_name", "object__name", "defect_mode__name_en"))
            ddm_groups: list = []
            ddm_group_map: dict = {}
            for o in all_ddm:
                ln = o.object.line
                key = str(ln.id) if ln else "__none__"
                if key not in ddm_group_map:
                    entry: dict = {
                        "line_id": str(ln.id) if ln else "",
                        "line_name": ln.line_name if ln else "ไม่ระบุ Line",
                        "items": [],
                    }
                    ddm_group_map[key] = entry
                    ddm_groups.append(entry)
                ddm_group_map[key]["items"].append({
                    "id": str(o.id),
                    "object_id": str(o.object_id),
                    "object_name": o.object.name,
                    "defect_mode_id": str(o.defect_mode_id),
                    "defect_mode_label": f"{o.defect_mode.name_th} / {o.defect_mode.name_en}",
                    "model_id": str(o.inspection_model_id),
                    "model_class": o.inspection_model.class_name,
                })
            paginator = Paginator(all_ddm, max(len(all_ddm), 1))
            page_obj = paginator.get_page(1)
            rows = []
            ctx["ddm_groups"] = ddm_groups
            ctx["objects_list"] = list(DetectionObject.objects.select_related("line").order_by("line__line_name", "name").values("id", "name"))
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

        # ------------------------------------------------------------------ inspection_report
        elif tab == "inspection_report":
            qs = InspectionReport.objects.select_related("line", "object", "defect_mode")
            if q:
                qs = qs.filter(
                    Q(line__line_name__icontains=q)
                    | Q(object__name__icontains=q)
                    | Q(defect_mode__name_th__icontains=q)
                    | Q(defect_mode__name_en__icontains=q)
                )
            all_ir = list(qs.order_by("line__line_name", "-report_date", "object__name"))
            ir_groups: list = []
            ir_group_map: dict = {}
            for o in all_ir:
                key = str(o.line_id) if o.line_id else "__none__"
                if key not in ir_group_map:
                    entry: dict = {
                        "line_id": str(o.line_id) if o.line_id else "",
                        "line_name": o.line.line_name if o.line_id else "ไม่ระบุ Line",
                        "items": [],
                    }
                    ir_group_map[key] = entry
                    ir_groups.append(entry)
                ir_group_map[key]["items"].append({
                    "id": str(o.id),
                    "line_id": str(o.line_id) if o.line_id else "",
                    "object_id": str(o.object_id),
                    "object_name": o.object.name,
                    "defect_mode_id": str(o.defect_mode_id),
                    "defect_mode_label": f"{o.defect_mode.name_th} / {o.defect_mode.name_en}",
                    "report_type": o.report_type,
                    "report_type_display": o.get_report_type_display(),
                    "count": o.count,
                    "target_count": o.target_count,
                    "count_display": f"{o.count}/{o.target_count}",
                    "report_date": o.report_date.strftime("%Y-%m-%d") if o.report_date else "",
                    "note": o.note or "",
                })
            paginator = Paginator(all_ir, max(len(all_ir), 1))
            page_obj = paginator.get_page(1)
            rows = []
            ctx["ir_groups"] = ir_groups
            ctx["lines_list"] = list(
                Line.objects.order_by("line_name").values("id", "line_name")
            )
            ctx["objects_list"] = list(
                DetectionObject.objects.select_related("line")
                .order_by("line__line_name", "name")
                .values("id", "name", "line_id")
            )
            ctx["defect_modes_list"] = list(
                DefectMode.objects.order_by("name_th").values("id", "name_th", "name_en")
            )
            _seen_types = set()
            report_type_options = []
            for val, label in InspectionReport.ReportType.choices:
                _seen_types.add(val)
                report_type_options.append({"value": val, "label": label})
            _existing_types = (
                InspectionReport.objects.exclude(report_type="")
                .order_by("report_type")
                .values_list("report_type", flat=True)
                .distinct()
            )
            for t in _existing_types:
                if t not in _seen_types:
                    _seen_types.add(t)
                    report_type_options.append({"value": t, "label": t})
            ctx["report_type_options"] = report_type_options

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
            _ok_media = _django_settings.MEDIA_URL.rstrip("/")
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
                        "photos_json": json.dumps([{"path": f"{_ok_media}/image_inspection/{pathlib.Path(p.image_path).name}", "caption": p.caption} for p in photos]),
                        "photo_count": len(photos),
                    })
                rows.append({
                    "id": str(log.id),
                    "inspected_at": _fmt_dt(log.inspected_at),
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

            # Scan image_inspection folder once, then match by QR code per row
            _img_dir = pathlib.Path(_django_settings.MEDIA_ROOT) / "image_inspection"
            _all_img_files: list[str] = []
            if _img_dir.is_dir():
                try:
                    _all_img_files = sorted(f.name for f in _img_dir.iterdir() if f.is_file())
                except OSError:
                    pass
            _media_url = _django_settings.MEDIA_URL.rstrip("/")

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
                        "photos_json": json.dumps([{"path": f"{_media_url}/image_inspection/{pathlib.Path(p.image_path).name}", "caption": p.caption} for p in photos]),
                        "photo_count": len(photos),
                    })

                # Match images by item_qr (unique per piece) to isolate per scan session.
                # Fall back to kanban_qr only when item_qr is absent (older records).
                qr_images: list[dict] = []
                seen_fnames: set[str] = set()
                match_qr = log.item_qr or log.kanban_qr
                if match_qr:
                    for fname in _all_img_files:
                        if match_qr in fname and fname not in seen_fnames:
                            seen_fnames.add(fname)
                            qr_images.append({
                                "path": f"{_media_url}/image_inspection/{fname}",
                                "caption": fname,
                            })

                rows.append({
                    "id": str(log.id),
                    "inspected_at": _fmt_dt(log.inspected_at),
                    "machine_no": log.machine.machine_no,
                    "machine_name": log.machine.machine_name,
                    "sd_code": log.item.sd_code or "",
                    "part_name": log.item.part_name or "",
                    "kanban_qr": log.kanban_qr,
                    "item_qr": log.item_qr,
                    "details": details_list,
                    "qr_images_json": json.dumps(qr_images),
                    "qr_image_count": len(qr_images),
                    "qr_first_image": qr_images[0]["path"] if qr_images else "",
                })
            ctx["log_machine_id"] = machine_id_filter
            ctx["date_from"] = date_from
            ctx["date_to"] = date_to
            ctx["machines_list"] = list(
                Machine.objects.order_by("machine_no").values("id", "machine_no", "machine_name")
            )

        # ------------------------------------------------------------------ kanban_mapping
        else:  # kanban_mapping
            from core.models.item_line import ItemLine as _ItemLine
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
            all_km = list(qs.order_by("item__sd_code", "item__sku", "kanban_qr"))

            item_ids = list({str(o.item_id) for o in all_km})
            item_to_line: dict = {}
            for il in (
                _ItemLine.objects.filter(item_id__in=item_ids)
                .select_related("line")
                .order_by("line__line_name")
            ):
                ik = str(il.item_id)
                if ik not in item_to_line:
                    item_to_line[ik] = (str(il.line_id), il.line.line_name)

            km_line_map: dict = {}
            km_line_order: list = []
            for o in all_km:
                ik = str(o.item_id)
                line_info = item_to_line.get(ik)
                if line_info:
                    lk, ln = line_info
                else:
                    lk, ln = "__none__", "ไม่ระบุ Line"
                if lk not in km_line_map:
                    km_line_map[lk] = {
                        "line_id": lk if lk != "__none__" else "",
                        "line_name": ln,
                        "mappings": [],
                    }
                    km_line_order.append(lk)
                km_line_map[lk]["mappings"].append({
                    "id": str(o.id),
                    "kanban_qr": o.kanban_qr,
                    "item_qr": o.item_qr,
                    "item_id": ik,
                    "item_label": f"{o.item.sd_code or o.item.sku} — {o.item.part_name}" if o.item else "-",
                })

            paginator = Paginator(all_km, max(len(all_km), 1))
            page_obj = paginator.get_page(1)
            rows = []
            sorted_groups = sorted(
                [v for k, v in km_line_map.items() if k != "__none__"],
                key=lambda g: g["line_name"],
            )
            if "__none__" in km_line_map:
                sorted_groups.append(km_line_map["__none__"])
            ctx["km_line_groups"] = sorted_groups
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
            "inspection_modelss":  InspectionModels.objects.count(),
            "object_detect_model": ObjectDetectionModel.objects.count(),
            "defect_detect_model": DefectDetectionInModels.objects.count(),
            "defect_mode":         DefectMode.objects.count(),
            "inspection_report":   InspectionReport.objects.count(),
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

    def _save_model_file(self, request) -> str | None:
        f = request.FILES.get("model_file")
        if not f:
            return None
        dest_dir = os.path.join(_django_settings.MEDIA_ROOT, "inspection_models")
        os.makedirs(dest_dir, exist_ok=True)
        name, ext = os.path.splitext(f.name)
        filename = f"{name}{ext}"
        dest_path = os.path.join(dest_dir, filename)
        if os.path.exists(dest_path):
            filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
            dest_path = os.path.join(dest_dir, filename)
        with open(dest_path, "wb") as out:
            for chunk in f.chunks():
                out.write(chunk)
        # แปลง Docker path → Windows path เพื่อ save ลง DB
        # /app/media/inspection_models/x.pt → D:\tb_app\tbsmproduction\media\inspection_models\x.pt
        win_base = _django_settings.WINDOWS_APP_BASE.rstrip("/\\").replace("\\", "/")
        windows_path = win_base + dest_path.replace("/app", "")
        return windows_path

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
            line_obj = self._resolve_fk(request.POST.get("line_id"), Line)

            if action == "create":
                if not name:
                    messages.error(request, "กรุณากรอกชื่อ Object")
                    return self._redirect_tab(request, tab)
                try:
                    with transaction.atomic():
                        DetectionObject.objects.create(
                            name=name,
                            description=description or None,
                            line=line_obj,
                        )
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
                        obj.line = line_obj
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

        # ============================================================= inspection_modelss
        elif tab == "inspection_modelss":
            class_name = (request.POST.get("class_name") or "").strip()
            description_en = (request.POST.get("description_en") or "").strip()
            description_th = (request.POST.get("description_th") or "").strip()
            model_path = (request.POST.get("model_path") or "").strip()
            model_type = (request.POST.get("model_type") or "OBJECT").strip()
            count_detect_raw = (request.POST.get("count_detect") or "0").strip()
            try:
                count_detect = int(count_detect_raw)
            except Exception:
                count_detect = 0

            if action == "bulk_delete":
                bulk_ids = request.POST.getlist("bulk_id")
                ids = [x for x in [b.strip() for b in bulk_ids] if _is_uuid(x)]
                if not ids:
                    messages.error(request, "กรุณาเลือกรายการที่ต้องการลบ")
                    return self._redirect_tab(request, tab)
                deleted = blocked = 0
                try:
                    with transaction.atomic():
                        for pk in ids:
                            obj = InspectionModels.objects.filter(pk=pk).first()
                            if obj is None:
                                continue
                            try:
                                obj.delete()
                                deleted += 1
                            except ProtectedError:
                                blocked += 1
                except Exception as e:
                    messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                    return self._redirect_tab(request, tab)
                if blocked:
                    messages.warning(request, f"ลบสำเร็จ {deleted} รายการ, ลบไม่ได้ {blocked} รายการ (มีข้อมูลอ้างอิง)")
                else:
                    messages.success(request, f"ลบสำเร็จ {deleted} รายการ")
                return self._redirect_tab(request, tab)

            if action == "create":
                if not class_name:
                    messages.error(request, "กรุณากรอก Class Name")
                    return self._redirect_tab(request, tab)
                try:
                    uploaded = self._save_model_file(request)
                    if uploaded and not model_path:
                        model_path = uploaded
                    with transaction.atomic():
                        InspectionModels.objects.create(
                            class_name=class_name,
                            description_en=description_en or None,
                            description_th=description_th or None,
                            model_path=model_path or None,
                            model_type=model_type,
                            count_detect=count_detect,
                        )
                    messages.success(request, "เพิ่ม Inspection Model สำเร็จ")
                except Exception as e:
                    messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return self._redirect_tab(request, tab)

            if action == "update":
                if not _is_uuid(obj_id):
                    messages.error(request, "ไม่พบรหัสรายการ")
                    return self._redirect_tab(request, tab)
                if not class_name:
                    messages.error(request, "กรุณากรอก Class Name")
                    return self._redirect_tab(request, tab)
                try:
                    uploaded = self._save_model_file(request)
                    if uploaded and not model_path:
                        model_path = uploaded
                    with transaction.atomic():
                        o = InspectionModels.objects.get(pk=obj_id)
                        o.class_name = class_name
                        o.description_en = description_en or None
                        o.description_th = description_th or None
                        o.model_type = model_type
                        if model_path:
                            o.model_path = model_path
                        o.count_detect = count_detect
                        o.save(update_fields=["class_name", "description_en", "description_th", "model_path", "model_type", "count_detect", "updated_at"])
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
                        o = InspectionModels.objects.get(pk=obj_id)
                        o.object_detection_models.all().delete()
                        o.defect_detection_models.all().delete()
                        o.delete()
                    messages.success(request, "ลบสำเร็จ")
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

        # ============================================================= inspection_report
        elif tab == "inspection_report":
            line_id = (request.POST.get("line_id") or "").strip()
            object_id = (request.POST.get("object_id") or "").strip()
            defect_mode_id = (request.POST.get("defect_mode_id") or "").strip()
            report_type = (request.POST.get("report_type") or "").strip()
            count_raw = (request.POST.get("count") or "").strip()
            target_count_raw = (request.POST.get("target_count") or "").strip()
            report_date_raw = (request.POST.get("report_date") or "").strip()
            note = (request.POST.get("note") or "").strip()

            line_obj = self._resolve_fk(line_id, Line)
            det_obj = self._resolve_fk(object_id, DetectionObject)
            defect_mode = self._resolve_fk(defect_mode_id, DefectMode)
            try:
                count = int(count_raw)
                if count < 0:
                    count = 0
            except Exception:
                count = 0
            try:
                target_count = int(target_count_raw)
                if target_count < 1:
                    target_count = 30
            except Exception:
                target_count = 30
            report_date = parse_date(report_date_raw) or _django_timezone.localdate()

            if action == "create":
                if not line_obj:
                    messages.error(request, "กรุณาเลือก Line")
                    return self._redirect_tab(request, tab)
                if not det_obj:
                    messages.error(request, "กรุณาเลือก Object")
                    return self._redirect_tab(request, tab)
                if not defect_mode:
                    messages.error(request, "กรุณาเลือก Defect")
                    return self._redirect_tab(request, tab)
                if not report_type:
                    messages.error(request, "กรุณาเลือกหรือกรอกประเภท")
                    return self._redirect_tab(request, tab)
                try:
                    with transaction.atomic():
                        InspectionReport.objects.create(
                            line=line_obj, object=det_obj, defect_mode=defect_mode,
                            report_type=report_type, count=count, target_count=target_count,
                            report_date=report_date, note=note,
                        )
                    messages.success(request, "เพิ่ม Inspection Report สำเร็จ")
                except Exception as e:
                    messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return self._redirect_tab(request, tab)

            if action == "update":
                if not line_obj:
                    messages.error(request, "กรุณาเลือก Line")
                    return self._redirect_tab(request, tab)
                if not det_obj:
                    messages.error(request, "กรุณาเลือก Object")
                    return self._redirect_tab(request, tab)
                if not defect_mode:
                    messages.error(request, "กรุณาเลือก Defect")
                    return self._redirect_tab(request, tab)
                if not report_type:
                    messages.error(request, "กรุณาเลือกหรือกรอกประเภท")
                    return self._redirect_tab(request, tab)
                try:
                    with transaction.atomic():
                        o = InspectionReport.objects.get(pk=obj_id)
                        o.line = line_obj
                        o.object = det_obj
                        o.defect_mode = defect_mode
                        o.report_type = report_type
                        o.count = count
                        o.target_count = target_count
                        o.report_date = report_date
                        o.note = note
                        o.save()
                    messages.success(request, "บันทึกการแก้ไขสำเร็จ")
                except InspectionReport.DoesNotExist:
                    messages.error(request, "ไม่พบรายการนี้")
                except Exception as e:
                    messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return self._redirect_tab(request, tab)

            if action == "delete":
                try:
                    with transaction.atomic():
                        InspectionReport.objects.get(pk=obj_id).delete()
                    messages.success(request, "ลบสำเร็จ")
                except InspectionReport.DoesNotExist:
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
