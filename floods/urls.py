from django.urls import path
from . import views

app_name = 'floods'

urlpatterns = [
    path('flood-dashboard/', views.floods_dashboard, name='flood_dashboard'),
    path('station/<str:station_id>/', views.station_detail, name='station_detail'),
    path('water-body/<int:water_body_id>/', views.water_body_detail, name='water_body_detail'),
]