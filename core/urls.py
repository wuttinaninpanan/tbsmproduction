from django.contrib import admin
from django.urls import path
from .views import HomeViews
from .views import LoginViews
from .views import ContactViews
from .views import AboutViews
from .views import ProfileViews
from .views import RecordViews
from .views import SettingsViews
from .views import ManageScrapViews




urlpatterns = [
    path('',HomeViews.as_view(),name="/"),
    path('login/',LoginViews.as_view(),name="login"),
    path('contact/',ContactViews.as_view(),name="contact"), 
    path('about/',AboutViews.as_view(),name="about"),
    path('profile/',ProfileViews.as_view(),name="profile"),
    path('record/',RecordViews.as_view(),name="record"),
    path('settings/',SettingsViews.as_view(),name="settings"),
    path('manage-scrap/',ManageScrapViews.as_view(),name="manage_scrap"),
]