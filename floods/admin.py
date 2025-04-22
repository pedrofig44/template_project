# floods/admin.py
from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin
from .models import (
    WaterBody,
    WaterStation,
    WaterReading,
    FloodWarning
)

@admin.register(WaterBody)
class WaterBodyAdmin(OSMGeoAdmin):
    list_display = ('name', 'water_body_type')
    search_fields = ('name',)

@admin.register(WaterStation)
class WaterStationAdmin(OSMGeoAdmin):
    list_display = ('name', 'station_id', 'measurement_type', 'water_body', 'is_active', 'last_reading_time')
    list_filter = ('measurement_type', 'water_body', 'is_active')
    search_fields = ('name', 'station_id')
    fieldsets = (
        (None, {
            'fields': ('name', 'station_id', 'measurement_type', 'water_body', 'is_active')
        }),
        ('API Configuration', {
            'fields': ('level_channel_id', 'flow_channel_id')
        }),
        ('Geographic Information', {
            'fields': ('concelho', 'location')
        }),
        ('Timestamps', {
            'fields': ('last_reading_time', 'created_at', 'updated_at')
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'last_reading_time')

@admin.register(WaterReading)
class WaterReadingAdmin(admin.ModelAdmin):
    list_display = ('station', 'timestamp', 'water_level', 'level_change', 'flow_rate', 'flow_change')
    list_filter = ('station', 'timestamp')
    date_hierarchy = 'timestamp'
    search_fields = ('station__name',)

@admin.register(FloodWarning)
class FloodWarningAdmin(admin.ModelAdmin):
    list_display = ('water_body', 'warning_level', 'title', 'start_time', 'is_active')
    list_filter = ('warning_level', 'is_active', 'water_body')
    search_fields = ('title', 'description')