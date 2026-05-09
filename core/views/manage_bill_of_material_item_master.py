from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from core.auth.decorators import staff_required
from core.models.bill_of_material import BillOfMaterial
from core.models.bill_of_material_item_master import BillOfMaterialItemMater
from core.models.item_list import Item_list
from core.services.auditlog import log_event


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


def _safe_decimal(value, default: Decimal = Decimal("0")) -> Decimal:
	if value is None:
		return default
	if isinstance(value, Decimal):
		return value
	if isinstance(value, (int, float)):
		try:
			return Decimal(str(value))
		except (InvalidOperation, ValueError):
			return default
	value = str(value).strip()
	if value == "":
		return default
	try:
		return Decimal(value)
	except (InvalidOperation, ValueError):
		return default


@method_decorator(staff_required, name="dispatch")
class ManageBillOfMaterialItemMasterViews(TemplateView):
	template_name = "mange_bill_of_material_item_master.html"

	def get_context_data(self, **kwargs):
		ctx = super().get_context_data(**kwargs)
		request = self.request

		q = (request.GET.get("q") or "").strip()
		per_page_raw = (request.GET.get("per_page") or "").strip()
		page = (request.GET.get("page") or "1").strip() or "1"

		allowed_per_page = {20, 50, 100, 200}
		try:
			per_page = int(per_page_raw or 20)
		except Exception:
			per_page = 20
		if per_page not in allowed_per_page:
			per_page = 20

		qs = BillOfMaterialItemMater.objects.select_related(
			"bom__item", "component"
		).all()
		if q:
			qs = qs.filter(
				Q(bom__item__sd_code__icontains=q)
				| Q(component__sd_code__icontains=q)
				| Q(component__part_name__icontains=q)
				| Q(unit__icontains=q)
			)
		qs = qs.order_by("bom__item__sd_code", "bom__revision", "sequence")
		paginator = Paginator(qs, per_page)
		page_obj = paginator.get_page(page)

		rows = []
		for obj in page_obj.object_list:
			rows.append({
				"id": str(obj.id),
				"bom_id": str(obj.bom_id) if obj.bom_id else "",
				"bom_sd_code": getattr(obj.bom.item, "sd_code", "") if obj.bom_id and obj.bom.item_id else "",
				"bom_revision": getattr(obj.bom, "revision", "") if obj.bom_id else "",
				"component_id": str(obj.component_id) if obj.component_id else "",
				"component_sd_code": getattr(obj.component, "sd_code", "") if obj.component_id else "",
				"component_part_name": getattr(obj.component, "part_name", "") if obj.component_id else "",
				"quantity": str(obj.quantity),
				"unit": obj.unit,
				"sequence": obj.sequence,
			})

		ctx["rows"] = rows
		ctx["q"] = q
		ctx["page_obj"] = page_obj
		ctx["paginator"] = paginator
		ctx["per_page"] = per_page
		ctx["rows_total"] = paginator.count
		ctx["page_items"] = _page_items(paginator.num_pages, page_obj.number)
		ctx["total_count"] = paginator.count
		ctx["boms"] = list(
			BillOfMaterial.objects.select_related("item")
			.order_by("item__sd_code", "revision")
			.values("id", "revision", "item__sd_code")
		)
		ctx["components"] = list(
			Item_list.objects.order_by("sd_code").values("id", "sd_code", "part_name")
		)
		return ctx

	def post(self, request, *args, **kwargs):
		action = (request.POST.get("action") or "").strip().lower()
		obj_id = (request.POST.get("id") or "").strip()

		if action == "bulk_delete":
			bulk_ids = request.POST.getlist("bulk_id")
			ids = [pk for pk in bulk_ids if _is_uuid((pk or "").strip())]
			if not ids:
				messages.error(request, "กรุณาเลือกรายการที่ต้องการลบ")
				return self.get(request, *args, **kwargs)

			deleted = 0
			blocked = 0
			not_found = 0
			try:
				with transaction.atomic():
					for pk in ids:
						obj = BillOfMaterialItemMater.objects.filter(pk=pk).first()
						if obj is None:
							not_found += 1
							continue
						try:
							obj.delete()
							deleted += 1
						except ProtectedError:
							blocked += 1
			except Exception as e:
				messages.error(request, f"เกิดข้อผิดพลาด: {e}")
				return self.get(request, *args, **kwargs)

			if blocked:
				messages.warning(request, f"ลบสำเร็จ {deleted} รายการ (ลบไม่ได้ {blocked}, ไม่พบ {not_found})")
			else:
				messages.success(request, f"ลบสำเร็จ {deleted} รายการ")
			return self.get(request, *args, **kwargs)

		if action in {"update", "delete"}:
			if not _is_uuid(obj_id):
				messages.error(request, "ไม่พบรหัสรายการ")
				return self.get(request, *args, **kwargs)

		if action == "delete":
			obj = BillOfMaterialItemMater.objects.filter(pk=obj_id).first()
			if obj is None:
				messages.error(request, "ไม่พบรายการ")
				return self.get(request, *args, **kwargs)
			try:
				obj.delete()
			except ProtectedError:
				messages.error(request, "ไม่สามารถลบได้: รายการนี้ถูกใช้งานอยู่")
				return self.get(request, *args, **kwargs)
			transaction.on_commit(
				lambda: log_event(
					request,
					action="bom_item:delete",
					message="ลบ BOM Item Master",
					metadata={"id": obj_id},
				)
			)
			messages.success(request, "ลบรายการสำเร็จ")
			return self.get(request, *args, **kwargs)

		# Shared fields for create / update
		bom_id = (request.POST.get("bom_id") or "").strip()
		component_id = (request.POST.get("component_id") or "").strip()
		quantity_raw = (request.POST.get("quantity") or "").strip()
		unit = (request.POST.get("unit") or "").strip()
		sequence_raw = (request.POST.get("sequence") or "1").strip() or "1"

		if not _is_uuid(bom_id):
			messages.error(request, "กรุณาเลือก BOM")
			return self.get(request, *args, **kwargs)
		if not _is_uuid(component_id):
			messages.error(request, "กรุณาเลือก Component")
			return self.get(request, *args, **kwargs)

		bom = BillOfMaterial.objects.filter(pk=bom_id).first()
		if bom is None:
			messages.error(request, "ไม่พบ BOM")
			return self.get(request, *args, **kwargs)
		component = Item_list.objects.filter(pk=component_id).first()
		if component is None:
			messages.error(request, "ไม่พบ Component")
			return self.get(request, *args, **kwargs)
		if not unit:
			messages.error(request, "กรุณาระบุ Unit")
			return self.get(request, *args, **kwargs)

		quantity = _safe_decimal(quantity_raw, default=Decimal("0"))
		try:
			sequence = int(sequence_raw)
		except (ValueError, TypeError):
			sequence = 1

		if action == "update":
			obj = BillOfMaterialItemMater.objects.filter(pk=obj_id).first()
			if obj is None:
				messages.error(request, "ไม่พบรายการ")
				return self.get(request, *args, **kwargs)
			obj.bom = bom
			obj.component = component
			obj.quantity = quantity
			obj.unit = unit
			obj.sequence = sequence
			try:
				obj.save(update_fields=["bom", "component", "quantity", "unit", "sequence", "updated_at"])
			except Exception as e:
				messages.error(request, f"บันทึกไม่สำเร็จ: {e}")
				return self.get(request, *args, **kwargs)
			transaction.on_commit(
				lambda: log_event(
					request,
					action="bom_item:update",
					message="แก้ไข BOM Item Master",
					metadata={"id": obj_id},
				)
			)
			messages.success(request, "แก้ไขรายการสำเร็จ")
			return self.get(request, *args, **kwargs)

		# Default: create
		try:
			obj = BillOfMaterialItemMater.objects.create(
				bom=bom,
				component=component,
				quantity=quantity,
				unit=unit,
				sequence=sequence,
				user=request.user,
			)
		except Exception as e:
			log_event(
				request,
				action="bom_item:create",
				status="failure",
				message="เพิ่ม BOM Item Master ไม่สำเร็จ",
				metadata={"error": str(e)},
			)
			messages.error(request, f"เพิ่มข้อมูลไม่สำเร็จ: {e}")
			return self.get(request, *args, **kwargs)

		transaction.on_commit(
			lambda: log_event(
				request,
				action="bom_item:create",
				message="เพิ่ม BOM Item Master",
				metadata={"id": str(obj.id)},
			)
		)
		messages.success(request, "เพิ่มข้อมูลสำเร็จ")
		return self.get(request, *args, **kwargs)
