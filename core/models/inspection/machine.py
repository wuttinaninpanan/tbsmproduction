from django.conf import settings
from django.db import models
from core.models.base import BaseModel
from core.models.line import Line
from core.models.department import Department


class Machine(BaseModel):
    machine_no = models.CharField(max_length=255, unique=True)        # รหัสเครื่อง
    machine_name = models.CharField(max_length=255)                    # ชื่อเครื่อง
    machine_detail = models.TextField(blank=True, null=True)           # คำอธิบายเกี่ยวกับเครื่อง

    # แผนกผู้รับผิดชอบ -> FK Department
    res_dept = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        related_name="machines",
        null=True,
        blank=True,
    )

    # ผู้รับผิดชอบ 1 / 2 -> FK User
    responsible1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="machines_responsible1",
        null=True,
        blank=True,
    )
    responsible2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="machines_responsible2",
        null=True,
        blank=True,
    )

    is_approved = models.BooleanField(default=False)                   # ได้รับการอนุมัติแล้วหรือยัง

    # M2M ระหว่าง Machine กับ Line ผ่านโมเดล MachineLine
    lines = models.ManyToManyField(
        Line,
        through="MachineLine",
        related_name="machines",
        blank=True,
    )

    def __str__(self):
        return f"{self.machine_no} - {self.machine_name}"
