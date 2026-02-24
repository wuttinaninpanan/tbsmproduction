from __future__ import annotations

import re
import uuid

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator

from core.auth.decorators import staff_required
from core.models.line import Line
from core.models.line_process import LineProcess
from core.services.auditlog import log_event


try:
    import openpyxl  # type: ignore
except Exception:  # pragma: no cover
    openpyxl = None


def _normalized_key(key: str) -> str:
    key = (key or "").strip().lower()
    key = re.sub(r"[^0-9a-z]+", "_", key)
    key = re.sub(r"_+", "_", key).strip("_")
    return key


def _excel_to_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value)
    return str(value).strip()


def _row_get_first(row: dict, *keys: str) -> str:
    for k in keys:
        if not k:
            continue
        v = row.get(k)
        s = _excel_to_str(v).strip()
        if s != "":
            return s
    return ""


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


def download_manage_line_import_template(request):
    """Download a template for importing production lines."""
    headers = [
        "line_name",
        "process_type",
        "description",
    ]

    # Use existing process names in sample rows (if available) to reduce confusion.
    process_samples: list[str] = []
    for p in LineProcess.objects.order_by("display_name", "name")[:2]:
        label = (getattr(p, "display_name", "") or getattr(p, "name", "") or "").strip()
        if label:
            process_samples.append(label)
    while len(process_samples) < 2:
        process_samples.append(f"PROCESS-{chr(ord('A') + len(process_samples))}")

    rows = [
        ["LINE-01", process_samples[0], "Main line"],
        ["LINE-02", process_samples[1], ""],
    ]

    if openpyxl is None:
        return HttpResponse(
            "XLSX format is not available (openpyxl is not installed).",
            status=400,
            content_type="text/plain; charset=utf-8",
        )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "lines"
    ws.append(headers)
    for r in rows:
        ws.append(r)
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 22

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="manage_line_import_template.xlsx"'
    wb.save(response)
    return response


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
class ManageLineViews(TemplateView):
    template_name = "manage_line.html"

    def get(self, request, *args, **kwargs):
        action = (request.GET.get("action") or "").strip().lower()
        if action == "download_template":
            return download_manage_line_import_template(request)
        return super().get(request, *args, **kwargs)

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

        qs = Line.objects.select_related("line_process").all()
        if q:
            qs = qs.filter(
                Q(line_name__icontains=q)
                | Q(description__icontains=q)
                | Q(line_process__name__icontains=q)
                | Q(line_process__display_name__icontains=q)
            )

        qs = qs.order_by("line_name")
        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)

        rows = []
        for line in page_obj.object_list:
            rows.append(
                {
                    "id": str(line.id),
                    "line_name": line.line_name,
                    "description": line.description or "",
                    "process_type_id": str(line.line_process_id) if line.line_process_id else "",
                    "process_type_name": getattr(line.line_process, "display_name", "")
                    or getattr(line.line_process, "name", ""),
                }
            )

        ctx["rows"] = rows
        ctx["processes"] = list(
            LineProcess.objects.order_by("display_name", "name").values(
                "id",
                "name",
                "display_name",
            )
        )

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

        if action == "import_master_data":
            if openpyxl is None:
                messages.error(request, "ไม่สามารถนำเข้า XLSX ได้: ยังไม่ได้ติดตั้ง openpyxl")
                return self.get(request, *args, **kwargs)
            upload = request.FILES.get("excel_file")
            if upload is None:
                messages.error(request, "กรุณาเลือกไฟล์ Excel (.xlsx)")
                return self.get(request, *args, **kwargs)
            name = (getattr(upload, "name", "") or "").lower()
            if not name.endswith(".xlsx"):
                messages.error(request, "รองรับเฉพาะไฟล์ .xlsx")
                return self.get(request, *args, **kwargs)

            created = 0
            updated = 0
            skipped = 0
            process_not_found = 0
            try:
                with transaction.atomic():
                    for row in _parse_xlsx(upload):
                        line_name = _row_get_first(row, "line_name", "line", "production_line")
                        description = _row_get_first(row, "description", "desc")
                        process_key = _row_get_first(
                            row,
                            "process_type",
                            "process_type_name",
                            "process",
                            "process_name",
                            "line_process",
                        )

                        if not line_name or not process_key:
                            skipped += 1
                            continue

                        process = (
                            LineProcess.objects.filter(display_name__iexact=process_key).first()
                            or LineProcess.objects.filter(name__iexact=process_key).first()
                        )
                        if process is None:
                            process_not_found += 1
                            continue

                        existing = Line.objects.filter(line_name__iexact=line_name).first()
                        if existing is None:
                            Line.objects.create(
                                line_name=line_name,
                                description=description,
                                line_process=process,
                                user=request.user,
                            )
                            created += 1
                        else:
                            existing.line_name = line_name
                            existing.description = description
                            existing.line_process = process
                            existing.save(update_fields=["line_name", "description", "line_process", "updated_at"])
                            updated += 1
            except Exception as e:
                log_event(
                    request,
                    action="line:import_master_data",
                    status="failure",
                    message="นำเข้า Line ไม่สำเร็จ",
                    metadata={"filename": getattr(upload, "name", ""), "error": str(e)},
                )
                messages.error(request, f"เกิดข้อผิดพลาดระหว่างนำเข้า: {e}")
                return self.get(request, *args, **kwargs)

            messages.success(
                request,
                f"นำเข้าสำเร็จ: +{created}, อัปเดต {updated}, ข้าม {skipped}, ไม่พบ Process {process_not_found}",
            )
            transaction.on_commit(
                lambda: log_event(
                    request,
                    action="line:import_master_data",
                    message="นำเข้า Line สำเร็จ",
                    metadata={
                        "filename": getattr(upload, "name", ""),
                        "created": created,
                        "updated": updated,
                        "skipped": skipped,
                        "process_not_found": process_not_found,
                    },
                )
            )
            return self.get(request, *args, **kwargs)

        if action == "bulk_delete_lines":
            bulk_ids = request.POST.getlist("bulk_id")
            ids = [pk for pk in bulk_ids if _is_uuid((pk or "").strip())]
            if not ids:
                messages.error(request, "กรุณาเลือกรายการที่ต้องการลบ")
                return self.get(request)

            deleted = 0
            blocked = 0
            not_found = 0
            try:
                with transaction.atomic():
                    for pk in ids:
                        obj = Line.objects.filter(pk=pk).first()
                        if obj is None:
                            not_found += 1
                            continue
                        try:
                            obj.delete()
                            deleted += 1
                        except ProtectedError:
                            blocked += 1
            except Exception as e:
                log_event(
                    request,
                    action="line:bulk_delete",
                    status="failure",
                    message="ลบ Line แบบ bulk ไม่สำเร็จ",
                    metadata={"selected": len(ids), "error": str(e)},
                )
                messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                return self.get(request)

            transaction.on_commit(
                lambda: log_event(
                    request,
                    action="line:bulk_delete",
                    message="ลบ Line แบบ bulk",
                    metadata={
                        "selected": len(ids),
                        "deleted": deleted,
                        "blocked": blocked,
                        "not_found": not_found,
                    },
                )
            )

            if blocked:
                messages.warning(
                    request,
                    f"ลบสำเร็จ {deleted} รายการ (ติดใช้งาน/ลบไม่ได้ {blocked}, ไม่พบ {not_found})",
                )
            else:
                messages.success(request, f"ลบสำเร็จ {deleted} รายการ")
            return self.get(request)

        if action in {"update", "delete"}:
            if not _is_uuid(obj_id):
                messages.error(request, "ไม่พบรหัสรายการ")
                return self.get(request)

        if action == "delete":
            obj = Line.objects.filter(pk=obj_id).first()
            if obj is None:
                messages.error(request, "ไม่พบรายการ")
                return self.get(request)
            try:
                obj.delete()
            except ProtectedError:
                messages.error(request, "ไม่สามารถลบได้: รายการนี้ถูกใช้งานอยู่")
                return self.get(request)

            transaction.on_commit(
                lambda: log_event(
                    request,
                    action="line:delete",
                    message="ลบ Line",
                    metadata={"id": obj_id, "line_name": obj.line_name},
                )
            )
            messages.success(request, "ลบรายการสำเร็จ")
            return self.get(request)

        line_name = (request.POST.get("line_name") or "").strip()
        description = (request.POST.get("description") or "").strip()
        process_type_id = (request.POST.get("process_type_id") or "").strip()

        if not line_name:
            messages.error(request, "กรุณาระบุ Production line")
            return self.get(request)
        if not _is_uuid(process_type_id):
            messages.error(request, "กรุณาเลือก Process type")
            return self.get(request)

        process = LineProcess.objects.filter(pk=process_type_id).first()
        if process is None:
            messages.error(request, "ไม่พบ Process type")
            return self.get(request)

        if action == "update":
            obj = Line.objects.filter(pk=obj_id).first()
            if obj is None:
                messages.error(request, "ไม่พบรายการ")
                return self.get(request)
            obj.line_name = line_name
            obj.description = description
            obj.line_process = process
            obj.save(update_fields=["line_name", "description", "line_process", "updated_at"])

            transaction.on_commit(
                lambda: log_event(
                    request,
                    action="line:update",
                    message="แก้ไข Line",
                    metadata={"id": obj_id, "line_name": line_name, "process_type": str(process.id)},
                )
            )
            messages.success(request, "แก้ไขรายการสำเร็จ")
            return self.get(request)

        # Default: create
        try:
            obj = Line.objects.create(
                line_name=line_name,
                description=description,
                line_process=process,
                user=request.user,
            )
        except Exception as e:
            log_event(
                request,
                action="line:create",
                status="failure",
                message="เพิ่ม Line ไม่สำเร็จ",
                metadata={"error": str(e)},
            )
            messages.error(request, f"เพิ่มข้อมูลไม่สำเร็จ: {e}")
            return self.get(request)

        transaction.on_commit(
            lambda: log_event(
                request,
                action="line:create",
                message="เพิ่ม Line",
                metadata={"id": str(obj.id), "line_name": obj.line_name, "process_type": str(process.id)},
            )
        )
        messages.success(request, "เพิ่มข้อมูลสำเร็จ")
        return self.get(request)
