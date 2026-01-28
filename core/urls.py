from django.contrib import admin
from django.urls import path
from .views import HomeViews
from .views import LoginViews
from .views import ContactViews
from .views import AboutViews




urlpatterns = [
    path('',HomeViews.as_view(),name="/"),
    path('login/',LoginViews.as_view(),name="login"),
    path('contact/',ContactViews.as_view(),name="contact"), 
    path('about/',AboutViews.as_view(),name="about"),
]