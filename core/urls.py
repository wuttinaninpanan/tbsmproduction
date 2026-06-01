from django.urls import path
from core.views import HomeViews , LoginViews , LogoutView , ContactViews , ContactSearchView , AboutViews , ProfileViews , ManageUserViews , AuditLogViews , ManageLineViews,ManageLineEditViews,LineItemSearchView,DashboardViews,RecordProductionView,RecordDefectsView,ManageScrapViews,ManageProductionViews,MonthlyComponentPartReportViews,ScrapWeightReportViews,ManageSettingsViews,ManageSettingsDefectByCategoryView,ManageBusinessPartnerViews,ManageAddressPartnerViews,ManageContactViews,ManageRequestsViews,BomTemplateView,ProductsView,ProductDetailView,ItemListView
from core.views import InspectionItemView, InspectionModelssView, InspectionModelsDefectView, InspectionResultView, InspectionErrorView, InspectionProductsView, InspectionDefectView, InspectionDefectImageView
from core.views import MachineLineView, MachineInspectionView, MachineProductInspectionView
from core.views import InspectionScrapDashboardView
from core.views import EmailReceiverView
from core.views import ManualListView, ManualDetailView, ManualFormView



urlpatterns = [
    path('',HomeViews.as_view(),name="/"),
    path('dashboard/', DashboardViews.as_view(), name="dashboard"),
    path('login/',LoginViews.as_view(),name="login"),
    path('logout/',LogoutView.as_view(),name="logout"),
    path('contact/',ContactViews.as_view(),name="contact"),
    path('contact/api/search/',ContactSearchView.as_view(),name="contact_search"),
    path('about/',AboutViews.as_view(),name="about"),
    path('profile/',ProfileViews.as_view(),name="profile"),
    path('manage-user/',ManageUserViews.as_view(),name="manage_user"),
    path('audit-log/', AuditLogViews.as_view(), name="audit-log"),
    path('manage-settings/', ManageSettingsViews.as_view(), name="manage_settings"),
    path('manage-settings/defect-by-category/<uuid:category_id>/', ManageSettingsDefectByCategoryView.as_view(), name="manage_settings_defect_by_category"),
	path('record/', RecordProductionView.as_view(), name="record"),
	path('record/defects/', RecordDefectsView.as_view(), name="record_defects"),
	path('manage-scrap/', ManageScrapViews.as_view(), name="manage_scrap"),
    path('manage-production/', ManageProductionViews.as_view(), name="manage_production"),
    path('report_scrap_monthly/', MonthlyComponentPartReportViews.as_view(), name="report_scrap_monthly"),
    path('report_scrap_weight/', ScrapWeightReportViews.as_view(), name="report_scrap_weight"),
    path('manage-line/', ManageLineViews.as_view(), name="manage_line"),
    path('manage-line/api/items/search/', LineItemSearchView.as_view(), name="manage_line_item_search"),
    path('manage-line/<uuid:id>/edit/', ManageLineEditViews.as_view(), name="manage_line_edit"),
    path('bom-template/', BomTemplateView.as_view(), name="bom_template"),
    path('products/', ProductsView.as_view(), name="products"),
    path('products/<uuid:item_id>/', ProductDetailView.as_view(), name="product_detail"),
    path('item-list/', ItemListView.as_view(), name="item_list"),
    path('manage-business-partner/', ManageBusinessPartnerViews.as_view(), name="manage_businesspartner"),
    path('manage-address-partner/', ManageAddressPartnerViews.as_view(), name="manage_address_partner"),
    path('manage-contact/', ManageContactViews.as_view(), name="manage_contact"),
    path('manage-requests/', ManageRequestsViews.as_view(), name="manage_requests"),
    path('manage-email-receiver/', EmailReceiverView.as_view(), name="manage_email_receiver"),

    path('manual/', ManualListView.as_view(), name="manual_list"),
    path('manual/new/', ManualFormView.as_view(), name="manual_new"),
    path('manual/<uuid:id>/edit/', ManualFormView.as_view(), name="manual_edit"),
    path('manual/<uuid:id>/', ManualDetailView.as_view(), name="manual_detail"),

    path('inspection/inspection_item/', InspectionItemView.as_view(), name="Inspection_item"),
    path('inspection/inspection_modelss/', InspectionModelssView.as_view(), name="inspection_modelss"),
    path('inspection/inspection_model_defect/', InspectionModelsDefectView.as_view(), name="inspection_model_defect"),
    path('inspection/inspection_result/', InspectionResultView.as_view(), name="inspection_result"),
    path('inspection/inspection_error/', InspectionErrorView.as_view(), name="inspection_error"),
    path('inspection/inspection_products/', InspectionProductsView.as_view(), name="inspection_products"),
    path('inspection/inspection_defect/', InspectionDefectView.as_view(), name="inspection_defect"),
    path('inspection/inspection_defect_image/', InspectionDefectImageView.as_view(), name="inspection_defect_image"),

    path('inspection/scrap-dashboard/', InspectionScrapDashboardView.as_view(), name="inspection_scrap_dashboard"),

    path('inspection/machine/', MachineLineView.as_view(), name="inspection_machine"),
    path('inspection/machine/<uuid:machine_id>/', MachineInspectionView.as_view(), name="inspection_machine_detail"),
    path('inspection/machine/<uuid:machine_id>/product/<uuid:item_id>/', MachineProductInspectionView.as_view(), name="inspection_machine_product"),
]