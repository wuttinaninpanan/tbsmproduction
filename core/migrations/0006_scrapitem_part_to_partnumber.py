from django.db import migrations, models


def _backfill_part_number_and_merge_duplicates(apps, schema_editor):
    ScrapItem = apps.get_model("core", "ScrapItem")
    ScrapRecord = apps.get_model("core", "ScrapRecord")

    # Backfill part_number from defect_mode.part
    for s in ScrapItem.objects.select_related("defect_mode", "defect_mode__part").all().iterator():
        part_id = getattr(getattr(s, "defect_mode", None), "part_id", None)
        if part_id and getattr(s, "part_number_id", None) != part_id:
            s.part_number_id = part_id
            s.save(update_fields=["part_number"])

    # Try to resolve any remaining null part_number (should be rare)
    null_qs = ScrapItem.objects.filter(part_number__isnull=True)
    for s in null_qs.iterator():
        rec = ScrapRecord.objects.filter(scrap_item_id=s.pk).order_by("pk").first()
        if rec is not None and getattr(rec, "part_number_id", None):
            s.part_number_id = rec.part_number_id
            s.save(update_fields=["part_number"])
        else:
            # Orphan scrap item: no way to determine part, delete it
            s.delete()

    # Merge duplicates within same part_number by name
    from django.db.models import Count, Min

    dup_groups = (
        ScrapItem.objects.values("part_number_id", "name")
        .annotate(cnt=Count("id"), min_id=Min("id"))
        .filter(cnt__gt=1)
    )

    for g in dup_groups.iterator():
        part_id = g["part_number_id"]
        name = g["name"]
        canonical_id = g["min_id"]
        duplicate_ids = list(
            ScrapItem.objects.filter(part_number_id=part_id, name=name)
            .exclude(id=canonical_id)
            .values_list("id", flat=True)
        )
        if not duplicate_ids:
            continue

        # Move records to canonical scrap item
        ScrapRecord.objects.filter(scrap_item_id__in=duplicate_ids).update(scrap_item_id=canonical_id)

        # Delete duplicates
        ScrapItem.objects.filter(id__in=duplicate_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_userprofile_avatar"),
    ]

    operations = [
        migrations.AddField(
            model_name="scrapitem",
            name="part_number",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.CASCADE,
                related_name="scrap_items",
                to="core.partnumber",
            ),
        ),
        migrations.RunPython(_backfill_part_number_and_merge_duplicates, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="scrapitem",
            name="part_number",
            field=models.ForeignKey(
                on_delete=models.CASCADE,
                related_name="scrap_items",
                to="core.partnumber",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="scrapitem",
            name="uniq_scrap_per_defect",
        ),
        migrations.RemoveField(
            model_name="scrapitem",
            name="defect_mode",
        ),
        migrations.AddConstraint(
            model_name="scrapitem",
            constraint=models.UniqueConstraint(
                fields=("part_number", "name"),
                name="uniq_scrap_per_part",
            ),
        ),
    ]
