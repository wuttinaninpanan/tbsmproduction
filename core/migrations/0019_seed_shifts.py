# Seeds the 3 organisation work shifts (idempotent).
#
# These are the options the operator picks from on Page 1 of /record/.
# Keyed on `name` so re-running never duplicates a row.
from django.db import migrations

DEFAULT_SHIFTS = [
    ("Shift A", 1),
    ("Shift B", 2),
    ("Shift D", 3),
]


def create_shifts(apps, schema_editor):
    Shift = apps.get_model("core", "Shift")
    for name, display_number in DEFAULT_SHIFTS:
        Shift.objects.update_or_create(
            name=name,
            defaults={"display_number": display_number},
        )


def remove_shifts(apps, schema_editor):
    Shift = apps.get_model("core", "Shift")
    Shift.objects.filter(name__in=[n for n, _ in DEFAULT_SHIFTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_shift_productionrecord_shift"),
    ]

    operations = [
        migrations.RunPython(create_shifts, remove_shifts),
    ]
