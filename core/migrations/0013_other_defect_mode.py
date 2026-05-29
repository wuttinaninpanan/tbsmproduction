# Seeds a single catch-all DefectMode named "Other".
#
# It is intentionally NOT linked to any ItemCategory (no DefectByCategory row),
# so it never shows up in the normal Defect-mode dropdown. It exists only so the
# Record flow can persist a ProcessDefect when the operator picks "อื่นๆ"
# (scrapping a workpiece for a reason outside the listed process defects); the
# specific reason is stored in ProcessDefect.comment.
from django.conf import settings
from django.db import migrations

OTHER_NAME_EN = "Other"


def create_other(apps, schema_editor):
    DefectMode = apps.get_model("core", "DefectMode")
    if DefectMode.objects.filter(name_en__iexact=OTHER_NAME_EN).exists():
        return
    # DefectMode.user is a required FK. Attach the sentinel to a superuser
    # (or the first user). On a brand-new DB with no users, skip — the Record
    # view will lazily create it on first use with the logged-in operator.
    User = apps.get_model(settings.AUTH_USER_MODEL)
    creator = (
        User.objects.filter(is_superuser=True).order_by("pk").first()
        or User.objects.order_by("pk").first()
    )
    if creator is None:
        return
    DefectMode.objects.create(
        name_th="อื่นๆ",
        name_en=OTHER_NAME_EN,
        name_jp="その他",
        user=creator,
    )


def remove_other(apps, schema_editor):
    DefectMode = apps.get_model("core", "DefectMode")
    DefectMode.objects.filter(name_en__iexact=OTHER_NAME_EN).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_productionrecord_time_window"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(create_other, remove_other),
    ]
