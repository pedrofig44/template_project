from django.urls import path
from . import views

app_name = 'climate'

urlpatterns = [
    # Temperature dashboard URLs
    path('temperature/', views.temperature_dashboard, name='temperature_dashboard'),
    path('temperature/station/<str:station_id>/', views.station_temperature_detail, name='station_temperature_detail'),
    path('temperature/api/chart-data/', views.temperature_chart_data, name='temperature_chart_data'),
    
    # Precipitation dashboard URLs
    path('precipitation/', views.precipitation_dashboard, name='precipitation_dashboard'),
    path('precipitation/station/<str:station_id>/', views.station_precipitation_detail, name='station_precipitation_detail'),
    path('precipitation/api/chart-data/', views.precipitation_chart_data, name='precipitation_chart_data'),
    
    
    # Wind dashboard URLs
    path('wind/', views.wind_dashboard, name='wind_dashboard'),
    path('wind/station/<str:station_id>/', views.station_wind_detail, name='station_wind_detail'),
    path('wind/api/chart-data/', views.wind_chart_data, name='wind_chart_data'),

    #API
    path('api/station-location/<str:station_id>/', views.station_location_data, name='station_location_data'),
]