from django.urls import path
from .views import main_dashboard_view


urlpatterns = [
    path('main_dashboard/', main_dashboard_view, name='main_dashboard'),
]