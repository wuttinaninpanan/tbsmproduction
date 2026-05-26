from django.conf import settings  # type: ignore
from django.db import models  # type: ignore

from core.models.base import BaseModel


class Manual(BaseModel):
    """คู่มือการใช้งาน — เนื้อหา rich-text (HTML จาก WYSIWYG) แบ่งตามกลุ่มผู้ใช้.

    `created_at`, `updated_at`, `is_active` และ UUID `id` มาจาก BaseModel แล้ว.
    """

    class UseFor(models.TextChoices):
        ALL = "ALL", "ทุกคน (All)"
        ADMIN = "ADMIN", "ผู้ดูแลระบบ (Admin)"
        STAFF = "STAFF", "เจ้าหน้าที่ (Staff)"
        USER = "USER", "ผู้ใช้งานทั่วไป (User)"

    title = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True, default="")
    detail = models.TextField(blank=True, default="")          # HTML จาก WYSIWYG (ฝังรูป base64 ได้)
    usefor = models.CharField(
        max_length=10,
        choices=UseFor.choices,
        default=UseFor.ALL,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manuals_created",
    )

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title
