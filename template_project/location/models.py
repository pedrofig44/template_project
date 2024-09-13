from django.db import models
from accounts.models import Organization

# Country Model
class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=3, unique=True)  # ISO Alpha-3 country code (e.g., PRT for Portugal)

    def __str__(self):
        return self.name

# Distrito (District) Model
class Distrito(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='distritos')
    name = models.CharField(max_length=100)
    location_id = models.CharField(max_length=7, unique=True)

    def __str__(self):
        return f"{self.name}, {self.country.name}"

# Concelho (Municipality) Model
class Concelho(models.Model):
    distrito = models.ForeignKey(Distrito, on_delete=models.CASCADE, related_name='concelhos')
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name}, {self.distrito.name}"

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

# SensorLocation Model
class SensorLocation(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='sensor_locations')
    district = models.ForeignKey(Distrito, on_delete=models.CASCADE, related_name='sensor_locations')
    coordinates = models.ForeignKey(Coordinates, on_delete=models.CASCADE, related_name='sensor_locations')
    name = models.CharField(max_length=255)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='sensor_locations', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name