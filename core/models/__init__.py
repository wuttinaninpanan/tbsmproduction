"""Model package entrypoint.

Only import *current* models here.

Legacy models previously stored under `core.models.backup` are intentionally not
imported anymore so they are fully removed from the application runtime.
"""

from .user import User
from .user_profile import UserProfile
from .defect_mode import DefectMode
from .auditlog_entry import AuditLogEntry
from .scrap_record import ScrapRecord

# Import other model modules so Django registers them (even if not re-exported).
from . import (  # noqa: F401
	bill_of_material,
	bill_of_material_item_master,
	bom_staging,
	businesspartner,
	defect_by_category,
	item_category,
	item_line,
	item_list,
	item_price,
	item_stage,
	line,
	line_process,
	rounting,
	scrap_record,
)

__all__ = [
	"User",
	"DefectMode",
	"UserProfile",
	"AuditLogEntry",
	"ScrapRecord",
]
