from django.db import models
from core.models.base import BaseModel
from django.conf import settings

class LineProcess(BaseModel):
    name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="processes"
    )


    def __str__(self):
        return self.name
    
        # INCOMING = "receiving", "Receiving"
        # PRESS = "press", "Press"
        # SUBLINE = "sub_line", "Sub Line"
        # EDP = "ed_paint", "ED Paint"
        # ASSY = "assy", "Assembly"
        # FINAL_INSPECTION = "final_inspection", "Final Inspection"
        # PICKING = "picking", "Picking"
        # PACKING = "packing", "Packing"
        # SHIPPING = "shipping", "Shipping"