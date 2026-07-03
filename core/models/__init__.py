"""Model package entrypoint.

Only import *current* models here.

Legacy models previously stored under `core.models.backup` are intentionally not
imported anymore so they are fully removed from the application runtime.
"""

from .user import User
from .user_profile import UserProfile
from .employee_info import (
	Contract,
	CostCenter,
	Division,
	Employee,
	EmployeeRole,
	EmployType,
	JobLevel,
	Organization,
	OrganizationEmployee,
	Position,
	Section,
)
from .defect_mode import DefectMode
from .auditlog_entry import AuditLogEntry
from .scrap_record import ScrapRecord
from .defect_stat import DefectStat
from .process_defect import ProductionRecord, ProcessDefect, ProcessDefectScrap
from core.models.inspection.inspection_model import InspectionModels
from core.models.inspection.inspection_item import InspectionItem
from core.models.inspection.inspection_model_defect import InspectionModelsDefect
from core.models.inspection.inspection_result import InspectionResult
from core.models.inspection.inspection_error import InspectionError
from core.models.inspection.inspection_products import InspectionProducts
from core.models.inspection.inspection_defect import InspectionDefect
from core.models.inspection.inspection_defect_image import InspectionDefectImage
from core.models.inspection.object_detection import (
	KanbanItemMapping,
	DetectionObject,
	ItemObject,
	MachineObject,
	ObjectDetectionModel,
	DefectDetectionInModels,
)
from core.models.inspection.inspection_log import (
	InspectionOKLog,
	InspectionOKLogDetail,
	InspectionOKLogDetailPhoto,
	InspectionNGLog,
	InspectionNGLogDetail,
	InspectionNGLogDetailPhoto,
)
from core.models.inspection.inspection_report import InspectionReport
from core.models.department import Department
from core.models.shift import Shift
from core.models.inspection.machine import Machine
from core.models.email_receiver import EmailReceiver
from core.models.manual import Manual
from core.models.contact_request import ContactMessage, PartRequest

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
	"EmployeeRole",
	"Division",
	"Section",
	"Position",
	"Organization",
	"EmployType",
	"JobLevel",
	"CostCenter",
	"Employee",
	"OrganizationEmployee",
	"Contract",
	"AuditLogEntry",
	"ScrapRecord",
	"DefectStat",
	"ProductionRecord",
	"ProcessDefect",
	"ProcessDefectScrap",
    "InspectionModels",
    "InspectionItem",
    "InspectionModelsDefect",
    "InspectionResult",
	"InspectionError",
    "InspectionProducts",
    "InspectionDefect",
    "InspectionDefectImage",
    "Department",
    "Shift",
    "Machine",
    "EmailReceiver",
    "Manual",
    "ContactMessage",
    "PartRequest",
    "KanbanItemMapping",
    "DetectionObject",
    "ItemObject",
    "MachineObject",
    "ObjectDetectionModel",
    "DefectDetectionInModels",
    "InspectionOKLog",
    "InspectionOKLogDetail",
    "InspectionOKLogDetailPhoto",
    "InspectionNGLog",
    "InspectionNGLogDetail",
    "InspectionNGLogDetailPhoto",
    "InspectionReport",
]
