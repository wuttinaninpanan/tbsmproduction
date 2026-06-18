from django.views.generic import TemplateView


class AboutViews(TemplateView):
    template_name = "core/about.html"
