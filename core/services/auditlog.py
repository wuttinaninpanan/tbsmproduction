from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from core.models import AuditLogEntry


def _get_client_ip(request: HttpRequest) -> str | None:
    forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
    if forwarded:
        ip = forwarded.split(",")[0].strip()
        return ip or None
    return (request.META.get("REMOTE_ADDR") or "").strip() or None


def log_event(
    request: HttpRequest | None,
    *,
    action: str,
    message: str = "",
    status: str = "success",
    actor_username: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Write an audit log entry (best-effort)."""

    try:
        actor = None
        ip_address = None
        user_agent = ""

        if request is not None:
            user = getattr(request, "user", None)
            if getattr(user, "is_authenticated", False):
                actor = user
            ip_address = _get_client_ip(request)
            user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:256]

        AuditLogEntry.objects.create(
            action=(action or "").strip()[:64] or "unknown",
            status=(status or "success").strip()[:16] or "success",
            actor=actor,
            actor_username=(actor_username or "").strip()[:150],
            ip_address=ip_address,
            user_agent=user_agent,
            message=(message or ""),
            metadata=metadata,
        )

        # Allow request-level middleware to skip generic logs when a view already
        # wrote a more meaningful audit entry.
        if request is not None:
            try:
                setattr(request, "_audit_logged", True)
            except Exception:
                pass
    except Exception:
        return
