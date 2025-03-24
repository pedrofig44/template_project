from django.urls import path
from .views import main_dashboard_view, index_dashboard_view

app_name = 'dashboard'

urlpatterns = [
    path('main_dashboard/', main_dashboard_view, name='main_dashboard'),
    path('index_dashboard/', index_dashboard_view, name='index_dashboard'),
    path('', main_dashboard_view, name='dashboard_home'),  # Default dashboard route
]