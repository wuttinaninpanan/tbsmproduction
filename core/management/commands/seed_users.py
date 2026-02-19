from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models.user_profile import UserProfile


@dataclass(frozen=True)
class SeedUserSpec:
    username: str
    role: str
    display_name: str


class Command(BaseCommand):
    help = "Seed initial users into the database (admin/staff/user)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            required=True,
            help="Password to set for all seeded users.",
        )
        parser.add_argument("--admin", default="admin", help="Admin username (superuser).")
        parser.add_argument("--staff", default="staff", help="Staff username.")
        parser.add_argument("--user", default="user", help="Normal user username.")
        parser.add_argument(
            "--no-update",
            action="store_true",
            help="If set, do not update existing users' password/flags.",
        )

    def handle(self, *args, **options):
        password: str = options["password"]
        no_update: bool = bool(options.get("no_update"))

        specs = [
            SeedUserSpec(username=options["admin"], role="admin", display_name=options["admin"]),
            SeedUserSpec(username=options["staff"], role="staff", display_name=options["staff"]),
            SeedUserSpec(username=options["user"], role="user", display_name=options["user"]),
        ]

        User = get_user_model()
        flags = {
            "admin": (True, True),
            "staff": (True, False),
            "user": (False, False),
        }

        for spec in specs:
            if not spec.username:
                continue

            user, created = User.objects.get_or_create(
                username=spec.username,
                defaults={"is_active": True},
            )

            if created or not no_update:
                user.set_password(password)
                is_staff, is_superuser = flags.get(spec.role, (False, False))
                user.is_staff = bool(is_staff)
                user.is_superuser = bool(is_superuser)
                user.is_active = True
                user.save()

            UserProfile.objects.get_or_create(
                user=user,
                defaults={"display_name": (spec.display_name or spec.username)},
            )

            status = "created" if created else ("skipped" if no_update else "updated")
            self.stdout.write(f"{spec.username}: {status} role={spec.role}")
