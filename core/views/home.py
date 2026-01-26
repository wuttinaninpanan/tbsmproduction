from django.views.generic import TemplateView  # type:ignore


# Create your views here.
class HomeViews(TemplateView):
    template_name = "index.html"