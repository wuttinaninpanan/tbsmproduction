"""โมเดลของเมนู "ติดต่อ" (หน้า /contact/).

มี 2 โมเดล:

* ``ContactMessage`` — ข้อความ "ติดต่อทั่วไป" ที่ผู้ใช้ส่งเข้ามา ไม่ต้องอนุมัติ
  staff อ่านได้ในหน้าจัดการคำขอ
* ``PartRequest`` — คำขอที่ "ต้องให้ Admin อนุมัติก่อน" ถึงจะสร้างข้อมูลจริง
  รวม 2 ชนิดไว้ในโมเดลเดียว แยกด้วย ``request_type``:
    - ``BOM_COMPONENT`` → อนุมัติแล้วสร้าง ``BillOfMaterialItemMater`` (เพิ่ม
      component เข้า BoM เดิม)
    - ``LINE_ITEM``    → อนุมัติแล้วสร้าง ``ItemLine`` (ผูก Item เดิมเข้าไลน์)

ฟิลด์เฉพาะของแต่ละชนิดเป็น nullable เพราะใช้ตารางเดียวกัน — การตรวจความครบถ้วน
ทำในชั้น view ตอนรับฟอร์มและตอนอนุมัติ
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from core.models.base import BaseModel
from .bill_of_material import BillOfMaterial
from .item_list import Item_list
from .item_stage import ItemStage
from .line import Line


class ContactMessage(BaseModel):
    """ข้อความติดต่อทั่วไป — ไม่ต้องอนุมัติ."""

    class Status(models.TextChoices):
        NEW = "NEW", "ใหม่"
        READ = "READ", "อ่านแล้ว"

    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    message = models.TextField()

    status = models.CharField(
        max_length=8,
        choices=Status.choices,
        default=Status.NEW,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_messages",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_status_display()})"


class PartRequest(BaseModel):
    """คำขอเพิ่มข้อมูลที่ต้องให้ Admin อนุมัติก่อนสร้างจริง."""

    class Type(models.TextChoices):
        BOM_COMPONENT = "BOM_COMPONENT", "เพิ่ม component เข้า BoM"
        LINE_ITEM = "LINE_ITEM", "ผูกพาร์ทเข้าไลน์ผลิต"

    class Status(models.TextChoices):
        PENDING = "PENDING", "รออนุมัติ"
        APPROVED = "APPROVED", "อนุมัติแล้ว"
        REJECTED = "REJECTED", "ปฏิเสธ"

    request_type = models.CharField(max_length=16, choices=Type.choices)
    status = models.CharField(
        max_length=8,
        choices=Status.choices,
        default=Status.PENDING,
    )

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="part_requests",
    )
    note = models.TextField(blank=True, help_text="รายละเอียด/เหตุผลจากผู้ขอ")

    # ---- ฟิลด์สำหรับ BOM_COMPONENT --------------------------------------
    bom = models.ForeignKey(
        BillOfMaterial,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="component_requests",
    )
    component = models.ForeignKey(
        Item_list,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    quantity = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    unit = models.CharField(max_length=20, blank=True)
    sequence = models.IntegerField(default=1)

    # ---- ฟิลด์สำหรับ LINE_ITEM ------------------------------------------
    item = models.ForeignKey(
        Item_list,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    line = models.ForeignKey(
        Line,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="item_requests",
    )
    item_stage = models.ForeignKey(
        ItemStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="item_requests",
    )

    # ---- ผลการพิจารณา ---------------------------------------------------
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_part_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(
        max_length=255, blank=True, help_text="หมายเหตุ/เหตุผลที่ปฏิเสธ"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_request_type_display()} — {self.get_status_display()}"
