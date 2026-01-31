from django.views.generic import TemplateView


class RecordViews(TemplateView):
    template_name = "record.html"

    def post(self, request, *args, **kwargs):
        # No persistence yet; keep the page functional for now.
        return self.get(request, *args, **kwargs)