from django.db import models
from core.models.base import BaseModel


class InspectionOKLog(BaseModel):
    """Header — 1 row ต่อ 1 การสแกนที่ผ่าน (OK)"""

    machine = models.ForeignKey(
        "Machine",
        on_delete=models.PROTECT,
        related_name="ok_logs",
    )
    item = models.ForeignKey(
        "Item_list",
        on_delete=models.PROTECT,
        related_name="ok_logs",
    )
    kanban_qr = models.CharField(max_length=255)
    item_qr = models.CharField(max_length=255)
    photo_path = models.TextField(blank=True, null=True)
    inspected_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["-inspected_at"]
        indexes = [
            models.Index(fields=["machine", "inspected_at"]),
            models.Index(fields=["item", "inspected_at"]),
            models.Index(fields=["kanban_qr"]),
        ]

    def __str__(self):
        return f"OK | {self.item_qr} | {self.inspected_at:%Y-%m-%d %H:%M:%S}"


class InspectionOKLogDetail(BaseModel):
    """Detail — N rows ต่อ 1 InspectionOKLog (ต่อ Object ที่ตรวจ)"""

    log = models.ForeignKey(
        InspectionOKLog,
        on_delete=models.CASCADE,
        related_name="details",
    )
    detection_object = models.ForeignKey(
        "DetectionObject",
        on_delete=models.PROTECT,
        related_name="ok_log_details",
    )
    camera_number = models.PositiveSmallIntegerField()
    object_found = models.BooleanField()
    object_count = models.PositiveIntegerField()
    expected_count = models.PositiveIntegerField()
    confidence = models.FloatField(blank=True, null=True)
    photo_path = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"OK Detail | {self.detection_object} | {self.object_count}/{self.expected_count}"


class InspectionNGLog(BaseModel):
    """Header — 1 row ต่อ 1 การสแกนที่ไม่ผ่าน (NG)"""

    machine = models.ForeignKey(
        "Machine",
        on_delete=models.PROTECT,
        related_name="ng_logs",
    )
    item = models.ForeignKey(
        "Item_list",
        on_delete=models.PROTECT,
        related_name="ng_logs",
    )
    kanban_qr = models.CharField(max_length=255)
    item_qr = models.CharField(max_length=255)
    photo_path = models.TextField(blank=True, null=True)
    inspected_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["-inspected_at"]
        indexes = [
            models.Index(fields=["machine", "inspected_at"]),
            models.Index(fields=["item", "inspected_at"]),
            models.Index(fields=["kanban_qr"]),
        ]

    def __str__(self):
        return f"NG | {self.item_qr} | {self.inspected_at:%Y-%m-%d %H:%M:%S}"


class InspectionNGLogDetail(BaseModel):
    """Detail — N rows ต่อ 1 InspectionNGLog (ต่อ Object ที่ตรวจ)"""

    log = models.ForeignKey(
        InspectionNGLog,
        on_delete=models.CASCADE,
        related_name="details",
    )
    detection_object = models.ForeignKey(
        "DetectionObject",
        on_delete=models.PROTECT,
        related_name="ng_log_details",
    )
    camera_number = models.PositiveSmallIntegerField()
    object_found = models.BooleanField()
    object_count = models.PositiveIntegerField()
    expected_count = models.PositiveIntegerField()
    defect_mode = models.ForeignKey(
        "DefectMode",
        on_delete=models.PROTECT,
        related_name="ng_log_details",
        blank=True,
        null=True,
    )
    confidence = models.FloatField(blank=True, null=True)
    photo_path = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"NG Detail | {self.detection_object} | {self.defect_mode}"


class InspectionOKLogDetailPhoto(BaseModel):
    """รูปภาพต่อ 1 OK detail — ออกแบบให้ psycopg2 INSERT ตรงได้
    table: core_inspectionoklogdetailphoto
    INSERT (id, detail_id, image_path, caption, photo_order, created_at, updated_at, is_active)
    """

    detail = models.ForeignKey(
        InspectionOKLogDetail,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image_path = models.TextField()
    caption = models.CharField(max_length=100, blank=True, default="")
    photo_order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["photo_order"]

    def __str__(self):
        return f"OK Photo | {self.caption} #{self.photo_order}"


class InspectionNGLogDetailPhoto(BaseModel):
    """รูปภาพต่อ 1 NG detail — ออกแบบให้ psycopg2 INSERT ตรงได้
    table: core_inspectionnglogdetailphoto
    INSERT (id, detail_id, image_path, caption, photo_order, created_at, updated_at, is_active)
    """

    detail = models.ForeignKey(
        InspectionNGLogDetail,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image_path = models.TextField()
    caption = models.CharField(max_length=100, blank=True, default="")
    photo_order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["photo_order"]

    def __str__(self):
        return f"NG Photo | {self.caption} #{self.photo_order}"
