from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from core.auth.decorators import staff_required
from core.models.bill_of_material import BillOfMaterial
from core.models.bill_of_material_item_master import BillOfMaterialItemMater
from core.models.inout import InOut
from core.models.item_category import ItemCategory
from core.models.item_line import ItemLine
from core.models.item_list import Item_list
from core.models.item_stage import ItemStage
from core.models.line import Line
from core.models.line_process import LineProcess
from core.models.portion import Portion
from core.models.side import Side
from core.models.way import Way


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
class ProductDetailView(TemplateView):
	"""Single-page editor for an FG item: top section edits the Item itself,
	bottom section manages the BOM components that make up this FG."""

	template_name = "core/product_detail.html"

	def get_item(self, item_id):
		if not _is_uuid(item_id):
			raise Http404("Invalid item id")
		item = (
			Item_list.objects
			.select_related("category", "stage", "portion", "side", "inout", "way")
			.filter(pk=item_id)
			.first()
		)
		if item is None:
			raise Http404("Item not found")
		return item

	def get_context_data(self, **kwargs):
		ctx = super().get_context_data(**kwargs)
		item_id = kwargs.get("item_id")
		item = self.get_item(item_id)

		bom = BillOfMaterial.objects.filter(item=item).first()

		bom_rows = []
		if bom is not None:
			qs = (
				BillOfMaterialItemMater.objects
				.filter(bom=bom)
				.select_related("component", "component__category", "component__stage")
				.order_by("sequence")
			)
			for obj in qs:
				comp = obj.component
				bom_rows.append({
					"id": str(obj.id),
					"component_id": str(comp.id) if comp else "",
					"component_item_code": getattr(comp, "item_code", "") or "",
					"component_sd_code": getattr(comp, "sd_code", "") or "",
					"component_part_number": getattr(comp, "part_number", "") or "",
					"component_part_name": getattr(comp, "part_name", "") or "",
					"quantity": str(obj.quantity),
					"unit": obj.unit,
					"sequence": obj.sequence,
				})

		ctx["item"] = item
		ctx["item_id"] = str(item.id)
		ctx["bom"] = bom
		ctx["bom_rows"] = bom_rows
		ctx["categories"] = list(ItemCategory.objects.order_by("name").values("id", "name"))
		ctx["stages"] = list(
			ItemStage.objects.order_by("display_name").values("id", "display_name", "code_prefix")
		)
		ctx["portions"] = list(Portion.objects.order_by("title").values("id", "title"))
		ctx["sides"] = list(Side.objects.order_by("title").values("id", "title"))
		ctx["inouts"] = list(InOut.objects.order_by("title").values("id", "title"))
		ctx["ways"] = list(Way.objects.order_by("title").values("id", "title"))
		ctx["lines"] = list(Line.objects.order_by("line_name").values("id", "line_name"))
		ctx["components"] = list(
			Item_list.objects.order_by("sd_code", "part_number").values(
				"id", "sd_code", "part_number", "part_name"
			)
		)

		# Currently linked ItemLines for this item (so the form can preselect)
		ctx["item_line_ids"] = list(
			ItemLine.objects.filter(item=item).values_list("line_id", flat=True)
		)
		return ctx

	def post(self, request, *args, **kwargs):
		item_id = kwargs.get("item_id")
		item = self.get_item(item_id)
		action = (request.POST.get("action") or "").strip().lower()

		if action == "update_item":
			return self._handle_update_item(request, item)
		if action == "add_component":
			return self._handle_add_component(request, item)
		if action == "update_component":
			return self._handle_update_component(request, item)
		if action == "delete_component":
			return self._handle_delete_component(request, item)

		messages.error(request, "ไม่รองรับการทำงานนี้")
		return redirect(reverse("product_detail", args=[item.id]))

	def _handle_update_item(self, request, item):
		sd_code = (request.POST.get("sd_code") or "").strip()
		part_number = (request.POST.get("part_number") or "").strip()
		part_name = (request.POST.get("part_name") or "").strip()
		sku = (request.POST.get("sku") or item.sku).strip()
		weight = _safe_decimal(request.POST.get("weight") or "0")
		cost = _safe_decimal(request.POST.get("cost") or "0")
		purchased_price = _safe_decimal(request.POST.get("purchased_price") or "0")
		comment = (request.POST.get("comment") or "").strip()
		reference_image = request.FILES.get("reference_image")
		clear_image = (request.POST.get("clear_image") or "").strip() in {"1", "true", "on", "yes"}

		if not sd_code or not part_number or not part_name:
			messages.error(request, "กรุณากรอก SD Code / Part number / Part name")
			return redirect(reverse("product_detail", args=[item.id]))

		def _resolve(model, value):
			value = (value or "").strip()
			if not value or not _is_uuid(value):
				return None
			return model.objects.filter(pk=value).first()

		category = _resolve(ItemCategory, request.POST.get("category_id"))
		stage = _resolve(ItemStage, request.POST.get("stage_id"))
		portion = _resolve(Portion, request.POST.get("portion_id"))
		side = _resolve(Side, request.POST.get("side_id"))
		inout = _resolve(InOut, request.POST.get("inout_id"))
		way = _resolve(Way, request.POST.get("way_id"))

		try:
			with transaction.atomic():
				item.sd_code = sd_code
				item.part_number = part_number
				item.part_name = part_name
				item.sku = sku
				item.weight = weight
				item.cost = cost
				item.purchased_price = purchased_price
				item.comment = comment
				item.category = category
				item.stage = stage
				item.portion = portion
				item.side = side
				item.inout = inout
				item.way = way
				# Reference image: clear, replace, or leave as-is.
				if clear_image:
					if item.reference_image:
						item.reference_image.delete(save=False)
					item.reference_image = None
				elif reference_image is not None:
					if item.reference_image:
						item.reference_image.delete(save=False)
					item.reference_image = reference_image
				# Full save() so the model auto-generates item_code if stage is
				# newly set and item_code is empty.
				item.save()

				# Reconcile ItemLine assignments with the selected lines.
				# `line_ids` may contain a mix of UUIDs (existing Line rows) and
				# free-text strings entered via Tom Select's create-on-the-fly —
				# resolve each input to a Line, creating new ones as needed.
				raw_line_inputs = [
					(v or "").strip() for v in request.POST.getlist("line_ids") if (v or "").strip()
				]
				default_line_process = LineProcess.objects.first()
				selected_line_ids: list = []
				for raw in raw_line_inputs:
					if _is_uuid(raw):
						selected_line_ids.append(raw)
						continue
					line_obj = Line.objects.filter(line_name__iexact=raw).first()
					if line_obj is None:
						if default_line_process is None:
							messages.warning(
								request,
								f"ข้าม Line ใหม่ '{raw}' — ต้องสร้าง LineProcess ก่อน",
							)
							continue
						line_obj = Line.objects.create(
							line_name=raw,
							line_process=default_line_process,
							user=request.user,
						)
					selected_line_ids.append(str(line_obj.id))

				current_links = {
					str(il.line_id): il
					for il in ItemLine.objects.filter(item=item).select_related("item_stage")
				}
				stage_for_link = item.stage
				for lid in selected_line_ids:
					if lid in current_links:
						continue
					line_obj = Line.objects.filter(pk=lid).first()
					if line_obj is None:
						continue
					if stage_for_link is None:
						messages.warning(
							request,
							"ต้องเลือก Stage ก่อนผูก Line — Line บางรายการยังไม่ถูกบันทึก",
						)
						continue
					ItemLine.objects.create(
						item=item,
						line=line_obj,
						item_stage=stage_for_link,
						user=request.user,
					)
				for lid, il in current_links.items():
					if lid not in selected_line_ids:
						il.delete()
		except IntegrityError as e:
			messages.error(request, f"บันทึกไม่สำเร็จ (ข้อมูลซ้ำ): {e}")
			return redirect(reverse("product_detail", args=[item.id]))
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
			return redirect(reverse("product_detail", args=[item.id]))

		messages.success(request, "บันทึกการแก้ไขสำเร็จ")
		return redirect(reverse("product_detail", args=[item.id]))

	def _ensure_bom(self, item, request):
		bom, _ = BillOfMaterial.objects.get_or_create(
			item=item,
			defaults={
				"revision": "A",
				"latest_eci": "",
				"user": request.user,
			},
		)
		return bom

	def _handle_add_component(self, request, item):
		component_id = (request.POST.get("component_id") or "").strip()
		quantity = _safe_decimal(request.POST.get("quantity") or "1", default=Decimal("1"))
		unit = (request.POST.get("unit") or "PCS").strip() or "PCS"
		sequence_raw = (request.POST.get("sequence") or "").strip()

		if not _is_uuid(component_id):
			messages.error(request, "กรุณาเลือก Component")
			return redirect(reverse("product_detail", args=[item.id]))
		component = Item_list.objects.filter(pk=component_id).first()
		if component is None:
			messages.error(request, "ไม่พบ Component")
			return redirect(reverse("product_detail", args=[item.id]))
		if component.id == item.id:
			messages.error(request, "ไม่สามารถเลือกตัวเองเป็น Component ได้")
			return redirect(reverse("product_detail", args=[item.id]))

		bom = self._ensure_bom(item, request)
		if BillOfMaterialItemMater.objects.filter(bom=bom, component=component).exists():
			messages.warning(request, "Component นี้อยู่ใน BOM อยู่แล้ว")
			return redirect(reverse("product_detail", args=[item.id]))

		try:
			sequence = int(sequence_raw) if sequence_raw else None
		except (ValueError, TypeError):
			sequence = None
		if sequence is None:
			last = BillOfMaterialItemMater.objects.filter(bom=bom).order_by("-sequence").first()
			sequence = (last.sequence + 1) if last and last.sequence else 1

		try:
			BillOfMaterialItemMater.objects.create(
				bom=bom,
				component=component,
				quantity=quantity,
				unit=unit,
				sequence=sequence,
				user=request.user,
			)
		except Exception as e:
			messages.error(request, f"เพิ่มไม่สำเร็จ: {e}")
			return redirect(reverse("product_detail", args=[item.id]))

		messages.success(request, "เพิ่ม Component สำเร็จ")
		return redirect(reverse("product_detail", args=[item.id]))

	def _handle_update_component(self, request, item):
		bom_item_id = (request.POST.get("bom_item_id") or "").strip()
		quantity = _safe_decimal(request.POST.get("quantity") or "1", default=Decimal("1"))
		unit = (request.POST.get("unit") or "PCS").strip() or "PCS"
		sequence_raw = (request.POST.get("sequence") or "").strip()

		if not _is_uuid(bom_item_id):
			messages.error(request, "ไม่พบรายการ")
			return redirect(reverse("product_detail", args=[item.id]))

		obj = BillOfMaterialItemMater.objects.filter(pk=bom_item_id, bom__item=item).first()
		if obj is None:
			messages.error(request, "ไม่พบรายการ Component")
			return redirect(reverse("product_detail", args=[item.id]))

		try:
			sequence = int(sequence_raw) if sequence_raw else obj.sequence
		except (ValueError, TypeError):
			sequence = obj.sequence

		obj.quantity = quantity
		obj.unit = unit
		obj.sequence = sequence
		try:
			obj.save(update_fields=["quantity", "unit", "sequence", "updated_at"])
		except Exception as e:
			messages.error(request, f"แก้ไขไม่สำเร็จ: {e}")
			return redirect(reverse("product_detail", args=[item.id]))

		messages.success(request, "แก้ไข Component สำเร็จ")
		return redirect(reverse("product_detail", args=[item.id]))

	def _handle_delete_component(self, request, item):
		bom_item_id = (request.POST.get("bom_item_id") or "").strip()
		if not _is_uuid(bom_item_id):
			messages.error(request, "ไม่พบรายการ")
			return redirect(reverse("product_detail", args=[item.id]))
		obj = BillOfMaterialItemMater.objects.filter(pk=bom_item_id, bom__item=item).first()
		if obj is None:
			messages.error(request, "ไม่พบรายการ Component")
			return redirect(reverse("product_detail", args=[item.id]))
		try:
			obj.delete()
		except ProtectedError:
			messages.error(request, "ลบไม่ได้: รายการนี้ถูกใช้งานอยู่")
			return redirect(reverse("product_detail", args=[item.id]))
		messages.success(request, "ลบ Component สำเร็จ")
		return redirect(reverse("product_detail", args=[item.id]))
