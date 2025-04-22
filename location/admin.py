from django.contrib import admin
from .models import Country, Distrito, Concelho, Region, WeatherStation

admin.site.register(Country)
admin.site.register(Region)
admin.site.register(Distrito)
admin.site.register(Concelho)

admin.site.register(WeatherStation)