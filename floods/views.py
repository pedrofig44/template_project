from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models import Avg, Max, Min, Count
from datetime import timedelta
import json
import polars as pl

from .models import WaterBody, WaterStation, WaterReading, FloodWarning
from location.models import Concelho
from dashboard.utils import generate_line_chart, generate_bar_chart

def floods_dashboard(request):
    """
    Main floods dashboard view showing overall water level and flood risk data
    """
    # Get current date and time
    current_date = timezone.now()
    
    # Get active water stations
    stations = WaterStation.objects.filter(is_active=True).order_by('name')
    
    # Get active water bodies
    water_bodies = WaterBody.objects.all().order_by('name')
    
    # Get recent water readings (last 24 hours)
    day_ago = current_date - timedelta(hours=24)
    recent_readings = WaterReading.objects.filter(
        timestamp__gte=day_ago
    ).order_by('-timestamp')
    
    # Get active flood warnings
    active_warnings = FloodWarning.objects.filter(
        is_active=True,
        end_time__gt=current_date
    ).order_by('-warning_level', '-start_time')
    
    # Calculate statistics
    stats = {
        'total_stations': stations.count(),
        'active_warnings': active_warnings.count(),
        'stations_with_data': recent_readings.values('station').distinct().count(),
    }
    
    # Get highest water levels
    highest_levels = []
    for station in stations:
        latest_reading = station.readings.order_by('-timestamp').first()
        if latest_reading and latest_reading.water_level is not None:
            # Calculate percentage of normal level
            if station.water_body.normal_level:
                level_percent = (latest_reading.water_level / station.water_body.normal_level) * 100
            else:
                level_percent = None
                
            highest_levels.append({
                'station': station,
                'water_body': station.water_body,
                'reading': latest_reading,
                'level_percent': level_percent
            })
    
    # Sort by water level (highest first)
    highest_levels.sort(key=lambda x: x['reading'].water_level if x['reading'].water_level else 0, reverse=True)
    
    # Limit to top 5
    highest_levels = highest_levels[:5]
    
    # Context for template
    context = {
        'stations': stations,
        'water_bodies': water_bodies,
        'stats': stats,
        'active_warnings': active_warnings,
        'highest_levels': highest_levels,
        'current_date': current_date
    }
    
    return render(request, 'floods/flood_dashboard.html', context)

def station_detail(request, station_id):
    """
    View for detailed information about a specific water station
    """
    # Get the station
    station = get_object_or_404(WaterStation, station_id=station_id)
    
    # Get time range for data
    time_range = request.GET.get('range', '24h')  # Default to 24 hours
    
    # Calculate time range
    now = timezone.now()
    if time_range == '24h':
        start_time = now - timedelta(hours=24)
        time_label = "Last 24 Hours"
    elif time_range == '48h':
        start_time = now - timedelta(hours=48)
        time_label = "Last 48 Hours"
    elif time_range == '7d':
        start_time = now - timedelta(days=7)
        time_label = "Last 7 Days"
    elif time_range == '30d':
        start_time = now - timedelta(days=30)
        time_label = "Last 30 Days"
    else:
        start_time = now - timedelta(hours=24)
        time_label = "Last 24 Hours"
    
    # Get readings for the time range
    readings = WaterReading.objects.filter(
        station=station,
        timestamp__gte=start_time
    ).order_by('timestamp')
    
    # Get active warnings for this station
    active_warnings = FloodWarning.objects.filter(
        station=station,
        is_active=True,
        end_time__gt=now
    ).order_by('-warning_level')
    
    # Calculate statistics
    stats = {
        'latest_level': None,
        'max_level': None,
        'avg_level': None,
        'latest_flow': None,
        'max_flow': None,
        'avg_flow': None,
    }
    
    # Generate level chart if data exists
    water_level_chart = None
    flow_rate_chart = None
    
    if readings.exists():
        # Calculate level statistics if station has level capability
        if station.has_level_capability():
            level_readings = readings.exclude(water_level__isnull=True)
            if level_readings.exists():
                level_stats = level_readings.aggregate(
                    max_level=Max('water_level'),
                    avg_level=Avg('water_level')
                )
                stats['max_level'] = level_stats['max_level']
                stats['avg_level'] = level_stats['avg_level']
                
                # Get latest level
                latest_level_reading = level_readings.order_by('-timestamp').first()
                if latest_level_reading:
                    stats['latest_level'] = latest_level_reading.water_level
                    stats['latest_timestamp'] = latest_level_reading.timestamp
                
                # Create chart data
                level_data = list(level_readings.values('timestamp', 'water_level'))
                df_level = pl.DataFrame(level_data)
                
                water_level_chart = generate_line_chart(
                    df=df_level,
                    title=f"Water Level History - {station.name}",
                    x_axis="Time",
                    y_axis="Water Level (m)"
                )
        
        # Calculate flow statistics if station has flow capability
        if station.has_flow_capability():
            flow_readings = readings.exclude(flow_rate__isnull=True)
            if flow_readings.exists():
                flow_stats = flow_readings.aggregate(
                    max_flow=Max('flow_rate'),
                    avg_flow=Avg('flow_rate')
                )
                stats['max_flow'] = flow_stats['max_flow']
                stats['avg_flow'] = flow_stats['avg_flow']
                
                # Get latest flow
                latest_flow_reading = flow_readings.order_by('-timestamp').first()
                if latest_flow_reading:
                    stats['latest_flow'] = latest_flow_reading.flow_rate
                    if not stats.get('latest_timestamp'):
                        stats['latest_timestamp'] = latest_flow_reading.timestamp
                
                # Create chart data
                flow_data = list(flow_readings.values('timestamp', 'flow_rate'))
                df_flow = pl.DataFrame(flow_data)
                
                flow_rate_chart = generate_line_chart(
                    df=df_flow,
                    title=f"Flow Rate History - {station.name}",
                    x_axis="Time",
                    y_axis="Flow Rate (l/s)"
                )
    
    # Context for template
    context = {
        'station': station,
        'readings': readings,
        'stats': stats,
        'active_warnings': active_warnings,
        'water_body': station.water_body,
        'time_range': time_range,
        'time_label': time_label,
        'now': now,
        'water_level_chart': water_level_chart,
        'flow_rate_chart': flow_rate_chart
    }
    
    return render(request, 'floods/station_detail.html', context)

def water_body_detail(request, water_body_id):
    """
    View for detailed information about a specific water body
    """
    # Get the water body
    water_body = get_object_or_404(WaterBody, pk=water_body_id)
    
    # Get all stations for this water body
    stations = water_body.stations.all().order_by('name')
    
    # Get current date and time
    now = timezone.now()
    
    # Get active warnings for this water body
    active_warnings = FloodWarning.objects.filter(
        water_body=water_body,
        is_active=True,
        end_time__gt=now
    ).order_by('-warning_level')
    
    # Get recent readings for all stations on this water body (last 24 hours)
    day_ago = now - timedelta(hours=24)
    recent_readings = WaterReading.objects.filter(
        station__in=stations,
        timestamp__gte=day_ago
    ).order_by('-timestamp')
    
    # Context for template
    context = {
        'water_body': water_body,
        'stations': stations,
        'active_warnings': active_warnings,
        'recent_readings': recent_readings,
        'now': now
    }
    
    return render(request, 'floods/water_body_detail.html', context)