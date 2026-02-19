from __future__ import annotations

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
	help = "Create standard auth groups for this project."

	DEFAULT_GROUPS = [
		"R&D",
		"Production",
		"Accounting",
		"Production Control",
	]

	def add_arguments(self, parser):
		parser.add_argument(
			"--names",
			nargs="*",
			default=None,
			help="Optional list of group names to create (defaults to standard set).",
		)

	def handle(self, *args, **options):
		names = options.get("names")
		if not names:
			names = list(self.DEFAULT_GROUPS)

		created = 0
		existed = 0
		for name in names:
			name = (name or "").strip()
			if not name:
				continue
			group, was_created = Group.objects.get_or_create(name=name)
			if was_created:
				created += 1
				self.stdout.write(self.style.SUCCESS(f"Created group: {group.name}"))
			else:
				existed += 1
				self.stdout.write(f"Group already exists: {group.name}")

		self.stdout.write(
			self.style.SUCCESS(
				f"Done. created={created} existed={existed} total={created + existed}"
			)
		)
