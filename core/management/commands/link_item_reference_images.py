from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models.item_list import Item_list


DEFAULT_IMAGE_DIR = Path("component_part_reference")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


def normalize_code(value: str) -> str:
    return (value or "").strip().casefold()


class Command(BaseCommand):
    help = (
        "Link Item_list.reference_image to files in media/component_part_reference "
        "whose basename matches Item_list.sd_code."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            default=str(DEFAULT_IMAGE_DIR),
            help="Directory under MEDIA_ROOT that contains reference images.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without saving changes.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Replace existing reference_image values when a matching file exists.",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Only print the summary.",
        )

    def handle(self, *args, **options):
        relative_dir = Path(options["dir"])
        image_dir = Path(settings.MEDIA_ROOT) / relative_dir
        dry_run = options["dry_run"]
        overwrite = options["overwrite"]
        quiet = options["quiet"]

        if not image_dir.exists():
            self.stderr.write(self.style.ERROR(f"Image directory not found: {image_dir}"))
            return

        files_by_code: dict[str, Path] = {}
        duplicate_files: dict[str, list[str]] = {}
        for path in sorted(image_dir.iterdir(), key=lambda p: p.name.casefold()):
            if not path.is_file() or path.suffix.casefold() not in IMAGE_EXTENSIONS:
                continue
            code = normalize_code(path.stem)
            if not code:
                continue
            if code in files_by_code:
                duplicate_files.setdefault(code, [files_by_code[code].name]).append(path.name)
                continue
            files_by_code[code] = path

        items = list(Item_list.objects.exclude(sd_code="").order_by("sd_code", "part_number"))
        matched = updated = skipped_existing = missing_file = duplicate_items = 0
        seen_item_codes: set[str] = set()
        used_codes: set[str] = set()

        for item in items:
            code = normalize_code(item.sd_code)
            if code in seen_item_codes:
                duplicate_items += 1
            else:
                seen_item_codes.add(code)

            image_path = files_by_code.get(code)
            if image_path is None:
                missing_file += 1
                continue

            matched += 1
            used_codes.add(code)
            relative_path = (relative_dir / image_path.name).as_posix()
            current = (item.reference_image.name or "").strip()
            if current and current == relative_path:
                skipped_existing += 1
                continue
            if current and not overwrite:
                skipped_existing += 1
                if not quiet:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Existing image kept for {item.sd_code}: {current} "
                            f"(matching file: {relative_path})"
                        )
                    )
                continue

            updated += 1
            if not quiet:
                self.stdout.write(f"{'Would link' if dry_run else 'Linked'} {item.sd_code} -> {relative_path}")
            if not dry_run:
                item.reference_image.name = relative_path
                item.save(update_fields=["reference_image", "updated_at"])

        unused_files = [
            path.name
            for code, path in sorted(files_by_code.items())
            if code not in used_codes
        ]

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Reference image link summary"))
        self.stdout.write(f"  image files found:          {len(files_by_code)}")
        self.stdout.write(f"  item rows checked:          {len(items)}")
        self.stdout.write(f"  matched item/image pairs:   {matched}")
        self.stdout.write(f"  updated:                    {updated}")
        self.stdout.write(f"  skipped existing/current:   {skipped_existing}")
        self.stdout.write(f"  items without image file:   {missing_file}")
        self.stdout.write(f"  duplicate item sd_code rows:{duplicate_items}")
        self.stdout.write(f"  duplicate image basenames:  {len(duplicate_files)}")
        self.stdout.write(f"  image files without item:   {len(unused_files)}")

        if duplicate_files:
            self.stdout.write(self.style.WARNING("Duplicate image basenames:"))
            for code, names in sorted(duplicate_files.items()):
                self.stdout.write(f"  {code}: {', '.join(names)}")

        if unused_files:
            self.stdout.write(self.style.WARNING("Image files without matching item (first 50):"))
            for name in unused_files[:50]:
                self.stdout.write(f"  {name}")
            if len(unused_files) > 50:
                self.stdout.write(f"  ... and {len(unused_files) - 50} more")
