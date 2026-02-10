from django.db import models


class ProductionLine(models.Model):
    code = models.CharField(max_length=32, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class PartNumber(models.Model):
    production_line = models.ForeignKey(ProductionLine, on_delete=models.CASCADE, related_name="parts")
    number = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["production_line__code", "number"]
        constraints = [
            models.UniqueConstraint(fields=["production_line", "number"], name="uniq_part_per_line"),
        ]

    def __str__(self) -> str:
        return self.number
