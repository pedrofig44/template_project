from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta, datetime

from location.models import City, WeatherStation, Concelho
from climate.models import DailyForecast, StationObservation, WeatherWarning, FireRisk

def main_dashboard_view(request):
    """
    Main dashboard view displaying current weather, forecasts, warnings
    """
    # Get location from request parameters or default to a fallback city
    location_id = request.GET.get('location')
    view_type = request.GET.get('view', 'summary')

    # Default to fallback location if no location specified
    try:
        if location_id:
            current_city = get_object_or_404(City, global_id=location_id)
            location_name = current_city.name  # Ensure location_name is set from the current_city
        else:
            # Default to Lisboa or first city in database
            current_city = City.objects.filter(name__iexact='Lisboa').first() or City.objects.first()
            location_id = current_city.global_id if current_city else None
            location_name = current_city.name if current_city else 'Lisboa'  # Set default location_name
    except Exception as e:
        # If there's any error, use a default name for display purposes
        current_city = None
        location_name = 'Lisboa'  # Ensure location_name is still set even if there's an error
    
    # Get available cities for the dropdown menu
    available_cities = City.objects.all().order_by('name')[:20]  # Limit to 20 cities
    
    # Get current date and time
    current_date = timezone.now()
    
    # FETCH WEATHER DATA
    
    # 1. Current Weather
    weather_data = {}
    try:
        if current_city:
            # Get the closest weather station to this city
            station = WeatherStation.objects.filter(
                concelho__dico_code=current_city.concelho.dico_code
            ).first()
            
            if station:
                # Get most recent observation
                latest_observation = StationObservation.objects.filter(
                    station=station
                ).order_by('-timestamp').first()
                
                if latest_observation:
                    # Map weather type from temperature and humidity
                    weather_type = 'clear'
                    description = 'Clear Sky'
                    
                    if latest_observation.precipitation > 0.5:
                        weather_type = 'rain'
                        description = 'Rainy'
                    elif latest_observation.humidity > 80:
                        weather_type = 'cloudy'
                        description = 'Cloudy'
                    elif latest_observation.humidity > 60:
                        weather_type = 'partly_cloudy'
                        description = 'Partly Cloudy'
                    
                    # Get wind direction as a string
                    wind_directions = {
                        0: 'No Direction', 1: 'North', 2: 'Northeast',
                        3: 'East', 4: 'Southeast', 5: 'South',
                        6: 'Southwest', 7: 'West', 8: 'Northwest', 9: 'North'
                    }
                    wind_direction = wind_directions.get(latest_observation.wind_direction, 'Unknown')
                    
                    # Create weather data dictionary
                    weather_data = {
                        'temperature': round(latest_observation.temperature, 1),
                        'humidity': round(latest_observation.humidity),
                        'wind_speed': round(latest_observation.wind_speed_kmh),
                        'wind_direction': wind_direction,
                        'precipitation_prob': round((latest_observation.precipitation > 0) * 100),
                        'pressure': latest_observation.pressure or 1013,
                        'weather_type': weather_type,
                        'description': description,
                        'last_update': latest_observation.timestamp
                    }
                    
                    # Try to get forecast for today to get min/max temperature
                    today_forecast = DailyForecast.objects.filter(
                        city=current_city,
                        forecast_date=current_date.date()
                    ).first()
                    
                    if today_forecast:
                        weather_data['temp_min'] = round(today_forecast.t_min)
                        weather_data['temp_max'] = round(today_forecast.t_max)
                    else:
                        # Estimate min/max from current temperature
                        weather_data['temp_min'] = round(latest_observation.temperature * 0.85)
                        weather_data['temp_max'] = round(latest_observation.temperature * 1.15)
    except Exception as e:
        # If there's an error, we'll keep the empty weather_data dictionary
        pass
    
    # 2. Weather Forecasts
    forecast_data = []
    try:
        if current_city:
            # Get forecasts for the next 5 days
            today = current_date.date()
            forecasts = DailyForecast.objects.filter(
                city=current_city,
                forecast_date__gte=today,
                forecast_date__lte=today + timedelta(days=5)
            ).order_by('forecast_date')
            
            # Weather type mappings (this would be more complete in a real app)
            weather_type_map = {
                1: {'type': 'clear', 'description': 'Clear Sky'},
                2: {'type': 'partly_cloudy', 'description': 'Partly Cloudy'},
                3: {'type': 'cloudy', 'description': 'Cloudy'},
                4: {'type': 'rain', 'description': 'Light Rain'},
                5: {'type': 'rain', 'description': 'Rain'},
                6: {'type': 'rain', 'description': 'Heavy Rain'},
                7: {'type': 'thunderstorm', 'description': 'Thunderstorm'},
                # Add more mappings as needed
            }
            
            # Process each forecast
            for forecast in forecasts:
                # Map the weather type
                weather_info = weather_type_map.get(
                    forecast.weather_type, 
                    {'type': 'partly_cloudy', 'description': 'Mixed Conditions'}
                )
                
                # Build forecast item
                forecast_item = {
                    'date': forecast.forecast_date,
                    'temp_min': round(forecast.t_min),
                    'temp_max': round(forecast.t_max),
                    'precipitation_prob': round(forecast.precipita_prob),
                    'wind_speed': round(forecast.wind_speed_class * 5),  # Simple conversion from class to km/h
                    'wind_direction': forecast.wind_dir,
                    'weather_type': weather_info['type'],
                    'description': weather_info['description']
                }
                
                forecast_data.append(forecast_item)
    except Exception as e:
        # If there's an error, we'll keep the empty forecast_data list
        pass
    
    # 3. Fire Risk
    fire_risk = {
        'level': 1,
        'description': 'Reduced Risk'
    }
    try:
        if current_city:
            # Get fire risk for this concelho
            risk = FireRisk.objects.filter(
                concelho=current_city.concelho,
                forecast_day=0  # Today
            ).first()
            
            if risk:
                risk_descriptions = {
                    1: 'Reduced Risk',
                    2: 'Moderate Risk',
                    3: 'High Risk',
                    4: 'Very High Risk',
                    5: 'Maximum Risk'
                }
                
                fire_risk = {
                    'level': risk.risk_level,
                    'description': risk_descriptions.get(risk.risk_level, 'Unknown Risk')
                }
    except Exception as e:
        # If there's an error, we'll keep the default fire_risk
        pass
    
    # 4. Weather Warnings
    warnings = []
    try:
        if current_city:
            # Get active warnings for this city, excluding green level warnings
            current_time = timezone.now()
            
            # First try to get warnings directly linked to the city
            active_warnings = WeatherWarning.objects.filter(
                city=current_city,
                end_time__gt=current_time
            ).exclude(
                awareness_level='green'  # Exclude green level warnings
            ).order_by('-awareness_level', 'end_time')
            
            # If no warnings found directly linked to the city, fallback to area_code matching
            if not active_warnings.exists():
                active_warnings = WeatherWarning.objects.filter(
                    area_code=current_city.ipma_area_code,
                    end_time__gt=current_time
                ).exclude(
                    awareness_level='green'  # Exclude green level warnings
                ).order_by('-awareness_level', 'end_time')
            
            # Define warning level colors
            level_colors = {
                'yellow': 'warning',
                'orange': 'danger',
                'red': 'danger'
            }
            
            for warning in active_warnings:
                warnings.append({
                    'type': warning.awareness_type,
                    'level': warning.awareness_level,
                    'color': level_colors.get(warning.awareness_level, 'warning'),
                    'description': warning.description,
                    'area': warning.area_code,
                    'start_time': warning.start_time,
                    'end_time': warning.end_time
                })
    except Exception as e:
        # If there's an error, we'll keep the empty warnings list
        pass
    
    # Prepare context with all the data
    context = {
        'location_name': location_name,
        'current_location_id': current_city.global_id if current_city else '',
        'available_cities': available_cities,
        'current_date': current_date,
        'weather_data': weather_data,
        'forecast_data': forecast_data,
        'fire_risk': fire_risk,
        'warnings': warnings,
        'air_quality': {
            'index': 2,
            'description': 'Good',
            'message': 'Air quality is satisfactory, and air pollution poses little or no risk.'
        },
        'uv_index': {
            'value': 5,
            'description': 'Moderate',
            'recommendation': 'Take precautions - cover up and wear sunscreen'
        },
        'pollen': {
            'level': 2,
            'description': 'Medium',
            'message': 'Moderate pollen levels may cause symptoms for people with pollen allergies.'
        },
        'climate_summary': {
            'avg_temp': 21.5,
            'max_temp': 28.3,
            'min_temp': 14.7,
            'normal_temp_range': '15-26',
            'monthly_precip': 45.2,
            'rainy_days': 7,
            'max_daily_precip': 12.5,
            'normal_monthly_precip': 48,
            'avg_wind': 12.3,
            'max_wind': 32.7,
            'predom_wind_dir': 'North',
            'calm_days': 3,
            'temp_diff': 1.2,
            'precip_diff': -10.8,
            'wind_diff': 0.5,
            'temp_trend': 'increasing',
            'temp_trend_value': 0.8,
            'precip_trend': 'decreasing',
            'precip_trend_value': 12,
            'extreme_events': 'Increasing frequency of heat waves'
        }
    }
    
    # Handle HTMX partial responses
    if request.headers.get('HX-Request') == 'true':
        if location_id:
            # Location changed, return the full dashboard content
            return render(request, 'dashboard/main_dashboard_content.html', context)
        elif view_type == 'summary':
            return render(request, 'dashboard/summary_partial.html', context)
        elif view_type == 'alerts':
            return render(request, 'dashboard/alerts_partial.html', context)
        else:
            return render(request, 'dashboard/main_dashboard_content.html', context)
    
    # Render full template
    return render(request, 'dashboard/main_dashboard.html', context)

def index_dashboard_view(request):
    """Legacy dashboard view kept for compatibility"""
    return render(request, 'dashboard/index_dashboard.html')