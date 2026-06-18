from __future__ import annotations

import uuid

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.shortcuts import redirect

from core.auth.decorators import staff_required
from core.models.businesspartner import BusinessPartner, Contact
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


@method_decorator(staff_required, name="dispatch")
class ManageContactViews(TemplateView):
	template_name = "core/manage_contact.html"

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

		qs = Contact.objects.select_related("partner").all()
		if q:
			qs = qs.filter(
				Q(first_name__icontains=q) |
				Q(last_name__icontains=q) |
				Q(telephone_number__icontains=q) |
				Q(email__icontains=q) |
				Q(partner__name__icontains=q) |
				Q(partner__code__icontains=q)
			)
		qs = qs.order_by("partner__code", "last_name", "first_name")
		paginator = Paginator(qs, per_page)
		page_obj = paginator.get_page(page)

		rows = []
		for obj in page_obj.object_list:
			rows.append({
				"id": str(obj.id),
				"partner_id": str(obj.partner_id),
				"partner_name": obj.partner.name,
				"first_name": obj.first_name,
				"last_name": obj.last_name,
				"telephone_number": obj.telephone_number or "",
				"email": obj.email or "",
			})

		ctx["rows"] = rows
		ctx["partners"] = list(BusinessPartner.objects.order_by("code").values("id", "code", "name"))
		ctx["q"] = q
		ctx["page_obj"] = page_obj
		ctx["paginator"] = paginator
		ctx["per_page"] = per_page
		ctx["rows_total"] = paginator.count
		ctx["page_items"] = _page_items(paginator.num_pages, page_obj.number)
		ctx["total_count"] = paginator.count
		return ctx

	def post(self, request, *args, **kwargs):
		action = (request.POST.get("action") or "").strip().lower()
		obj_id = (request.POST.get("id") or "").strip()
		partner_id = (request.POST.get("partner_id") or "").strip()
		first_name = (request.POST.get("first_name") or "").strip()
		last_name = (request.POST.get("last_name") or "").strip()
		telephone_number = (request.POST.get("telephone_number") or "").strip()
		email = (request.POST.get("email") or "").strip()

		if action == "bulk_delete":
			bulk_ids = request.POST.getlist("bulk_id")
			ids = [x for x in [b.strip() for b in bulk_ids] if _is_uuid(x)]
			if not ids:
				messages.error(request, "กรุณาเลือกรายการที่ต้องการลบ")
				return redirect(request.get_full_path())
			deleted = blocked = 0
			try:
				with transaction.atomic():
					for pk in ids:
						obj = Contact.objects.filter(pk=pk).first()
						if obj is None:
							continue
						try:
							obj.delete()
							deleted += 1
						except ProtectedError:
							blocked += 1
			except Exception as e:
				messages.error(request, f"เกิดข้อผิดพลาด: {e}")
				return redirect(request.get_full_path())
			if blocked:
				messages.warning(request, f"ลบสำเร็จ {deleted} รายการ, ลบไม่ได้ {blocked} รายการ")
			else:
				messages.success(request, f"ลบสำเร็จ {deleted} รายการ")
			return redirect(request.get_full_path())
		if action == "create":
			if not _is_uuid(partner_id) or not first_name or not last_name:
				messages.error(request, "กรุณากรอกข้อมูลที่จำเป็นให้ครบ")
				return redirect(request.get_full_path())
			try:
				with transaction.atomic():
					partner = BusinessPartner.objects.get(pk=partner_id)
					obj = Contact.objects.create(
						partner=partner,
						first_name=first_name,
						last_name=last_name,
						telephone_number=telephone_number,
						email=email,
					)
					messages.success(request, "เพิ่ม Contact สำเร็จ")
					transaction.on_commit(lambda: log_event(request, action="contact:create", message="เพิ่ม Contact", metadata={"id": str(obj.pk)}))
			except Exception as e:
				messages.error(request, f"เกิดข้อผิดพลาด: {e}")
			return redirect(request.get_full_path())
		if action == "update":
			if not _is_uuid(obj_id):
				messages.error(request, "ไม่พบรหัสรายการ")
				return redirect(request.get_full_path())
			if not first_name or not last_name:
				messages.error(request, "กรุณากรอกข้อมูลที่จำเป็นให้ครบ")
				return redirect(request.get_full_path())
			try:
				with transaction.atomic():
					obj = Contact.objects.get(pk=obj_id)
					fields_map = {
						"first_name": first_name,
						"last_name": last_name,
						"telephone_number": telephone_number,
						"email": email,
					}
					if _is_uuid(partner_id):
						fields_map["partner_id"] = partner_id
					updated = []
					for field, val in fields_map.items():
						if str(getattr(obj, field) or "") != val:
							setattr(obj, field, val)
							updated.append(field)
					if updated:
						updated.append("updated_at")
						obj.save(update_fields=updated)
						messages.success(request, "บันทึกการแก้ไขสำเร็จ")
					else:
						messages.info(request, "ไม่มีการเปลี่ยนแปลง")
			except Exception as e:
				messages.error(request, f"เกิดข้อผิดพลาด: {e}")
			return redirect(request.get_full_path())
		if action == "delete":
			if not _is_uuid(obj_id):
				messages.error(request, "ไม่พบรหัสรายการ")
				return redirect(request.get_full_path())
			try:
				with transaction.atomic():
					obj = Contact.objects.get(pk=obj_id)
					obj.delete()
					messages.success(request, "ลบสำเร็จ")
			except ProtectedError:
				messages.error(request, "ลบไม่ได้ มีข้อมูลอ้างอิงอยู่")
			except Exception as e:
				messages.error(request, f"เกิดข้อผิดพลาด: {e}")
			return redirect(request.get_full_path())
		messages.error(request, "ไม่รู้จัก action")
		return redirect(request.get_full_path())