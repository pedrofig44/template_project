from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Avg, Max, Min, Sum
from datetime import timedelta
import json
import polars as pl

from location.models import WeatherStation, City, Concelho
from climate.models import StationObservation, DailyForecast
from dashboard.utils import generate_line_chart, generate_bar_chart, generate_combined_chart

from django.core.serializers import serialize
from django.contrib.auth.decorators import login_required

@login_required
def temperature_dashboard(request):
    """
    Main temperature dashboard view showing temperature data across all stations
    """
    # Get all active weather stations
    stations = WeatherStation.objects.all().order_by('name')
    
    # Get selected station or default to first station
    selected_station_id = request.GET.get('station')
    if selected_station_id:
        selected_station = get_object_or_404(WeatherStation, station_id=selected_station_id)
    else:
        selected_station = stations.first()
        
    
    # Get the time range (default to last 24 hours)
    time_range = request.GET.get('range', '24h')
    
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
    
    # Get temperature data for the selected station
    temperature_data = None
    stats = {
        'avg_temp': None,
        'max_temp': None,
        'min_temp': None,
        'current_temp': None,
        'temp_trend': None,
    }
    
    if selected_station:
        # Get observations for the selected time range
        observations = StationObservation.objects.filter(
            station=selected_station,
            timestamp__gte=start_time,
            temperature__gt=-90  # Filter out invalid readings (-99)
        ).order_by('timestamp')
        
        if observations.exists():
            # Calculate stats
            stats_data = observations.aggregate(
                avg_temp=Avg('temperature'),
                max_temp=Max('temperature'),
                min_temp=Min('temperature')
            )
            
            stats['avg_temp'] = round(stats_data['avg_temp'], 1) if stats_data['avg_temp'] else None
            stats['max_temp'] = round(stats_data['max_temp'], 1) if stats_data['max_temp'] else None
            stats['min_temp'] = round(stats_data['min_temp'], 1) if stats_data['min_temp'] else None
            
            # Get current temperature (latest observation)
            latest_obs = observations.last()
            stats['current_temp'] = round(latest_obs.temperature, 1) if latest_obs else None
            
            # Calculate temperature trend (comparing to previous day's average)
            previous_day_start = start_time - timedelta(days=1)
            previous_day_avg = StationObservation.objects.filter(
                station=selected_station,
                timestamp__gte=previous_day_start,
                timestamp__lt=start_time,
                temperature__gt=-90
            ).aggregate(avg_temp=Avg('temperature'))['avg_temp']
            
            if previous_day_avg and stats['avg_temp']:
                diff = stats['avg_temp'] - previous_day_avg
                if diff > 0.5:
                    stats['temp_trend'] = 'rising'
                elif diff < -0.5:
                    stats['temp_trend'] = 'falling'
                else:
                    stats['temp_trend'] = 'stable'
                stats['temp_diff'] = round(diff, 1)
            
            # Convert to DataFrame for plotting
            if len(observations) > 0:
                # Convert directly to polars DataFrame
                data = list(observations.values('timestamp', 'temperature'))
                df_pl = pl.DataFrame(data)
                
                # Generate chart using dashboard utils
                chart_title = f"Temperature for {selected_station.name}"
                temperature_data = generate_line_chart(
                    df_pl, 
                    title=chart_title,
                    x_axis="Time", 
                    y_axis="Temperature (°C)"
                )
    
    # Get forecast data for comparison
    forecast_data = None
    if selected_station and selected_station.concelho:
        # Find a city in the same concelho
        city = City.objects.filter(concelho=selected_station.concelho).first()
        
        if city:
            # Get forecasts for the next few days
            forecasts = DailyForecast.objects.filter(
                city=city,
                forecast_date__gte=now.date()
            ).order_by('forecast_date')[:5]  # Next 5 days
            
            if forecasts.exists():
                # Prepare forecast data for the template
                forecast_data = []
                for forecast in forecasts:
                    forecast_data.append({
                        'date': forecast.forecast_date,
                        'min_temp': forecast.t_min,
                        'max_temp': forecast.t_max,
                        'forecast_item': forecast
                    })
                    
    
    # Prepare context
    context = {
        'stations': stations,
        'selected_station': selected_station,
        'time_range': time_range,
        'time_label': time_label,
        'temperature_data': temperature_data,
        'stats': stats,
        'forecast_data': forecast_data,
    }
    
    return render(request, 'climate/temperature_dashboard.html', context)

@login_required
def station_temperature_detail(request, station_id):
    """
    Detailed view for a specific weather station's temperature data
    """
    # Get the station
    station = get_object_or_404(WeatherStation, station_id=station_id)
    
    # Get time range (default to last 7 days)
    time_range = request.GET.get('range', '7d')
    
    # Calculate start time based on range
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
    elif time_range == '90d':
        start_time = now - timedelta(days=90)
        time_label = "Last 90 Days"
    else:
        start_time = now - timedelta(days=7)
        time_label = "Last 7 Days"
    
    # Get the observations
    observations = StationObservation.objects.filter(
        station=station,
        timestamp__gte=start_time,
        temperature__gt=-90  # Filter out invalid readings
    ).order_by('timestamp')
    
    # Calculate statistics
    stats = {}
    if observations.exists():
        # Basic stats
        stats_data = observations.aggregate(
            avg_temp=Avg('temperature'),
            max_temp=Max('temperature'),
            min_temp=Min('temperature')
        )
        
        stats = {
            'avg_temp': round(stats_data['avg_temp'], 1) if stats_data['avg_temp'] else None,
            'max_temp': round(stats_data['max_temp'], 1) if stats_data['max_temp'] else None,
            'min_temp': round(stats_data['min_temp'], 1) if stats_data['min_temp'] else None,
            'observation_count': observations.count(),
        }
        
        # Get latest temp
        latest_obs = observations.last()
        if latest_obs:
            stats['current_temp'] = round(latest_obs.temperature, 1)
            stats['current_time'] = latest_obs.timestamp
    
    # Generate temperature chart
    temperature_chart = None
    if observations.exists():
        # Convert directly to polars DataFrame
        data = list(observations.values('timestamp', 'temperature'))
        df_pl = pl.DataFrame(data)
        
        chart_title = f"Temperature History for {station.name}"
        temperature_chart = generate_line_chart(
            df_pl, 
            title=chart_title,
            x_axis="Date/Time", 
            y_axis="Temperature (°C)"
        )
    
    # Generate hourly averages for time-of-day analysis
    hourly_data = None
    if observations.count() > 24:
        # This would be a more complex query to get hourly averages
        # For this example, we'll skip the actual implementation
        # but in a real app, you'd aggregate by hour
        pass
    
    # Prepare context
    context = {
        'station': station,
        'time_range': time_range,
        'time_label': time_label,
        'stats': stats,
        'temperature_chart': temperature_chart,
        'hourly_data': hourly_data
    }
    
    return render(request, 'climate/station_temperature_detail.html', context)

@login_required
def temperature_chart_data(request):
    """
    API endpoint to get temperature chart data for AJAX requests
    """
    station_id = request.GET.get('station')
    time_range = request.GET.get('range', '24h')
    
    # Validate input
    if not station_id:
        return JsonResponse({'error': 'Station ID is required'}, status=400)
    
    # Get station
    try:
        station = WeatherStation.objects.get(station_id=station_id)
    except WeatherStation.DoesNotExist:
        return JsonResponse({'error': 'Station not found'}, status=404)
    
    # Calculate time range
    now = timezone.now()
    if time_range == '24h':
        start_time = now - timedelta(hours=24)
    elif time_range == '48h':
        start_time = now - timedelta(hours=48)
    elif time_range == '7d':
        start_time = now - timedelta(days=7)
    elif time_range == '30d':
        start_time = now - timedelta(days=30)
    else:
        start_time = now - timedelta(hours=24)
    
    # Get observations
    observations = StationObservation.objects.filter(
        station=station,
        timestamp__gte=start_time,
        temperature__gt=-90
    ).order_by('timestamp')
    
    # Prepare data for chart
    chart_data = {
        'timestamps': [],
        'temperatures': []
    }
    
    for obs in observations:
        chart_data['timestamps'].append(obs.timestamp.isoformat())
        chart_data['temperatures'].append(round(obs.temperature, 1))
    
    return JsonResponse(chart_data)

@login_required
def station_location_data(request, station_id):
    """Return GeoJSON for a specific weather station"""
    try:
        station = WeatherStation.objects.get(station_id=station_id)
        
        # If the station has a location field (Point)
        if station.location:
            # Create GeoJSON feature
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [station.location.x, station.location.y]  # [longitude, latitude]
                },
                "properties": {
                    "name": station.name,
                    "id": station.station_id,
                    "concelho": station.concelho.name,
                }
            }
            
            # Return as GeoJSON
            return JsonResponse({
                "type": "FeatureCollection",
                "features": [feature]
            })
        else:
            # If no location field, try to get coordinates another way
            # Assuming you might have latitude/longitude directly on the model
            lat = getattr(station, 'latitude', None)
            lng = getattr(station, 'longitude', None)
            
            if lat and lng:
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lng, lat]  # [longitude, latitude]
                    },
                    "properties": {
                        "name": station.name,
                        "id": station.station_id,
                        "concelho": station.concelho.name,
                    }
                }
                
                return JsonResponse({
                    "type": "FeatureCollection",
                    "features": [feature]
                })
            
            # If no coordinates available
            return JsonResponse({
                "type": "FeatureCollection",
                "features": []
            })
    except WeatherStation.DoesNotExist:
        return JsonResponse({
            "type": "FeatureCollection",
            "features": []
        })

@login_required
def wind_dashboard(request):
    """
    Main wind dashboard view showing wind data across all stations
    """
    # Get all active weather stations
    stations = WeatherStation.objects.all().order_by('name')
    
    # Get selected station or default to first station
    selected_station_id = request.GET.get('station')
    if selected_station_id:
        selected_station = get_object_or_404(WeatherStation, station_id=selected_station_id)
    else:
        selected_station = stations.first()
        
    # Get the time range (default to last 24 hours)
    time_range = request.GET.get('range', '24h')
    
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
    
    # Get wind data for the selected station
    wind_data = None
    stats = {
        'avg_speed': None,
        'max_speed': None,
        'min_speed': None,
        'current_speed': None,
        'current_direction': None,
        'direction_text': None,
        'wind_trend': None,
    }
    
    wind_rose_data = None
    
    if selected_station:
        # Get observations for the selected time range
        observations = StationObservation.objects.filter(
            station=selected_station,
            timestamp__gte=start_time,
            wind_speed_kmh__gt=-90  # Filter out invalid readings (-99)
        ).order_by('timestamp')
        
        if observations.exists():
            # Calculate stats
            stats_data = observations.aggregate(
                avg_speed=Avg('wind_speed_kmh'),
                max_speed=Max('wind_speed_kmh'),
                min_speed=Min('wind_speed_kmh')
            )
            
            stats['avg_speed'] = round(stats_data['avg_speed'], 1) if stats_data['avg_speed'] else None
            stats['max_speed'] = round(stats_data['max_speed'], 1) if stats_data['max_speed'] else None
            stats['min_speed'] = round(stats_data['min_speed'], 1) if stats_data['min_speed'] else None
            
            # Get current wind (latest observation)
            latest_obs = observations.last()
            if latest_obs:
                stats['current_speed'] = round(latest_obs.wind_speed_kmh, 1)
                stats['current_direction'] = latest_obs.wind_direction
                # Map wind direction code to text
                direction_map = {
                    0: 'No Direction',
                    1: 'North', 
                    2: 'Northeast', 
                    3: 'East',
                    4: 'Southeast', 
                    5: 'South', 
                    6: 'Southwest',
                    7: 'West', 
                    8: 'Northwest', 
                    9: 'North'
                }
                stats['direction_text'] = direction_map.get(latest_obs.wind_direction, 'Unknown')
            
            # Calculate wind trend (comparing to previous day's average)
            previous_day_start = start_time - timedelta(days=1)
            previous_day_avg = StationObservation.objects.filter(
                station=selected_station,
                timestamp__gte=previous_day_start,
                timestamp__lt=start_time,
                wind_speed_kmh__gt=-90
            ).aggregate(avg_speed=Avg('wind_speed_kmh'))['avg_speed']
            
            if previous_day_avg and stats['avg_speed']:
                diff = stats['avg_speed'] - previous_day_avg
                if diff > 1.0:
                    stats['wind_trend'] = 'increasing'
                elif diff < -1.0:
                    stats['wind_trend'] = 'decreasing'
                else:
                    stats['wind_trend'] = 'stable'
                stats['wind_diff'] = round(diff, 1)
            
            # Convert to DataFrame for plotting
            if len(observations) > 0:
                # Convert directly to polars DataFrame
                data = list(observations.values('timestamp', 'wind_speed_kmh'))
                df_pl = pl.DataFrame(data)
                
                # Generate chart using dashboard utils
                chart_title = f"Wind Speed for {selected_station.name}"
                wind_data = generate_line_chart(
                    df_pl, 
                    title=chart_title,
                    x_axis="Time", 
                    y_axis="Wind Speed (km/h)"
                )
                
                # Create wind rose data
                # Count occurrences of each wind direction
                direction_counts = {}
                for obs in observations:
                    dir_key = obs.wind_direction
                    if dir_key not in direction_counts:
                        direction_counts[dir_key] = 0
                    direction_counts[dir_key] += 1
                
                # Prepare data for wind rose chart
                wind_rose_trace = {
                    "type": "barpolar",
                    "r": [],
                    "theta": [],
                    "name": "Wind Direction",
                    "marker": {"color": "#1E88E5"}
                }
                
                for dir_code, count in direction_counts.items():
                    if dir_code != 0:  # Skip "No Direction"
                        # Convert direction code to degrees
                        degrees = (dir_code - 1) * 45
                        wind_rose_trace["theta"].append(degrees)
                        wind_rose_trace["r"].append(count)
                
                # Create wind rose layout
                wind_rose_layout = {
                    "title": "Wind Direction Distribution",
                    "font": {"size": 12},
                    "polar": {
                        "radialaxis": {"visible": True, "showticklabels": True},
                        "angularaxis": {
                            "tickmode": "array",
                            "tickvals": [0, 45, 90, 135, 180, 225, 270, 315],
                            "ticktext": ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
                        }
                    },
                    "showlegend": False
                }
                
                # Convert to JSON for template
                wind_rose_data = json.dumps({
                    "data": [wind_rose_trace],
                    "layout": wind_rose_layout
                })
    
    # Prepare context
    context = {
        'stations': stations,
        'selected_station': selected_station,
        'time_range': time_range,
        'time_label': time_label,
        'wind_data': wind_data,
        'wind_rose_data': wind_rose_data,
        'stats': stats,
    }
    
    return render(request, 'climate/wind_dashboard.html', context)

@login_required
def station_wind_detail(request, station_id):
    """
    Detailed view for a specific weather station's wind data
    """
    # Get the station
    station = get_object_or_404(WeatherStation, station_id=station_id)
    
    # Get time range (default to last 7 days)
    time_range = request.GET.get('range', '7d')
    
    # Calculate start time based on range
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
    elif time_range == '90d':
        start_time = now - timedelta(days=90)
        time_label = "Last 90 Days"
    else:
        start_time = now - timedelta(days=7)
        time_label = "Last 7 Days"
    
    # Get the observations
    observations = StationObservation.objects.filter(
        station=station,
        timestamp__gte=start_time,
        wind_speed_kmh__gt=-90  # Filter out invalid readings
    ).order_by('timestamp')
    
    # Calculate statistics
    stats = {}
    if observations.exists():
        # Basic stats
        stats_data = observations.aggregate(
            avg_speed=Avg('wind_speed_kmh'),
            max_speed=Max('wind_speed_kmh'),
            min_speed=Min('wind_speed_kmh')
        )
        
        stats = {
            'avg_speed': round(stats_data['avg_speed'], 1) if stats_data['avg_speed'] else None,
            'max_speed': round(stats_data['max_speed'], 1) if stats_data['max_speed'] else None,
            'min_speed': round(stats_data['min_speed'], 1) if stats_data['min_speed'] else None,
            'observation_count': observations.count(),
        }
        
        # Get latest wind data
        latest_obs = observations.last()
        if latest_obs:
            stats['current_speed'] = round(latest_obs.wind_speed_kmh, 1)
            stats['current_direction'] = latest_obs.wind_direction
            # Map wind direction code to text
            direction_map = {
                0: 'No Direction',
                1: 'North', 
                2: 'Northeast', 
                3: 'East',
                4: 'Southeast', 
                5: 'South', 
                6: 'Southwest',
                7: 'West', 
                8: 'Northwest', 
                9: 'North'
            }
            stats['direction_text'] = direction_map.get(latest_obs.wind_direction, 'Unknown')
            stats['current_time'] = latest_obs.timestamp
    
    # Generate wind speed chart
    wind_chart = None
    if observations.exists():
        # Convert directly to polars DataFrame
        data = list(observations.values('timestamp', 'wind_speed_kmh'))
        df_pl = pl.DataFrame(data)
        
        chart_title = f"Wind Speed History for {station.name}"
        wind_chart = generate_line_chart(
            df_pl, 
            title=chart_title,
            x_axis="Date/Time", 
            y_axis="Wind Speed (km/h)"
        )
    
    # Generate wind direction distribution
    wind_rose_data = None
    if observations.count() > 0:
        # Count occurrences of each wind direction
        direction_counts = {}
        for obs in observations:
            dir_key = obs.wind_direction
            if dir_key not in direction_counts:
                direction_counts[dir_key] = 0
            direction_counts[dir_key] += 1
        
        # Prepare data for wind rose chart
        wind_rose_trace = {
            "type": "barpolar",
            "r": [],
            "theta": [],
            "name": "Wind Direction",
            "marker": {"color": "#1E88E5"}
        }
        
        for dir_code, count in direction_counts.items():
            if dir_code != 0:  # Skip "No Direction"
                # Convert direction code to degrees
                degrees = (dir_code - 1) * 45
                wind_rose_trace["theta"].append(degrees)
                wind_rose_trace["r"].append(count)
        
        # Create wind rose layout
        wind_rose_layout = {
            "title": "Wind Direction Distribution",
            "font": {"size": 12},
            "polar": {
                "radialaxis": {"visible": True, "showticklabels": True},
                "angularaxis": {
                    "tickmode": "array",
                    "tickvals": [0, 45, 90, 135, 180, 225, 270, 315],
                    "ticktext": ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
                }
            },
            "showlegend": False
        }
        
        # Convert to JSON for template
        wind_rose_data = json.dumps({
            "data": [wind_rose_trace],
            "layout": wind_rose_layout
        })
    
    # Generate hourly averages for time-of-day analysis
    hourly_wind_data = None
    if observations.count() > 24:
        # This would be a more complex query to get hourly averages
        # For this example, we'll just indicate this would contain the hourly data
        pass
    
    # Prepare context
    context = {
        'station': station,
        'time_range': time_range,
        'time_label': time_label,
        'stats': stats,
        'wind_chart': wind_chart,
        'wind_rose_data': wind_rose_data,
        'hourly_wind_data': hourly_wind_data
    }
    
    return render(request, 'climate/station_wind_detail.html', context)

@login_required
def wind_chart_data(request):
    """
    API endpoint to get wind chart data for AJAX requests
    """
    station_id = request.GET.get('station')
    time_range = request.GET.get('range', '24h')
    
    # Validate input
    if not station_id:
        return JsonResponse({'error': 'Station ID is required'}, status=400)
    
    # Get station
    try:
        station = WeatherStation.objects.get(station_id=station_id)
    except WeatherStation.DoesNotExist:
        return JsonResponse({'error': 'Station not found'}, status=404)
    
    # Calculate time range
    now = timezone.now()
    if time_range == '24h':
        start_time = now - timedelta(hours=24)
    elif time_range == '48h':
        start_time = now - timedelta(hours=48)
    elif time_range == '7d':
        start_time = now - timedelta(days=7)
    elif time_range == '30d':
        start_time = now - timedelta(days=30)
    else:
        start_time = now - timedelta(hours=24)
    
    # Get observations
    observations = StationObservation.objects.filter(
        station=station,
        timestamp__gte=start_time,
        wind_speed_kmh__gt=-90
    ).order_by('timestamp')
    
    # Prepare data for chart
    chart_data = {
        'timestamps': [],
        'wind_speeds': [],
        'directions': []
    }
    
    for obs in observations:
        chart_data['timestamps'].append(obs.timestamp.isoformat())
        chart_data['wind_speeds'].append(round(obs.wind_speed_kmh, 1))
        chart_data['directions'].append(obs.wind_direction)
    
    return JsonResponse(chart_data)

@login_required
def precipitation_dashboard(request):
    """
    Main precipitation dashboard view showing precipitation data across all stations
    """
    # Get all active weather stations
    stations = WeatherStation.objects.all().order_by('name')
    
    # Get selected station or default to first station
    selected_station_id = request.GET.get('station')
    if selected_station_id:
        selected_station = get_object_or_404(WeatherStation, station_id=selected_station_id)
    else:
        selected_station = stations.first()
        
    # Get the time range (default to last 7 days for precipitation, as it's less frequent than temperature)
    time_range = request.GET.get('range', '7d')
    
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
        start_time = now - timedelta(days=7)
        time_label = "Last 7 Days"
    
    # Get precipitation data for the selected station
    precipitation_data = None
    stats = {
        'total_precip': None,
        'max_precip': None,
        'avg_precip': None,
        'rainy_days': None,
        'current_precip': None,
        'precip_trend': None,
    }
    
    if selected_station:
        # Get observations for the selected time range
        observations = StationObservation.objects.filter(
            station=selected_station,
            timestamp__gte=start_time,
            precipitation__gt=-90  # Filter out invalid readings (-99)
        ).order_by('timestamp')
        
        if observations.exists():
            # Calculate stats
            stats_data = observations.aggregate(
                avg_precip=Avg('precipitation'),
                max_precip=Max('precipitation'),
                total_precip=Sum('precipitation')
            )
            
            stats['avg_precip'] = round(stats_data['avg_precip'], 1) if stats_data['avg_precip'] else None
            stats['max_precip'] = round(stats_data['max_precip'], 1) if stats_data['max_precip'] else None
            stats['total_precip'] = round(stats_data['total_precip'], 1) if stats_data['total_precip'] else None
            
            # Count rainy days (days with precipitation > 0.1mm)
            # Group by date and count days with precipitation
            rainy_days = observations.filter(precipitation__gt=0.1).dates('timestamp', 'day').count()
            stats['rainy_days'] = rainy_days
            
            # Get current precipitation (latest observation)
            latest_obs = observations.last()
            stats['current_precip'] = round(latest_obs.precipitation, 1) if latest_obs else None
            
            # Calculate precipitation trend (comparing to previous period's total)
            previous_period_start = start_time - (start_time - now)  # Same duration as current period
            previous_period_total = StationObservation.objects.filter(
                station=selected_station,
                timestamp__gte=previous_period_start,
                timestamp__lt=start_time,
                precipitation__gt=-90
            ).aggregate(total=Sum('precipitation'))['total']
            
            if previous_period_total and stats['total_precip']:
                diff = stats['total_precip'] - previous_period_total
                if diff > 1.0:
                    stats['precip_trend'] = 'increasing'
                elif diff < -1.0:
                    stats['precip_trend'] = 'decreasing'
                else:
                    stats['precip_trend'] = 'stable'
                stats['precip_diff'] = round(diff, 1)
            
            # Convert to DataFrame for plotting
            if len(observations) > 0:
                # For precipitation, a bar chart might be more appropriate
                data = list(observations.values('timestamp', 'precipitation'))
                df_pl = pl.DataFrame(data)
                
                # Generate bar chart using dashboard utils
                chart_title = f"Precipitation for {selected_station.name}"
                precipitation_data = generate_bar_chart(
                    df_pl, 
                    title=chart_title,
                    x_axis="Time", 
                    y_axis="Precipitation (mm)"
                )
    
    # Get forecast data for comparison
    forecast_data = None
    if selected_station and selected_station.concelho:
        # Find a city in the same concelho
        city = City.objects.filter(concelho=selected_station.concelho).first()
        
        if city:
            # Get forecasts for the next few days
            forecasts = DailyForecast.objects.filter(
                city=city,
                forecast_date__gte=now.date()
            ).order_by('forecast_date')[:5]  # Next 5 days
            
            if forecasts.exists():
                # Prepare forecast data for the template
                forecast_data = []
                for forecast in forecasts:
                    forecast_data.append({
                        'date': forecast.forecast_date,
                        'precipita_prob': forecast.precipita_prob,
                        'forecast_item': forecast
                    })
    
    # Prepare context
    context = {
        'stations': stations,
        'selected_station': selected_station,
        'time_range': time_range,
        'time_label': time_label,
        'precipitation_data': precipitation_data,
        'stats': stats,
        'forecast_data': forecast_data,
    }
    
    return render(request, 'climate/precipitation_dashboard.html', context)

@login_required
def station_precipitation_detail(request, station_id):
    """
    Detailed view for a specific weather station's precipitation data
    """
    # Get the station
    station = get_object_or_404(WeatherStation, station_id=station_id)
    
    # Get time range (default to last 30 days for precipitation details)
    time_range = request.GET.get('range', '30d')
    
    # Calculate start time based on range
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
    elif time_range == '90d':
        start_time = now - timedelta(days=90)
        time_label = "Last 90 Days"
    else:
        start_time = now - timedelta(days=30)
        time_label = "Last 30 Days"
    
    # Get the observations
    observations = StationObservation.objects.filter(
        station=station,
        timestamp__gte=start_time,
        precipitation__gt=-90  # Filter out invalid readings
    ).order_by('timestamp')
    
    # Calculate statistics
    stats = {}
    if observations.exists():
        # Basic stats
        stats_data = observations.aggregate(
            avg_precip=Avg('precipitation'),
            max_precip=Max('precipitation'),
            total_precip=Sum('precipitation')
        )
        
        stats = {
            'avg_precip': round(stats_data['avg_precip'], 1) if stats_data['avg_precip'] else None,
            'max_precip': round(stats_data['max_precip'], 1) if stats_data['max_precip'] else None,
            'total_precip': round(stats_data['total_precip'], 1) if stats_data['total_precip'] else None,
            'observation_count': observations.count(),
            'rainy_days': observations.filter(precipitation__gt=0.1).dates('timestamp', 'day').count()
        }
        
        # Get latest precipitation
        latest_obs = observations.last()
        if latest_obs:
            stats['current_precip'] = round(latest_obs.precipitation, 1)
            stats['current_time'] = latest_obs.timestamp
    
    # Generate precipitation charts
    precipitation_chart = None
    daily_accumulation_chart = None
    
    if observations.exists():
        # Convert directly to polars DataFrame for the main chart
        data = list(observations.values('timestamp', 'precipitation'))
        df_pl = pl.DataFrame(data)
        
        chart_title = f"Precipitation History for {station.name}"
        precipitation_chart = generate_bar_chart(
            df_pl, 
            title=chart_title,
            x_axis="Date/Time", 
            y_axis="Precipitation (mm)"
        )
        
        # Create daily accumulation data (sum precipitation by day)
        # This is best done with Django's database aggregation
        daily_data = observations.values('timestamp__date').annotate(
            daily_sum=Sum('precipitation')
        ).order_by('timestamp__date')
        
        # Convert to polars DataFrame for the daily accumulation chart
        if daily_data:
            daily_list = [
                {'timestamp': item['timestamp__date'], 'daily_precip': item['daily_sum']} 
                for item in daily_data
            ]
            df_daily = pl.DataFrame(daily_list)
            
            daily_chart_title = f"Daily Precipitation for {station.name}"
            daily_accumulation_chart = generate_bar_chart(
                df_daily,
                title=daily_chart_title,
                x_axis="Date",
                y_axis="Daily Precipitation (mm)"
            )
    
    # Generate monthly precipitation patterns (optional, for longer time ranges)
    monthly_pattern = None
    if time_range in ['90d', '30d'] and observations.exists():
        # This would aggregate precipitation by month
        # Implementation depends on the specific visualization needs
        pass
    
    # Prepare context
    context = {
        'station': station,
        'time_range': time_range,
        'time_label': time_label,
        'stats': stats,
        'precipitation_chart': precipitation_chart,
        'daily_accumulation_chart': daily_accumulation_chart,
        'monthly_pattern': monthly_pattern
    }
    
    return render(request, 'climate/station_precipitation_detail.html', context)

@login_required
def precipitation_chart_data(request):
    """
    API endpoint to get precipitation chart data for AJAX requests
    """
    station_id = request.GET.get('station')
    time_range = request.GET.get('range', '7d')
    
    # Validate input
    if not station_id:
        return JsonResponse({'error': 'Station ID is required'}, status=400)
    
    # Get station
    try:
        station = WeatherStation.objects.get(station_id=station_id)
    except WeatherStation.DoesNotExist:
        return JsonResponse({'error': 'Station not found'}, status=404)
    
    # Calculate time range
    now = timezone.now()
    if time_range == '24h':
        start_time = now - timedelta(hours=24)
    elif time_range == '48h':
        start_time = now - timedelta(hours=48)
    elif time_range == '7d':
        start_time = now - timedelta(days=7)
    elif time_range == '30d':
        start_time = now - timedelta(days=30)
    else:
        start_time = now - timedelta(days=7)
    
    # Get observations
    observations = StationObservation.objects.filter(
        station=station,
        timestamp__gte=start_time,
        precipitation__gt=-90
    ).order_by('timestamp')
    
    # Prepare data for chart
    chart_data = {
        'timestamps': [],
        'precipitation': []
    }
    
    for obs in observations:
        chart_data['timestamps'].append(obs.timestamp.isoformat())
        chart_data['precipitation'].append(round(obs.precipitation, 1))
    
    return JsonResponse(chart_data)