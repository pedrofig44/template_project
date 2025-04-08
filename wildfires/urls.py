# wildfires/urls.py
from django.urls import path
from . import views

app_name = 'wildfires'

urlpatterns = [
    path('dashboard/', views.wildfire_dashboard, name='dashboard'),
    path('risk-map/', views.wildfire_risk_map, name='risk_map'),
    path('district/<str:district_code>/', views.district_detail, name='district_detail')
]