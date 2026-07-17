from .home import HomeViews
from .login import LoginViews
from .logout import LogoutView
from .contact import ContactViews, ContactSearchView
from .about import AboutViews
from .profile import ProfileViews
from .manage_user import ManageUserViews
from .auditlog import AuditLogViews
from .bom_template import BomTemplateView
from .products import ProductsView
from .product_detail import ProductDetailView
from .item_list import ItemListView
from .manage_settings import ManageSettingsViews
from .manage_settings_defect_by_category import ManageSettingsDefectByCategoryView
from .manage_group_permissions import ManageGroupPermissionsViews, ManageGroupPermissionsDetailView
from .manage_businesspartner import ManageBusinessPartnerViews
from .manage_address_partner import ManageAddressPartnerViews
from .manage_contact import ManageContactViews
from .manage_requests import ManageRequestsViews
from .record import RecordProductionView, RecordDefectsView
from .manage_scrap import ManageScrapViews
from .manage_production import ManageProductionViews
from .manage_line import ManageLineViews, ManageLineEditViews, LineItemSearchView
from .dashboard import DashboardViews
from .report_scrap_monthly import MonthlyComponentPartReportViews
from .report_scrap_weight import ScrapWeightReportViews
from .email_receiver import EmailReceiverView
from .manual import ManualListView, ManualDetailView, ManualFormView


## For auto inspection machine
from core.views.inspection.inspection_item import InspectionItemView
from core.views.inspection.inspection_modelss import InspectionModelssView
from core.views.inspection.inspection_model_defect import InspectionModelsDefectView
from core.views.inspection.inspection_result import InspectionResultView
from core.views.inspection.inspection_error import InspectionErrorView
from core.views.inspection.inspection_products import InspectionProductsView
from core.views.inspection.inspection_defect import InspectionDefectView
from core.views.inspection.inspection_defect_image import InspectionDefectImageView
from core.views.inspection.machine_line import MachineLineView
from core.views.inspection.machine_inspection import MachineInspectionView
from core.views.inspection.machine_product_inspection import MachineProductInspectionView
from core.views.inspection.scrap_dashboard import InspectionScrapDashboardView
from core.views.inspection.kanban_item_mapping import KanbanItemMappingView
from core.views.inspection.detection_object import DetectionObjectView
from core.views.inspection.item_object import ItemObjectView
from core.views.inspection.machine_object import MachineObjectView
from core.views.inspection.object_detection_model import ObjectDetectionModelView
from core.views.inspection.defect_detection_in_models import DefectDetectionInModelsView
from core.views.inspection.defect_mode_view import DefectModeView
from core.views.inspection.inspection_logs import InspectionLogsView