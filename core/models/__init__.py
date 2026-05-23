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
from .defect_stat import DefectStat
from core.models.inspection.inspection_model import InspectionModels
from core.models.inspection.inspection_item import InspectionItem
from core.models.inspection.inspection_model_defect import InspectionModelsDefect
from core.models.inspection.inspection_result import InspectionResult
from core.models.inspection.inspection_error import InspectionError
from core.models.inspection.inspection_products import InspectionProducts
from core.models.inspection.inspection_defect import InspectionDefect
from core.models.inspection.inspection_defect_image import InspectionDefectImage
from core.models.department import Department
from core.models.inspection.machine import Machine
from core.models.inspection.machine_line import MachineLine

# Import other model modules so Django registers them (even if not re-exported).
from . import (  # noqa: F401
	bill_of_material,
	bill_of_material_item_master,
	businesspartner,
	defect_by_category,
	inout,
	item_category,
	item_line,
	item_list,
	item_price,
	item_stage,
	line,
	line_process,
	plant,
	portion,
	process,
	rounting,
	scrap_record,
	side,
	way,
)

__all__ = [
	"User",
	"DefectMode",
	"UserProfile",
	"AuditLogEntry",
	"ScrapRecord",
	"DefectStat",
    "InspectionModels",
    "InspectionItem",
    "InspectionModelsDefect",
    "InspectionResult",
	"InspectionError",
    "InspectionProducts",
    "InspectionDefect",
    "InspectionDefectImage",
    "Department",
    "Machine",
    "MachineLine",
]
