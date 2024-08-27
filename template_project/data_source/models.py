from django.db import models
from accounts.models import Organization

class SensorLocation(models.Model):
    country = models.CharField(max_length=255)
    district = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='sensor_locations', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    
class SensorData(models.Model):
    sensor = models.ForeignKey('SensorLocation', on_delete=models.CASCADE, related_name='data')
    timestamp = models.DateTimeField(auto_now_add=True)
    temperature = models.DecimalField(max_digits=5, decimal_places=2)
    humidity = models.DecimalField(max_digits=5, decimal_places=2)
    precipitation = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"Data from {self.sensor.name} at {self.timestamp}"