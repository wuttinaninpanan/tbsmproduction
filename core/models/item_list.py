from django.db import models  # type:ignore
from core.models.base import BaseModel
from .item_category import ItemCategory
from .businesspartner import BusinessPartner
from django.conf import settings


class Item_list(BaseModel):

    class ItemType(models.TextChoices):
        # Production flow status:
        #   Raw → Stamping(WIP) → Sub-line(WIP) → Assembly(Semi-FG) → Inspection(FG)
        FG = "FG", "Finished Good (ผ่าน Inspection)"
        SEMI_FG = "SEMI_FG", "Semi-FG (ผ่าน Assembly)"
        WIP = "WIP", "WIP (หลัง Stamping หรือ Sub-line)"
        COMP = "COMP", "Purchased Component (ซื้อจาก supplier)"
        RAW = "RAW", "Raw Material / Coil"
        CONS = "CONS", "Consumable (Oil / Paint / Welding Wire)"

    class Unit(models.TextChoices):
        PCS = "PCS", "Piece"
        KG = "KG", "Kilogram"
        LITER = "L", "Liter"
        METER = "M", "Meter"
        SET = "SET", "Set"

    sd_code = models.CharField(max_length=255, blank=True, db_index=True)
    part_number = models.CharField(max_length=255, db_index=True)
    part_name = models.CharField(max_length=255)
    # SKU ใช้สำหรับแยก variant เช่น สี — พาร์ทผลิตทั่วไปไม่จำเป็นต้องมี
    sku = models.CharField(max_length=100, blank=True, null=True, unique=True)

    item_type = models.CharField(
        max_length=10,
        choices=ItemType.choices,
        blank=True,
        default="",
        help_text="ประเภท item — ผู้ใช้กำหนดเอง (ตาม production flow)",
    )
    unit = models.CharField(
        max_length=5,
        choices=Unit.choices,
        default=Unit.PCS,
        help_text="หน่วยนับ",
    )

    weight = models.DecimalField(max_digits=10, decimal_places=4, default=0, help_text="kg")

    reference_image = models.FileField(
        upload_to="component_part_reference/",
        blank=True,
        null=True,
    )

    category = models.ForeignKey(
        ItemCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )

    supplier = models.ForeignKey(
        BusinessPartner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supplied_items",
        help_text="Supplier หลัก (ซื้อจากใคร)",
    )

    purchased_price = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    level = models.IntegerField(blank=True, null=True)
    comment = models.CharField(max_length=255, blank=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="items",
    )

    def __str__(self):
        return f"{self.sku} - {self.part_name}"

    @property
    def number(self) -> str:
        return (self.part_number or "").strip()

    @property
    def name(self) -> str:
        return (self.part_name or "").strip()

    @property
    def is_manufactured(self) -> bool:
        return self.item_type in (self.ItemType.FG, self.ItemType.SEMI_FG, self.ItemType.WIP)

