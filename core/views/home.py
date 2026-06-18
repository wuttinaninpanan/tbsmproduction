from django.views.generic import TemplateView  # type:ignore

from core.models.defect_mode import DefectMode
from core.models.item_list import Item_list
from core.models.line import Line
from core.models.process_defect import ProcessDefectScrap


# Create your views here.
class HomeViews(TemplateView):
    template_name = "core/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["kpi"] = {
            # One scrapped-component entry = one ProcessDefectScrap row.
            "records_total": ProcessDefectScrap.objects.count(),
            "lines_total": Line.objects.count(),
            "parts_total": Item_list.objects.count(),
            "defect_modes_total": DefectMode.objects.count(),
        }
        return ctx