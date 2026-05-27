from django.db import models
from core.models.base import BaseModel


class KanbanPartMapping(BaseModel):
    """คู่ที่ถูกต้องระหว่าง QR ของ Kanban กับ QR ของชิ้นงาน (part).

    ใช้ตรวจ "ผิดรุ่น": สแกน kanban_qr -> หาแถวนี้ -> เทียบ part_qr ที่สแกนได้จริง
    กับ part_qr ที่ลงทะเบียนไว้ ถ้าไม่ตรง = ชิ้นงานผิดรุ่น
    """

    item = models.ForeignKey(
        "Item_list",
        on_delete=models.PROTECT,
        related_name="kanban_part_mappings",
    )
    # 1 kanban ผูกได้ part เดียวเท่านั้น เพื่อให้ lookup ตอนตรวจไม่กำกวม
    kanban_qr = models.CharField(max_length=255, unique=True)
    part_qr = models.CharField(max_length=255)

    def __str__(self):
        return f"Kanban: {self.kanban_qr} - Part: {self.part_qr}"

class DetectionObject(BaseModel):
    """ชิ้นส่วน/ตำแหน่งที่โมเดล object detection ต้องตรวจเจอ พร้อมจำนวนที่คาดหวัง."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)

    object_detection_model = models.CharField(max_length=255)
    model_path = models.CharField(max_length=500)

    def __str__(self):
        return self.name

class ObjectMachineMapping(BaseModel):
    """Mapping ระหว่างเครื่องจักรกับ Object ที่ต้องตรวจ."""

    machine = models.ForeignKey(
        "Machine",
        on_delete=models.PROTECT,
        related_name="object_machine_mappings",
    )
    object = models.ForeignKey(
        "DetectionObject",
        on_delete=models.PROTECT,
        related_name="machine_mappings",
    )

    def __str__(self):
        return f"{self.machine.name} - {self.object.name}"

class ObjectItem(BaseModel):
    """รายการ Item ที่ควรประกอบอยู่ใน DetectionObject หนึ่งๆ."""

    object = models.ForeignKey(
        "DetectionObject",
        on_delete=models.PROTECT,
        related_name="object_items",
    )
    item = models.ForeignKey(
        "Item_list",
        on_delete=models.PROTECT,
        related_name="detection_objects",
    )
    is_exist = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.object.name} - {self.item.name}"

class DefectDetection(BaseModel):
    """Defect ที่อาจเกิดใน DetectionObject หนึ่งๆ พร้อมโมเดลที่ใช้ตรวจ."""

    defect_mode = models.ForeignKey(
        "DefectMode",
        on_delete=models.PROTECT,
        related_name="defect_detections",
    )
    defect_detection_model = models.CharField(max_length=255)
    model_path = models.CharField(max_length=500)
    object = models.ForeignKey(
        "DetectionObject",
        on_delete=models.PROTECT,
        related_name="defect_detections",
    )

    def __str__(self):
        return f"{self.object.name} - {self.defect_mode.name}"
