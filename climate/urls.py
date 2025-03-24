from django.urls import path
from . import views

app_name = 'climate'

urlpatterns = [
    path('temperature/', views.temperature_dashboard, name='temperature_dashboard'),
    path('temperature/station/<str:station_id>/', views.station_temperature_detail, name='station_temperature_detail'),
    path('temperature/api/chart-data/', views.temperature_chart_data, name='temperature_chart_data'),
    
    
    # New wind dashboard URLs
    path('wind/', views.wind_dashboard, name='wind_dashboard'),
    path('wind/station/<str:station_id>/', views.station_wind_detail, name='station_wind_detail'),
    path('wind/api/chart-data/', views.wind_chart_data, name='wind_chart_data'),

    #API
    path('api/station-location/<str:station_id>/', views.station_location_data, name='station_location_data'),
]