from .home import HomeViews
from .login import LoginViews
from .logout import LogoutView
from .contact import ContactViews
from .about import AboutViews
from .profile import ProfileViews
from .manage_user import ManageUserViews
from .auditlog import AuditLogViews
from .manage_defectmode import ManageDefectModeViews
from .manage_defectmodecategory import ManageDefectModeCategoryViews
from .manage_item_list import ManageItemListViews
from .manage_item_category import ManageItemCategoryViews
from .manage_item_line import ManageItemLineViews
from .manage_bill_of_material import ManageBillOfMaterialViews
from .manage_bill_of_material_item_master import ManageBillOfMaterialItemMasterViews
from .bom_template import BomTemplateView
from .products import ProductsView
from .product_detail import ProductDetailView
from .manage_item_stage import ManageItemStageViews
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