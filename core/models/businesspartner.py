from django.db import models
from core.models.base import BaseModel
from django.core.exceptions import ValidationError

#Business partner หมายถึงคตู่ค้า สามารถครอบคลุมทั้งลูกค้าและSupplier
class BusinessPartner(BaseModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    tax_id = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.name

# บทบาทของคู่ค้า ว่าเขาเป็นลูกค้าหรือSupplier หรือ sub contractor
class Role(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

# กำหนด payment termหรือcredit term ระยะเวลาในการจ่ายเงิน
class Term(BaseModel):

    class TermType(models.TextChoices):
        AR = "AR", "Account Receivable"
        AP = "AP", "Account Payable"

    name = models.CharField(max_length=100)
    days = models.PositiveIntegerField()
    term_type = models.CharField(max_length=2, choices=TermType.choices)

    def __str__(self):
        return f"{self.name} ({self.days} days)"

# บทบาทของคู่ค้าว่าเป็นลูกค้าหรือSupplier ถ้าเป็นลูกค้าจะเป็น AR ถ้าเป็นSupplierจะเป็น AP
# กรณีลูกค้าจะมีการกำหนดcredit limitด้วย ว่ามีเครดิตได้ไม่เกินกี่บาท
class PartnerRole(BaseModel):

    partner = models.ForeignKey(
        BusinessPartner,
        on_delete=models.CASCADE,
        related_name="roles"
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE
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

    # Credit Limit ควรอยู่ที่ customer role เท่านั้น
    credit_limit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # ช่วยกรอง roleกับpayment or credit
    def clean(self):
        if self.role.code == "CUSTOMER" and not self.ar_term:
            raise ValidationError("Customer role must have AR Term")

        if self.role.code == "SUPPLIER" and not self.ap_term:
            raise ValidationError("Supplier role must have AP Term")

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