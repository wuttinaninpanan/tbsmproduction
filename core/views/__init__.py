from .home import HomeViews
from .login import LoginViews
from .logout import LogoutView
from .contact import ContactViews
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
from .manage_businesspartner import ManageBusinessPartnerViews
from .manage_address_partner import ManageAddressPartnerViews
from .manage_contact import ManageContactViews
from .record import RecordViews
from .manage_scrap import ManageScrapViews
from .manage_line import ManageLineViews, ManageLineEditViews, LineItemSearchView
from .dashboard import DashboardViews
from .report_scrap_monthly import MonthlyComponentPartReportViews
from .report_scrap_weight import ScrapWeightReportViews


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