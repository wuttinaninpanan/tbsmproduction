"""Synchronize cloud users and employee master data without replacing ERP rows."""
from __future__ import annotations

import json
from pathlib import Path

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


DEFAULT_INPUT = Path("core/fixtures/employee_seed.json")


MODEL_PLAN = [
    ("core.role", "core.EmployeeRole", {}),
    ("core.division", "core.Division", {}),
    ("core.department", "core.Department", {"division": "core.division"}),
    ("core.section", "core.Section", {"department": "core.department"}),
    ("core.position", "core.Position", {}),
    (
        "core.organization",
        "core.Organization",
        {"section": "core.section", "department": "core.department", "division": "core.division"},
    ),
    ("core.employtype", "core.EmployType", {}),
    ("core.joblevel", "core.JobLevel", {}),
    ("core.costcenter", "core.CostCenter", {}),
]

EMPLOYEE_PLAN = [
    (
        "core.employee",
        "core.Employee",
        {
            "user": "core.user",
            "position": "core.position",
            "job_level": "core.joblevel",
            "cost_center": "core.costcenter",
            "employ_type": "core.employtype",
        },
    ),
    (
        "core.organizationemployee",
        "core.OrganizationEmployee",
        {"employee": "core.employee", "organization": "core.organization"},
    ),
    (
        "core.contract",
        "core.Contract",
        {"employee": "core.employee", "renewed_as": "core.employee"},
    ),
]


class Command(BaseCommand):
    help = "Sync cloud users and employee master data from tbapp_application fixture.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "--input",
            default=str(DEFAULT_INPUT),
            help=f"Path to tbapp_application fixture.json (default: {DEFAULT_INPUT}).",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Remove employee records missing from the source. ERP users are retained.",
        )
        parser.add_argument(
            "--deactivate-missing-users",
            action="store_true",
            help="Deactivate local users missing from the source instead of deleting them.",
        )

    def handle(self, *args, **options):
        path = Path(options["input"])
        if not path.exists():
            raise CommandError(f"Fixture not found: {path}")

        try:
            records = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CommandError(f"Cannot read fixture: {exc}") from exc

        grouped: dict[str, list[dict]] = {}
        for record in records:
            grouped.setdefault(record["model"].lower(), []).append(record)

        maps: dict[str, dict[str, object]] = {}
        counts: dict[str, int] = {}

        with transaction.atomic():
            for source_label, target_label, relations in MODEL_PLAN:
                counts[target_label] = self._sync_model(
                    grouped.get(source_label, []), source_label, target_label, relations, maps
                )

            counts["core.User"] = self._sync_users(grouped.get("core.user", []), maps)

            for source_label, target_label, relations in EMPLOYEE_PLAN:
                counts[target_label] = self._sync_model(
                    grouped.get(source_label, []), source_label, target_label, relations, maps
                )

            self._sync_profiles_from_employees()
            if options["replace"]:
                self._remove_missing(maps)
            if options["deactivate_missing_users"]:
                get_user_model().objects.exclude(pk__in=maps.get("core.user", {}).values()).update(is_active=False)

        self.stdout.write(self.style.SUCCESS("Employee sync completed."))
        for label, count in counts.items():
            self.stdout.write(f"  {label:30s} {count:>6d}")

    def _sync_users(self, records, maps):
        User = get_user_model()
        role_map = maps.get("core.role", {})
        user_map = maps.setdefault("core.user", {})
        field_names = {field.name for field in User._meta.concrete_fields}
        ignored = {"id", "role", "created_at", "updated_at", "date_joined"}

        for record in records:
            source_pk = str(record["pk"])
            source = record["fields"]
            username = source["username"]
            defaults = {
                key: value
                for key, value in source.items()
                if key in field_names and key not in ignored
            }
            defaults["employee_role_id"] = role_map.get(str(source.get("role"))) if source.get("role") else None
            user, _ = User.objects.update_or_create(username=username, defaults=defaults)
            user_map[source_pk] = user.pk
            user_map[username] = user.pk
        return len(records)

    def _sync_model(self, records, source_label, target_label, relations, maps):
        model = apps.get_model(target_label)
        field_names = {field.name for field in model._meta.concrete_fields}
        target_map = maps.setdefault(source_label, {})

        for record in records:
            source_pk = str(record["pk"])
            source = record["fields"]
            defaults = {
                key: value
                for key, value in source.items()
                if key in field_names and key not in relations and key not in {"id", "created_at", "updated_at"}
            }
            for field_name, related_label in relations.items():
                source_fk = source.get(field_name)
                if isinstance(source_fk, (list, tuple)):
                    source_fk = source_fk[0] if source_fk else None
                defaults[f"{field_name}_id"] = maps.get(related_label, {}).get(str(source_fk)) if source_fk else None

            target = None
            if target_label == "core.Department":
                target = model.objects.filter(name=source["name"]).first()
            if target is None:
                target, _ = model.objects.update_or_create(pk=record["pk"], defaults=defaults)
            else:
                for key, value in defaults.items():
                    setattr(target, key, value)
                target.save()
            target_map[source_pk] = target.pk
        return len(records)

    def _remove_missing(self, maps):
        for label, source_label in [
            ("core.Contract", "core.contract"),
            ("core.OrganizationEmployee", "core.organizationemployee"),
            ("core.Employee", "core.employee"),
        ]:
            model = apps.get_model(label)
            model.objects.exclude(pk__in=maps.get(source_label, {}).values()).delete()

    def _sync_profiles_from_employees(self):
        Employee = apps.get_model("core.Employee")
        UserProfile = apps.get_model("core.UserProfile")
        shift_map = {"A": "shift_a", "B": "shift_b", "Day": "shift_day"}
        for employee in Employee.objects.select_related("user").prefetch_related("organization_assignments"):
            assignment = employee.organization_assignments.first()
            defaults = {"display_name": f"{employee.title}{employee.first_name} {employee.last_name}".strip()}
            if assignment:
                defaults["shift"] = shift_map.get(assignment.shift, "shift_day")
            UserProfile.objects.update_or_create(user=employee.user, defaults=defaults)
