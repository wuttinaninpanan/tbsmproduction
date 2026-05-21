from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from core.auth.decorators import staff_required
from core.models.item_category import ItemCategory
from core.models.item_line import ItemLine
from core.models.item_list import Item_list
from core.models.item_stage import ItemStage
from core.models.line import Line


def _is_uuid(value: str) -> bool:
	try:
		uuid.UUID(str(value))
	except Exception:
		return False
	return True


def _safe_decimal(value, default: Decimal = Decimal("0")) -> Decimal:
	if value is None:
		return default
	if isinstance(value, Decimal):
		return value
	value = str(value).strip()
	if value == "":
		return default
	try:
		return Decimal(value)
	except (InvalidOperation, ValueError):
		return default


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
class ProductsView(TemplateView):
	"""Read-only listing of items that have at least one ItemLine assignment."""
	template_name = "products.html"

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
			.filter(id__in=ItemLine.objects.values("item_id"))
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
				| Q(portion__title__icontains=q)
				| Q(side__title__icontains=q)
				| Q(inout__title__icontains=q)
				| Q(way__title__icontains=q)
				| Q(comment__icontains=q)
			)

		# Map item_id -> list of line names so we can show all assigned lines.
		item_ids = list(qs.values_list("id", flat=True))
		lines_by_item: dict = {}
		if item_ids:
			for il in (
				ItemLine.objects
				.filter(item_id__in=item_ids)
				.select_related("line")
			):
				lines_by_item.setdefault(il.item_id, []).append(
					getattr(il.line, "line_name", "") or ""
				)

		paginator = Paginator(qs, per_page)
		page_obj = paginator.get_page(page)

		rows = []
		for item in page_obj.object_list:
			line_names = lines_by_item.get(item.id, [])
			image_url = ""
			try:
				if getattr(item, "reference_image", None):
					image_url = item.reference_image.url
			except Exception:
				image_url = ""
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
		ctx["lines"] = list(Line.objects.order_by("line_name").values("id", "line_name"))
		return ctx

	def post(self, request, *args, **kwargs):
		action = (request.POST.get("action") or "").strip().lower()
		if action == "create_item":
			return self._handle_create_item(request)
		if action == "delete_item":
			return self._handle_delete_item(request)
		messages.error(request, "ไม่รองรับการทำงานนี้")
		return redirect(request.get_full_path())

	def _resolve_fk(self, model, value):
		value = (value or "").strip()
		if not value or not _is_uuid(value):
			return None
		return model.objects.filter(pk=value).first()

	def _handle_create_item(self, request):
		sd_code = (request.POST.get("sd_code") or "").strip()
		part_number = (request.POST.get("part_number") or "").strip()
		part_name = (request.POST.get("part_name") or "").strip()
		sku = (request.POST.get("sku") or "").strip()
		weight = _safe_decimal(request.POST.get("weight") or "0")
		cost = _safe_decimal(request.POST.get("cost") or "0")
		purchased_price = _safe_decimal(request.POST.get("purchased_price") or "0")
		comment = (request.POST.get("comment") or "").strip()

		if not part_number or not part_name or not sku:
			messages.error(request, "กรุณากรอก Part Number / Part Name / SKU")
			return redirect(request.get_full_path())

		# กัน SD Code ซ้ำ: เครื่องตรวจหา Item_list ด้วย sd_code ถ้ามีหลายแถว
		# จะ map ไม่ได้แล้วบันทึกผลเป็น NULL (ดูเคส DAR-46 ที่ถูกเพิ่มซ้ำ 3 แถว)
		if sd_code and Item_list.objects.filter(sd_code=sd_code).exists():
			messages.error(request, f"มี SD Code \"{sd_code}\" อยู่แล้ว — ห้ามเพิ่มซ้ำ (ถ้าต้องการแก้ไข ให้เข้าไปแก้ที่รายการเดิม)")
			return redirect(request.get_full_path())

		category = self._resolve_fk(ItemCategory, request.POST.get("category_id"))
		stage = self._resolve_fk(ItemStage, request.POST.get("stage_id"))

		line_ids = [
			(v or "").strip()
			for v in request.POST.getlist("line_ids")
			if (v or "").strip() and _is_uuid((v or "").strip())
		]

		try:
			with transaction.atomic():
				item = Item_list(
					sd_code=sd_code,
					part_number=part_number,
					part_name=part_name,
					sku=sku,
					weight=weight,
					cost=cost,
					purchased_price=purchased_price,
					comment=comment,
					category=category,
					stage=stage,
					user=request.user,
				)
				item.save()

				if line_ids:
					if stage is None:
						messages.warning(request, "ข้าม Line: ต้องเลือก Stage ก่อนผูก Line")
					else:
						for lid in line_ids:
							line_obj = Line.objects.filter(pk=lid).first()
							if line_obj is None:
								continue
							ItemLine.objects.create(
								item=item,
								line=line_obj,
								item_stage=stage,
								user=request.user,
							)
		except IntegrityError as e:
			messages.error(request, f"เพิ่มไม่สำเร็จ (ข้อมูลซ้ำ): {e}")
			return redirect(request.get_full_path())
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
			return redirect(request.get_full_path())

		messages.success(request, "เพิ่ม Product สำเร็จ")
		return redirect(request.get_full_path())

	def _handle_delete_item(self, request):
		item_id = (request.POST.get("id") or "").strip()
		if not _is_uuid(item_id):
			messages.error(request, "ไม่พบรหัสรายการ")
			return redirect(request.get_full_path())
		item = Item_list.objects.filter(pk=item_id).first()
		if item is None:
			messages.error(request, "ไม่พบรายการ")
			return redirect(request.get_full_path())
		try:
			with transaction.atomic():
				item.delete()
		except ProtectedError:
			messages.error(
				request,
				"ลบไม่ได้: รายการนี้ถูกใช้งานอยู่ (เป็น Component ใน BOM อื่น / มี Scrap / Defect Stat)"
			)
			return redirect(request.get_full_path())
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
			return redirect(request.get_full_path())
		messages.success(request, "ลบ Product สำเร็จ")
		return redirect(request.get_full_path())
