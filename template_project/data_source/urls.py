from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import WeatherForecastViewSet

router = DefaultRouter()
router.register(r'weather', WeatherForecastViewSet, basename='weatherforecast')

urlpatterns = [
    path('', include(router.urls)),
]