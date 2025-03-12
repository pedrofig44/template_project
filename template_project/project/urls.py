from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

# Function to redirect to the main dashboard
def redirect_to_dashboard(request):
    return redirect('dashboard:main_dashboard')

urlpatterns = [
    # Root URL now points to the main dashboard
    path('', redirect_to_dashboard, name='home'),
    
    # Admin URL
    path("admin/", admin.site.urls),
    
    # Account URLs - not at root anymore
    path('accounts/', include('accounts.urls')),
    
    # Other app URLs
    path('', include('analytics.urls')),
    path('', include('api.urls')),
    path('', include('dashboard.urls', namespace='dashboard')),
    path('', include('data_source.urls')),
    path('', include('climate.urls', namespace='climate')),
]