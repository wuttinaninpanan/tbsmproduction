from django.db import models
from core.models.base import BaseModel
from core.models.inspection.machine import Machine
from core.models.line import Line


class MachineLine(BaseModel):
    """โมเดลเชื่อม M2M ระหว่าง Machine กับ Line"""

    machine = models.ForeignKey(
        Machine,
        on_delete=models.CASCADE,
        related_name="machine_lines",
    )

    line = models.ForeignKey(
        Line,
        on_delete=models.CASCADE,
        related_name="machine_lines",
    )

    class Meta:
        unique_together = ("machine", "line")

    def __str__(self):
        return f"{self.machine} @ {self.line}"
