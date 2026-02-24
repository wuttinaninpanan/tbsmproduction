from __future__ import annotations

from time import monotonic
from typing import Any

from django.http import HttpRequest

from core.services.auditlog import log_event


class AuditLogMiddleware:
    """Request-level audit logging.

    Logs (best-effort) after the response is produced so we can record status code
    and route information. Avoids logging static/media noise and redacts sensitive keys.
    """

    _SKIP_PREFIXES = ("/static/", "/media/")
    _SKIP_EXACT = ("/favicon.ico",)

    # Avoid duplicate entries with explicit login/logout logging already in views.
    _SKIP_ALL_METHODS_FOR_PATHS = {"/logout/"}
    _SKIP_POST_FOR_PATHS = {"/login/"}

    _SENSITIVE_KEY_HINTS = ("password", "pass", "secret", "token", "key", "authorization")

    _PAGE_OPEN_MESSAGES = {
        "home": "เปิดหน้า Home",
        "dashboard": "เปิดหน้า Dashboard",
        "record": "เปิดหน้า Record",
        "settings": "เปิดหน้า Settings",
        "manage_component_part": "เปิดหน้า Manage Component Part",
        "manage_defectmode": "เปิดหน้า Manage Defect Mode",
        "manage_production": "เปิดหน้า Manage Production",
        "manage_user": "เปิดหน้า Manage User",
        "report_component_part_monthly": "เปิดหน้า Monthly Component Part Report",
        "profile": "เปิดหน้า Profile",
        "about": "เปิดหน้า About",
        "contact": "เปิดหน้า Contact",
        "audit-log": "เปิดหน้า Audit Log",
        "login": "เปิดหน้า Login",
    }

    def _normalize_page_key(self, *, url_name: str, view_name: str, path: str) -> str:
        key = (url_name or view_name or path or "").strip()
        if key in {"", "/"}:
            return "home"
        if key.startswith("/"):
            key = key.strip("/").replace("/", "_")
        return key or "home"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        started = monotonic()
        try:
            response = self.get_response(request)
        except Exception as exc:
            self._log_request(
                request,
                status_code=500,
                duration_ms=int((monotonic() - started) * 1000),
                error=exc,
            )
            raise

        self._log_request(
            request,
            status_code=getattr(response, "status_code", 0) or 0,
            duration_ms=int((monotonic() - started) * 1000),
            error=None,
        )
        return response

    def _should_skip(self, request: HttpRequest) -> bool:
        path = (getattr(request, "path", "") or "/").strip() or "/"

        if path in self._SKIP_EXACT:
            return True
        if any(path.startswith(prefix) for prefix in self._SKIP_PREFIXES):
            return True

        if path in self._SKIP_ALL_METHODS_FOR_PATHS:
            return True
        if request.method.upper() == "POST" and path in self._SKIP_POST_FOR_PATHS:
            return True

        return False

    def _redact_value(self, key: str, value: Any) -> Any:
        k = (key or "").lower()
        if any(h in k for h in self._SENSITIVE_KEY_HINTS):
            return "[REDACTED]"
        if isinstance(value, (list, tuple)):
            return [self._redact_value(key, v) for v in value][:10]
        if isinstance(value, str):
            if len(value) > 500:
                return value[:500] + "…"
            return value
        return value

    def _sanitize_querydict(self, qd) -> dict[str, Any]:
        out: dict[str, Any] = {}
        try:
            keys = list(qd.keys())[:50]
            for key in keys:
                values = qd.getlist(key)
                if not values:
                    continue
                out[key] = self._redact_value(key, values if len(values) > 1 else values[0])
        except Exception:
            return {}
        return out

    def _status_label(self, status_code: int) -> str:
        if 200 <= status_code < 400:
            return "success"
        if status_code >= 400:
            return "failure"
        return "info"

    def _log_request(self, request: HttpRequest, *, status_code: int, duration_ms: int, error: Exception | None) -> None:
        if self._should_skip(request):
            return

        # If the view already wrote a domain-specific audit entry (e.g. "edit Component Part Record"),
        # skip the generic request log to reduce noise.
        if getattr(request, "_audit_logged", False):
            return

        user = getattr(request, "user", None)
        is_authed = bool(getattr(user, "is_authenticated", False))

        # Log all authenticated traffic; for unauthenticated, log only failures (to reduce noise).
        if not is_authed and status_code < 400:
            return

        resolver_match = getattr(request, "resolver_match", None)
        view_name = ""
        url_name = ""
        if resolver_match is not None:
            view_name = (getattr(resolver_match, "view_name", "") or "").strip()
            url_name = (getattr(resolver_match, "url_name", "") or "").strip()

        method = (getattr(request, "method", "GET") or "GET").upper()
        path = (getattr(request, "path", "") or "").strip() or "/"

        if method == "GET" and status_code < 400 and error is None:
            page_key = self._normalize_page_key(url_name=url_name, view_name=view_name, path=path)
            action = f"page:view:{page_key}"
            message = self._PAGE_OPEN_MESSAGES.get(page_key, f"เปิดหน้า {page_key}")
        else:
            action_parts = ["http", method.lower()]
            if url_name:
                action_parts.append(url_name)
            elif view_name:
                action_parts.append(view_name)
            else:
                action_parts.append(path.strip("/") or "root")
            action = ":".join(action_parts)
            message = f"{method} {path} -> {status_code}"

        metadata: dict[str, Any] = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
        }
        if view_name:
            metadata["view_name"] = view_name
        if url_name:
            metadata["url_name"] = url_name
        if method == "GET" and status_code < 400 and error is None:
            metadata["page_key"] = page_key

        try:
            metadata["query"] = self._sanitize_querydict(getattr(request, "GET", {}))
        except Exception:
            pass

        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            try:
                post = getattr(request, "POST", None)
                if post is not None:
                    # Keep it light: only capture known/important fields.
                    if "action" in post:
                        metadata["form_action"] = (post.get("action") or "").strip()[:100]
                    metadata["post_keys"] = list(post.keys())[:50]
            except Exception:
                pass

        if error is not None:
            metadata["error"] = f"{error.__class__.__name__}: {str(error)[:300]}"

        log_event(
            request,
            action=action,
            status=self._status_label(status_code),
            message=message,
            metadata=metadata,
        )
