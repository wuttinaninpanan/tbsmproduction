from __future__ import annotations

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator

from core.models import DefectMode, PartNumber, ProductionLine, ScrapItem
from core.decorators import staff_required


@method_decorator(staff_required, name='dispatch')
class ManageProductionViews(TemplateView):
	template_name = "manage_production.html"

	def get_context_data(self, **kwargs):
		ctx = super().get_context_data(**kwargs)
		request = self.request

		q = (request.GET.get("q") or "").strip()
		selected_line = (request.GET.get("line") or "").strip().upper()
		selected_part = (request.GET.get("part") or "").strip()
		selected_defect = (request.GET.get("defect") or "").strip()

		lines_qs = (
			ProductionLine.objects.annotate(
				part_count=Count("parts", distinct=True),
				record_count=Count("scrap_records", distinct=True),
			)
			.order_by("code")
		)
		parts_qs = (
			PartNumber.objects.select_related("production_line")
			.annotate(
				defect_count=Count("defects", distinct=True),
				record_count=Count("scrap_records", distinct=True),
			)
			.order_by("production_line__code", "number")
		)
		defects_qs = (
			DefectMode.objects.select_related("part__production_line")
			.annotate(
				scrap_count=Count("scraps", distinct=True),
				record_count=Count("scrap_records", distinct=True),
			)
			.order_by("part__production_line__code", "part__number", "name")
		)
		scraps_qs = (
			ScrapItem.objects.select_related("defect_mode__part__production_line")
			.annotate(record_count=Count("scrap_records", distinct=True))
			.order_by(
				"defect_mode__part__production_line__code",
				"defect_mode__part__number",
				"defect_mode__name",
				"name",
			)
		)

		if selected_line:
			parts_qs = parts_qs.filter(production_line__code=selected_line)
			defects_qs = defects_qs.filter(part__production_line__code=selected_line)
			scraps_qs = scraps_qs.filter(defect_mode__part__production_line__code=selected_line)

		if selected_part:
			defects_qs = defects_qs.filter(part__number=selected_part)
			scraps_qs = scraps_qs.filter(defect_mode__part__number=selected_part)

		if selected_defect:
			defects_qs = defects_qs.filter(name=selected_defect)
			scraps_qs = scraps_qs.filter(defect_mode__name=selected_defect)

		if q:
			lines_qs = lines_qs.filter(code__icontains=q)
			parts_qs = parts_qs.filter(Q(number__icontains=q) | Q(production_line__code__icontains=q))
			defects_qs = defects_qs.filter(
				Q(name__icontains=q)
				| Q(part__number__icontains=q)
				| Q(part__production_line__code__icontains=q)
			)
			scraps_qs = scraps_qs.filter(
				Q(name__icontains=q)
				| Q(defect_mode__name__icontains=q)
				| Q(defect_mode__part__number__icontains=q)
				| Q(defect_mode__part__production_line__code__icontains=q)
			)

		# Dropdown options
		ctx["production_lines"] = list(ProductionLine.objects.order_by("code").values_list("code", flat=True))
		ctx["part_numbers"] = list(
			PartNumber.objects.filter(production_line__code=selected_line).order_by("number").values_list("number", flat=True)
			if selected_line
			else PartNumber.objects.order_by("number").values_list("number", flat=True)
		)
		ctx["defect_names"] = list(
			DefectMode.objects.filter(part__production_line__code=selected_line, part__number=selected_part)
			.order_by("name")
			.values_list("name", flat=True)
			if (selected_line and selected_part)
			else DefectMode.objects.order_by("name").values_list("name", flat=True)
		)

		# Build a single flattened table to make scanning easier.
		# Primary rows come from ScrapItem; then we add "empty" placeholder rows
		# for Defect/Part/Line that don't have children.
		scrap_items = list(scraps_qs[:5000])
		defects = list(defects_qs[:3000])
		parts = list(parts_qs[:2000])
		lines = list(lines_qs[:500])

		rows = []
		seen_line_ids = set()
		seen_part_ids = set()
		seen_defect_ids = set()
		for s in scrap_items:
			line = s.defect_mode.part.production_line
			part = s.defect_mode.part
			defect = s.defect_mode
			seen_line_ids.add(line.id)
			seen_part_ids.add(part.id)
			seen_defect_ids.add(defect.id)
			rows.append(
				{
					"line_id": line.id,
					"line_code": line.code,
					"part_id": part.id,
					"part_number": part.number,
					"defect_id": defect.id,
					"defect_name": defect.name,
					"scrap_image_url": s.reference_image.url if getattr(s, "reference_image", None) else "",
					"scrap_id": s.id,
					"scrap_name": s.name,
					"record_count": getattr(s, "record_count", 0),
				}
			)

		# Add placeholder rows (defects without scraps)
		for d in defects:
			if d.id in seen_defect_ids:
				continue
			line = d.part.production_line
			part = d.part
			seen_line_ids.add(line.id)
			seen_part_ids.add(part.id)
			rows.append(
				{
					"line_id": line.id,
					"line_code": line.code,
					"part_id": part.id,
					"part_number": part.number,
					"defect_id": d.id,
					"defect_name": d.name,
					"scrap_image_url": "",
					"scrap_id": "",
					"scrap_name": "",
					"record_count": getattr(d, "record_count", 0),
				}
			)

		# Add placeholder rows (parts without defects)
		for p in parts:
			if p.id in seen_part_ids:
				continue
			line = p.production_line
			seen_line_ids.add(line.id)
			rows.append(
				{
					"line_id": line.id,
					"line_code": line.code,
					"part_id": p.id,
					"part_number": p.number,
					"defect_id": "",
					"defect_name": "",
					"scrap_image_url": "",
					"scrap_id": "",
					"scrap_name": "",
					"record_count": getattr(p, "record_count", 0),
				}
			)

		# Add placeholder rows (lines without parts)
		for l in lines:
			if l.id in seen_line_ids:
				continue
			rows.append(
				{
					"line_id": l.id,
					"line_code": l.code,
					"part_id": "",
					"part_number": "",
					"defect_id": "",
					"defect_name": "",
					"scrap_image_url": "",
					"scrap_id": "",
					"scrap_name": "",
					"record_count": getattr(l, "record_count", 0),
				}
			)

		rows.sort(key=lambda r: (r.get("line_code") or "", r.get("part_number") or "", r.get("defect_name") or "", r.get("scrap_name") or ""))
		ctx["rows"] = rows

		ctx["q"] = q
		ctx["selected_line"] = selected_line
		ctx["selected_part"] = selected_part
		ctx["selected_defect"] = selected_defect

		ctx["counts"] = {
			"lines": lines_qs.count(),
			"parts": parts_qs.count(),
			"defects": defects_qs.count(),
			"scraps": scraps_qs.count(),
		}

		return ctx

	def post(self, request, *args, **kwargs):
		action = (request.POST.get("action") or "").strip().lower()
		obj_id = (request.POST.get("id") or "").strip()
		value = (request.POST.get("value") or "").strip()

		line_id = (request.POST.get("line_id") or "").strip()
		part_id = (request.POST.get("part_id") or "").strip()
		defect_id = (request.POST.get("defect_id") or "").strip()
		scrap_id = (request.POST.get("scrap_id") or "").strip()

		line_code = (request.POST.get("line_code") or "").strip().upper()
		part_number = (request.POST.get("part_number") or "").strip()
		defect_name = (request.POST.get("defect_name") or "").strip()
		scrap_name = (request.POST.get("scrap_name") or "").strip()
		scrap_image = request.FILES.get("scrap_image")

		def _int_or_none(v: str):
			return int(v) if v and v.isdigit() else None

		line_pk = _int_or_none(line_id)
		part_pk = _int_or_none(part_id)
		defect_pk = _int_or_none(defect_id)
		scrap_pk = _int_or_none(scrap_id)

		# Unified row actions (preferred by UI)
		if action in {"update_master_row", "delete_master_row"}:
			try:
				with transaction.atomic():
					if action == "update_master_row":
						# Rename-only updates for each existing object in the row.
						# Does not re-parent objects; it just updates code/number/name fields.
						if line_pk is not None and line_code:
							line = ProductionLine.objects.get(pk=line_pk)
							if line.code != line_code:
								line.code = line_code
								line.save(update_fields=["code", "updated_at"])

						if part_pk is not None and part_number:
							part = PartNumber.objects.get(pk=part_pk)
							if part.number != part_number:
								part.number = part_number
								part.save(update_fields=["number", "updated_at"])

						if defect_pk is not None and defect_name:
							defect = DefectMode.objects.get(pk=defect_pk)
							defect_updated_fields = []
							if defect.name != defect_name:
								defect.name = defect_name
								defect_updated_fields.append("name")
							if defect_updated_fields:
								defect_updated_fields.append("updated_at")
								defect.save(update_fields=defect_updated_fields)

						if scrap_pk is not None and scrap_name:
							scrap = ScrapItem.objects.get(pk=scrap_pk)
							scrap_updated_fields = []
							if scrap.name != scrap_name:
								scrap.name = scrap_name
								scrap_updated_fields.append("name")
							if scrap_image is not None:
								scrap.reference_image = scrap_image
								scrap_updated_fields.append("reference_image")
							if scrap_updated_fields:
								scrap_updated_fields.append("updated_at")
								scrap.save(update_fields=scrap_updated_fields)

						messages.success(request, "บันทึกการแก้ไขสำเร็จ")
						return self.get(request, *args, **kwargs)

					# delete_master_row: delete deepest object in the row
					if scrap_pk is not None:
						ScrapItem.objects.get(pk=scrap_pk).delete()
						messages.success(request, "ลบ Scrap สำเร็จ")
						return self.get(request, *args, **kwargs)
					if defect_pk is not None:
						DefectMode.objects.get(pk=defect_pk).delete()
						messages.success(request, "ลบ Defect สำเร็จ")
						return self.get(request, *args, **kwargs)
					if part_pk is not None:
						PartNumber.objects.get(pk=part_pk).delete()
						messages.success(request, "ลบ Part สำเร็จ")
						return self.get(request, *args, **kwargs)
					if line_pk is not None:
						ProductionLine.objects.get(pk=line_pk).delete()
						messages.success(request, "ลบ Line สำเร็จ")
						return self.get(request, *args, **kwargs)

					messages.error(request, "ไม่พบข้อมูลให้ลบ")
					return self.get(request, *args, **kwargs)

			except ProtectedError:
				messages.error(
					request,
					"ลบไม่ได้: มีข้อมูล Scrap Record อ้างอิงอยู่ (โปรดลบ/ย้ายรายการในหน้า manage_scrap หรือหน้า record ก่อน)",
				)
			except IntegrityError as e:
				messages.error(request, f"บันทึกไม่สำเร็จ (ข้อมูลซ้ำหรือผิดเงื่อนไข): {e}")
			except Exception as e:
				messages.error(request, f"เกิดข้อผิดพลาด: {e}")

			return self.get(request, *args, **kwargs)

		# Legacy per-level actions (kept for backwards compatibility)
		if not obj_id.isdigit():
			messages.error(request, "ไม่พบรหัสรายการ")
			return self.get(request, *args, **kwargs)

		pk = int(obj_id)

		try:
			with transaction.atomic():
				if action == "update_line":
					new_code = value.upper()
					if not new_code:
						messages.error(request, "กรุณากรอก Production line code")
						return self.get(request, *args, **kwargs)
					line = ProductionLine.objects.get(pk=pk)
					old = line.code
					line.code = new_code
					line.save(update_fields=["code", "updated_at"])
					messages.success(request, f"อัปเดต Production line {old} → {new_code} สำเร็จ")

				elif action == "delete_line":
					line = ProductionLine.objects.get(pk=pk)
					code = line.code
					line.delete()
					messages.success(request, f"ลบ Production line {code} สำเร็จ")

				elif action == "update_part":
					new_number = value
					if not new_number:
						messages.error(request, "กรุณากรอก Part number")
						return self.get(request, *args, **kwargs)
					part = PartNumber.objects.select_related("production_line").get(pk=pk)
					old = part.number
					part.number = new_number
					part.save(update_fields=["number", "updated_at"])
					messages.success(request, f"อัปเดต Part {part.production_line.code}: {old} → {new_number} สำเร็จ")

				elif action == "delete_part":
					part = PartNumber.objects.select_related("production_line").get(pk=pk)
					label = f"{part.production_line.code} {part.number}"
					part.delete()
					messages.success(request, f"ลบ Part {label} สำเร็จ")

				elif action == "update_defect":
					new_name = value
					if not new_name:
						messages.error(request, "กรุณากรอก Defect mode")
						return self.get(request, *args, **kwargs)
					defect = DefectMode.objects.select_related("part__production_line").get(pk=pk)
					old = defect.name
					defect.name = new_name
					defect.save(update_fields=["name", "updated_at"])
					messages.success(
						request,
						f"อัปเดต Defect {defect.part.production_line.code} {defect.part.number}: {old} → {new_name} สำเร็จ",
					)

				elif action == "delete_defect":
					defect = DefectMode.objects.select_related("part__production_line", "part").get(pk=pk)
					label = f"{defect.part.production_line.code} {defect.part.number} / {defect.name}"
					defect.delete()
					messages.success(request, f"ลบ Defect {label} สำเร็จ")

				elif action == "update_scrap":
					new_name = value
					if not new_name:
						messages.error(request, "กรุณากรอก Scrap item")
						return self.get(request, *args, **kwargs)
					scrap = ScrapItem.objects.select_related("defect_mode__part__production_line").get(pk=pk)
					old = scrap.name
					scrap.name = new_name
					scrap.save(update_fields=["name", "updated_at"])
					messages.success(
						request,
						f"อัปเดต Scrap {scrap.defect_mode.part.production_line.code} {scrap.defect_mode.part.number} / {scrap.defect_mode.name}: {old} → {new_name} สำเร็จ",
					)

				elif action == "delete_scrap":
					scrap = ScrapItem.objects.select_related("defect_mode__part__production_line").get(pk=pk)
					label = f"{scrap.defect_mode.part.production_line.code} {scrap.defect_mode.part.number} / {scrap.defect_mode.name} / {scrap.name}"
					scrap.delete()
					messages.success(request, f"ลบ Scrap {label} สำเร็จ")

				else:
					messages.error(request, "คำสั่งไม่ถูกต้อง")

		except ProductionLine.DoesNotExist:
			messages.error(request, "ไม่พบ Production line")
		except PartNumber.DoesNotExist:
			messages.error(request, "ไม่พบ Part number")
		except DefectMode.DoesNotExist:
			messages.error(request, "ไม่พบ Defect mode")
		except ScrapItem.DoesNotExist:
			messages.error(request, "ไม่พบ Scrap item")
		except ProtectedError:
			messages.error(
				request,
				"ลบไม่ได้: มีข้อมูล Scrap Record อ้างอิงอยู่ (โปรดลบ/ย้ายรายการในหน้า manage_scrap หรือหน้า record ก่อน)",
			)
		except IntegrityError as e:
			messages.error(request, f"บันทึกไม่สำเร็จ (ข้อมูลซ้ำหรือผิดเงื่อนไข): {e}")
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")

		return self.get(request, *args, **kwargs)
