from django.db import models
from core.models.base import BaseModel
from .line_process import LineProcess
from django.conf import settings

class Line(BaseModel):
    line_name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True)
    
    line_process = models.ForeignKey(
        LineProcess,
        on_delete=models.CASCADE,
        related_name="lines"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="lines"
    )

    def __str__(self):
        return self.line_name

    @property
    def code(self) -> str:
        # Backward-compat with older templates expecting `.code`.
        return (self.line_name or "").strip()

