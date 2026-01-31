from django.views.generic import TemplateView


class ManageScrapViews(TemplateView):
    template_name = "manage-scrap.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Until persistence is implemented, provide safe defaults so the page renders.
        ctx.setdefault("scrap_records", [])
        ctx.setdefault("production_lines", [])
        ctx.setdefault("selected_line", "")
        ctx.setdefault("q", "")
        ctx.setdefault("date_from", "")
        ctx.setdefault("date_to", "")
        ctx.setdefault("total_count", 0)
        # Optional: override in backend to point at a delete endpoint.
        ctx.setdefault("delete_action", "")
        return ctx

    def post(self, request, *args, **kwargs):
        # No persistence yet; keep the page functional for now.
        return self.get(request, *args, **kwargs)
