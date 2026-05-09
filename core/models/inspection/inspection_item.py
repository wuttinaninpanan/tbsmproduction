from django.db import models
from core.models.base import BaseModel
from core.models.bill_of_material import BillOfMaterial
from core.models.bill_of_material_item_master import BillOfMaterialItemMater
from core.models.defect_by_category import DefectByCategory
from core.models.inspection.inspection_model import InspectionModels

class InspectionItem(BaseModel):
    name = models.CharField(max_length=255)

    bill_of_material_item_master = models.ForeignKey(
        BillOfMaterialItemMater,
        on_delete=models.CASCADE,
        related_name="products_structure"
    )
    class_name_bom = models.CharField(max_length=255, default='')

    inspection_model = models.ForeignKey(
        InspectionModels,
        on_delete=models.CASCADE,
        related_name="products_structure"
    )
    is_exist = models.BooleanField(default=False)

    camera_number = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.name}_{self.inspection_model.class_name}"