from __future__ import annotations

from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from core.auth.decorators import staff_required
from core.models.item_category import ItemCategory
from core.models.item_line import ItemLine
from core.models.item_list import Item_list
from core.models.item_stage import ItemStage


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
class ItemListView(TemplateView):
    """Read-only listing of EVERY item in Item_list (FG, components, raw materials),
    regardless of Line assignment. (อ่านอย่างเดียว)"""

    template_name = "item_list.html"

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

        qs = (
            Item_list.objects
            .select_related("category", "stage", "portion", "side", "inout", "way")
            .order_by("item_code", "sd_code")
        )
        if q:
            qs = qs.filter(
                Q(item_code__icontains=q)
                | Q(sd_code__icontains=q)
                | Q(part_number__icontains=q)
                | Q(part_name__icontains=q)
                | Q(sku__icontains=q)
                | Q(category__name__icontains=q)
                | Q(stage__display_name__icontains=q)
                | Q(portion__title__icontains=q)
                | Q(side__title__icontains=q)
                | Q(inout__title__icontains=q)
                | Q(way__title__icontains=q)
                | Q(comment__icontains=q)
            )

        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)

        # Map item_id -> line names (for the items shown on this page only).
        page_item_ids = [obj.id for obj in page_obj.object_list]
        lines_by_item: dict = {}
        if page_item_ids:
            for il in (
                ItemLine.objects
                .filter(item_id__in=page_item_ids)
                .select_related("line")
            ):
                lines_by_item.setdefault(il.item_id, []).append(
                    getattr(il.line, "line_name", "") or ""
                )

        rows = []
        for item in page_obj.object_list:
            image_url = ""
            try:
                if getattr(item, "reference_image", None):
                    image_url = item.reference_image.url
            except Exception:
                image_url = ""
            line_names = lines_by_item.get(item.id, [])
            rows.append({
                "id": str(item.id),
                "item_code": item.item_code or "",
                "sd_code": item.sd_code or "",
                "part_number": item.part_number or "",
                "part_name": item.part_name or "",
                "reference_image_url": image_url,
                "sku": item.sku or "",
                "weight": str(item.weight),
                "cost": str(item.cost),
                "purchased_price": str(item.purchased_price),
                "category_name": getattr(item.category, "name", "") if item.category_id else "",
                "stage_name": getattr(item.stage, "display_name", "") if item.stage_id else "",
                "portion_name": getattr(item.portion, "title", "") if item.portion_id else "",
                "side_name": getattr(item.side, "title", "") if item.side_id else "",
                "inout_name": getattr(item.inout, "title", "") if item.inout_id else "",
                "way_name": getattr(item.way, "title", "") if item.way_id else "",
                "comment": item.comment or "",
                "line_names": ", ".join(sorted({l for l in line_names if l})),
            })

        ctx["rows"] = rows
        ctx["q"] = q
        ctx["page_obj"] = page_obj
        ctx["paginator"] = paginator
        ctx["per_page"] = per_page
        ctx["rows_total"] = paginator.count
        ctx["page_items"] = _page_items(paginator.num_pages, page_obj.number)
        ctx["total_count"] = paginator.count

        ctx["categories"] = list(ItemCategory.objects.order_by("name").values("id", "name"))
        ctx["stages"] = list(
            ItemStage.objects.order_by("display_name").values("id", "display_name", "code_prefix")
        )
        return ctx
