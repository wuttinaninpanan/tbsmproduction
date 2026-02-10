from __future__ import annotations

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator

from core.decorators import staff_required
from core.models import DefectMode

try:
	import openpyxl  # type: ignore
except Exception:  # pragma: no cover
	openpyxl = None


def _normalized_key(key: str) -> str:
	return (key or "").strip().lower().replace(" ", "_")


def _parse_xlsx(uploaded_file):
	if openpyxl is None:
		raise RuntimeError("openpyxl is not installed")
	wb = openpyxl.load_workbook(uploaded_file, read_only=True, data_only=True)
	ws = wb.active
	rows = ws.iter_rows(values_only=True)
	try:
		headers = next(rows)
	except StopIteration:
		return
	keys = [_normalized_key(str(h) if h is not None else "") for h in headers]
	for values in rows:
		row = {}
		for idx, value in enumerate(values):
			k = keys[idx] if idx < len(keys) else ""
			if not k:
				continue
			row[k] = value
		yield row


def download_manage_defectmode_import_template(request):
	"""Download a template for importing global defect modes."""
	headers = ["defect_name", "defect_code"]
	rows = [["Crack", "DEF-001"], ["Scratch", ""], ["Color uneven", "DEF-100"]]
	if openpyxl is None:
		return HttpResponse(
			"XLSX format is not available (openpyxl is not installed).",
			status=400,
			content_type="text/plain; charset=utf-8",
		)
	wb = openpyxl.Workbook()
	ws = wb.active
	ws.title = "defectmode"
	ws.append(headers)
	for r in rows:
		ws.append(r)
	for col in range(1, len(headers) + 1):
		ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 26

	response = HttpResponse(
		content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
	)
	response["Content-Disposition"] = 'attachment; filename="manage_defectmode_import_template.xlsx"'
	wb.save(response)
	return response


@method_decorator(staff_required, name="dispatch")
class ManageDefectModeViews(TemplateView):
	template_name = "manage_defectmode.html"

	def get(self, request, *args, **kwargs):
		action = (request.GET.get("action") or "").strip().lower()
		if action == "download_template":
			return download_manage_defectmode_import_template(request)
		return super().get(request, *args, **kwargs)

	def get_context_data(self, **kwargs):
		ctx = super().get_context_data(**kwargs)
		request = self.request

		q = (request.GET.get("q") or "").strip()
		per_page_raw = (request.GET.get("per_page") or "").strip()
		page = (request.GET.get("page") or "1").strip() or "1"

		qs = DefectMode.objects.filter(part__isnull=True).all()
		if q:
			qs = qs.filter(
				Q(name__icontains=q)
				| Q(code__icontains=q)
			)

		allowed_per_page = {20, 50, 100, 200}
		try:
			per_page = int(per_page_raw or 20)
		except Exception:
			per_page = 20
		if per_page not in allowed_per_page:
			per_page = 20

		qs = qs.order_by("name")
		paginator = Paginator(qs, per_page)
		page_obj = paginator.get_page(page)
		rows = []
		for d in page_obj.object_list:
			rows.append({"id": d.id, "code": d.code or "", "name": d.name})

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
		uploaded = request.FILES.get("excel_file")

		defect_code = (request.POST.get("defect_code") or "").strip()
		defect_name = (request.POST.get("defect_name") or "").strip()

		if action == "import_master_data":
			if not uploaded:
				messages.error(request, "กรุณาเลือกไฟล์ Excel/CSV ก่อนนำเข้า")
				return self.get(request, *args, **kwargs)

			filename = (uploaded.name or "").lower()
			try:
				if filename.endswith(".xlsx"):
					rows_iter = _parse_xlsx(uploaded)
				else:
					messages.error(request, "รองรับเฉพาะไฟล์ Excel (.xlsx) เท่านั้น")
					return self.get(request, *args, **kwargs)
			except RuntimeError:
				messages.error(request, "ยังไม่รองรับไฟล์ .xlsx ในสภาพแวดล้อมนี้ (ต้องติดตั้ง openpyxl)")
				return self.get(request, *args, **kwargs)

			created = 0
			skipped = 0
			dup = 0
			try:
				with transaction.atomic():
					for row in rows_iter:
						name = (row.get("defect_name") or row.get("defect") or row.get("name") or "")
						name = str(name).strip()
						code = (row.get("defect_code") or row.get("code") or "")
						code = str(code).strip() if code is not None else ""
						if not name:
							skipped += 1
							continue
						if DefectMode.objects.filter(part__isnull=True, name__iexact=name).exists():
							dup += 1
							continue
						DefectMode.objects.create(part=None, name=name, code=code or None)
						created += 1
			except Exception as e:
				messages.error(request, f"เกิดข้อผิดพลาดระหว่างนำเข้า: {e}")
				return self.get(request, *args, **kwargs)

			messages.success(request, f"นำเข้าสำเร็จ: +{created}, ซ้ำ {dup}, ข้าม {skipped}")
			return self.get(request, *args, **kwargs)


		if action == "create_defect":
			if not defect_name:
				messages.error(request, "กรุณากรอก Defect name")
				return self.get(request, *args, **kwargs)
			try:
				with transaction.atomic():
					# Keep global defects unique by name (case-insensitive)
					if DefectMode.objects.filter(part__isnull=True, name__iexact=defect_name).exists():
						raise IntegrityError("Defect mode ซ้ำ (global): มีชื่อเดียวกันอยู่แล้ว")
					DefectMode.objects.create(part=None, code=defect_code or None, name=defect_name)
					messages.success(request, "เพิ่ม Defect mode สำเร็จ")
					return self.get(request, *args, **kwargs)
			except IntegrityError as e:
				messages.error(request, f"บันทึกไม่สำเร็จ (ข้อมูลซ้ำหรือผิดเงื่อนไข): {e}")
				return self.get(request, *args, **kwargs)
			except Exception as e:
				messages.error(request, f"เกิดข้อผิดพลาด: {e}")
				return self.get(request, *args, **kwargs)

		if action == "update_defect":
			if not obj_id.isdigit():
				messages.error(request, "ไม่พบรหัสรายการ")
				return self.get(request, *args, **kwargs)
			if not defect_name:
				messages.error(request, "กรุณากรอก Defect name")
				return self.get(request, *args, **kwargs)
			try:
				with transaction.atomic():
					defect = DefectMode.objects.get(pk=int(obj_id))
					# Only allow editing global defects in this page
					if defect.part_id is not None:
						messages.error(request, "หน้านี้แก้ไขได้เฉพาะ Defect mode แบบ global เท่านั้น")
						return self.get(request, *args, **kwargs)

					updated_fields = []

					new_code = defect_code or None
					if defect.code != new_code:
						defect.code = new_code
						updated_fields.append("code")

					if defect.name != defect_name:
						# Prevent duplicate global names
						if DefectMode.objects.filter(part__isnull=True, name__iexact=defect_name).exclude(pk=defect.pk).exists():
							raise IntegrityError("Defect mode ซ้ำ (global): มีชื่อเดียวกันอยู่แล้ว")
						defect.name = defect_name
						updated_fields.append("name")

					if updated_fields:
						updated_fields.append("updated_at")
						defect.save(update_fields=updated_fields)
						messages.success(request, "บันทึกการแก้ไขสำเร็จ")
					else:
						messages.info(request, "ไม่มีการเปลี่ยนแปลง")
					return self.get(request, *args, **kwargs)
			except ProtectedError:
				messages.error(request, "บันทึกไม่สำเร็จ: มีข้อมูล Scrap Record อ้างอิงอยู่")
				return self.get(request, *args, **kwargs)
			except IntegrityError as e:
				messages.error(request, f"บันทึกไม่สำเร็จ (ข้อมูลซ้ำหรือผิดเงื่อนไข): {e}")
				return self.get(request, *args, **kwargs)
			except Exception as e:
				messages.error(request, f"เกิดข้อผิดพลาด: {e}")
				return self.get(request, *args, **kwargs)

		if action == "delete_defect":
			if not obj_id.isdigit():
				messages.error(request, "ไม่พบรหัสรายการ")
				return self.get(request, *args, **kwargs)
			try:
				with transaction.atomic():
					defect = DefectMode.objects.get(pk=int(obj_id))
					if defect.part_id is not None:
						messages.error(request, "หน้านี้ลบได้เฉพาะ Defect mode แบบ global เท่านั้น")
						return self.get(request, *args, **kwargs)
					defect.delete()
					messages.success(request, "ลบ Defect mode สำเร็จ")
					return self.get(request, *args, **kwargs)
			except ProtectedError:
				messages.error(
					request,
					"ลบไม่ได้: มีข้อมูล Scrap Record อ้างอิงอยู่ (โปรดลบ/ย้ายรายการที่เกี่ยวข้องก่อน)",
				)
				return self.get(request, *args, **kwargs)
			except Exception as e:
				messages.error(request, f"เกิดข้อผิดพลาด: {e}")
				return self.get(request, *args, **kwargs)

		messages.error(request, "ไม่รองรับการทำงานนี้")
		return self.get(request, *args, **kwargs)
