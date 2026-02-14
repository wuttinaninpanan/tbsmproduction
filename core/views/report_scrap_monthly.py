import calendar
from datetime import datetime, timedelta

from django.db.models import DateTimeField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.utils import timezone
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator

from core.auth.decorators import staff_required
from core.models import PartNumber, ProductionLine, ComponentPartRecord

try:
	import openpyxl  # type: ignore
except Exception:  # pragma: no cover
	openpyxl = None


@method_decorator(staff_required, name="dispatch")
class MonthlyComponentPartReportViews(TemplateView):
    template_name = "report_scrap_monthly.html"

    def get(self, request, *args, **kwargs):
        export = (request.GET.get("export") or "").strip().lower()
        if export == "xlsx":
            return self._export_xlsx()
        return super().get(request, *args, **kwargs)

    def _parse_month_year(self):
        month_raw = (self.request.GET.get("month") or "").strip()
        now = timezone.localtime(timezone.now())

        year = now.year
        month = now.month
        if month_raw:
            try:
                parts = month_raw.split("-")
                if len(parts) == 2:
                    year = int(parts[0])
                    month = int(parts[1])
                    if not (1 <= month <= 12):
                        raise ValueError("month out of range")
            except Exception:
                year = now.year
                month = now.month
        return year, month

    def _build_report(self, year: int, month: int, selected_line: str):
        tz = timezone.get_current_timezone()

        start_dt = timezone.make_aware(datetime(year, month, 1, 8, 0, 0), tz)
        if month == 12:
            end_dt = timezone.make_aware(datetime(year + 1, 1, 1, 8, 0, 0), tz)
        else:
            end_dt = timezone.make_aware(datetime(year, month + 1, 1, 8, 0, 0), tz)

        days_in_month = calendar.monthrange(year, month)[1]
        days = list(range(1, days_in_month + 1))

        parts_qs = (
            PartNumber.objects.select_related("production_line")
            .all()
            .order_by("production_line__code", "number")
        )
        if selected_line:
            parts_qs = parts_qs.filter(production_line__code=selected_line)
        parts_list = list(parts_qs)

        adjusted_dt = ExpressionWrapper(
            F("created_at") - Value(timedelta(hours=8)),
            output_field=DateTimeField(),
        )

        records_qs = ComponentPartRecord.objects.filter(created_at__gte=start_dt, created_at__lt=end_dt)
        if selected_line:
            records_qs = records_qs.filter(part_number__production_line__code=selected_line)

        agg = (
            records_qs.annotate(work_date=TruncDate(adjusted_dt))
            .values("part_number_id", "work_date")
            .annotate(total=Sum("quantity"))
        )

        part_day_totals: dict[tuple[int, int], int] = {}
        for r in agg:
            part_id = r.get("part_number_id")
            work_date = r.get("work_date")
            total = int(r.get("total") or 0)
            if not part_id or work_date is None:
                continue
            day = int(work_date.day)
            if 1 <= day <= days_in_month:
                part_day_totals[(int(part_id), day)] = total

        column_totals = {d: 0 for d in days}
        grand_total = 0
        rows = []
        for part in parts_list:
            values = []
            row_total = 0
            for d in days:
                v = int(part_day_totals.get((part.id, d), 0))
                values.append(v)
                row_total += v
                column_totals[d] += v
            grand_total += row_total
            rows.append(
                {
                    "production_line": part.production_line.code,
                    "part_number": part.number,
                    "values": values,
                    "total": row_total,
                }
            )

        return days, rows, [column_totals[d] for d in days], grand_total

    def _export_xlsx(self):
        if openpyxl is None:
            return HttpResponse(
                "XLSX export is not available (openpyxl is not installed).",
                status=400,
                content_type="text/plain; charset=utf-8",
            )

        selected_line = (self.request.GET.get("line") or "").strip().upper()
        year, month = self._parse_month_year()
        days, rows, column_totals, grand_total = self._build_report(year, month, selected_line)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"{year:04d}-{month:02d}"

        header = ["Production Line", "Part Number"] + [str(d) for d in days] + ["Total"]
        ws.append(header)
        for r in rows:
            ws.append([r["production_line"], r["part_number"], *r["values"], r["total"]])

        # Footer totals
        ws.append(["", "Total", *column_totals, grand_total])

        ws.freeze_panes = "C2"
        # Basic widths
        ws.column_dimensions["A"].width = 18
        ws.column_dimensions["B"].width = 18

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        suffix = f"_{selected_line}" if selected_line else ""
        response["Content-Disposition"] = (
            f'attachment; filename="component_part_monthly_{year:04d}-{month:02d}{suffix}.xlsx"'
        )
        wb.save(response)
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        selected_line = (self.request.GET.get("line") or "").strip().upper()
        year, month = self._parse_month_year()
        days, rows, column_totals, grand_total = self._build_report(year, month, selected_line)

        ctx.update(
            {
                "year": year,
                "month": month,
                "month_value": f"{year:04d}-{month:02d}",
                "production_lines": list(ProductionLine.objects.order_by("code").values_list("code", flat=True)),
                "selected_line": selected_line,
                "days": days,
                "rows": rows,
                "column_totals": column_totals,
                "grand_total": grand_total,
            }
        )
        return ctx
