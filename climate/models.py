from django.db import models
from location.models import City, WeatherStation

class DailyForecast(models.Model):
    WIND_DIRECTIONS = [
        ('N', 'North'), ('NE', 'Northeast'), ('E', 'East'),
        ('SE', 'Southeast'), ('S', 'South'), ('SW', 'Southwest'),
        ('W', 'West'), ('NW', 'Northwest')
    ]
    
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='forecasts')
    forecast_date = models.DateField()
    update_date = models.DateTimeField()
    t_min = models.FloatField(verbose_name="Minimum Temperature (°C)")
    t_max = models.FloatField(verbose_name="Maximum Temperature (°C)")
    precipita_prob = models.FloatField(verbose_name="Precipitation Probability (%)")
    wind_dir = models.CharField(max_length=2, choices=WIND_DIRECTIONS)
    wind_speed_class = models.IntegerField()
    weather_type = models.IntegerField()
    latitude = models.FloatField()
    longitude = models.FloatField()

    class Meta:
        ordering = ['forecast_date']
        unique_together = ['city', 'forecast_date']

class HighPrecisionForecast(models.Model):
    DAY_CHOICES = [(0, 'Today'), (1, 'Tomorrow'), (2, 'Day After Tomorrow')]
    
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='hp_forecasts')
    forecast_day = models.IntegerField(choices=DAY_CHOICES)
    forecast_date = models.DateField()
    update_date = models.DateTimeField()
    t_min = models.FloatField()
    t_max = models.FloatField()
    precipita_prob = models.FloatField()
    wind_dir = models.CharField(max_length=2, choices=DailyForecast.WIND_DIRECTIONS)
    wind_speed_class = models.IntegerField()
    precip_intensity_class = models.IntegerField()
    weather_type = models.IntegerField()

    class Meta:
        ordering = ['forecast_day']
        unique_together = ['city', 'forecast_day']

class WeatherWarning(models.Model):
    AWARENESS_LEVELS = [
        ('green', 'No Warning'),
        ('yellow', 'Yellow Warning'),
        ('orange', 'Orange Warning'),
        ('red', 'Red Warning')
    ]
    
    awareness_type = models.CharField(max_length=50)
    awareness_level = models.CharField(max_length=6, choices=AWARENESS_LEVELS)
    area_code = models.CharField(max_length=10, verbose_name="Area Aviso Code")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    description = models.TextField(blank=True)
    
    # New field to create a relationship with the City model
    city = models.ForeignKey(
        City, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='weather_warnings',
        limit_choices_to={'ipma_area_code__isnull': False}
    )
    
    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.get_awareness_level_display()} - {self.awareness_type} ({self.area_code})"
    
    def save(self, *args, **kwargs):
        # If city is not set but area_code is, try to find a matching city
        if not self.city and self.area_code:
            try:
                matching_city = City.objects.filter(ipma_area_code=self.area_code).first()
                if matching_city:
                    self.city = matching_city
            except Exception:
                # If any error occurs, continue without setting the city
                pass
        
        super().save(*args, **kwargs)

class StationObservation(models.Model):
    WIND_DIRECTIONS = [
        (0, 'No Direction'), (1, 'N'), (2, 'NE'),
        (3, 'E'), (4, 'SE'), (5, 'S'),
        (6, 'SW'), (7, 'W'), (8, 'NW'), (9, 'N')
    ]
    
    station = models.ForeignKey(WeatherStation, on_delete=models.CASCADE, related_name='observations')
    timestamp = models.DateTimeField()
    temperature = models.FloatField()
    humidity = models.FloatField()
    wind_speed_kmh = models.FloatField()
    wind_speed_ms = models.FloatField()
    wind_direction = models.IntegerField(choices=WIND_DIRECTIONS)
    precipitation = models.FloatField()
    pressure = models.FloatField(null=True)
    radiation = models.FloatField(null=True)

    class Meta:
        ordering = ['-timestamp']
        unique_together = ['station', 'timestamp']


class FireRisk(models.Model):
    RISK_LEVELS = [
        (1, 'Reduced Risk'),
        (2, 'Moderate Risk'),
        (3, 'High Risk'),
        (4, 'Very High Risk'),
        (5, 'Maximum Risk')
    ]
    
    DAY_CHOICES = [(0, 'Today'), (1, 'Tomorrow')]
    
    concelho = models.ForeignKey(
        'location.Concelho',
        to_field='dico_code',
        on_delete=models.CASCADE,
        related_name='fire_risks'
    )
    forecast_day = models.IntegerField(choices=DAY_CHOICES)
    forecast_date = models.DateField()
    model_run_date = models.DateField()
    update_date = models.DateTimeField()
    risk_level = models.IntegerField(choices=RISK_LEVELS)
    
    class Meta:
        ordering = ['forecast_day', 'concelho']
        unique_together = ['concelho', 'forecast_day']
        verbose_name = 'Fire Risk'
        verbose_name_plural = 'Fire Risks'

    def __str__(self):
        return f"{self.concelho.name} - Day {self.forecast_day} - {self.get_risk_level_display()}"