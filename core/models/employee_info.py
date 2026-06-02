from django.conf import settings
from django.db import models

from core.models.base import BaseModel


class EmployeeRole(BaseModel):
    name = models.CharField(max_length=50, unique=True)
    title_th = models.CharField(max_length=100, blank=True)
    title_en = models.CharField(max_length=100, blank=True)
    title_ja = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    description_ja = models.TextField(blank=True)
    is_system_role = models.BooleanField(default=False)
    level = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "employee_roles"
        ordering = ["-level", "name"]

    def __str__(self):
        return self.title_th or self.name


class Division(BaseModel):
    code = models.CharField(max_length=20, unique=True, null=True, blank=True, db_index=True)
    short_name = models.CharField(max_length=10, blank=True)
    name = models.CharField(max_length=200, unique=True)
    name_en = models.CharField(max_length=200, blank=True)
    name_ja = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    description_ja = models.TextField(blank=True)

    class Meta:
        db_table = "divisions"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Section(BaseModel):
    department = models.ForeignKey(
        "core.Department", on_delete=models.PROTECT, related_name="sections", null=True, blank=True
    )
    code = models.CharField(max_length=20, unique=True, null=True, blank=True, db_index=True)
    short_name = models.CharField(max_length=10, blank=True)
    name = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200, blank=True)
    name_ja = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    description_ja = models.TextField(blank=True)

    class Meta:
        db_table = "sections"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Position(BaseModel):
    short_name = models.CharField(max_length=10, blank=True)
    name = models.CharField(max_length=200, unique=True)
    name_en = models.CharField(max_length=200, blank=True)
    name_ja = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    description_ja = models.TextField(blank=True)

    class Meta:
        db_table = "positions"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Organization(BaseModel):
    section = models.ForeignKey(
        Section, on_delete=models.PROTECT, related_name="organizations", null=True, blank=True
    )
    department = models.ForeignKey(
        "core.Department", on_delete=models.PROTECT, related_name="organizations", null=True, blank=True
    )
    division = models.ForeignKey(
        Division, on_delete=models.PROTECT, related_name="organizations", null=True, blank=True
    )
    code = models.CharField(max_length=20, unique=True, null=True, blank=True, db_index=True)
    short_name = models.CharField(max_length=10, blank=True)
    name = models.CharField(max_length=200, db_index=True)
    name_en = models.CharField(max_length=200, blank=True)
    name_ja = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    description_ja = models.TextField(blank=True)

    class Meta:
        db_table = "organizations"
        ordering = ["name"]

    def __str__(self):
        return self.name


class EmployType(BaseModel):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "employ_types"

    def __str__(self):
        return self.name


class JobLevel(BaseModel):
    name = models.CharField(max_length=20, unique=True)

    class Meta:
        db_table = "job_levels"
        ordering = ["name"]

    def __str__(self):
        return self.name


class CostCenter(BaseModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "cost_centers"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Employee(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="employee")
    emp_code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=50, blank=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    title_en = models.CharField(max_length=50, blank=True)
    first_name_en = models.CharField(max_length=150, blank=True)
    last_name_en = models.CharField(max_length=150, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    position = models.ForeignKey(Position, on_delete=models.PROTECT, related_name="employees", null=True, blank=True)
    job_level = models.ForeignKey(JobLevel, on_delete=models.PROTECT, related_name="employees", null=True, blank=True)
    cost_center = models.ForeignKey(CostCenter, on_delete=models.PROTECT, related_name="employees", null=True, blank=True)
    employ_type = models.ForeignKey(EmployType, on_delete=models.PROTECT, related_name="employees")

    class Meta:
        db_table = "employees"
        ordering = ["emp_code"]

    def __str__(self):
        return f"{self.emp_code} - {self.title}{self.first_name} {self.last_name}"

    @property
    def department(self):
        assignment = self.organization_assignments.select_related("organization__department").first()
        return assignment.organization.department if assignment else None


class OrganizationEmployee(BaseModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="organization_assignments")
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="organization_employees")
    shift = models.CharField(max_length=10, choices=[("A", "Shift A"), ("B", "Shift B"), ("Day", "Shift Day")])

    class Meta:
        db_table = "organization_employees"


class Contract(BaseModel):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="contracts")
    round_number = models.PositiveSmallIntegerField(choices=[(1, "Round 1"), (2, "Round 2")])
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.PositiveIntegerField(editable=False, default=0)
    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("extended", "Extended"), ("completed", "Completed"), ("terminated", "Terminated")],
        default="active",
    )
    note = models.TextField(blank=True)
    renewed_as = models.OneToOneField(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="previous_contract"
    )

    class Meta:
        db_table = "contracts"
        unique_together = ("employee", "round_number")
        ordering = ["employee", "round_number"]

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            self.duration_days = (self.end_date - self.start_date).days
        super().save(*args, **kwargs)
