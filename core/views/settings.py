from django.views.generic import TemplateView


class SettingsViews(TemplateView):
    template_name = "add-production.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Until persistence is implemented, provide safe defaults so the page renders.
        ctx.setdefault("production_lines", [])
        ctx.setdefault("master_data", {"productionLines": []})
        return ctx

    def post(self, request, *args, **kwargs):
        # No persistence yet; keep the page functional for now.
        return self.get(request, *args, **kwargs)
