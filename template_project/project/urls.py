from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', include('accounts.urls')),
    path('', include('analytics.urls')),
    path('', include('api.urls')),
    path('', include('dashboard.urls')),
    path('', include('data_source.urls')),
]
