# predictions/urls.py
from django.urls import path
from . import views

app_name = 'predictions'

urlpatterns = [
    path('risk-map/', views.prediction_risk_map, name='risk_map'),
]