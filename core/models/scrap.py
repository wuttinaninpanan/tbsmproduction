from django.conf import settings
from django.db import models

from .defects import DefectMode
from .production import PartNumber, ProductionLine


class ScrapItem(models.Model):
    part_number = models.ForeignKey(PartNumber, on_delete=models.CASCADE, related_name="scrap_items")
    name = models.CharField(max_length=128)
    reference_image = models.ImageField(upload_to="scrap_reference/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["part_number__production_line__code", "part_number__number", "name"]
        constraints = [
            models.UniqueConstraint(fields=["part_number", "name"], name="uniq_scrap_per_part"),
        ]

    def __str__(self) -> str:
        return self.name


class ScrapRecord(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    production_line = models.ForeignKey(ProductionLine, on_delete=models.PROTECT, related_name="scrap_records")
    part_number = models.ForeignKey(PartNumber, on_delete=models.PROTECT, related_name="scrap_records")
    defect_mode = models.ForeignKey(DefectMode, on_delete=models.PROTECT, related_name="scrap_records")
    scrap_item = models.ForeignKey(ScrapItem, on_delete=models.PROTECT, related_name="scrap_records")
    quantity = models.PositiveIntegerField(default=1)
    photo = models.ImageField(upload_to="scrap_photos/", blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scrap_records",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"{self.production_line} {self.part_number} {self.defect_mode} {self.scrap_item} x{self.quantity}"
        )
