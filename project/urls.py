from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns



urlpatterns = [
    # Admin URL
    path("admin/", admin.site.urls),
    
    # Language switching URL - this is important for the language selector to work
    path('i18n/', include('django.conf.urls.i18n')),
]

urlpatterns += i18n_patterns(
    # Home app URLs - this will handle the root URL
    path('', include('home.urls', namespace='home')),
    
    # Account URLs
    path('accounts/', include('accounts.urls')),
    
    # Other app URLs
    path('analytics/', include('analytics.urls')),
    path('api/', include('api.urls')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('data-source/', include('data_source.urls')),
    path('climate/', include('climate.urls', namespace='climate')),
    path('utils/', include('utils.urls', namespace='utils')),
    path('wildfires/', include('wildfires.urls', namespace='wildfires')),
    path('floods/', include('floods.urls', namespace='floods')),
    
    # Optional: set to False to prevent adding language prefix to default language
    prefix_default_language=False
)

# Add static and media URL patterns if in debug mode
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)