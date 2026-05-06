"""
BOM Tree View
─────────────
หน้า UI สำหรับดูโครงสร้าง BOM แบบ multi-level

Features:
  - เลือก FG item + ใส่ qty → แสดง BOM tree
  - แสดง flat list (requirements สำหรับ MRP/cost)
  - Where-used reverse lookup (?component=<sku>)
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from dataclasses import asdict

from django.db.models import Prefetch, Q
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from core.auth.decorators import user_required
from core.models.bill_of_material import BillOfMaterial
from core.models.bill_of_material_item_master import BillOfMaterialItemMaster
from core.models.item_list import Item_list
from core.services.bom_explosion import (
    explode_bom_tree,
    explode_bom_flat,
    where_used,
    tree_summary,
    ExplodedNode,
)


def _flatten_tree_for_template(node: ExplodedNode) -> list[dict]:
    """แปลง tree → flat list ที่มี indent info สำหรับ template"""
    rows: list[dict] = []

    def _walk(n: ExplodedNode):
        rows.append({
            "level": n.level,
            "indent_range": range(n.level),
            "sd_code": n.item.sd_code or "",
            "sku": n.item.sku or "",
            "part_no": n.item.part_number,
            "part_name": n.item.part_name,
            "item_type": n.item.item_type,
            "item_type_display": n.item.get_item_type_display(),
            "unit": n.item.unit,
            "qty_per_parent": n.qty_per_parent,
            "qty_total": n.qty_total,
            "scrap_percent": n.scrap_percent,
            "process": n.process,
            "is_leaf": n.is_leaf,
            "has_cycle": n.has_cycle,
            "has_children": bool(n.children),
            "item_id": str(n.item.id),
        })
        for c in n.children:
            _walk(c)

    _walk(node)
    return rows


@method_decorator(user_required, name="dispatch")
class BomTreeViews(TemplateView):
    template_name = "bom_tree.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request

        # ─── Input params ───
        # รองรับทั้ง part_no (ใหม่) และ sku (เก่า) — lookup ทั้งสองแบบ
        part_no = (request.GET.get("part_no") or request.GET.get("sku") or "").strip()
        qty_raw = (request.GET.get("qty") or "1").strip()
        mode = (request.GET.get("mode") or "tree").strip().lower()  # tree | flat | where_used
        q = (request.GET.get("q") or "").strip()
        depth_raw = (request.GET.get("depth") or "1").strip()

        try:
            qty = Decimal(qty_raw) if qty_raw else Decimal("1")
            if qty <= 0:
                qty = Decimal("1")
        except (InvalidOperation, ValueError):
            qty = Decimal("1")

        # depth: 1 = ชั้นเดียว (default), "all" = เปิดสุด
        if depth_raw.lower() in ("all", "max", "999"):
            depth = 99
            depth_label = "all"
        else:
            try:
                depth = max(1, int(depth_raw))
            except (ValueError, TypeError):
                depth = 1
            depth_label = str(depth)

        # ─── FG item picker (Level 0) ───
        # Filter ด้วย level=0 (ระดับบนสุดใน BOM) — สำหรับ item_type อาจยังว่างอยู่
        # ถ้าผู้ใช้เซ็ต item_type='FG' แล้ว จะใช้ filter นั้นแทน
        has_fg_tagged = Item_list.objects.filter(item_type=Item_list.ItemType.FG).exists()
        if has_fg_tagged:
            fg_qs = Item_list.objects.filter(item_type=Item_list.ItemType.FG)
        else:
            fg_qs = Item_list.objects.filter(level=0)
        fg_qs = fg_qs.order_by("part_number")
        fg_total = fg_qs.count()
        if q:
            fg_qs = fg_qs.filter(
                Q(sd_code__icontains=q)
                | Q(part_number__icontains=q)
                | Q(part_name__icontains=q)
            )

        # ─── โหลด FG + Level 1 children (explicit dict lookup — เสถียรกว่า prefetch) ───
        fg_items = list(fg_qs.only("id", "sd_code", "part_number", "part_name"))
        fg_ids = [f.id for f in fg_items]

        # Step 1: หา BOM ของ FG ทั้งหมด (item_id → BOM)
        bom_map: dict = {}
        for b in BillOfMaterial.objects.filter(item_id__in=fg_ids, is_active=True):
            bom_map[b.item_id] = b

        # Step 2: หา children ของทุก BOM (bom_id → list of BOMItemMaster)
        bom_ids = [b.id for b in bom_map.values()]
        children_by_bom: dict = {}
        if bom_ids:
            qs_items = (
                BillOfMaterialItemMaster.objects
                .filter(bom_id__in=bom_ids, is_active=True)
                .select_related("component")
                .order_by("sequence")
            )
            for bi in qs_items:
                children_by_bom.setdefault(bi.bom_id, []).append(bi)

        fg_list: list[dict] = []
        for fg in fg_items:
            bom = bom_map.get(fg.id)
            children: list[dict] = []
            if bom:
                for bi in children_by_bom.get(bom.id, []):
                    comp = bi.component
                    children.append({
                        "sd_code": comp.sd_code or "",
                        "part_number": comp.part_number,
                        "part_name": comp.part_name,
                        "quantity": bi.quantity,
                    })
            fg_list.append({
                "id": str(fg.id),
                "sd_code": fg.sd_code or "",
                "part_number": fg.part_number,
                "part_name": fg.part_name,
                "children": children,
                "child_count": len(children),
                "has_bom": bom is not None,
            })
        fg_filtered_count = len(fg_list)

        # ─── Selected item ───
        selected_item: Item_list | None = None
        tree_rows: list[dict] = []
        flat_rows: list[dict] = []
        where_used_rows: list[dict] = []
        stats: dict = {}

        if part_no:
            selected_item = Item_list.objects.filter(part_number=part_no).first()

            if selected_item:
                if mode == "where_used":
                    # Reverse lookup — ไม่จำเป็นต้องเป็น FG
                    entries = where_used(selected_item, direct_only=False)
                    for e in entries:
                        where_used_rows.append({
                            "parent_part_no": e.parent_item.part_number,
                            "parent_sd": e.parent_item.sd_code or "",
                            "parent_name": e.parent_item.part_name,
                            "parent_type": e.parent_item.get_item_type_display(),
                            "parent_id": str(e.parent_item.id),
                            "bom_rev": e.bom.revision,
                            "quantity": e.quantity,
                            "process": e.process,
                            "level": e.level,
                        })
                else:
                    # Tree mode ใช้ depth ที่ผู้ใช้เลือก (default=1)
                    # Flat mode ต้อง explode ทั้งหมดเพื่อรวม raw materials ทุกชั้น
                    tree_depth = depth if mode == "tree" else 99
                    tree = explode_bom_tree(selected_item, qty=qty, max_depth=tree_depth)
                    stats = tree_summary(tree)
                    tree_rows = _flatten_tree_for_template(tree)

                    if mode == "flat":
                        reqs = explode_bom_flat(selected_item, qty=qty, leaf_only=True)
                        for r in reqs:
                            flat_rows.append({
                                "sd_code": r.item.sd_code or "",
                                "part_no": r.item.part_number,
                                "part_name": r.item.part_name,
                                "item_type": r.item.get_item_type_display(),
                                "total_qty": r.total_qty,
                                "unit": r.unit,
                                "appears_in": r.appears_in,
                                "item_id": str(r.item.id),
                            })

        ctx.update({
            "part_no": part_no,
            "qty": qty,
            "q": q,
            "mode": mode,
            "depth": depth_label,
            "fg_list": fg_list,
            "fg_total": fg_total,
            "fg_filtered_count": fg_filtered_count,
            "has_fg_tagged": has_fg_tagged,
            "selected_item": selected_item,
            "tree_rows": tree_rows,
            "flat_rows": flat_rows,
            "where_used_rows": where_used_rows,
            "stats": stats,
        })
        return ctx
