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
from .views import ManageScrapViews
from .views import ManageProductionViews
from .views import AddUserViews
from .views import ManageUserViews
from .views.add_user import download_user_import_template
from .views.settings import download_production_import_template





urlpatterns = [
    path('',HomeViews.as_view(),name="/"),
    path('login/',LoginViews.as_view(),name="login"),
    path('logout/',LogoutView.as_view(),name="logout"),
    path('contact/',ContactViews.as_view(),name="contact"), 
    path('about/',AboutViews.as_view(),name="about"),
    path('profile/',ProfileViews.as_view(),name="profile"),
    path('record/',RecordViews.as_view(),name="record"),
    path('settings/',SettingsViews.as_view(),name="settings"),
    path('manage-scrap/',ManageScrapViews.as_view(),name="manage_scrap"),
    path('manage-production/', ManageProductionViews.as_view(), name="manage_production"),
    path('add-user/',AddUserViews.as_view(),name="add_user"),
    path('add-user/template/', download_user_import_template, name="user_import_template"),
    path('add-production/template/', download_production_import_template, name="production_import_template"),
    path('manage-user/',ManageUserViews.as_view(),name="manage_user"),
    path('add-production/',SettingsViews.as_view(),name="add_production"),
]