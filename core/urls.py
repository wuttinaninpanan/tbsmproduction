from django.urls import path
from core.views import HomeViews , LoginViews , LogoutView , ContactViews , AboutViews , ProfileViews , ManageUserViews , AuditLogViews , ManageDefectModeViews, ManageDefectModeCategoryViews ,ManageLineViews,ManageLineEditViews,LineItemSearchView,DashboardViews,ManageItemListViews,ManageItemCategoryViews,ManageItemLineViews , ManageBillOfMaterialViews,ManageBillOfMaterialItemMasterViews,RecordViews,ManageScrapViews,MonthlyComponentPartReportViews,ScrapWeightReportViews,ManageItemStageViews,ManageBusinessPartnerViews,ManageAddressPartnerViews,ManageContactViews,BomTemplateView,ProductsView,ProductDetailView
from core.views import InspectionItemView, InspectionModelssView, InspectionModelsDefectView, InspectionResultView, InspectionErrorView, InspectionProductsView



urlpatterns = [
    path('',HomeViews.as_view(),name="/"),
    path('dashboard/', DashboardViews.as_view(), name="dashboard"),
    path('login/',LoginViews.as_view(),name="login"),
    path('logout/',LogoutView.as_view(),name="logout"),
    path('contact/',ContactViews.as_view(),name="contact"), 
    path('about/',AboutViews.as_view(),name="about"),
    path('profile/',ProfileViews.as_view(),name="profile"),
    path('manage-user/',ManageUserViews.as_view(),name="manage_user"),
    path('audit-log/', AuditLogViews.as_view(), name="audit-log"),
    path('manage-defectmode/', ManageDefectModeViews.as_view(), name="manage_defectmode"),
    path('manage-defectmodecategory/', ManageDefectModeCategoryViews.as_view(), name="manage_defectmodecategory"),
    path('manage-item_list/', ManageItemListViews.as_view(), name="manage_item_list"),
	path('record/', RecordViews.as_view(), name="record"),
	path('manage-scrap/', ManageScrapViews.as_view(), name="manage_scrap"),
    path('report_scrap_monthly/', MonthlyComponentPartReportViews.as_view(), name="report_scrap_monthly"),
    path('report_scrap_weight/', ScrapWeightReportViews.as_view(), name="report_scrap_weight"),
    path('manage-line/', ManageLineViews.as_view(), name="manage_line"),
    path('manage-line/api/items/search/', LineItemSearchView.as_view(), name="manage_line_item_search"),
    path('manage-line/<uuid:id>/edit/', ManageLineEditViews.as_view(), name="manage_line_edit"),
    path('manage-item-category/', ManageItemCategoryViews.as_view(), name="manage_item_category"),
    path('manage-item-line/', ManageItemLineViews.as_view(), name="manage_item_line"),
    path('manage-bill-of-material/', ManageBillOfMaterialViews.as_view(), name="manage_bill_of_material"),
    path('manage-bom-item-master/', ManageBillOfMaterialItemMasterViews.as_view(), name="manage_bom_item_master"),
    path('bom-template/', BomTemplateView.as_view(), name="bom_template"),
    path('products/', ProductsView.as_view(), name="products"),
    path('products/<uuid:item_id>/', ProductDetailView.as_view(), name="product_detail"),
    path('manage-item-stage/', ManageItemStageViews.as_view(), name="manage_item_stage"),
    path('manage-business-partner/', ManageBusinessPartnerViews.as_view(), name="manage_businesspartner"),
    path('manage-address-partner/', ManageAddressPartnerViews.as_view(), name="manage_address_partner"),
    path('manage-contact/', ManageContactViews.as_view(), name="manage_contact"),

    path('inspection/inspection_item/', InspectionItemView.as_view(), name="Inspection_item"),
    path('inspection/inspection_modelss/', InspectionModelssView.as_view(), name="inspection_modelss"),
    path('inspection/inspection_model_defect/', InspectionModelsDefectView.as_view(), name="inspection_model_defect"),
    path('inspection/inspection_result/', InspectionResultView.as_view(), name="inspection_result"),
    path('inspection/inspection_error/', InspectionErrorView.as_view(), name="inspection_error"),
    path('inspection/inspection_products/', InspectionProductsView.as_view(), name="inspection_products"),
]