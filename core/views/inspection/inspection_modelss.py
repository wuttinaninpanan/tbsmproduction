from __future__ import annotations

from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views import View

from core.auth.decorators import staff_required


@method_decorator(staff_required, name="dispatch")
class InspectionModelssView(View):
    """Legacy standalone page — merged into the "Inspection Models" tab on /inspection/machine/."""

    def get(self, request, *args, **kwargs):
        return redirect("/inspection/machine/?tab=inspection_modelss")
