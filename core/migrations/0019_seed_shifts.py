# Seeds the 3 organisation work shifts (idempotent).
#
# These are the options the operator picks from on Page 1 of /record/.
# Keep these primary keys in sync with core/fixtures/master_seed.json so
# `loaddata` can update the rows instead of inserting duplicate names.
import uuid

from django.db import migrations

DEFAULT_SHIFTS = [
    ("05df7075-4d69-439a-961f-89689efa8910", "Shift A", 1),
    ("53b977fb-51e6-415a-ad18-3f0df09264e0", "Shift B", 2),
    ("9eb18f2a-fd35-42bf-b3d5-fae241d25d81", "Shift D", 3),
]


def create_shifts(apps, schema_editor):
    Shift = apps.get_model("core", "Shift")
    for pk, name, display_number in DEFAULT_SHIFTS:
        canonical_id = uuid.UUID(pk)
        shift = Shift.objects.filter(pk=canonical_id).first()
        if shift is not None:
            shift.name = name
            shift.display_number = display_number
            shift.save(update_fields=["name", "display_number"])
            continue

        Shift.objects.create(
            id=canonical_id,
            name=name,
            display_number=display_number,
        )


def remove_shifts(apps, schema_editor):
    Shift = apps.get_model("core", "Shift")
    Shift.objects.filter(name__in=[n for _, n, _ in DEFAULT_SHIFTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_shift_productionrecord_shift"),
    ]

    operations = [
        migrations.RunPython(create_shifts, remove_shifts),
    ]
