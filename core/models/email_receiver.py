from django.conf import settings  # type: ignore
from django.db import models  # type: ignore

from core.models.base import BaseModel


class EmailReceiver(BaseModel):
    """ผู้รับอีเมลรายงานอัตโนมัติ — ตั้งค่าว่าใครได้รับ, ความถี่, และข้อมูลอะไรบ้าง.

    การส่งจริงทำโดย management command ``send_scheduled_reports`` ที่ถูกตั้งเวลา
    รันโดย OS (cron / Task Scheduler) วันละครั้ง แล้วเลือกผู้รับที่ "ถึงกำหนด"
    ตาม ``frequency`` + ``last_sent_at``.
    """

    class Frequency(models.TextChoices):
        DAILY = "DAILY", "ทุกวัน"
        WEEKLY = "WEEKLY", "ทุกสัปดาห์ (จันทร์)"
        MONTHLY = "MONTHLY", "ทุกเดือน (วันที่ 1)"

    name = models.CharField(max_length=255)                       # ชื่อผู้รับ / คำอธิบาย
    email = models.EmailField()

    frequency = models.CharField(
        max_length=10,
        choices=Frequency.choices,
        default=Frequency.DAILY,
    )

    # ข้อมูลที่จะแนบไปกับอีเมล (เลือกได้หลายอย่าง)
    send_production_report = models.BooleanField(default=True)     # ข้อมูลการผลิต/ของเสีย (manage-production)
    send_inspection_report = models.BooleanField(default=False)   # ผลตรวจ inspection machine

    # เวลาที่ส่งสำเร็จล่าสุด — ใช้กันส่งซ้ำในวันเดียวกัน
    last_sent_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_receivers_created",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"
