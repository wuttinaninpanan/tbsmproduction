import uuid

from django.db import migrations


CANONICAL_SHIFTS = [
    ("05df7075-4d69-439a-961f-89689efa8910", "Shift A", 1),
    ("53b977fb-51e6-415a-ad18-3f0df09264e0", "Shift B", 2),
    ("9eb18f2a-fd35-42bf-b3d5-fae241d25d81", "Shift D", 3),
]


def canonicalize_shift_ids(apps, schema_editor):
    Shift = apps.get_model("core", "Shift")
    ProductionRecord = apps.get_model("core", "ProductionRecord")

    for pk, name, display_number in CANONICAL_SHIFTS:
        canonical_id = uuid.UUID(pk)
        canonical = Shift.objects.filter(pk=canonical_id).first()
        by_name = Shift.objects.filter(name=name).exclude(pk=canonical_id).first()

        if canonical is None and by_name is None:
            Shift.objects.create(
                id=canonical_id,
                name=name,
                display_number=display_number,
            )
            continue

        if canonical is None:
            old_id = by_name.pk
            by_name.name = f"{name} (old {str(old_id)[:8]})"
            by_name.save(update_fields=["name"])
            canonical = Shift.objects.create(
                id=canonical_id,
                name=name,
                display_number=display_number,
            )
            ProductionRecord.objects.filter(shift_id=old_id).update(shift=canonical)
            by_name.delete()
            continue

        if by_name is not None:
            ProductionRecord.objects.filter(shift=by_name).update(shift=canonical)
            by_name.delete()

        canonical.name = name
        canonical.display_number = display_number
        canonical.save(update_fields=["name", "display_number"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0026_add_inspection_log_detail_photo"),
    ]

    operations = [
        migrations.RunPython(canonicalize_shift_ids, noop_reverse),
    ]
