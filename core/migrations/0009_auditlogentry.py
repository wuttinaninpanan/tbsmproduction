from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_rename_scrap_to_component_part"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditLogEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(db_index=True, max_length=64)),
                (
                    "status",
                    models.CharField(
                        choices=[("success", "Success"), ("failure", "Failure"), ("info", "Info")],
                        db_index=True,
                        default="success",
                        max_length=16,
                    ),
                ),
                ("actor_username", models.CharField(blank=True, default="", max_length=150)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, default="", max_length=256)),
                ("message", models.TextField(blank=True, default="")),
                ("metadata", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="auditlogentry",
            index=models.Index(fields=["action", "created_at"], name="audit_action_created_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlogentry",
            index=models.Index(fields=["status", "created_at"], name="audit_status_created_idx"),
        ),
    ]
