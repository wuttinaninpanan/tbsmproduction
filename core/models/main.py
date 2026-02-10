"""Compatibility layer.

Historically, all models lived in this module. They have been split into
dedicated modules under `core.models` for easier maintenance.

Keep importing from `core.models` (preferred) or `core.models.main` (legacy).
"""

from .defects import DefectMode
from .production import PartNumber, ProductionLine
from .profiles import UserProfile
from .scrap import ScrapItem, ScrapRecord

__all__ = [
	"ProductionLine",
	"PartNumber",
	"DefectMode",
	"ScrapItem",
	"ScrapRecord",
	"UserProfile",
]
