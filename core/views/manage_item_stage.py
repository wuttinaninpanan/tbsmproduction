from __future__ import annotations

import uuid

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from core.auth.decorators import staff_required
from core.models.item_stage import ItemStage
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
class ManageItemStageViews(TemplateView):
	template_name = "manage_item_stage.html"

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

		qs = ItemStage.objects.all()
		if q:
			qs = qs.filter(Q(name__icontains=q) | Q(display_name__icontains=q))
		qs = qs.order_by("name")
		paginator = Paginator(qs, per_page)
		page_obj = paginator.get_page(page)

		rows = []
		for obj in page_obj.object_list:
			rows.append({
				"id": str(obj.id),
				"name": obj.name,
				"display_name": obj.display_name,
			})

		ctx["rows"] = rows
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
		name = (request.POST.get("name") or "").strip()
		display_name = (request.POST.get("display_name") or "").strip()

		if action == "bulk_delete":
			bulk_ids = request.POST.getlist("bulk_id")
			ids = [x for x in [b.strip() for b in bulk_ids] if _is_uuid(x)]
			if not ids:
				messages.error(request, "กรุณาเลือกรายการที่ต้องการลบ")
				return self.get(request, *args, **kwargs)
			deleted = blocked = 0
			try:
				with transaction.atomic():
					for pk in ids:
						obj = ItemStage.objects.filter(pk=pk).first()
						if obj is None:
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
				messages.warning(request, f"ลบสำเร็จ {deleted} รายการ, ลบไม่ได้ {blocked} รายการ (มีข้อมูลอ้างอิง)")
			else:
				messages.success(request, f"ลบสำเร็จ {deleted} รายการ")
			return self.get(request, *args, **kwargs)

		if action == "create":
			if not name:
				messages.error(request, "กรุณากรอก Name")
				return self.get(request, *args, **kwargs)
			try:
				with transaction.atomic():
					obj = ItemStage.objects.create(name=name, display_name=display_name, user=request.user)
					messages.success(request, "เพิ่ม Item Stage สำเร็จ")
					transaction.on_commit(lambda: log_event(request, action="item_stage:create", message="เพิ่ม Item Stage", metadata={"id": str(obj.pk), "name": name}))
			except Exception as e:
				messages.error(request, f"เกิดข้อผิดพลาด: {e}")
			return self.get(request, *args, **kwargs)

		if action == "update":
			if not _is_uuid(obj_id):
				messages.error(request, "ไม่พบรหัสรายการ")
				return self.get(request, *args, **kwargs)
			if not name:
				messages.error(request, "กรุณากรอก Name")
				return self.get(request, *args, **kwargs)
			try:
				with transaction.atomic():
					obj = ItemStage.objects.get(pk=obj_id)
					updated = []
					if obj.name != name:
						obj.name = name
						updated.append("name")
					if obj.display_name != display_name:
						obj.display_name = display_name
						updated.append("display_name")
					if updated:
						updated.append("updated_at")
						obj.save(update_fields=updated)
						messages.success(request, "บันทึกการแก้ไขสำเร็จ")
					else:
						messages.info(request, "ไม่มีการเปลี่ยนแปลง")
			except Exception as e:
				messages.error(request, f"เกิดข้อผิดพลาด: {e}")
			return self.get(request, *args, **kwargs)

		if action == "delete":
			if not _is_uuid(obj_id):
				messages.error(request, "ไม่พบรหัสรายการ")
				return self.get(request, *args, **kwargs)
			try:
				with transaction.atomic():
					obj = ItemStage.objects.get(pk=obj_id)
					obj.delete()
					messages.success(request, "ลบสำเร็จ")
			except ProtectedError:
				messages.error(request, "ลบไม่ได้ มีข้อมูลอ้างอิงอยู่")
			except Exception as e:
				messages.error(request, f"เกิดข้อผิดพลาด: {e}")
			return self.get(request, *args, **kwargs)

		messages.error(request, "ไม่รู้จัก action")
		return self.get(request, *args, **kwargs)
