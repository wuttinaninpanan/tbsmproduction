"""Compatibility layer.

Historically, all models lived in this module. They have been split into
dedicated modules under `core.models` for easier maintenance.

Keep importing from `core.models` (preferred) or `core.models.main` (legacy).
"""

from .user import User
from .defect_mode import DefectMode
from .user_profile import UserProfile
from .auditlog_entry import AuditLogEntry

__all__ = [
	"User",
	"DefectMode",
	"UserProfile",
	"AuditLogEntry",
]
