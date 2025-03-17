from django.db import models
from django.contrib.gis.db import models as gis_models
from location.models import Concelho, Distrito

class Wildfire(models.Model):
    """
    Core model for wildfire incidents across Portugal.
    Stores essential information about each wildfire event.
    """
    # Primary identification
    codigo_sgif = models.CharField(max_length=50, primary_key=True, verbose_name="SGIF Code")
    codigo_anepc = models.FloatField(null=True, blank=True, verbose_name="ANEPC Code")
    
    # Temporal data
    data_hora_alerta = models.DateTimeField(verbose_name="Alert Date/Time")
    data_hora_extincao = models.DateTimeField(verbose_name="Extinction Date/Time")
    duracao_horas = models.FloatField(verbose_name="Duration (Hours)")
    inc_sup_24horas = models.BooleanField(default=False, verbose_name="Incident > 24 Hours")
    
    # Location data - both as Point and as separate coordinates
    longitude = models.FloatField(verbose_name="Longitude")
    latitude = models.FloatField(verbose_name="Latitude")
    
    # Administrative divisions
    concelho = models.ForeignKey(Concelho, on_delete=models.CASCADE, 
                                related_name='wildfires')
    distrito = models.ForeignKey(Distrito, on_delete=models.CASCADE, 
                               related_name='wildfires')
    
    # Temporal components for easier querying
    ano = models.IntegerField(verbose_name="Year")
    mes = models.IntegerField(verbose_name="Month")
    dia = models.IntegerField(verbose_name="Day")
    hora = models.IntegerField(verbose_name="Hour")


    
    class Meta:
        verbose_name = "Wildfire"
        verbose_name_plural = "Wildfires"
        ordering = ['-data_hora_alerta']
        indexes = [
            models.Index(fields=['ano', 'mes']),
            models.Index(fields=['concelho']),
            models.Index(fields=['distrito']),
        ]
    
    def __str__(self):
        return f"Wildfire {self.codigo_sgif} - {self.concelho.name} ({self.data_hora_alerta.strftime('%Y-%m-%d')})"
    
    def save(self, *args, **kwargs):
        # Auto-populate the Point field from longitude and latitude if not set
        if self.longitude and self.latitude and not self.location:
            self.location = gis_models.Point(self.longitude, self.latitude)
        super().save(*args, **kwargs)

class YearlyWildfireSummary(models.Model):
    """
    Annual summary statistics of wildfire incidents by concelho.
    """
    year = models.IntegerField(verbose_name="Year")
    concelho = models.ForeignKey(Concelho, on_delete=models.CASCADE, related_name='yearly_wildfire_summaries')
    total_fires = models.IntegerField(verbose_name="Total Fires")
    total_area_ha = models.FloatField(verbose_name="Total Burned Area (ha)")
    forest_area_ha = models.FloatField(verbose_name="Forest Area Burned (ha)")
    shrub_area_ha = models.FloatField(verbose_name="Shrubland Area Burned (ha)")
    agric_area_ha = models.FloatField(verbose_name="Agricultural Area Burned (ha)")
    avg_duration_hours = models.FloatField(verbose_name="Average Fire Duration (hours)")
    fires_over_24h = models.IntegerField(verbose_name="Fires Lasting Over 24 Hours")
    max_fire_size_ha = models.FloatField(verbose_name="Maximum Fire Size (ha)")
    
    class Meta:
        verbose_name = "Yearly Wildfire Summary"
        verbose_name_plural = "Yearly Wildfire Summaries"
        ordering = ['-year', 'concelho']
        # Ensure we have only one record per year and concelho
        unique_together = ['year', 'concelho']
        indexes = [
            models.Index(fields=['year']),
            models.Index(fields=['concelho']),
        ]
    
    def __str__(self):
        return f"{self.concelho.name} - {self.year} ({self.total_fires} fires)"

    def total_natural_area_ha(self):
        """Returns the sum of forest and shrubland area burned"""
        return self.forest_area_ha + self.shrub_area_ha