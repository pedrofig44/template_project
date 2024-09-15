from django.db import models
from location.models import Distrito

class SensorDataDummy(models.Model):
    sensor = models.ForeignKey('location.SensorInfo', on_delete=models.CASCADE, related_name='data')
    timestamp = models.DateTimeField(auto_now_add=True)
    temperature = models.DecimalField(max_digits=5, decimal_places=2)
    humidity = models.DecimalField(max_digits=5, decimal_places=2)
    precipitation = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"Data from {self.sensor.name} at {self.timestamp}"
    

class WeatherForecast(models.Model):
    distrito = models.ForeignKey(Distrito, on_delete=models.CASCADE, related_name='weather_forecasts')
    forecast_date = models.DateField()
    data_update = models.DateTimeField()
    id_weather_type = models.IntegerField()
    temperature_min = models.DecimalField(max_digits=5, decimal_places=2)
    temperature_max = models.DecimalField(max_digits=5, decimal_places=2)
    precipitation_probability = models.DecimalField(max_digits=5, decimal_places=2)
    predominant_wind_direction = models.CharField(max_length=2)
    wind_speed_class = models.IntegerField()
    precipitation_intensity_class = models.IntegerField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Forecast for {self.distrito.name} on {self.forecast_date}"