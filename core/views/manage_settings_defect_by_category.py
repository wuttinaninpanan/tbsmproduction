from __future__ import annotations

import uuid

from django.contrib import messages
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from core.auth.decorators import staff_required
from core.models.defect_by_category import DefectByCategory
from core.models.defect_mode import DefectMode
from core.models.defect_stat import DefectStat
from core.models.item_category import ItemCategory
from core.models.process_defect import ProcessDefect
from core.models.scrap_record import ScrapRecord
from core.services.auditlog import log_event


def _is_uuid(value: str) -> bool:
	try:
		uuid.UUID(str(value))
	except Exception:
		return False
	return True


@method_decorator(staff_required, name="dispatch")
class ManageSettingsDefectByCategoryView(TemplateView):
	"""Pick-list editor: tick which Defect modes belong to a category.

	The whole defect-mode catalogue is rendered as a checkbox grid; ticking a
	box means a DefectByCategory row exists for (category, defect_mode) with
	``is_inlist=True`` (the flag the recording/scrap screens filter on).
	Search filters the grid client-side, so every checkbox is always submitted
	and the save can safely reconcile against the full catalogue.
	"""

	template_name = "core/manage_settings_defect_by_category.html"

	def _get_category(self):
		category_id = self.kwargs.get("category_id")
		category = ItemCategory.objects.filter(pk=category_id).first()
		if category is None:
			raise Http404("Category not found")
		return category

	# ------------------------------------------------------------------ GET

	def get_context_data(self, **kwargs):
		ctx = super().get_context_data(**kwargs)
		category = self._get_category()

		# Show ONLY defects linked to this category (those with a
		# DefectByCategory row). A box is ticked when that link is active
		# (is_inlist=True) → the defect shows in the recording dropdown.
		links = (
			DefectByCategory.objects
			.filter(category=category)
			.select_related("defect_mode")
			.order_by("defect_mode__name_en", "defect_mode__name_th")
		)
		defects_by_id: dict[str, dict] = {}
		for link in links:
			d = link.defect_mode
			if d is None:
				continue
			key = str(d.id)
			entry = defects_by_id.get(key)
			if entry is None:
				defects_by_id[key] = {
					"id": key,
					"name_en": d.name_en or "",
					"name_th": d.name_th or "",
					"name_jp": d.name_jp or "",
					"checked": bool(link.is_inlist),
				}
			else:
				# Defensive: collapse any duplicate (category, defect) rows.
				entry["checked"] = entry["checked"] or bool(link.is_inlist)
		defects = list(defects_by_id.values())

		# Defects NOT yet linked to this category — options for the Add search.
		linked_ids = set(defects_by_id.keys())
		available_defects = [
			{
				"id": str(d.id),
				"name_en": d.name_en or "",
				"name_th": d.name_th or "",
				"name_jp": d.name_jp or "",
			}
			for d in DefectMode.objects.order_by("name_en", "name_th")
			if str(d.id) not in linked_ids
		]

		ctx["category"] = category
		ctx["defects"] = defects
		ctx["selected_count"] = sum(1 for d in defects if d["checked"])
		ctx["available_defects"] = available_defects
		ctx["back_url"] = reverse("manage_settings") + "?tab=item_category"
		return ctx

	# ------------------------------------------------------------------ POST

	def post(self, request, *args, **kwargs):
		action = (request.POST.get("action") or "").strip().lower()
		if action == "dbc_sync":
			return self._dbc_sync(request)
		if action == "dbc_add":
			return self._dbc_add(request)
		if action == "dbc_delete":
			return self._dbc_delete(request)
		messages.error(request, "ไม่รู้จัก action")
		return redirect(request.get_full_path())

	def _dbc_delete(self, request):
		"""Unlink a defect from this category. Delete the DefectMode itself only
		when it is safe to: it must be linked to no other category AND not used by
		any defect record (its PK is stored on ScrapRecord/DefectStat rows, so
		deleting it there would break history). Otherwise keep the DefectMode and
		just remove the category link."""
		category = self._get_category()
		defect_id = (request.POST.get("defect_mode_id") or "").strip()
		if not _is_uuid(defect_id):
			messages.error(request, "ไม่พบรหัส Defect")
			return redirect("manage_settings_defect_by_category", category_id=category.id)
		defect = DefectMode.objects.filter(pk=defect_id).first()
		if defect is None:
			messages.error(request, "ไม่พบ Defect")
			return redirect("manage_settings_defect_by_category", category_id=category.id)
		name = defect.name_en or defect.name_th or defect.name_jp or ""
		in_records = False
		try:
			with transaction.atomic():
				# 1) unlink from THIS category
				removed, _ = DefectByCategory.objects.filter(category=category, defect_mode=defect).delete()
				# 2) still linked to another category?
				still_linked = DefectByCategory.objects.filter(defect_mode=defect).exists()
				# 3) referenced by any defect record? (PK saved on the record rows)
				#    ProcessDefect is the current recording table; ScrapRecord/
				#    DefectStat are kept for legacy history still in the DB.
				in_records = (
					ProcessDefect.objects.filter(defect_mode=defect).exists()
					or ScrapRecord.objects.filter(defect_mode=defect).exists()
					or DefectStat.objects.filter(defect_mode=defect).exists()
				)
				# Only delete the DefectMode when nothing else needs it.
				defect_deleted = False
				if removed and not still_linked and not in_records:
					try:
						with transaction.atomic():
							defect.delete()
						defect_deleted = True
					except ProtectedError:
						defect_deleted = False  # safety net for any other PROTECT ref → keep it
				transaction.on_commit(
					lambda: log_event(
						request,
						action="defectmodecategory:delete",
						message="unlink defect from category",
						metadata={
							"category_id": str(category.id),
							"defect_mode_id": defect_id,
							"defect_deleted": defect_deleted,
							"in_records": in_records,
						},
					)
				)
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
			return redirect("manage_settings_defect_by_category", category_id=category.id)

		if not removed:
			messages.info(request, f"“{name}” ไม่ได้ผูกกับ category นี้")
		elif defect_deleted:
			messages.success(request, f"ลบ “{name}” ออกจาก category นี้ และลบออกจากระบบแล้ว (ไม่ได้ผูกกับ category อื่น)")
		elif in_records:
			messages.success(request, f"ลบ “{name}” ออกจาก category นี้แล้ว — ยังเก็บ defect ไว้ในระบบเพราะมีประวัติการบันทึกของเสียอ้างอิงอยู่")
		elif still_linked:
			messages.success(request, f"ลบ “{name}” ออกจาก category นี้แล้ว (ยังผูกกับ category อื่นอยู่)")
		else:
			messages.success(request, f"ลบ “{name}” ออกจาก category นี้แล้ว")
		return redirect("manage_settings_defect_by_category", category_id=category.id)

	def _dbc_add(self, request):
		"""Link an existing DefectMode to this category (from the Add search)."""
		category = self._get_category()
		defect_id = (request.POST.get("defect_mode_id") or "").strip()
		if not _is_uuid(defect_id):
			messages.error(request, "กรุณาเลือก Defect จากรายการ")
			return redirect("manage_settings_defect_by_category", category_id=category.id)
		defect = DefectMode.objects.filter(pk=defect_id).first()
		if defect is None:
			messages.error(request, "ไม่พบ Defect ที่เลือก")
			return redirect("manage_settings_defect_by_category", category_id=category.id)
		try:
			with transaction.atomic():
				existing = DefectByCategory.objects.filter(category=category, defect_mode=defect).first()
				if existing is not None:
					# Already linked (e.g. hidden) — just make sure it shows.
					if not existing.is_inlist:
						existing.is_inlist = True
						existing.save(update_fields=["is_inlist", "updated_at"])
						messages.success(request, f"“{defect.name_en}” อยู่ใน list อยู่แล้ว — เปิดแสดงให้แล้ว")
					else:
						messages.info(request, f"“{defect.name_en}” อยู่ใน list อยู่แล้ว")
				else:
					DefectByCategory.objects.create(
						category=category,
						defect_mode=defect,
						title=f"{category.name} - {defect.name_en}".strip(),
						description="",
						is_inlist=True,
						user=request.user,
					)
					transaction.on_commit(
						lambda: log_event(
							request,
							action="defectmodecategory:add",
							message="add defect to category",
							metadata={"category_id": str(category.id), "defect_mode_id": str(defect.id)},
						)
					)
					messages.success(request, f"เพิ่ม “{defect.name_en}” เข้า list แล้ว")
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
		return redirect("manage_settings_defect_by_category", category_id=category.id)

	def _dbc_sync(self, request):
		category = self._get_category()

		# The set of defect_mode ids the user ticked, restricted to real defects.
		submitted = {
			v.strip()
			for v in request.POST.getlist("defect_mode_ids")
			if _is_uuid(v.strip())
		}

		# Only defects already linked to this category appear in the grid, so we
		# only ever toggle existing rows — never create or delete. Linking a
		# defect to a category happens at defect creation (Defect Mode tab).
		existing_by_defect: dict[str, list[DefectByCategory]] = {}
		for row in DefectByCategory.objects.filter(category=category):
			existing_by_defect.setdefault(str(row.defect_mode_id), []).append(row)

		checked_ids = submitted & set(existing_by_defect)

		shown = hidden = 0
		try:
			with transaction.atomic():
				# Ticked → is_inlist=True (show), unticked → is_inlist=False
				# (hide but keep the link, so the defect never goes orphan).
				for did, rows in existing_by_defect.items():
					target = did in checked_ids
					for row in rows:
						if row.is_inlist != target:
							row.is_inlist = target
							row.save(update_fields=["is_inlist", "updated_at"])
							if target:
								shown += 1
							else:
								hidden += 1

				transaction.on_commit(
					lambda: log_event(
						request,
						action="defectmodecategory:sync",
						message="toggle defect visibility for category",
						metadata={
							"category_id": str(category.id),
							"shown": shown,
							"hidden": hidden,
						},
					)
				)
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
			return redirect("manage_settings_defect_by_category", category_id=category.id)

		if shown or hidden:
			parts = []
			if shown:
				parts.append(f"เปิดแสดง {shown}")
			if hidden:
				parts.append(f"ซ่อน {hidden}")
			messages.success(request, "บันทึกสำเร็จ: " + ", ".join(parts) + " รายการ")
		else:
			messages.info(request, "ไม่มีการเปลี่ยนแปลง")
		return redirect("manage_settings_defect_by_category", category_id=category.id)
