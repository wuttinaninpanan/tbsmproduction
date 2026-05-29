from __future__ import annotations

from datetime import timedelta

from django.db.models import F, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView  # type:ignore

from core.auth.decorators import user_required
from core.models.defect_mode import DefectMode
from core.models.item_list import Item_list
from core.models.line import Line
from core.models.process_defect import ProcessDefect, ProcessDefectScrap, ProductionRecord


def _rate(defects, produced) -> float:
    """Defect rate (%) = defects / produced × 100 (0 when nothing produced)."""
    return round(defects / produced * 100, 2) if produced else 0.0


@method_decorator(user_required, name="dispatch")
class DashboardViews(TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        today = timezone.localdate()
        now = timezone.localtime(timezone.now())
        year, month = today.year, today.month
        is_staff = bool(self.request.user.is_staff or self.request.user.is_superuser)

        # Production backbone: ProductionRecord (qty produced) → ProcessDefect
        # (qty defective) → ProcessDefectScrap (pieces scrapped).
        pr_qs = ProductionRecord.objects.all()
        pd_qs = ProcessDefect.objects.all()
        scrap_qs = ProcessDefectScrap.objects.all()
        if not is_staff:
            user = self.request.user
            pr_qs = pr_qs.filter(created_by=user)
            pd_qs = pd_qs.filter(production_record__created_by=user)
            scrap_qs = scrap_qs.filter(process_defect__production_record__created_by=user)

        pr_month = pr_qs.filter(created_at__year=year, created_at__month=month)
        pd_month = pd_qs.filter(created_at__year=year, created_at__month=month)

        def _sum(qs, field):
            return qs.aggregate(s=Sum(field))["s"] or 0

        produced_month = _sum(pr_month, "products_quantity")
        defects_month = _sum(pd_month, "quantity")
        produced_today = _sum(pr_qs.filter(created_at__date=today), "products_quantity")
        defects_today = _sum(pd_qs.filter(created_at__date=today), "quantity")
        scrap_month = _sum(scrap_qs.filter(created_at__year=year, created_at__month=month), "quantity")

        ctx["kpi"] = {
            "produced_today": produced_today,
            "produced_month": produced_month,
            "produced_total": _sum(pr_qs, "products_quantity"),
            "defects_today": defects_today,
            "defects_month": defects_month,
            "defects_total": _sum(pd_qs, "quantity"),
            "defect_rate_month": _rate(defects_month, produced_month),
            "scrap_month": scrap_month,
            "lines_total": Line.objects.count(),
            "parts_total": Item_list.objects.count(),
            "component_parts_total": Item_list.objects.count(),
            "defect_modes_total": DefectMode.objects.count(),
        }

        # ---- Top production lines this month (produced / defects / rate) ----
        prod_by_line = {
            r["ln"]: int(r["s"] or 0)
            for r in pr_month.values(ln=F("line__line_name")).annotate(s=Sum("products_quantity"))
        }
        def_by_line = {
            r["ln"]: int(r["s"] or 0)
            for r in pd_month.values(ln=F("production_record__line__line_name")).annotate(s=Sum("quantity"))
        }
        top_lines_month = [
            {
                "line": ln or "-",
                "produced": prod_by_line.get(ln, 0),
                "defects": def_by_line.get(ln, 0),
                "rate": _rate(def_by_line.get(ln, 0), prod_by_line.get(ln, 0)),
            }
            for ln in (set(prod_by_line) | set(def_by_line))
        ]
        # 10 lines with the highest defect rate (tie → more defects, then name).
        top_lines_month.sort(key=lambda x: (-x["rate"], -x["defects"], x["line"]))
        ctx["top_lines_month"] = top_lines_month[:10]

        # ---- Top items this month (produced / defects / rate) ----
        prod_by_item: dict = {}
        item_label: dict = {}
        for r in pr_month.values("item_id", sd=F("item__sd_code"), nm=F("item__part_name")).annotate(s=Sum("products_quantity")):
            prod_by_item[r["item_id"]] = int(r["s"] or 0)
            item_label[r["item_id"]] = (r["sd"] or "-", r["nm"] or "")
        def_by_item: dict = {}
        for r in pd_month.values(
            iid=F("production_record__item_id"),
            sd=F("production_record__item__sd_code"),
            nm=F("production_record__item__part_name"),
        ).annotate(s=Sum("quantity")):
            def_by_item[r["iid"]] = int(r["s"] or 0)
            item_label.setdefault(r["iid"], (r["sd"] or "-", r["nm"] or ""))
        top_items_month = []
        for iid in (set(prod_by_item) | set(def_by_item)):
            p = prod_by_item.get(iid, 0)
            d = def_by_item.get(iid, 0)
            sd, nm = item_label.get(iid, ("-", ""))
            top_items_month.append(
                {"sd": sd or "-", "name": nm or "", "produced": p, "defects": d, "rate": _rate(d, p)}
            )
        # 10 items with the highest defect rate (tie → more defects, then SD).
        top_items_month.sort(key=lambda x: (-x["rate"], -x["defects"], x["sd"]))
        ctx["top_items_month"] = top_items_month[:10]

        # ---- Top defect modes this month (by defective qty) ----
        top_defect_modes_month = [
            {"name": r["nm"] or "-", "total_qty": int(r["s"] or 0)}
            for r in pd_month.values(nm=F("defect_mode__name_th"))
            .annotate(s=Sum("quantity"))
            .order_by("-s", "nm")[:6]
        ]
        ctx["top_defect_modes_month"] = top_defect_modes_month

        # ---- Daily produced vs defective (last 14 days) ----
        days = 14
        start_date = today - timedelta(days=days - 1)
        date_keys, date_labels = [], []
        for i in range(days):
            d = start_date + timedelta(days=i)
            date_keys.append(d.isoformat())
            date_labels.append(d.strftime("%d %b"))

        def _daily_map(qs, field):
            return {
                (row["d"].isoformat() if row.get("d") else ""): int(row.get("s") or 0)
                for row in qs.filter(created_at__date__gte=start_date, created_at__date__lte=today)
                .annotate(d=TruncDate("created_at"))
                .values("d")
                .annotate(s=Sum(field))
            }

        produced_daily = _daily_map(pr_qs, "products_quantity")
        defects_daily = _daily_map(pd_qs, "quantity")
        scrap_daily = _daily_map(scrap_qs, "quantity")  # pieces thrown (ProcessDefectScrap)

        # ---- Top "Single part" scraps this month ----
        # A single-part scrap is a not-yet-assembled component thrown away with
        # no produced product → its ProductionRecord has item IS NULL (the unique
        # marker set by /record/defects/). Broken down by the scrapped component.
        single_scrap_qs = scrap_qs.filter(
            created_at__year=year,
            created_at__month=month,
            process_defect__production_record__item__isnull=True,
        )
        single_part_rows = [
            {"sd": r["sd"] or "-", "name": r["nm"] or "", "qty": int(r["s"] or 0)}
            for r in single_scrap_qs.values(
                sd=F("component_part__sd_code"),
                nm=F("component_part__part_name"),
            )
            .annotate(s=Sum("quantity"))
            .order_by("-s", "sd")[:10]
        ]
        ctx["single_part_month"] = sum(x["qty"] for x in single_part_rows)

        ctx["charts"] = {
            "daily": {
                "labels": date_labels,
                "data": [produced_daily.get(k, 0) for k in date_keys],
                "data2": [defects_daily.get(k, 0) for k in date_keys],
                "label1": "ผลิต",
                "label2": "ของเสีย",
            },
            "scrap_daily": {
                "labels": date_labels,
                "data": [scrap_daily.get(k, 0) for k in date_keys],
            },
            "top_defect": {
                "labels": [x["name"] for x in top_defect_modes_month],
                "data": [x["total_qty"] for x in top_defect_modes_month],
            },
            "single_part": {
                "labels": [x["sd"] for x in single_part_rows],
                "names": [x["name"] for x in single_part_rows],
                "data": [x["qty"] for x in single_part_rows],
            },
        }

        # ---- Recent production records (line · part · produced · defects · rate) ----
        recent_records = list(
            pr_qs.select_related("line", "item", "created_by", "created_by__profile")
            .prefetch_related("defects")
            .order_by("-created_at")[:10]
        )
        # Surface any defect comments (e.g. the reason typed for an "อื่นๆ" defect).
        for r in recent_records:
            r.defect_comments = [
                (d.comment or "").strip() for d in r.defects.all() if (d.comment or "").strip()
            ]
        ctx["recent_records"] = recent_records

        ctx["now"] = now
        ctx["is_staff"] = is_staff
        return ctx
