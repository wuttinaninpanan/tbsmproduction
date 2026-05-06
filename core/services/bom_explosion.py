"""
BOM Explosion Service
─────────────────────
Core business logic สำหรับ Bill of Material

ฟังก์ชันหลัก:
  - explode_bom_tree()  : คืนค่าโครงสร้าง BOM เป็น nested tree (สำหรับ UI)
  - explode_bom_flat()  : คืนค่า flat list ของ leaf items พร้อมปริมาณรวม (MRP/cost)
  - where_used()        : reverse lookup — component นี้ถูกใช้ในการผลิต FG ตัวไหนบ้าง
  - rollup_cost()       : คำนวณ cost ของ parent item จาก components (recursive)

หมายเหตุ:
  - ระบบนี้เป็น Multi-level BOM — แต่ละ SEMI/FG มี BillOfMaterial ของตัวเอง
  - ถ้า component เป็น SEMI/FG ที่มี BOM อยู่ → recursive ลงไป
  - ถ้า component ไม่มี BOM → ถือเป็น leaf (raw material / purchased component)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from core.models.bill_of_material import BillOfMaterial
from core.models.bill_of_material_item_master import BillOfMaterialItemMaster
from core.models.item_list import Item_list


DEFAULT_MAX_DEPTH = 15


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ExplodedNode:
    """1 node ใน BOM tree"""
    item: Item_list
    level: int = 0
    qty_per_parent: Decimal = Decimal("1")   # ใช้ต่อ 1 parent (เช่น BOM qty = 2)
    qty_total: Decimal = Decimal("1")         # ปริมาณสะสมรวม scrap
    scrap_percent: Decimal = Decimal("0")
    process: str = ""
    bom: Optional[BillOfMaterial] = None      # BOM ที่ใช้ (ถ้าเป็น manufactured)
    children: list["ExplodedNode"] = field(default_factory=list)
    is_leaf: bool = True                      # True = ไม่มี BOM ลึกลงไป
    path: list[str] = field(default_factory=list)  # SKU chain จาก root

    @property
    def sku(self) -> str:
        return self.item.sku

    @property
    def has_cycle(self) -> bool:
        # path includes self at the end — cycle = self.sku ปรากฏซ้ำใน ancestor chain
        if not self.path:
            return False
        return self.path.count(self.sku) > 1


@dataclass
class RequirementLine:
    """1 บรรทัดในผลลัพธ์ flat (aggregate) — ใช้สำหรับ MRP/cost"""
    item: Item_list
    total_qty: Decimal              # รวมจากทุก path ใน tree แล้ว
    unit: str
    appears_in: int = 1             # จำนวนครั้งที่พบใน tree


# ─────────────────────────────────────────────────────────────────────────────
# Core helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_active_bom(item: Item_list, revision: Optional[str] = None) -> Optional[BillOfMaterial]:
    """หา BOM ที่ active ที่สุดของ item นี้ — ถ้าไม่มี return None"""
    qs = BillOfMaterial.objects.filter(item=item, is_active=True)
    if revision:
        qs = qs.filter(revision=revision)
    return qs.order_by("-updated_at").first()


def _effective_scrap(bom_item: BillOfMaterialItemMaster) -> Decimal:
    """scrap ของ component → ถ้ามีของตัวเองใช้อันนั้น ไม่งั้นใช้ของ BOM header"""
    if bom_item.scrap_percent and bom_item.scrap_percent > 0:
        return Decimal(str(bom_item.scrap_percent))
    return Decimal(str(bom_item.bom.scrap_percent))


# ─────────────────────────────────────────────────────────────────────────────
# (1) BOM Explosion → Tree
# ─────────────────────────────────────────────────────────────────────────────

def explode_bom_tree(
    item: Item_list,
    qty: Decimal | int | float = 1,
    revision: Optional[str] = None,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> ExplodedNode:
    """
    Explode BOM ของ `item` ออกเป็น tree โดยคูณกับ `qty`

    ตัวอย่าง:
        >>> fg = Item_list.objects.get(sku="EHT-13")
        >>> root = explode_bom_tree(fg, qty=100)
        >>> print(root.qty_total)          # 100
        >>> for child in root.children:
        ...     print(child.item.sku, child.qty_total)
    """
    qty = Decimal(str(qty))
    root = ExplodedNode(item=item, level=0, qty_per_parent=qty, qty_total=qty,
                        path=[item.sku])
    _expand(root, revision=revision, max_depth=max_depth)
    return root


def _expand(
    node: ExplodedNode,
    revision: Optional[str],
    max_depth: int,
) -> None:
    """recursive helper สำหรับ expand BOM"""
    if node.has_cycle:
        return

    # ตรวจสอบก่อนว่า item นี้มี BOM หรือไม่ (เพื่อให้ is_leaf ถูกต้อง
    # แม้จะไม่ได้ expand ลึกต่อเพราะถึง max_depth)
    bom = _get_active_bom(node.item, revision=revision)
    if not bom:
        return  # ไม่มี BOM → leaf จริงๆ

    node.bom = bom
    node.is_leaf = False  # บอกว่า item นี้ยังเจาะลึกต่อได้

    # ถ้าถึง max_depth แล้วก็ไม่โหลด children ต่อ (แต่ is_leaf=False แล้ว → UI รู้ว่า drill-down ได้)
    if node.level >= max_depth:
        return

    # ดึง BOM items พร้อม prefetch
    bom_items = (
        BillOfMaterialItemMaster.objects
        .filter(bom=bom, is_active=True)
        .select_related("component")
        .order_by("sequence")
    )

    for bi in bom_items:
        scrap = _effective_scrap(bi)
        qty_per = Decimal(str(bi.quantity))
        # ปริมาณสะสมรวม scrap
        qty_total = node.qty_total * qty_per * (Decimal("1") + scrap / Decimal("100"))

        child = ExplodedNode(
            item=bi.component,
            level=node.level + 1,
            qty_per_parent=qty_per,
            qty_total=qty_total,
            scrap_percent=scrap,
            process=bi.process or bi.component.item_type,
            path=node.path + [bi.component.sku],
        )
        _expand(child, revision=revision, max_depth=max_depth)
        node.children.append(child)


# ─────────────────────────────────────────────────────────────────────────────
# (2) BOM Explosion → Flat list (aggregate)
# ─────────────────────────────────────────────────────────────────────────────

def explode_bom_flat(
    item: Item_list,
    qty: Decimal | int | float = 1,
    revision: Optional[str] = None,
    leaf_only: bool = True,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> list[RequirementLine]:
    """
    Explode BOM เป็น flat list — aggregate qty ของ item เดียวกันที่พบหลายที่

    Args:
        leaf_only: True = เฉพาะ leaf (raw/component ไม่มี BOM)
                   False = รวม sub-assembly ด้วย

    Returns: list ของ RequirementLine เรียงจาก total_qty มากไปน้อย
    """
    tree = explode_bom_tree(item, qty=qty, revision=revision, max_depth=max_depth)
    agg: dict[str, RequirementLine] = {}

    def _walk(node: ExplodedNode):
        if node.level > 0:  # ไม่รวม root (FG)
            include = node.is_leaf if leaf_only else True
            if include:
                key = node.item.sku
                if key in agg:
                    agg[key].total_qty += node.qty_total
                    agg[key].appears_in += 1
                else:
                    agg[key] = RequirementLine(
                        item=node.item,
                        total_qty=node.qty_total,
                        unit=node.item.unit,
                        appears_in=1,
                    )
        for child in node.children:
            _walk(child)

    _walk(tree)
    return sorted(agg.values(), key=lambda r: -r.total_qty)


# ─────────────────────────────────────────────────────────────────────────────
# (3) Where Used — Reverse BOM lookup
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class WhereUsedEntry:
    parent_item: Item_list      # item ที่ใช้ component นี้ใน BOM
    bom: BillOfMaterial
    quantity: Decimal
    process: str
    level: int = 1              # depth จาก component (1 = parent ตรงๆ)


def where_used(
    component: Item_list,
    max_depth: int = DEFAULT_MAX_DEPTH,
    direct_only: bool = False,
) -> list[WhereUsedEntry]:
    """
    หาว่า `component` ถูกใช้ใน BOM ของ item ไหนบ้าง (reverse lookup)

    Args:
        direct_only: True = เฉพาะ parent ตรง (level 1)
                     False = ไต่ขึ้นไปหา FG ทั้งหมดที่ใช้ component นี้
    """
    results: list[WhereUsedEntry] = []
    visited: set[str] = set()

    def _walk(comp: Item_list, level: int):
        if level > max_depth or comp.sku in visited:
            return
        visited.add(comp.sku)

        # หา BOMItemMaster ที่ component = comp
        usages = (
            BillOfMaterialItemMaster.objects
            .filter(component=comp, is_active=True)
            .select_related("bom", "bom__item")
        )
        for u in usages:
            if not u.bom.is_active:
                continue
            entry = WhereUsedEntry(
                parent_item=u.bom.item,
                bom=u.bom,
                quantity=Decimal(str(u.quantity)),
                process=u.process,
                level=level,
            )
            results.append(entry)

            if not direct_only:
                _walk(u.bom.item, level + 1)

    _walk(component, level=1)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# (4) Cost Rollup
# ─────────────────────────────────────────────────────────────────────────────

def rollup_cost(
    item: Item_list,
    revision: Optional[str] = None,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> Decimal:
    """
    คำนวณ cost ของ item จาก components ที่ใช้ประกอบ (recursive)

    กฎ:
      - ถ้า item ไม่มี BOM → ใช้ item.cost หรือ item.purchased_price
      - ถ้ามี BOM → Σ(component_cost × qty × (1 + scrap%))

    Note: ยังไม่รวม labor/overhead — เป็น material cost ล้วนๆ
    """
    tree = explode_bom_tree(item, qty=1, revision=revision, max_depth=max_depth)
    return _calc_cost(tree)


def _calc_cost(node: ExplodedNode) -> Decimal:
    if node.is_leaf or not node.children:
        # ใช้ cost ของ item (fallback → purchased_price)
        base = Decimal(str(node.item.cost or 0))
        if base == 0:
            base = Decimal(str(node.item.purchased_price or 0))
        return base * node.qty_per_parent

    total = Decimal("0")
    for child in node.children:
        child_cost_per = _calc_cost(child)  # cost ต่อ 1 unit ของ parent
        with_scrap = child_cost_per * (Decimal("1") + child.scrap_percent / Decimal("100"))
        total += with_scrap
    return total * node.qty_per_parent


# ─────────────────────────────────────────────────────────────────────────────
# (5) Helper: summary สำหรับแสดงผล
# ─────────────────────────────────────────────────────────────────────────────

def tree_summary(tree: ExplodedNode) -> dict:
    """สรุปสถิติจาก tree — จำนวน leaf, max depth, total nodes"""
    stats = {"total_nodes": 0, "leaf_count": 0, "max_depth": 0,
             "has_cycles": False, "unique_skus": set()}

    def _walk(n: ExplodedNode):
        stats["total_nodes"] += 1
        stats["max_depth"] = max(stats["max_depth"], n.level)
        stats["unique_skus"].add(n.sku)
        if n.has_cycle:
            stats["has_cycles"] = True
        if n.is_leaf:
            stats["leaf_count"] += 1
        for c in n.children:
            _walk(c)

    _walk(tree)
    stats["unique_skus"] = len(stats["unique_skus"])
    return stats
