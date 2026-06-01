from django.db import models
from core.models.base import BaseModel


class KanbanItemMapping(BaseModel):
    """คู่ที่ถูกต้องระหว่าง QR ของ Kanban กับ QR ของชิ้นงาน (item).

    ใช้ตรวจ "ผิดรุ่น": สแกน kanban_qr -> หาแถวนี้ -> เทียบ item_qr ที่สแกนได้จริง
    กับ item_qr ที่ลงทะเบียนไว้ ถ้าไม่ตรง = ชิ้นงานผิดรุ่น
    """

    item = models.ForeignKey(
        "Item_list",
        on_delete=models.PROTECT,
        related_name="kanban_item_mappings",
    )
    # 1 kanban ผูกได้ item เดียวเท่านั้น เพื่อให้ lookup ตอนตรวจไม่กำกวม
    kanban_qr = models.CharField(max_length=255, unique=True)
    item_qr = models.CharField(max_length=255)

    def __str__(self):
        return f"Kanban: {self.kanban_qr} - Item: {self.item_qr}"


class DetectionObject(BaseModel):
    """ชิ้นส่วน/ตำแหน่งที่โมเดล object detection ต้องตรวจเจอ.

    จำนวน item ที่คาดหวังของแต่ละ object เก็บไว้ใน ItemObject (ต่อ item)
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class ItemObject(BaseModel):
    """Item_list <-> DetectionObject : object หนึ่งคาดหวังให้มี item อะไรบ้าง กี่ชิ้น.

    ใช้ตรวจ "ขาด/เกิน" ในข้อ 2: เทียบ item ที่ตรวจเจอจริงกับรายการ + quantity ที่นี่
    """

    item = models.ForeignKey(
        "Item_list",
        on_delete=models.PROTECT,
        related_name="item_objects",
    )
    object = models.ForeignKey(
        "DetectionObject",
        on_delete=models.PROTECT,
        related_name="item_objects",
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("item", "object")

    def __str__(self):
        return f"{self.object.name} - {self.item.name} x{self.quantity}"


class MachineObject(BaseModel):
    """Machine <-> DetectionObject : เครื่องนี้ต้องตรวจ object อะไรบ้าง."""

    machine = models.ForeignKey(
        "Machine",
        on_delete=models.PROTECT,
        related_name="machine_objects",
    )
    object = models.ForeignKey(
        "DetectionObject",
        on_delete=models.PROTECT,
        related_name="machine_objects",
    )

    class Meta:
        unique_together = ("machine", "object")

    def __str__(self):
        return f"{self.machine} - {self.object.name}"


class ObjectDetectionModel(BaseModel):
    """DetectionObject <-> InspectionModels : object นี้ใช้ ML model ตัวไหนตรวจ."""

    object = models.ForeignKey(
        "DetectionObject",
        on_delete=models.PROTECT,
        related_name="object_detection_models",
    )
    inspection_model = models.ForeignKey(
        "InspectionModels",
        on_delete=models.PROTECT,
        related_name="object_detection_models",
    )

    class Meta:
        unique_together = ("object", "inspection_model")

    def __str__(self):
        return f"{self.object.name} - {self.inspection_model.class_name}"


class DefectDetectionInModels(BaseModel):
    """DetectionObject + DefectMode <-> InspectionModels : defect mode ของ object นี้ใช้ model ไหนตรวจ."""

    object = models.ForeignKey(
        "DetectionObject",
        on_delete=models.PROTECT,
        related_name="defect_detection_models",
    )
    defect_mode = models.ForeignKey(
        "DefectMode",
        on_delete=models.PROTECT,
        related_name="defect_detection_models",
    )
    inspection_model = models.ForeignKey(
        "InspectionModels",
        on_delete=models.PROTECT,
        related_name="defect_detection_models",
    )

    class Meta:
        unique_together = ("object", "defect_mode", "inspection_model")

    def __str__(self):
        return f"{self.object.name} - {self.defect_mode.name} - {self.inspection_model.class_name}"
