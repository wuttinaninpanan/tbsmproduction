from __future__ import annotations

from django.conf import settings
from django.db import models


class AuditLogEntry(models.Model):
    """Application-level audit log entry."""

    STATUS_CHOICES = [
        ("success", "Success"),
        ("failure", "Failure"),
        ("info", "Info"),
    ]

    action = models.CharField(max_length=64, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default="success",
        db_index=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    actor_username = models.CharField(max_length=150, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=256, blank=True, default="")
    message = models.TextField(blank=True, default="")
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["action", "created_at"], name="audit_action_created_idx"),
            models.Index(fields=["status", "created_at"], name="audit_status_created_idx"),
        ]

    def __str__(self) -> str:
        who = self.actor.username if self.actor_id else (self.actor_username or "-")
        return f"{self.created_at:%Y-%m-%d %H:%M:%S} {who} {self.action}"
