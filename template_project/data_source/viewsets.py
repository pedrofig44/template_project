from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import WeatherForecast
from .serializers import WeatherForecastSerializer

class WeatherForecastViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WeatherForecastSerializer
    queryset = WeatherForecast.objects.all()

    @action(detail=False, url_path='distrito/(?P<location_id>[^/.]+)')
    def by_distrito(self, request, location_id=None):
        today = timezone.now().date()
        forecasts = self.queryset.filter(
            distrito__location_id=location_id,
            forecast_date=today
        )
        serializer = self.get_serializer(forecasts, many=True)
        return Response(serializer.data)