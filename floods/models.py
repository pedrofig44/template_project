# floods/models.py
from django.contrib.gis.db import models
from location.models import Concelho

class WaterBody(models.Model):
    WATER_BODY_TYPES = [
        ('river', 'River'),
        ('lake', 'Lake'),
        ('reservoir', 'Reservoir'),
        ('stream', 'Stream'),
        ('coastal', 'Coastal Water')
    ]
    
    name = models.CharField(max_length=255)
    water_body_type = models.CharField(max_length=20, choices=WATER_BODY_TYPES)
    description = models.TextField(blank=True, null=True)
    concelho = models.ForeignKey(Concelho, on_delete=models.CASCADE, related_name='water_bodies')
    
    # Optional geometry for river/lake shape
    geometry = models.LineStringField(null=True, blank=True, srid=4326)
    
    # Reference levels for flooding
    normal_level = models.FloatField(null=True, blank=True, help_text="Normal water level (m)")
    warning_level = models.FloatField(null=True, blank=True, help_text="Level that triggers warnings (m)")
    danger_level = models.FloatField(null=True, blank=True, help_text="Level that constitutes flooding (m)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Water Body"
        verbose_name_plural = "Water Bodies"
        
    def __str__(self):
        return f"{self.name} ({self.get_water_body_type_display()})"
    
    
class WaterStation(models.Model):
    MEASUREMENT_CAPABILITIES = [
        ('level', 'Water Level Only'),
        ('flow', 'Water Flow Only'),
        ('combined', 'Level and Flow'),
    ]
    
    name = models.CharField(max_length=255)
    station_id = models.CharField(max_length=50, unique=True)
    
    # Channel IDs for API
    level_channel_id = models.CharField(max_length=50, blank=True, null=True, help_text="API channel ID for level data")
    flow_channel_id = models.CharField(max_length=50, blank=True, null=True, help_text="API channel ID for flow data")
    
    measurement_type = models.CharField(max_length=20, choices=MEASUREMENT_CAPABILITIES)
    water_body = models.ForeignKey(WaterBody, on_delete=models.CASCADE, related_name='stations')
    
    # Geographic information
    concelho = models.ForeignKey('location.Concelho', on_delete=models.CASCADE, related_name='water_stations')
    location = models.PointField(null=True, blank=True, srid=4326)
    
    # Operational information
    is_active = models.BooleanField(default=True)
    last_reading_time = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Water Station"
        verbose_name_plural = "Water Stations"
        
    def __str__(self):
        return f"{self.name} ({self.station_id})"
    
    def get_latest_reading(self):
        return self.readings.order_by('-timestamp').first()
        
    def has_level_capability(self):
        return self.measurement_type in ['level', 'combined']
        
    def has_flow_capability(self):
        return self.measurement_type in ['flow', 'combined']
    
    
    
class WaterReading(models.Model):
    station = models.ForeignKey(WaterStation, on_delete=models.CASCADE, related_name='readings')
    timestamp = models.DateTimeField()
    
    # Water level data
    water_level = models.FloatField(null=True, blank=True, help_text="Water level in meters")
    level_change = models.FloatField(null=True, blank=True, help_text="Change in level since last reading (m)")
    
    # Water flow data
    flow_rate = models.FloatField(null=True, blank=True, help_text="Flow rate in liters per second (l/s)")
    flow_change = models.FloatField(null=True, blank=True, help_text="Change in flow since last reading (l/s)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Water Reading"
        verbose_name_plural = "Water Readings"
        unique_together = ['station', 'timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['station', 'timestamp']),
        ]
        
    def __str__(self):
        reading_info = []
        if self.water_level is not None:
            reading_info.append(f"{self.water_level}m")
        if self.flow_rate is not None:
            reading_info.append(f"{self.flow_rate}l/s")
            
        return f"{self.station.name} - {self.timestamp}: {', '.join(reading_info)}"
    
    def is_level_reading(self):
        return self.water_level is not None
        
    def is_flow_reading(self):
        return self.flow_rate is not None
    
    
    
class FloodWarning(models.Model):
    WARNING_LEVELS = [
        ('watch', 'Watch'),
        ('advisory', 'Advisory'),
        ('warning', 'Warning'),
        ('emergency', 'Emergency'),
    ]
    
    water_body = models.ForeignKey(WaterBody, on_delete=models.CASCADE, related_name='flood_warnings')
    station = models.ForeignKey(WaterStation, null=True, blank=True, on_delete=models.SET_NULL, related_name='flood_warnings')
    
    # Reference to the reading that triggered this warning
    triggered_by_reading = models.ForeignKey(WaterReading, null=True, blank=True, on_delete=models.SET_NULL)
    
    warning_level = models.CharField(max_length=20, choices=WARNING_LEVELS)
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Flood Warning"
        verbose_name_plural = "Flood Warnings"
        
    def __str__(self):
        return f"{self.get_warning_level_display()} for {self.water_body.name} - {self.start_time.strftime('%Y-%m-%d')}"