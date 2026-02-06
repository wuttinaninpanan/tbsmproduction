from django.conf import settings
from django.db import models
from .base import BaseModels




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


class DefectMode(models.Model):
	part = models.ForeignKey(PartNumber, on_delete=models.CASCADE, related_name="defects")
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


class ScrapItem(models.Model):
	defect_mode = models.ForeignKey(DefectMode, on_delete=models.CASCADE, related_name="scraps")
	name = models.CharField(max_length=128)
	reference_image = models.ImageField(upload_to="scrap_reference/", blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["defect_mode__name", "name"]
		constraints = [
			models.UniqueConstraint(fields=["defect_mode", "name"], name="uniq_scrap_per_defect"),
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
		return f"{self.production_line} {self.part_number} {self.defect_mode} {self.scrap_item} x{self.quantity}"


class UserProfile(models.Model):
	SHIFT_CHOICES = [
		('shift_a', 'กะ A'),
		('shift_b', 'กะ B'),
		('shift_day', 'กะ Day'),
	]
	
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='profile'
	)
	shift = models.CharField(
		max_length=20,
		choices=SHIFT_CHOICES,
		default='shift_day',
		help_text='เลือกกะการทำงาน'
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self) -> str:
		return f"{self.user.username} - {self.get_shift_display()}"
