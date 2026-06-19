from decimal import Decimal
from django.db import migrations
from django.db.models import Q


def set_zero_quantity_to_one(apps, schema_editor):
    # พาร์ทลูก (component) ที่จำนวนเป็นศูนย์/ติดลบ/ว่าง (NULL) → ตั้งค่า default = 1
    BillOfMaterialItemMater = apps.get_model("core", "BillOfMaterialItemMater")
    BillOfMaterialItemMater.objects.filter(
        Q(quantity__lte=0) | Q(quantity__isnull=True)
    ).update(quantity=Decimal("1"))


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(set_zero_quantity_to_one, noop),
    ]
