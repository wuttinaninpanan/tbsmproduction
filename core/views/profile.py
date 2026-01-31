from django.views.generic import TemplateView


class ProfileViews(TemplateView):
    template_name = "profile.html"