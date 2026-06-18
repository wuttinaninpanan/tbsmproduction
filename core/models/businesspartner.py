from django.db import models
from django.core.exceptions import ValidationError
from core.models.base import BaseModel


# Business partner หมายถึงคู่ค้า ครอบคลุมทั้งลูกค้าและ Supplier
class BusinessPartner(BaseModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    tax_id = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.name


# บทบาทของคู่ค้า ว่าเป็นลูกค้า Supplier หรือ Sub Contractor
class Role(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# กำหนด payment term หรือ credit term
class Term(BaseModel):

    class TermType(models.TextChoices):
        AR = "AR", "Account Receivable"
        AP = "AP", "Account Payable"

    name = models.CharField(max_length=100)
    days = models.PositiveIntegerField()
    term_type = models.CharField(max_length=2, choices=TermType.choices)

    def __str__(self):
        return f"{self.name} ({self.days} days)"


# บทบาทของคู่ค้า
class PartnerRole(BaseModel):
    partner = models.ForeignKey(
        BusinessPartner,
        on_delete=models.CASCADE,
        related_name="partner_roles"
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="partner_roles"
    )

    ar_term = models.ForeignKey(
        Term,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_roles",
        limit_choices_to={"term_type": "AR"}
    )

    ap_term = models.ForeignKey(
        Term,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supplier_roles",
        limit_choices_to={"term_type": "AP"}
    )

    # Credit Limit ควรใช้เฉพาะ customer
    credit_limit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )

    def clean(self):
        if not self.role:
            return

        if self.role.code == "CUSTOMER":
            if not self.ar_term:
                raise ValidationError("Customer role must have AR Term")
            if self.ap_term:
                raise ValidationError("Customer role must not have AP Term")

        if self.role.code == "SUPPLIER":
            if not self.ap_term:
                raise ValidationError("Supplier role must have AP Term")
            if self.ar_term:
                raise ValidationError("Supplier role must not have AR Term")

    class Meta:
        unique_together = ("partner", "role")

    def __str__(self):
        return f"{self.partner.name} - {self.role.name}"


# ช่องทางการติดต่อ
class Contact(BaseModel):
    partner = models.ForeignKey(
        BusinessPartner,
        on_delete=models.CASCADE,
        related_name="contacts"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    telephone_number = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# ที่อยู่
class Address(BaseModel):
    class AddressType(models.TextChoices):
        BILLING = "billing", "Billing"
        SHIPPING = "shipping", "Shipping"
        HEAD_OFFICE = "head_office", "Head Office"

    partner = models.ForeignKey(
        BusinessPartner,
        on_delete=models.CASCADE,
        related_name="addresses"
    )

    address_type = models.CharField(
        max_length=20,
        choices=AddressType.choices
    )
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    subdistrict = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    country = models.CharField(max_length=100, default="Thailand")

    def __str__(self):
        return f"{self.partner.name} - {self.address_type}"