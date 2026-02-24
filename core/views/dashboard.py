from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models import F
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView  # type:ignore

from core.auth.decorators import user_required
from core.models.defect_mode import DefectMode
from core.models.item_list import Item_list
from core.models.line import Line
from core.models.scrap_record import ScrapRecord


@method_decorator(user_required, name="dispatch")
class DashboardViews(TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        today = timezone.localdate()
        now = timezone.localtime(timezone.now())
        current_year = today.year
        current_month = today.month

        records_qs = ScrapRecord.objects.all()
        is_staff = bool(self.request.user.is_staff or self.request.user.is_superuser)

        if is_staff:
            scoped_qs = records_qs
        else:
            scoped_qs = records_qs.filter(created_by=self.request.user)

        recent_qs = scoped_qs

        ctx["kpi"] = {
            "records_today": records_qs.filter(created_at__date=today).count(),
            "records_month": records_qs.filter(created_at__year=current_year, created_at__month=current_month).count(),
            "records_total": records_qs.count(),
            "lines_total": Line.objects.count(),
            "parts_total": Item_list.objects.count(),
            "component_parts_total": Item_list.objects.count(),
            "defect_modes_total": DefectMode.objects.count(),
        }

        top_raw = list(
            scoped_qs.filter(created_at__year=current_year, created_at__month=current_month)
            .values(line_name=F("production_line__line_name"))
            .annotate(total_qty=Sum("quantity"), total_records=Count("id"))
            .order_by("-total_qty", "-total_records", "line_name")[:5]
        )
        ctx["top_lines_month"] = [
            {
                "production_line__code": (r.get("line_name") or "-")
                if (r.get("line_name") is not None)
                else "-",
                "total_qty": r.get("total_qty") or 0,
                "total_records": r.get("total_records") or 0,
            }
            for r in top_raw
        ]

        # Charts
        days = 14
        start_date = today - timedelta(days=days - 1)
        date_labels: list[str] = []
        date_keys: list[str] = []
        for i in range(days):
            d = start_date + timedelta(days=i)
            date_keys.append(d.isoformat())
            date_labels.append(d.strftime("%d %b"))

        daily_counts_map = {
            (row["d"].isoformat() if row.get("d") else ""): int(row.get("c") or 0)
            for row in scoped_qs.filter(created_at__date__gte=start_date, created_at__date__lte=today)
            .annotate(d=TruncDate("created_at"))
            .values("d")
            .annotate(c=Count("id"))
        }
        daily_counts = [daily_counts_map.get(k, 0) for k in date_keys]

        top_defect_raw = list(
            scoped_qs.filter(created_at__year=current_year, created_at__month=current_month)
            .values(defect_name=F("defect_mode__name_th"))
            .annotate(total_qty=Sum("quantity"), total_records=Count("id"))
            .order_by("-total_qty", "-total_records", "defect_name")[:5]
        )
        ctx["top_defect_modes_month"] = [
            {
                "name": (r.get("defect_name") or "-"),
                "total_qty": r.get("total_qty") or 0,
                "total_records": r.get("total_records") or 0,
            }
            for r in top_defect_raw
        ]

        top_line_labels = [r.get("production_line__code") or "-" for r in ctx["top_lines_month"]]
        top_line_qty = [int(r.get("total_qty") or 0) for r in ctx["top_lines_month"]]

        top_defect_labels = [r.get("name") or "-" for r in ctx["top_defect_modes_month"]]
        top_defect_qty = [int(r.get("total_qty") or 0) for r in ctx["top_defect_modes_month"]]

        ctx["charts"] = {
            "daily": {"labels": date_labels, "data": daily_counts},
            "top_lines": {"labels": top_line_labels, "data": top_line_qty},
            "top_defect": {"labels": top_defect_labels, "data": top_defect_qty},
        }

        ctx["recent_records"] = list(
            recent_qs.select_related(
                "production_line",
                "part_number",
                "defect_mode",
                "component_part",
                "created_by",
                "created_by__profile",
            )
            .order_by("-created_at")[:10]
        )

        ctx["now"] = now
        ctx["is_staff"] = is_staff
        return ctx