from django.views.generic import TemplateView
from django.utils.decorators import method_decorator

from core.decorators import user_required


@method_decorator(user_required, name='dispatch')
class ProfileViews(TemplateView):
    template_name = "profile.html"