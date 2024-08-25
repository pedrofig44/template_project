from django.db import models
from django.conf import settings

class Location(models.Model):
    country = models.CharField(max_length=255)
    district = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
class SensorInfo(models.Model):
    SYSTEM_SENSOR = 'system'
    API_SENSOR = 'api'

    SENSOR_TYPE_CHOICES = (
        (SYSTEM_SENSOR, 'System Sensor'),
        (API_SENSOR, 'API Sensor'),
    )

    model = models.CharField(max_length=100)
    source = models.CharField(max_length=100)
    source_type = models.CharField(max_length=100, choices=SENSOR_TYPE_CHOICES, default=SYSTEM_SENSOR)
    sensor_type = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.model} ({self.sensor_type})"
    
class SensorStatus(models.Model):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='sensors')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sensors')
    location = models.ForeignKey('Location', on_delete=models.SET_NULL, null=True, blank=True, related_name='sensors')
    sensor_info = models.OneToOneField('SensorInfo', on_delete=models.CASCADE, related_name='sensor')
    name = models.CharField(max_length=255)
    battery_status = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    last_checked = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.sensor_info.model})"
    
class SensorData(models.Model):
    sensor = models.ForeignKey('SensorStatus', on_delete=models.CASCADE, related_name='data')
    timestamp = models.DateTimeField(auto_now_add=True)
    temperature = models.DecimalField(max_digits=5, decimal_places=2)
    humidity = models.DecimalField(max_digits=5, decimal_places=2)
    precipitation = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"Data from {self.sensor.name} at {self.timestamp}"