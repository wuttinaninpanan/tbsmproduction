from __future__ import annotations

import uuid

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.shortcuts import redirect

from core.auth.decorators import staff_required
from core.models.bill_of_material_item_master import BillOfMaterialItemMater
from core.models.inspection.inspection_item import InspectionItem
from core.models.inspection.inspection_model import InspectionModels
from core.models.item_line import ItemLine


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
class InspectionItemView(TemplateView):
    template_name = "core/inspection/inspection_item.html"

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

        qs = InspectionItem.objects.select_related(
            "bill_of_material_item_master__bom__item",
            "bill_of_material_item_master__component",
            "inspection_model"
        )

        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(inspection_model__class_name__icontains=q)
                | Q(class_name_bom__icontains=q)
                | Q(bill_of_material_item_master__bom__item__sd_code__icontains=q)
                | Q(bill_of_material_item_master__bom__item__sku__icontains=q)
                | Q(bill_of_material_item_master__bom__item__part_name__icontains=q)
                | Q(bill_of_material_item_master__component__part_name__icontains=q)
            )

        qs = qs.order_by("name")
        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)

        # Build a map: fg_item_id -> [line_name, ...] so we can group rows by Line
        # without changing any data. This is a frontend-only grouping.
        page_fg_ids = [
            obj.bill_of_material_item_master.bom.item_id
            for obj in page_obj.object_list
            if obj.bill_of_material_item_master
            and obj.bill_of_material_item_master.bom_id
            and obj.bill_of_material_item_master.bom.item_id
        ]
        fg_line_map: dict = {}
        if page_fg_ids:
            for il in (
                ItemLine.objects
                .filter(item_id__in=page_fg_ids)
                .select_related("line")
            ):
                fg_line_map.setdefault(il.item_id, []).append(
                    getattr(il.line, "line_name", "") or ""
                )

        rows = []
        for obj in page_obj.object_list:
            bom_master = obj.bill_of_material_item_master
            bom_label = ""
            fg_id = None
            fg_sd_code = ""
            fg_part_name = ""

            if bom_master and bom_master.bom_id and bom_master.bom.item_id:
                product = bom_master.bom.item
                fg_id = product.id
                fg_sd_code = product.sd_code or product.sku or ""
                fg_part_name = product.part_name or ""
                component_name = (
                    bom_master.component.part_name
                    if bom_master.component_id else ""
                )
                if component_name and component_name != product.part_name:
                    bom_label = f"{fg_sd_code} — {fg_part_name} [{component_name}]"
                else:
                    bom_label = f"{fg_sd_code} — {fg_part_name}"

            line_names = sorted({ln for ln in fg_line_map.get(fg_id, []) if ln}) if fg_id else []

            rows.append({
                "id": str(obj.id),
                "name": obj.name,
                "bom_item_id": str(bom_master.id) if bom_master else "",
                "bom_item_label": bom_label,
                "class_name_bom": obj.class_name_bom,
                "inspection_model_id": str(obj.inspection_model_id) if obj.inspection_model_id else "",
                "inspection_model_class": getattr(obj.inspection_model, "class_name", "") if obj.inspection_model_id else "",
                "is_exist": obj.is_exist,
                "camera_number": obj.camera_number,
                "line_names": line_names,
                "fg_sd_code": fg_sd_code,
                "fg_part_name": fg_part_name,
            })

        # Nested grouping (frontend-only): Line → FG (เบอร์งาน) → items.
        # Items belonging to multiple Lines appear under each Line's section;
        # within a Line they are further grouped by FG sd_code (the "เบอร์งาน").
        nested: dict = {}
        for r in rows:
            line_keys = r["line_names"] if r["line_names"] else ["(ไม่ระบุ Line)"]
            fg_key = r["fg_sd_code"] or "(ไม่ระบุเบอร์งาน)"
            fg_label = (
                f"{r['fg_sd_code']} — {r['fg_part_name']}"
                if r["fg_sd_code"] and r["fg_part_name"]
                else (r["fg_sd_code"] or "(ไม่ระบุเบอร์งาน)")
            )
            for ln in line_keys:
                line_bucket = nested.setdefault(ln, {})
                fg_bucket = line_bucket.setdefault(fg_key, {"label": fg_label, "items": []})
                fg_bucket["items"].append(r)

        grouped_rows = []
        for ln, fg_map in sorted(nested.items()):
            fg_groups = []
            line_count = 0
            for fg_key, payload in sorted(fg_map.items()):
                fg_groups.append({
                    "fg_key": fg_key,
                    "fg_label": payload["label"],
                    "items": payload["items"],
                    "count": len(payload["items"]),
                })
                line_count += len(payload["items"])
            grouped_rows.append({
                "line_name": ln,
                "fg_groups": fg_groups,
                "count": line_count,
            })

        ctx["rows"] = rows
        ctx["grouped_rows"] = grouped_rows
        ctx["q"] = q
        ctx["page_obj"] = page_obj
        ctx["paginator"] = paginator
        ctx["per_page"] = per_page
        ctx["rows_total"] = paginator.count
        ctx["page_items"] = _page_items(paginator.num_pages, page_obj.number)
        ctx["total_count"] = paginator.count

        ctx["bom_items"] = list(
            BillOfMaterialItemMater.objects
            .select_related("bom__item", "component")
            .order_by("bom__item__sd_code", "sequence")
            .values(
                "id",
                "bom__item__sd_code",
                "bom__item__sku",
                "bom__item__part_name",
                "component__part_name",
            )
        )

        ctx["inspection_models_list"] = list(
            InspectionModels.objects.order_by("class_name").values("id", "class_name")
        )

        return ctx

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip().lower()
        obj_id = (request.POST.get("id") or "").strip()
        name = (request.POST.get("name") or "").strip()
        bom_item_id = (request.POST.get("bom_item_id") or "").strip()
        class_name_bom = (request.POST.get("class_name_bom") or "").strip()
        insp_model_id = (request.POST.get("inspection_model_id") or "").strip()
        is_exist_raw = request.POST.get("is_exist")
        is_exist = str(is_exist_raw).lower() == "true"

        camera_number_raw = request.POST.get("camera_number")

        try:
            camera_number = int(camera_number_raw)
        except (TypeError, ValueError):
            camera_number = 0

        # ================= BULK DELETE =================
        if action == "bulk_delete":
            bulk_ids = request.POST.getlist("bulk_id")
            ids = [x for x in [b.strip() for b in bulk_ids] if _is_uuid(x)]

            if not ids:
                messages.error(request, "กรุณาเลือกรายการที่ต้องการลบ")
                return redirect(request.get_full_path())
            deleted = blocked = 0

            try:
                with transaction.atomic():
                    for pk in ids:
                        obj = InspectionItem.objects.filter(pk=pk).first()
                        if obj is None:
                            continue
                        try:
                            obj.delete()
                            deleted += 1
                        except ProtectedError:
                            blocked += 1
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return redirect(request.get_full_path())
            if blocked:
                messages.warning(request, f"ลบสำเร็จ {deleted} รายการ, ลบไม่ได้ {blocked} รายการ (มีข้อมูลอ้างอิง)")
            else:
                messages.success(request, f"ลบสำเร็จ {deleted} รายการ")

            return redirect(request.get_full_path())
        # ================= CREATE =================
        if action == "create":
            if not name:
                messages.error(request, "กรุณากรอก Name")
                return redirect(request.get_full_path())
            if not _is_uuid(bom_item_id):
                messages.error(request, "กรุณาเลือก BOM Item Master")
                return redirect(request.get_full_path())
            if not class_name_bom:
                messages.error(request, "กรุณากรอก Class Name BOM")
                return redirect(request.get_full_path())
            if not _is_uuid(insp_model_id):
                messages.error(request, "กรุณาเลือก Inspection Model")
                return redirect(request.get_full_path())
            try:
                bom_obj = BillOfMaterialItemMater.objects.get(pk=bom_item_id)
                insp_obj = InspectionModels.objects.get(pk=insp_model_id)

                with transaction.atomic():
                    InspectionItem.objects.create(
                        name=name,
                        bill_of_material_item_master=bom_obj,
                        class_name_bom=class_name_bom,
                        inspection_model=insp_obj,
                        is_exist=is_exist,
                        camera_number=camera_number,
                    )

                messages.success(request, "เพิ่ม Inspection Item สำเร็จ")

            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")

            return redirect(request.get_full_path())
        # ================= UPDATE =================
        if action == "update":
            if not _is_uuid(obj_id):
                messages.error(request, "ไม่พบรหัสรายการ")
                return redirect(request.get_full_path())
            if not name:
                messages.error(request, "กรุณากรอก Name")
                return redirect(request.get_full_path())
            if not _is_uuid(bom_item_id):
                messages.error(request, "กรุณาเลือก BOM Item Master")
                return redirect(request.get_full_path())
            if not class_name_bom:
                messages.error(request, "กรุณากรอก Class Name BOM")
                return redirect(request.get_full_path())
            if not _is_uuid(insp_model_id):
                messages.error(request, "กรุณาเลือก Inspection Model")
                return redirect(request.get_full_path())
            try:
                obj = InspectionItem.objects.get(pk=obj_id)
                bom_obj = BillOfMaterialItemMater.objects.get(pk=bom_item_id)
                insp_obj = InspectionModels.objects.get(pk=insp_model_id)

                with transaction.atomic():
                    obj.name = name
                    obj.bill_of_material_item_master = bom_obj
                    obj.class_name_bom = class_name_bom
                    obj.inspection_model = insp_obj
                    obj.is_exist = is_exist
                    obj.camera_number = camera_number

                    obj.save(update_fields=[
                        "name",
                        "bill_of_material_item_master",
                        "class_name_bom",
                        "inspection_model",
                        "is_exist",
                        "camera_number",
                        "updated_at"
                    ])

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
                    obj = InspectionItem.objects.get(pk=obj_id)
                    obj.delete()

                messages.success(request, "ลบสำเร็จ")

            except ProtectedError:
                messages.error(request, "ลบไม่ได้ มีข้อมูลอ้างอิงอยู่")
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")

            return redirect(request.get_full_path())
        messages.error(request, "ไม่รู้จัก action")
        return redirect(request.get_full_path())