from django.db import models

from .production import PartNumber


class DefectMode(models.Model):
    part = models.ForeignKey(PartNumber, on_delete=models.CASCADE, related_name="defects", blank=True, null=True)
    code = models.CharField(max_length=64, blank=True, null=True)
    name = models.CharField(max_length=128)
    reference_image = models.ImageField(upload_to="defect_reference/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["part__production_line__code", "part__number", "name"]
        constraints = [
            models.UniqueConstraint(fields=["part", "name"], name="uniq_defect_per_part"),
        ]

    def __str__(self) -> str:
        return self.name
