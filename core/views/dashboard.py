from __future__ import annotations

from datetime import timedelta

from django.db.models import DateField, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
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

        pr_month = pr_qs.filter(
            Q(production_date__year=year, production_date__month=month)
            | Q(production_date__isnull=True, created_at__year=year, created_at__month=month)
        )
        pd_month = pd_qs.filter(
            Q(production_record__production_date__year=year, production_record__production_date__month=month)
            | Q(production_record__production_date__isnull=True, created_at__year=year, created_at__month=month)
        )
        scrap_month_qs = scrap_qs.filter(
            Q(process_defect__production_record__production_date__year=year, process_defect__production_record__production_date__month=month)
            | Q(process_defect__production_record__production_date__isnull=True, created_at__year=year, created_at__month=month)
        )

        def _sum(qs, field):
            return qs.aggregate(s=Sum(field))["s"] or 0

        scrap_amount_expr = ExpressionWrapper(
            F("quantity") * F("component_part__cost"),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        )
        scrap_weight_expr = ExpressionWrapper(
            F("quantity") * F("component_part__weight"),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        )

        def _scrap_amount(qs):
            return qs.aggregate(s=Sum(scrap_amount_expr))["s"] or 0

        def _scrap_weight(qs):
            return qs.aggregate(s=Sum(scrap_weight_expr))["s"] or 0

        produced_month = _sum(pr_month, "products_quantity")
        defects_month = _sum(pd_month, "quantity")
        produced_today = _sum(
            pr_qs.filter(Q(production_date=today) | Q(production_date__isnull=True, created_at__date=today)),
            "products_quantity",
        )
        defects_today = _sum(
            pd_qs.filter(
                Q(production_record__production_date=today)
                | Q(production_record__production_date__isnull=True, created_at__date=today)
            ),
            "quantity",
        )
        scrap_month = _sum(scrap_month_qs, "quantity")
        scrap_today_qs = scrap_qs.filter(
            Q(process_defect__production_record__production_date=today)
            | Q(process_defect__production_record__production_date__isnull=True, created_at__date=today)
        )

        ctx["kpi"] = {
            "produced_today": produced_today,
            "produced_month": produced_month,
            "produced_total": _sum(pr_qs, "products_quantity"),
            "defects_today": defects_today,
            "defects_month": defects_month,
            "defects_total": _sum(pd_qs, "quantity"),
            "defect_rate_month": _rate(defects_month, produced_month),
            "scrap_month": scrap_month,
            "scrap_amount_today": _scrap_amount(scrap_today_qs),
            "scrap_amount_month": _scrap_amount(scrap_month_qs),
            "scrap_amount_total": _scrap_amount(scrap_qs),
            "scrap_weight_today": _scrap_weight(scrap_today_qs),
            "scrap_weight_month": _scrap_weight(scrap_month_qs),
            "scrap_weight_total": _scrap_weight(scrap_qs),
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
            date_field = Coalesce("production_date", TruncDate("created_at"), output_field=DateField())
            return {
                (row["d"].isoformat() if row.get("d") else ""): int(row.get("s") or 0)
                for row in qs.filter(
                    Q(production_date__gte=start_date, production_date__lte=today)
                    | Q(production_date__isnull=True, created_at__date__gte=start_date, created_at__date__lte=today)
                )
                .annotate(d=date_field)
                .values("d")
                .annotate(s=Sum(field))
            }

        def _related_daily_map(qs, field, pr_prefix):
            date_field = Coalesce(f"{pr_prefix}production_date", TruncDate("created_at"), output_field=DateField())
            return {
                (row["d"].isoformat() if row.get("d") else ""): int(row.get("s") or 0)
                for row in qs.filter(
                    Q(**{f"{pr_prefix}production_date__gte": start_date, f"{pr_prefix}production_date__lte": today})
                    | Q(**{f"{pr_prefix}production_date__isnull": True, "created_at__date__gte": start_date, "created_at__date__lte": today})
                )
                .annotate(d=date_field)
                .values("d")
                .annotate(s=Sum(field))
            }

        produced_daily = _daily_map(pr_qs, "products_quantity")
        defects_daily = _related_daily_map(pd_qs, "quantity", "production_record__")
        scrap_daily = _related_daily_map(scrap_qs, "quantity", "process_defect__production_record__")  # pieces thrown (ProcessDefectScrap)

        # ---- Top "Single part" scraps this month ----
        # A single-part scrap is a not-yet-assembled component thrown away with
        # no produced product → its ProductionRecord has item IS NULL (the unique
        # marker set by /record/defects/). Broken down by the scrapped component.
        single_scrap_qs = scrap_month_qs.filter(
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
            pr_qs.select_related("line", "item", "shift", "created_by", "created_by__profile")
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
