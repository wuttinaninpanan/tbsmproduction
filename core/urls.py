from django.contrib import admin
from django.urls import path
from .views import HomeViews
from .views import LoginViews
from .views import LogoutView
from .views import ContactViews
from .views import AboutViews
from .views import ProfileViews
from .views import RecordViews
from .views import SettingsViews
from .views import ManageComponentPartViews
from .views import ManageProductionViews
from .views.manage_production import download_manage_production_import_template
from .views import ManageDefectModeViews
from .views.manage_defectmode import download_manage_defectmode_import_template
from .views import ManageUserViews
from .views import MonthlyComponentPartReportViews
from .views.settings import download_production_import_template
from .views.dashboard import DashboardViews
from .views import AuditLogViews





urlpatterns = [
    path('',HomeViews.as_view(),name="/"),
    path('login/',LoginViews.as_view(),name="login"),
    path('logout/',LogoutView.as_view(),name="logout"),
    path('contact/',ContactViews.as_view(),name="contact"), 
    path('about/',AboutViews.as_view(),name="about"),
    path('profile/',ProfileViews.as_view(),name="profile"),
    path('record/',RecordViews.as_view(),name="record"),
    path('settings/',SettingsViews.as_view(),name="settings"),
    path('manage-component-part/', ManageComponentPartViews.as_view(), name="manage_component_part"),
    path('manage-defectmode/', ManageDefectModeViews.as_view(), name="manage_defectmode"),
    path(
        "manage-defectmode/template/",
        download_manage_defectmode_import_template,
        name="manage_defectmode_import_template",
    ),
    path('manage-production/', ManageProductionViews.as_view(), name="manage_production"),
    path(
        "manage-production/template/",
        download_manage_production_import_template,
        name="manage_production_import_template",
    ),
    path('add-production/template/', download_production_import_template, name="production_import_template"),
    path('manage-user/',ManageUserViews.as_view(),name="manage_user"),
    path('report-component-part-monthly/', MonthlyComponentPartReportViews.as_view(), name="report_component_part_monthly"),
    path('dashboard/', DashboardViews.as_view(), name="dashboard"),
    path('audit-log/', AuditLogViews.as_view(), name="audit-log"),
]