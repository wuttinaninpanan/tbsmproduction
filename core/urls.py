from django.urls import path
from .views import HomeViews
from .views import LoginViews
from .views import LogoutView
from .views import ContactViews
from .views import AboutViews
from .views import ProfileViews
from .views import ManageUserViews
from .views import AuditLogViews
from .views import ManageDefectModeViews, ManageDefectModeCategoryViews
from .views import ManageItemListViews
from .views import ManageItemCategoryViews
from .views import ManageItemLineViews
from .views import ManageBillOfMaterialViews
from .views import RecordViews
from .views import ManageScrapViews
from .views import ManageLineViews
from .views import DashboardViews
from .views import MonthlyComponentPartReportViews





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
    path('manage-line/', ManageLineViews.as_view(), name="manage_line"),
    path('manage-item-category/', ManageItemCategoryViews.as_view(), name="manage_item_category"),
    path('manage-item-line/', ManageItemLineViews.as_view(), name="manage_item_line"),
    path('manage-bill-of-material/', ManageBillOfMaterialViews.as_view(), name="manage_bill_of_material"),
]