from django.db import models    

class SensorDataDummy(models.Model):
    sensor = models.ForeignKey('location.SensorLocation', on_delete=models.CASCADE, related_name='data')
    timestamp = models.DateTimeField(auto_now_add=True)
    temperature = models.DecimalField(max_digits=5, decimal_places=2)
    humidity = models.DecimalField(max_digits=5, decimal_places=2)
    precipitation = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"Data from {self.sensor.name} at {self.timestamp}"