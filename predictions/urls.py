# predictions/urls.py
from django.urls import path
from . import views

app_name = 'predictions'

urlpatterns = [
    path('risk-map/', views.prediction_risk_map, name='risk_map'),
    path('dashboard/', views.prediction_dashboard, name='dashboard'),
    path('historical-analysis/', views.historical_analysis, name='historical_analysis'),
    
]