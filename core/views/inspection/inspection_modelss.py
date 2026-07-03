from __future__ import annotations

from django.shortcuts import redirect
from django.views import View


class InspectionModelssView(View):
    """Legacy standalone page — merged into the "Inspection Models" tab on /inspection/machine/."""

    def get(self, request, *args, **kwargs):
        return redirect("/inspection/machine/?tab=inspection_modelss")
