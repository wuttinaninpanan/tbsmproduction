from __future__ import annotations

import uuid

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from core.auth.decorators import staff_required
from core.models.defect_by_category import DefectByCategory
from core.models.defect_mode import DefectMode
from core.models.item_category import ItemCategory
from core.models.item_stage import ItemStage
from core.models.way import Way
from core.services.auditlog import log_event


TABS = ("item_stage", "item_category", "defect_mode", "way")


def _is_uuid(value: str) -> bool:
	try:
		uuid.UUID(str(value))
	except Exception:
		return False
	return True


def _parse_bool(value) -> bool:
	v = (value or "").strip().lower()
	return v in {"1", "true", "t", "yes", "y", "on"}


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
class ManageSettingsViews(TemplateView):
	template_name = "core/manage_settings.html"

	# ------------------------------------------------------------------ GET

	def get_context_data(self, **kwargs):
		ctx = super().get_context_data(**kwargs)
		request = self.request

		tab = (request.GET.get("tab") or "item_stage").strip().lower()
		if tab not in TABS:
			tab = "item_stage"

		q = (request.GET.get("q") or "").strip()
		page = (request.GET.get("page") or "1").strip() or "1"
		try:
			per_page = int((request.GET.get("per_page") or "100").strip())
		except Exception:
			per_page = 100
		if per_page not in {100, 200, 500, 1000}:
			per_page = 100

		# Build the active section's rows + pagination
		if tab == "item_stage":
			qs = ItemStage.objects.all()
			if q:
				qs = qs.filter(Q(name__icontains=q) | Q(display_name__icontains=q))
			qs = qs.order_by("name")
			paginator = Paginator(qs, per_page)
			page_obj = paginator.get_page(page)
			rows = [
				{"id": str(o.id), "name": o.name, "display_name": o.display_name}
				for o in page_obj.object_list
			]
		elif tab == "item_category":
			# Count only the active (is_inlist=True) defect links — the ones that
			# actually show in the recording dropdown for this category.
			qs = ItemCategory.objects.annotate(
				defect_count=Count("category_defects", filter=Q(category_defects__is_inlist=True))
			)
			if q:
				qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
			qs = qs.order_by("name")
			paginator = Paginator(qs, per_page)
			page_obj = paginator.get_page(page)
			rows = [
				{"id": str(o.id), "name": o.name, "description": o.description, "defect_count": o.defect_count}
				for o in page_obj.object_list
			]
		elif tab == "defect_mode":
			qs = DefectMode.objects.all()
			if q:
				qs = qs.filter(
					Q(name_th__icontains=q)
					| Q(name_en__icontains=q)
					| Q(name_jp__icontains=q)
					| Q(description_th__icontains=q)
					| Q(description_en__icontains=q)
					| Q(description_jp__icontains=q)
				)
			qs = qs.order_by("name_en", "name_th")
			paginator = Paginator(qs, per_page)
			page_obj = paginator.get_page(page)
			rows = [
				{
					"id": str(o.id),
					"name_th": o.name_th,
					"name_en": o.name_en,
					"name_jp": o.name_jp,
					"description_th": o.description_th or "",
					"description_en": o.description_en or "",
					"description_jp": o.description_jp or "",
				}
				for o in page_obj.object_list
			]
		else:  # way
			qs = Way.objects.all()
			if q:
				qs = qs.filter(Q(title__icontains=q))
			qs = qs.order_by("title")
			paginator = Paginator(qs, per_page)
			page_obj = paginator.get_page(page)
			rows = [
				{"id": str(o.id), "title": o.title}
				for o in page_obj.object_list
			]

		ctx["tab"] = tab
		ctx["q"] = q
		ctx["per_page"] = per_page
		ctx["rows"] = rows
		ctx["page_obj"] = page_obj
		ctx["paginator"] = paginator
		ctx["rows_total"] = paginator.count
		ctx["total_count"] = paginator.count
		ctx["page_items"] = _page_items(paginator.num_pages, page_obj.number)

		# Tab totals (lightweight counts for badges)
		ctx["count_item_stage"] = ItemStage.objects.count()
		ctx["count_item_category"] = ItemCategory.objects.count()
		ctx["count_defect_mode"] = DefectMode.objects.count()
		ctx["count_way"] = Way.objects.count()

		# Category options for the "เพิ่มรายการของเสีย" modal (defect_mode tab).
		ctx["categories"] = list(ItemCategory.objects.order_by("name").values("id", "name"))

		return ctx

	# ------------------------------------------------------------------ POST

	def post(self, request, *args, **kwargs):
		action = (request.POST.get("action") or "").strip().lower()

		# Each handler returns either a response (from self.get) or None to fall through.
		handler = {
			# ItemStage
			"stage_create": self._stage_create,
			"stage_update": self._stage_update,
			"stage_delete": self._stage_delete,
			# ItemCategory
			"cat_create": self._cat_create,
			"cat_update": self._cat_update,
			"cat_delete": self._cat_delete,
			# DefectMode
			"defect_create": self._defect_create,
			"defect_update": self._defect_update,
			"defect_delete": self._defect_delete,
			# Way
			"way_create": self._way_create,
			"way_update": self._way_update,
			"way_delete": self._way_delete,
		}.get(action)

		if handler is None:
			messages.error(request, "ไม่รู้จัก action")
			return redirect(request.get_full_path())
		return handler(request, *args, **kwargs)

	# -------------------------------------------------- ItemStage handlers

	def _stage_create(self, request, *args, **kwargs):
		name = (request.POST.get("name") or "").strip()
		display_name = (request.POST.get("display_name") or "").strip()
		if not name:
			messages.error(request, "กรุณากรอก Name")
			return redirect(request.get_full_path())
		try:
			with transaction.atomic():
				obj = ItemStage.objects.create(name=name, display_name=display_name, user=request.user)
				transaction.on_commit(
					lambda: log_event(request, action="item_stage:create", message="เพิ่ม Item Stage", metadata={"id": str(obj.pk), "name": name})
				)
			messages.success(request, "เพิ่ม Item Stage สำเร็จ")
		except IntegrityError:
			messages.error(request, "ข้อมูลซ้ำ: Name นี้มีอยู่แล้ว")
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
		return redirect(request.get_full_path())

	def _stage_update(self, request, *args, **kwargs):
		obj_id = (request.POST.get("id") or "").strip()
		if not _is_uuid(obj_id):
			messages.error(request, "ไม่พบรหัสรายการ")
			return redirect(request.get_full_path())
		name = (request.POST.get("name") or "").strip()
		display_name = (request.POST.get("display_name") or "").strip()
		if not name:
			messages.error(request, "กรุณากรอก Name")
			return redirect(request.get_full_path())
		obj = ItemStage.objects.filter(pk=obj_id).first()
		if obj is None:
			messages.error(request, "ไม่พบรายการ")
			return redirect(request.get_full_path())
		try:
			with transaction.atomic():
				fields = []
				if obj.name != name:
					obj.name = name
					fields.append("name")
				if obj.display_name != display_name:
					obj.display_name = display_name
					fields.append("display_name")
				if fields:
					fields.append("updated_at")
					obj.save(update_fields=fields)
					transaction.on_commit(
						lambda: log_event(request, action="item_stage:update", message="แก้ไข Item Stage", metadata={"id": obj_id})
					)
					messages.success(request, "บันทึกการแก้ไขสำเร็จ")
				else:
					messages.info(request, "ไม่มีการเปลี่ยนแปลง")
		except IntegrityError:
			messages.error(request, "ข้อมูลซ้ำ: Name นี้มีอยู่แล้ว")
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
		return redirect(request.get_full_path())

	def _stage_delete(self, request, *args, **kwargs):
		obj_id = (request.POST.get("id") or "").strip()
		if not _is_uuid(obj_id):
			messages.error(request, "ไม่พบรหัสรายการ")
			return redirect(request.get_full_path())
		obj = ItemStage.objects.filter(pk=obj_id).first()
		if obj is None:
			messages.error(request, "ไม่พบรายการ")
			return redirect(request.get_full_path())
		try:
			obj.delete()
			transaction.on_commit(
				lambda: log_event(request, action="item_stage:delete", message="ลบ Item Stage", metadata={"id": obj_id})
			)
			messages.success(request, "ลบสำเร็จ")
		except ProtectedError:
			messages.error(request, "ลบไม่ได้: มีข้อมูลอ้างอิงอยู่")
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
		return redirect(request.get_full_path())

	# -------------------------------------------------- ItemCategory handlers

	def _cat_create(self, request, *args, **kwargs):
		name = (request.POST.get("name") or "").strip()
		description = (request.POST.get("description") or "").strip()
		if not name:
			messages.error(request, "กรุณาระบุชื่อ Category")
			return redirect(request.get_full_path())
		try:
			with transaction.atomic():
				if ItemCategory.objects.filter(name__iexact=name).exists():
					messages.error(request, "ข้อมูลซ้ำ: ชื่อ Category นี้มีอยู่แล้ว")
					return redirect(request.get_full_path())
				obj = ItemCategory.objects.create(name=name, description=description, user=request.user)
				transaction.on_commit(
					lambda: log_event(request, action="item_category:create", message="เพิ่ม ItemCategory", metadata={"id": str(obj.id), "name": name})
				)
			messages.success(request, "เพิ่ม Category สำเร็จ")
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
		return redirect(request.get_full_path())

	def _cat_update(self, request, *args, **kwargs):
		obj_id = (request.POST.get("id") or "").strip()
		if not _is_uuid(obj_id):
			messages.error(request, "ไม่พบรหัสรายการ")
			return redirect(request.get_full_path())
		name = (request.POST.get("name") or "").strip()
		description = (request.POST.get("description") or "").strip()
		if not name:
			messages.error(request, "กรุณาระบุชื่อ Category")
			return redirect(request.get_full_path())
		obj = ItemCategory.objects.filter(pk=obj_id).first()
		if obj is None:
			messages.error(request, "ไม่พบรายการ")
			return redirect(request.get_full_path())
		try:
			with transaction.atomic():
				if obj.name.lower() != name.lower() and ItemCategory.objects.filter(name__iexact=name).exclude(pk=obj.pk).exists():
					messages.error(request, "ข้อมูลซ้ำ: ชื่อ Category นี้มีอยู่แล้ว")
					return redirect(request.get_full_path())
				obj.name = name
				obj.description = description
				obj.save(update_fields=["name", "description", "updated_at"])
				transaction.on_commit(
					lambda: log_event(request, action="item_category:update", message="แก้ไข ItemCategory", metadata={"id": obj_id, "name": name})
				)
			messages.success(request, "บันทึกการแก้ไขสำเร็จ")
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
		return redirect(request.get_full_path())

	def _cat_delete(self, request, *args, **kwargs):
		obj_id = (request.POST.get("id") or "").strip()
		if not _is_uuid(obj_id):
			messages.error(request, "ไม่พบรหัสรายการ")
			return redirect(request.get_full_path())
		obj = ItemCategory.objects.filter(pk=obj_id).first()
		if obj is None:
			messages.error(request, "ไม่พบรายการ")
			return redirect(request.get_full_path())
		try:
			obj.delete()
			transaction.on_commit(
				lambda: log_event(request, action="item_category:delete", message="ลบ ItemCategory", metadata={"id": obj_id})
			)
			messages.success(request, "ลบสำเร็จ")
		except ProtectedError:
			messages.error(request, "ลบไม่ได้: มีข้อมูลอ้างอิงอยู่")
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
		return redirect(request.get_full_path())

	# -------------------------------------------------- DefectMode handlers

	def _defect_payload(self, request):
		return {
			"name_th": (request.POST.get("name_th") or "").strip(),
			"name_en": (request.POST.get("name_en") or "").strip(),
			"name_jp": (request.POST.get("name_jp") or "").strip(),
			"description_th": (request.POST.get("description_th") or "").strip(),
			"description_en": (request.POST.get("description_en") or "").strip(),
			"description_jp": (request.POST.get("description_jp") or "").strip(),
		}

	def _defect_create(self, request, *args, **kwargs):
		p = self._defect_payload(request)
		if not p["name_th"] or not p["name_en"] or not p["name_jp"]:
			messages.error(request, "กรุณากรอกชื่อ Defect mode ให้ครบทั้ง TH/EN/JP")
			return redirect(request.get_full_path())
		# Category is required: the new defect is linked to it via DefectByCategory.
		category_id = (request.POST.get("category_id") or "").strip()
		if not _is_uuid(category_id):
			messages.error(request, "กรุณาเลือก Category")
			return redirect(request.get_full_path())
		category = ItemCategory.objects.filter(pk=category_id).first()
		if category is None:
			messages.error(request, "ไม่พบ Category ที่เลือก")
			return redirect(request.get_full_path())
		try:
			with transaction.atomic():
				if DefectMode.objects.filter(name_en__iexact=p["name_en"]).exists():
					raise IntegrityError("Defect mode ซ้ำ: name_en มีอยู่แล้ว")
				obj = DefectMode.objects.create(**p, user=request.user)
				DefectByCategory.objects.create(
					category=category,
					defect_mode=obj,
					title=f"{category.name} - {obj.name_en}".strip(),
					description="",
					is_inlist=True,
					user=request.user,
				)
				transaction.on_commit(
					lambda: log_event(request, action="defectmode:create", message="เพิ่ม defect mode", metadata={"id": str(obj.pk), "name_en": p["name_en"], "category_id": str(category.id)})
				)
			messages.success(request, f"เพิ่มรายการของเสียสำเร็จ และผูกกับ Category “{category.name}”")
		except IntegrityError as e:
			messages.error(request, f"บันทึกไม่สำเร็จ (ข้อมูลซ้ำหรือผิดเงื่อนไข): {e}")
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
		return redirect(request.get_full_path())

	def _defect_update(self, request, *args, **kwargs):
		obj_id = (request.POST.get("id") or "").strip()
		if not _is_uuid(obj_id):
			messages.error(request, "ไม่พบรหัสรายการ")
			return redirect(request.get_full_path())
		p = self._defect_payload(request)
		if not p["name_th"] or not p["name_en"] or not p["name_jp"]:
			messages.error(request, "กรุณากรอกชื่อ Defect mode ให้ครบทั้ง TH/EN/JP")
			return redirect(request.get_full_path())
		obj = DefectMode.objects.filter(pk=obj_id).first()
		if obj is None:
			messages.error(request, "ไม่พบรายการ")
			return redirect(request.get_full_path())
		try:
			with transaction.atomic():
				if obj.name_en != p["name_en"] and DefectMode.objects.filter(name_en__iexact=p["name_en"]).exclude(pk=obj.pk).exists():
					raise IntegrityError("Defect mode ซ้ำ: name_en มีอยู่แล้ว")
				fields = []
				for k, v in p.items():
					if (getattr(obj, k) or "") != v:
						setattr(obj, k, v)
						fields.append(k)
				if fields:
					fields.append("updated_at")
					obj.save(update_fields=fields)
					transaction.on_commit(
						lambda: log_event(request, action="defectmode:update", message="แก้ไข defect mode", metadata={"id": obj_id, "fields": [f for f in fields if f != "updated_at"]})
					)
					messages.success(request, "บันทึกการแก้ไขสำเร็จ")
				else:
					messages.info(request, "ไม่มีการเปลี่ยนแปลง")
		except IntegrityError as e:
			messages.error(request, f"บันทึกไม่สำเร็จ: {e}")
		except ProtectedError:
			messages.error(request, "บันทึกไม่สำเร็จ: มีข้อมูล Component Part Record อ้างอิงอยู่")
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
		return redirect(request.get_full_path())

	def _defect_delete(self, request, *args, **kwargs):
		obj_id = (request.POST.get("id") or "").strip()
		if not _is_uuid(obj_id):
			messages.error(request, "ไม่พบรหัสรายการ")
			return redirect(request.get_full_path())
		obj = DefectMode.objects.filter(pk=obj_id).first()
		if obj is None:
			messages.error(request, "ไม่พบรายการ")
			return redirect(request.get_full_path())
		try:
			obj.delete()
			transaction.on_commit(
				lambda: log_event(request, action="defectmode:delete", message="ลบ defect mode", metadata={"id": obj_id})
			)
			messages.success(request, "ลบ Defect mode สำเร็จ")
		except ProtectedError:
			messages.error(request, "ลบไม่ได้: มีข้อมูล Component Part Record อ้างอิงอยู่")
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
		return redirect(request.get_full_path())

	# -------------------------------------------------- Way handlers

	def _way_create(self, request, *args, **kwargs):
		title = (request.POST.get("title") or "").strip()
		if not title:
			messages.error(request, "กรุณากรอก Title")
			return redirect(request.get_full_path())
		try:
			with transaction.atomic():
				obj = Way.objects.create(title=title, user=request.user)
				transaction.on_commit(
					lambda: log_event(request, action="way:create", message="เพิ่ม Way", metadata={"id": str(obj.pk), "title": title})
				)
			messages.success(request, "เพิ่ม Way สำเร็จ")
		except IntegrityError:
			messages.error(request, "ข้อมูลซ้ำ: Title นี้มีอยู่แล้ว")
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
		return redirect(request.get_full_path())

	def _way_update(self, request, *args, **kwargs):
		obj_id = (request.POST.get("id") or "").strip()
		if not _is_uuid(obj_id):
			messages.error(request, "ไม่พบรหัสรายการ")
			return redirect(request.get_full_path())
		title = (request.POST.get("title") or "").strip()
		if not title:
			messages.error(request, "กรุณากรอก Title")
			return redirect(request.get_full_path())
		obj = Way.objects.filter(pk=obj_id).first()
		if obj is None:
			messages.error(request, "ไม่พบรายการ")
			return redirect(request.get_full_path())
		try:
			with transaction.atomic():
				if obj.title != title:
					obj.title = title
					obj.save(update_fields=["title", "updated_at"])
					transaction.on_commit(
						lambda: log_event(request, action="way:update", message="แก้ไข Way", metadata={"id": obj_id})
					)
					messages.success(request, "บันทึกการแก้ไขสำเร็จ")
				else:
					messages.info(request, "ไม่มีการเปลี่ยนแปลง")
		except IntegrityError:
			messages.error(request, "ข้อมูลซ้ำ: Title นี้มีอยู่แล้ว")
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
		return redirect(request.get_full_path())

	def _way_delete(self, request, *args, **kwargs):
		obj_id = (request.POST.get("id") or "").strip()
		if not _is_uuid(obj_id):
			messages.error(request, "ไม่พบรหัสรายการ")
			return redirect(request.get_full_path())
		obj = Way.objects.filter(pk=obj_id).first()
		if obj is None:
			messages.error(request, "ไม่พบรายการ")
			return redirect(request.get_full_path())
		try:
			obj.delete()
			transaction.on_commit(
				lambda: log_event(request, action="way:delete", message="ลบ Way", metadata={"id": obj_id})
			)
			messages.success(request, "ลบ Way สำเร็จ")
		except ProtectedError:
			messages.error(request, "ลบไม่ได้: มีข้อมูลอ้างอิงอยู่")
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
		return redirect(request.get_full_path())

