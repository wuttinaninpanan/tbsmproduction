from __future__ import annotations

import csv
from datetime import date

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView  # type:ignore

from core.auth.decorators import admin_required
from core.models import AuditLogEntry


@method_decorator(admin_required, name="dispatch")
class AuditLogViews(TemplateView):
    template_name = "auditlog.html"

    def get(self, request, *args, **kwargs):
        export = (request.GET.get("export") or "").strip().lower()
        if export == "csv":
            qs = self._filtered_qs()
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = 'attachment; filename="audit_log.csv"'
            response.write("\ufeff")
            writer = csv.writer(response, lineterminator="\r\n")
            writer.writerow(["created_at", "actor", "action", "status", "ip_address", "message"])
            for row in qs.select_related("actor")[:50000]:
                actor = row.actor.username if row.actor_id else (row.actor_username or "")
                writer.writerow(
                    [
                        row.created_at.isoformat(sep=" ", timespec="seconds"),
                        actor,
                        row.action,
                        row.status,
                        row.ip_address or "",
                        (row.message or "").replace("\n", " ").strip(),
                    ]
                )
            return response
        return super().get(request, *args, **kwargs)

    def _filtered_qs(self):
        request = self.request
        q = (request.GET.get("q") or "").strip()
        action = (request.GET.get("action") or "").strip()
        status = (request.GET.get("status") or "").strip().lower()
        start_raw = (request.GET.get("start") or "").strip()
        end_raw = (request.GET.get("end") or "").strip()

        qs = AuditLogEntry.objects.all().select_related("actor")

        if q:
            qs = qs.filter(
                Q(action__icontains=q)
                | Q(message__icontains=q)
                | Q(ip_address__icontains=q)
                | Q(actor__username__icontains=q)
                | Q(actor__first_name__icontains=q)
                | Q(actor__last_name__icontains=q)
                | Q(actor_username__icontains=q)
            )

        if action:
            qs = qs.filter(action=action)

        if status in {"success", "failure", "info"}:
            qs = qs.filter(status=status)

        start_d: date | None = parse_date(start_raw) if start_raw else None
        end_d: date | None = parse_date(end_raw) if end_raw else None
        if start_d:
            qs = qs.filter(created_at__date__gte=start_d)
        if end_d:
            qs = qs.filter(created_at__date__lte=end_d)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request

        q = (request.GET.get("q") or "").strip()
        action = (request.GET.get("action") or "").strip()
        status = (request.GET.get("status") or "").strip().lower()
        start_raw = (request.GET.get("start") or "").strip()
        end_raw = (request.GET.get("end") or "").strip()
        page = (request.GET.get("page") or "1").strip() or "1"
        per_page_raw = (request.GET.get("per_page") or "").strip()

        qs = self._filtered_qs()

        allowed_per_page = {20, 50, 100, 200}
        try:
            per_page = int(per_page_raw or 50)
        except Exception:
            per_page = 50
        if per_page not in allowed_per_page:
            per_page = 50

        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)

        action_options = [
            r["action"]
            for r in AuditLogEntry.objects.values("action")
            .annotate(c=Count("id"))
            .order_by("action")
            if r.get("action")
        ]

        kpi = {
            "total": qs.count(),
            "actors": qs.exclude(actor__isnull=True).values("actor_id").distinct().count(),
            "logins": qs.filter(action="login").count(),
            "failures": qs.filter(status="failure").count(),
        }

        ctx.update(
            {
                "rows": list(page_obj.object_list),
                "q": q,
                "filter_action": action,
                "filter_status": status,
                "start": start_raw,
                "end": end_raw,
                "kpi": kpi,
                "action_options": action_options,
                "page_obj": page_obj,
                "paginator": paginator,
                "per_page": per_page,
                "rows_total": paginator.count,
            }
        )
        return ctx