import django.db.models.deletion
from django.db import migrations, models


def copy_lines_to_fk(apps, schema_editor):
    """ย้ายข้อมูลความสัมพันธ์เดิม (M2M ผ่าน MachineLine) มาเป็น FK เดียว.

    ข้อมูลปัจจุบันแต่ละเครื่องมีไลน์เดียวอยู่แล้ว เผื่อกรณีมีหลายไลน์
    จะเลือกไลน์แรก (เรียงตาม created_at) ให้กับเครื่องนั้น.
    """
    Machine = apps.get_model("core", "Machine")
    MachineLine = apps.get_model("core", "MachineLine")

    seen = set()
    for ml in MachineLine.objects.all().order_by("created_at"):
        if ml.machine_id in seen:
            continue
        seen.add(ml.machine_id)
        Machine.objects.filter(pk=ml.machine_id).update(line_id=ml.line_id)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_processdefect_processdefectscrap_productionrecord_and_more"),
    ]

    operations = [
        # ลบ M2M (เป็นการแก้ state เท่านั้น เพราะตารางเป็นของ through model MachineLine
        # การลบฟิลด์ก่อนจึงเลี่ยง related_name="machines" ชนกับ FK ใหม่ด้านล่าง)
        migrations.RemoveField(
            model_name="machine",
            name="lines",
        ),
        # ฟิลด์ที่ค้างยังไม่เคยถูก migrate มาก่อน
        migrations.AddField(
            model_name="machine",
            name="machine_type",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="machine",
            name="category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="machines",
                to="core.itemcategory",
            ),
        ),
        # FK ใหม่: 1 เครื่องจักร -> 1 ไลน์
        migrations.AddField(
            model_name="machine",
            name="line",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="machines",
                to="core.line",
            ),
        ),
        # ย้ายข้อมูลเดิมก่อนทิ้งตาราง through
        migrations.RunPython(copy_lines_to_fk, migrations.RunPython.noop),
        migrations.DeleteModel(
            name="MachineLine",
        ),
    ]
