from django.db import models
from accounts.models import Organization
from django.core.validators import RegexValidator, MinLengthValidator, MaxLengthValidator

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
    distrito = models.ForeignKey(Distrito, on_delete=models.CASCADE, related_name='concelhos')
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
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='weather_stations')
    name = models.CharField(max_length=100)
    station_id = models.CharField(max_length=50, unique=True)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return f"{self.name} Station ({self.city.name})"

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