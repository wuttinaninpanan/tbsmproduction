from django.db import models
from django.utils import timezone
from core.models.base import BaseModel
from core.models.line import Line


class InspectionReport(BaseModel):
    """บันทึกผลการทดสอบตรวจสอบ: ไลน์ / Object / Defect / ประเภท / จำนวนครั้ง."""

    class ReportType(models.TextChoices):
        NORMAL = "NORMAL", "ปกติ"
        OIL = "OIL", "แบบทาน้ำมัน"

    line = models.ForeignKey(
        Line,
        on_delete=models.PROTECT,
        related_name="inspection_reports",
    )
    object = models.ForeignKey(
        "DetectionObject",
        on_delete=models.PROTECT,
        related_name="inspection_reports",
    )
    defect_mode = models.ForeignKey(
        "DefectMode",
        on_delete=models.PROTECT,
        related_name="inspection_reports",
    )
    # choices เป็นแค่ค่าเริ่มต้น — หน้าฟอร์มอนุญาตให้เพิ่มประเภทใหม่แบบอิสระได้ (ไม่ enforce ที่ DB)
    report_type = models.CharField(
        max_length=50,
        choices=ReportType.choices,
        default=ReportType.NORMAL,
    )
    count = models.PositiveIntegerField(default=1)
    target_count = models.PositiveIntegerField(default=30)
    report_date = models.DateField(default=timezone.localdate)
    note = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.line.line_name} - {self.object.name} - {self.get_report_type_display()} {self.count}/{self.target_count} ({self.report_date})"
