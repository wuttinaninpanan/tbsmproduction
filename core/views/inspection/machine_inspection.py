from __future__ import annotations

from django.db.models import Count, Q
from django.http import Http404
from django.views.generic import TemplateView

from core.models.inspection.inspection_item import InspectionItem
from core.models.inspection.machine import Machine
from core.models.item_line import ItemLine


class MachineInspectionView(TemplateView):
    """หน้ารายการ "ผลิตภัณฑ์ที่ผลิต" ของเครื่อง (master).

    แสดงผลิตภัณฑ์ (Item_list) ทุกตัวที่ผูกกับไลน์ของเครื่องนี้ผ่าน ItemLine
    จัดกลุ่มตาม Line — คลิกผลิตภัณฑ์เพื่อเข้าไปจัดการ Inspection Item ของผลิตภัณฑ์นั้น.
    """

    template_name = "inspection/machine_inspection.html"

    def _get_machine(self):
        machine_id = self.kwargs.get("machine_id")
        machine = (
            Machine.objects.prefetch_related("lines")
            .filter(pk=machine_id)
            .first()
        )
        if machine is None:
            raise Http404("ไม่พบเครื่อง")
        return machine

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request

        machine = self._get_machine()
        line_ids = list(machine.lines.values_list("id", flat=True))
        line_names_allowed = {
            ln for ln in machine.lines.values_list("line_name", flat=True) if ln
        }

        q = (request.GET.get("q") or "").strip()

        # ItemLine = ความสัมพันธ์ ผลิตภัณฑ์ ↔ ไลน์ (ผลิตภัณฑ์ที่ผลิตในไลน์นั้น)
        item_lines_qs = (
            ItemLine.objects.filter(line_id__in=line_ids)
            .select_related("item", "item__bom_header", "line")
        )

        if q:
            item_lines_qs = item_lines_qs.filter(
                Q(item__sd_code__icontains=q)
                | Q(item__sku__icontains=q)
                | Q(item__part_number__icontains=q)
                | Q(item__part_name__icontains=q)
                | Q(line__line_name__icontains=q)
            )

        item_lines_qs = item_lines_qs.order_by("line__line_name", "item__sd_code", "item__sku")

        # นับ Inspection Item ต่อผลิตภัณฑ์ (อิงจาก BoM ของผลิตภัณฑ์นั้น)
        product_ids = {il.item_id for il in item_lines_qs}
        insp_counts: dict = {}
        if product_ids:
            insp_counts = dict(
                InspectionItem.objects.filter(
                    bill_of_material_item_master__bom__item_id__in=product_ids
                )
                .values("bill_of_material_item_master__bom__item_id")
                .annotate(c=Count("id"))
                .values_list("bill_of_material_item_master__bom__item_id", "c")
            )

        # จัดกลุ่ม Line → ผลิตภัณฑ์
        nested: dict = {}
        seen_per_line: dict = {}
        total_products = 0
        for il in item_lines_qs:
            item = il.item
            line_name = getattr(il.line, "line_name", "") or "(ไม่ระบุ Line)"

            # กันผลิตภัณฑ์ซ้ำในไลน์เดียวกัน (ปกติ unique_together กันอยู่แล้ว แต่กันไว้)
            line_seen = seen_per_line.setdefault(line_name, set())
            if item.id in line_seen:
                continue
            line_seen.add(item.id)

            has_bom = bool(getattr(item, "bom_header", None))
            sd_code = item.sd_code or item.sku or ""

            row = {
                "machine_id": str(machine.id),
                "item_id": str(item.id),
                "sd_code": sd_code,
                "sku": item.sku or "",
                "part_number": item.part_number or "",
                "part_name": item.part_name or "",
                "has_bom": has_bom,
                "insp_count": insp_counts.get(item.id, 0),
            }
            nested.setdefault(line_name, []).append(row)
            total_products += 1

        grouped_rows = []
        for line_name in sorted(nested.keys()):
            products = nested[line_name]
            grouped_rows.append({
                "line_name": line_name,
                "products": products,
                "count": len(products),
            })

        ctx["machine"] = machine
        ctx["machine_id"] = str(machine.id)
        ctx["line_names"] = sorted(line_names_allowed)
        ctx["grouped_rows"] = grouped_rows
        ctx["q"] = q
        ctx["total_count"] = total_products

        return ctx
