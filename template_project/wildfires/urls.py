# wildfires/urls.py
from django.urls import path
from . import views

app_name = 'wildfires'

urlpatterns = [
    path('dashboard/', views.wildfire_dashboard, name='dashboard'),
]