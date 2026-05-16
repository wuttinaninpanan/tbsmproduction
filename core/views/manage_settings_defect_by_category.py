from __future__ import annotations

import uuid

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from core.auth.decorators import staff_required
from core.models.defect_by_category import DefectByCategory
from core.models.defect_mode import DefectMode
from core.models.item_category import ItemCategory
from core.services.auditlog import log_event


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
class ManageSettingsDefectByCategoryView(TemplateView):
	template_name = "manage_settings_defect_by_category.html"

	def _get_category(self):
		category_id = self.kwargs.get("category_id")
		category = ItemCategory.objects.filter(pk=category_id).first()
		if category is None:
			raise Http404("Category not found")
		return category

	# ------------------------------------------------------------------ GET

	def get_context_data(self, **kwargs):
		ctx = super().get_context_data(**kwargs)
		request = self.request
		category = self._get_category()

		q = (request.GET.get("q") or "").strip()
		page = (request.GET.get("page") or "1").strip() or "1"
		try:
			per_page = int((request.GET.get("per_page") or "100").strip())
		except Exception:
			per_page = 100
		if per_page not in {100, 200, 500, 1000}:
			per_page = 100

		qs = (
			DefectByCategory.objects
			.select_related("defect_mode")
			.filter(category=category)
		)
		if q:
			qs = qs.filter(
				Q(title__icontains=q)
				| Q(description__icontains=q)
				| Q(defect_mode__name_th__icontains=q)
				| Q(defect_mode__name_en__icontains=q)
				| Q(defect_mode__name_jp__icontains=q)
			)
		qs = qs.order_by("defect_mode__name_en", "title")
		paginator = Paginator(qs, per_page)
		page_obj = paginator.get_page(page)
		rows = [
			{
				"id": str(o.id),
				"defect_mode_id": str(o.defect_mode_id) if o.defect_mode_id else "",
				"defect_name_en": getattr(o.defect_mode, "name_en", "") or "",
				"defect_name_th": getattr(o.defect_mode, "name_th", "") or "",
				"defect_name_jp": getattr(o.defect_mode, "name_jp", "") or "",
				"title": o.title or "",
				"description": o.description or "",
				"is_inlist": bool(o.is_inlist),
			}
			for o in page_obj.object_list
		]

		ctx["category"] = category
		ctx["q"] = q
		ctx["per_page"] = per_page
		ctx["rows"] = rows
		ctx["rows_total"] = paginator.count
		ctx["page_obj"] = page_obj
		ctx["paginator"] = paginator
		ctx["page_items"] = _page_items(paginator.num_pages, page_obj.number)
		ctx["all_defects"] = list(
			DefectMode.objects.order_by("name_en", "name_th").values("id", "name_th", "name_en", "name_jp")
		)
		ctx["back_url"] = reverse("manage_settings") + "?tab=defect_by_category"
		return ctx

	# ------------------------------------------------------------------ POST

	def post(self, request, *args, **kwargs):
		action = (request.POST.get("action") or "").strip().lower()
		handler = {
			"dbc_create": self._dbc_create,
			"dbc_update": self._dbc_update,
			"dbc_delete": self._dbc_delete,
		}.get(action)
		if handler is None:
			messages.error(request, "ไม่รู้จัก action")
			return redirect(request.get_full_path())
		return handler(request, *args, **kwargs)

	def _payload(self, request):
		return {
			"defect_mode_id": (request.POST.get("defect_mode_id") or "").strip(),
			"title": (request.POST.get("title") or "").strip(),
			"description": (request.POST.get("description") or "").strip(),
			"is_inlist": _parse_bool(request.POST.get("is_inlist") or ""),
		}

	def _dbc_create(self, request, *args, **kwargs):
		category = self._get_category()
		p = self._payload(request)
		if not _is_uuid(p["defect_mode_id"]):
			messages.error(request, "กรุณาเลือก Defect mode")
			return redirect(request.get_full_path())
		defect = DefectMode.objects.filter(pk=p["defect_mode_id"]).first()
		if defect is None:
			messages.error(request, "ไม่พบ Defect mode")
			return redirect(request.get_full_path())
		title = p["title"] or f"{category.name} - {defect.name_en}".strip()
		try:
			with transaction.atomic():
				existing = DefectByCategory.objects.filter(category=category, defect_mode=defect).first()
				if existing:
					existing.title = title
					existing.description = p["description"]
					existing.is_inlist = p["is_inlist"]
					existing.save(update_fields=["title", "description", "is_inlist", "updated_at"])
					transaction.on_commit(
						lambda: log_event(request, action="defectmodecategory:create_as_update", message="create->update", metadata={"id": str(existing.id), "category_id": str(category.id)})
					)
					messages.success(request, "บันทึกสำเร็จ (อัปเดตรายการเดิม)")
				else:
					obj = DefectByCategory.objects.create(
						category=category,
						defect_mode=defect,
						title=title,
						description=p["description"],
						is_inlist=p["is_inlist"],
						user=request.user,
					)
					transaction.on_commit(
						lambda: log_event(request, action="defectmodecategory:create", message="create", metadata={"id": str(obj.id), "category_id": str(category.id)})
					)
					messages.success(request, "เพิ่มข้อมูลสำเร็จ")
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
		return redirect("manage_settings_defect_by_category", category_id=category.id)

	def _dbc_update(self, request, *args, **kwargs):
		category = self._get_category()
		obj_id = (request.POST.get("id") or "").strip()
		if not _is_uuid(obj_id):
			messages.error(request, "ไม่พบรหัสรายการ")
			return redirect(request.get_full_path())
		p = self._payload(request)
		if not _is_uuid(p["defect_mode_id"]):
			messages.error(request, "กรุณาเลือก Defect mode")
			return redirect(request.get_full_path())
		obj = DefectByCategory.objects.filter(pk=obj_id, category=category).first()
		if obj is None:
			messages.error(request, "ไม่พบรายการ")
			return redirect(request.get_full_path())
		defect = DefectMode.objects.filter(pk=p["defect_mode_id"]).first()
		if defect is None:
			messages.error(request, "ไม่พบ Defect mode")
			return redirect(request.get_full_path())
		obj.defect_mode = defect
		obj.title = p["title"] or f"{category.name} - {defect.name_en}".strip()
		obj.description = p["description"]
		obj.is_inlist = p["is_inlist"]
		obj.save(update_fields=["defect_mode", "title", "description", "is_inlist", "updated_at"])
		transaction.on_commit(
			lambda: log_event(request, action="defectmodecategory:update", message="update", metadata={"id": obj_id, "category_id": str(category.id)})
		)
		messages.success(request, "แก้ไขข้อมูลสำเร็จ")
		return redirect("manage_settings_defect_by_category", category_id=category.id)

	def _dbc_delete(self, request, *args, **kwargs):
		category = self._get_category()
		obj_id = (request.POST.get("id") or "").strip()
		if not _is_uuid(obj_id):
			messages.error(request, "ไม่พบรหัสรายการ")
			return redirect(request.get_full_path())
		obj = DefectByCategory.objects.filter(pk=obj_id, category=category).first()
		if obj is None:
			messages.error(request, "ไม่พบรายการ")
			return redirect(request.get_full_path())
		obj.delete()
		transaction.on_commit(
			lambda: log_event(request, action="defectmodecategory:delete", message="delete", metadata={"id": obj_id, "category_id": str(category.id)})
		)
		messages.success(request, "ลบข้อมูลสำเร็จ")
		return redirect("manage_settings_defect_by_category", category_id=category.id)
