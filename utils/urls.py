from django.urls import path
from . import views

app_name = 'utils'

urlpatterns = [
    path('search-items/', views.search_items, name='search_items'),
]