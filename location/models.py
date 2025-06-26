from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from accounts.models import Organization
from django.core.validators import RegexValidator, MinLengthValidator, MaxLengthValidator
from django.contrib.gis.db import models

class Country(models.Model):
    code = models.CharField(
        max_length=3, 
        primary_key=True, 
        validators=[MinLengthValidator(2), MaxLengthValidator(3)]
    )
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Countries"

    def __str__(self):
        return f"{self.name} ({self.code})"

class Region(models.Model):
    REGION_TYPE_CHOICES = [
        (1, 'Mainland Portugal'),
        (2, 'Madeira Archipelago'),
        (3, 'Azores Archipelago')
    ]
    
    region_code = models.IntegerField(primary_key=True, choices=REGION_TYPE_CHOICES)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)


    def __str__(self):
        return f"{self.name} ({self.get_region_code_display()})"

class Distrito(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='distritos')
    district_code = models.CharField(
        primary_key=True,
        max_length=2,
        validators=[MinLengthValidator(2), MaxLengthValidator(2)],
        verbose_name="District Code (DICO part 1)"
    )
    name = models.CharField(max_length=100)
    
    class Meta:
        ordering = ['district_code']

    def __str__(self):
        return f"{self.name} (DICO-{self.district_code})"

class Concelho(models.Model):
    distrito = models.ForeignKey(Distrito, to_field='district_code', on_delete=models.CASCADE, related_name='concelhos')
    concelho_code = models.CharField(
        max_length=2,
        validators=[MinLengthValidator(2), MaxLengthValidator(2)],
        verbose_name="Municipality Code (DICO part 2)"
    )
    dico_code = models.CharField(
        max_length=4,
        unique=True,
        validators=[MinLengthValidator(4), MaxLengthValidator(4)],
        help_text="Full DICO code (District + Municipality)"
    )
    name = models.CharField(max_length=100)
    
    in_wildfire_training = models.BooleanField(
        default=False,
        help_text="Whether this concelho was included in wildfire prediction model training data (251 out of 308 concelhos)"
    )
    
    
    class Meta:
        unique_together = ('distrito', 'concelho_code')
        ordering = ['dico_code']

    def save(self, *args, **kwargs):
        # Auto-generate DICO code from distrito + concelho
        self.dico_code = f"{self.distrito.district_code}{self.concelho_code}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.dico_code})"

class City(models.Model):
    concelho = models.ForeignKey(
        Concelho, 
        on_delete=models.CASCADE,
        related_name='cities',
        to_field='dico_code'  # Use unique DICO code as reference
    )
    global_id = models.CharField(
        max_length=7,
        unique=True,
        validators=[MinLengthValidator(7), MaxLengthValidator(7)],
        verbose_name="IPMA Global ID"
    )
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    ipma_area_code = models.CharField(
        max_length=3,
        validators=[MinLengthValidator(3), MaxLengthValidator(3)],
        verbose_name="IPMA Area Code"
    )

    class Meta:
        verbose_name_plural = "Cities"

    def __str__(self):
        return f"{self.name} ({self.global_id})"

class WeatherStation(models.Model):
    concelho = models.ForeignKey(
        'location.Concelho',  # Reference the Concelho model
        to_field='dico_code',
        on_delete=models.CASCADE, 
        related_name='weather_stations',  # This allows concelho.weather_stations.all()
        verbose_name="Municipality"
    )
    name = models.CharField(max_length=100)
    station_id = models.CharField(max_length=50, unique=True)
    location = models.PointField(null=True)

    def __str__(self):
        return f"{self.name} Station ({self.concelho.name})"

    def save(self, *args, **kwargs):
        if not self.location and hasattr(self, 'latitude') and hasattr(self, 'longitude'):
            self.location = Point(self.longitude, self.latitude)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['concelho', 'name']

# Coordinates Model
class Coordinates(models.Model):
    concelho = models.ForeignKey(Concelho, on_delete=models.CASCADE, related_name='coordinates')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)  # Latitude: -90 to 90, 6 decimal places
    longitude = models.DecimalField(max_digits=9, decimal_places=6)  # Longitude: -180 to 180, 6 decimal places

    def __str__(self):
        return f"Coordinates: {self.latitude}, {self.longitude}"

# Address Model
class Address(models.Model):
    street = models.CharField(max_length=255)
    number = models.CharField(max_length=10, null=True, blank=True)  # Optional, for buildings with a number
    postal_code = models.CharField(max_length=20)
    concelho = models.ForeignKey(Concelho, on_delete=models.CASCADE, related_name='addresses')
    coordinates = models.OneToOneField(Coordinates, on_delete=models.SET_NULL, null=True, blank=True)  # Optional

    def __str__(self):
        return f"{self.street}, {self.number}, {self.concelho.name}, {self.postal_code}"


# SensorInfo Model
class SensorInfo(models.Model):
    sensor_id = models.CharField(
        max_length=8,
        validators=[RegexValidator(r'^\d{8}$', 'Sensor ID must be an 8-digit number.')]
    )  # Unique 8-digit identifier for the sensor
    coordinates = models.ForeignKey(Coordinates, on_delete=models.CASCADE, related_name='sensor_locations')
    manufacturer = models.CharField(max_length=255, null=True, blank=True)  # Manufacturer of the sensor
    model = models.CharField(max_length=255, null=True, blank=True)  # Model name of the sensor
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='sensor_locations', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.model} ({self.sensor_id})"
    

class ConcelhoLandOccupation(models.Model):
    """
    Land occupation/soil usage data for each concelho
    Based on training data features for land classification
    """
    concelho = models.ForeignKey(
        Concelho, 
        on_delete=models.CASCADE, 
        related_name='land_occupation'
    )
    
    # Area data
    area_ha = models.DecimalField(
        max_digits=12, decimal_places=4,
        help_text="Area of the concelho in hectares"
    )
    
    # Land occupation percentages (from training data)
    territorios_artificializados = models.DecimalField(
        max_digits=8, decimal_places=4,
        help_text="Percentage of artificalized territories"
    )
    pastagens = models.DecimalField(
        max_digits=8, decimal_places=4,
        help_text="Percentage of pastures"
    )
    florestas = models.DecimalField(
        max_digits=8, decimal_places=4,
        help_text="Percentage of forests"
    )
    massas_agua_superficiais = models.DecimalField(
        max_digits=8, decimal_places=4,
        help_text="Percentage of surface water bodies"
    )
    matos = models.DecimalField(
        max_digits=8, decimal_places=4,
        help_text="Percentage of scrubland/bushes"
    )
    superficies_agroflorestais = models.DecimalField(
        max_digits=8, decimal_places=4,
        help_text="Percentage of agroforestry surfaces (SAF)"
    )
    espacos_descobertos_pouca_vegetacao = models.DecimalField(
        max_digits=8, decimal_places=4,
        help_text="Percentage of bare ground or sparse vegetation"
    )
    agricultura = models.DecimalField(
        max_digits=8, decimal_places=4,
        help_text="Percentage of agriculture"
    )
    zonas_humidas = models.DecimalField(
        max_digits=8, decimal_places=4,
        help_text="Percentage of wetlands"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['concelho']
        ordering = ['concelho']
        verbose_name = "Concelho Land Occupation"
        verbose_name_plural = "Concelho Land Occupations"
        indexes = [
            models.Index(fields=['concelho']),
        ]
    
    def __str__(self):
        return f"Land occupation for {self.concelho.name}"
    
    @property
    def total_percentage(self):
        """Calculate total percentage (should be close to 100)"""
        return (
            self.territorios_artificializados + self.pastagens + self.florestas +
            self.massas_agua_superficiais + self.matos + self.superficies_agroflorestais +
            self.espacos_descobertos_pouca_vegetacao + self.agricultura + self.zonas_humidas
        )
    
    def get_land_occupation_dict(self):
        """Return land occupation data as dictionary for ML model input"""
        return {
            'Territórios artificializados': float(self.territorios_artificializados),
            'Pastagens': float(self.pastagens),
            'Florestas': float(self.florestas),
            'Massas de água superficiais': float(self.massas_agua_superficiais),
            'Matos': float(self.matos),
            'Superfícies agroflorestais (SAF)': float(self.superficies_agroflorestais),
            'Espaços descobertos ou com pouca vegetação': float(self.espacos_descobertos_pouca_vegetacao),
            'Agricultura': float(self.agricultura),
            'Zonas húmidas': float(self.zonas_humidas),
            'area_ha': float(self.area_ha),
        }