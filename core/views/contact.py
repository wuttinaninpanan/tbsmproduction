from django.views.generic import TemplateView


class ContactViews(TemplateView):
    template_name = "contact.html"

