# wildfires/views.py
from django.shortcuts import render, get_object_or_404
from .models import YearlyWildfireSummary
from location.models import Concelho
from django.db.models import Sum, Avg, Max, Min, Count
from django.utils import timezone
import polars as pl
import json
from dashboard.utils import generate_line_chart, generate_pie_chart 
from location.models import Distrito, Concelho, WeatherStation
from climate.models import FireRisk, StationObservation

from datetime import timedelta

from django.conf import settings

def wildfire_dashboard(request):
    """
    Wildfire dashboard view showing yearly wildfire statistics by concelho
    """
    # Get the current year
    # current_year = timezone.now().year
    # Use 2023 as default year since there's no data for 2024/2025
    current_year = 2023
    
    # Get selected concelho or default to first concelho with data
    concelho_id = request.GET.get('concelho')
    
    if concelho_id:
        selected_concelho = get_object_or_404(Concelho, dico_code=concelho_id)
    else:
        # Find a concelho with data, or default to first concelho
        concelho_with_data = YearlyWildfireSummary.objects.filter(year=current_year).first()
        if concelho_with_data:
            selected_concelho = concelho_with_data.concelho
        else:
            selected_concelho = Concelho.objects.first()
    
    # Get all concelhos for the dropdown
    all_concelhos = Concelho.objects.all().order_by('name')
    
    # Get yearly data for the selected concelho
    yearly_data = YearlyWildfireSummary.objects.filter(
        concelho=selected_concelho
    ).order_by('-year')
    
    # Get current year and previous year data
    current_year_data = yearly_data.filter(year=current_year).first()
    prev_year_data = yearly_data.filter(year=current_year-1).first()
    
    # Calculate the comparison with previous year
    comparison = {}
    if current_year_data and prev_year_data:
        comparison = {
            'total_fires': {
                'value': current_year_data.total_fires - prev_year_data.total_fires,
                'percent': (current_year_data.total_fires - prev_year_data.total_fires) / prev_year_data.total_fires * 100 if prev_year_data.total_fires else 0
            },
            'total_area_ha': {
                'value': current_year_data.total_area_ha - prev_year_data.total_area_ha,
                'percent': (current_year_data.total_area_ha - prev_year_data.total_area_ha) / prev_year_data.total_area_ha * 100 if prev_year_data.total_area_ha else 0
            },
            'forest_area_ha': {
                'value': current_year_data.forest_area_ha - prev_year_data.forest_area_ha,
                'percent': (current_year_data.forest_area_ha - prev_year_data.forest_area_ha) / prev_year_data.forest_area_ha * 100 if prev_year_data.forest_area_ha else 0
            },
            'shrub_area_ha': {
                'value': current_year_data.shrub_area_ha - prev_year_data.shrub_area_ha,
                'percent': (current_year_data.shrub_area_ha - prev_year_data.shrub_area_ha) / prev_year_data.shrub_area_ha * 100 if prev_year_data.shrub_area_ha else 0
            },
            'agric_area_ha': {
                'value': current_year_data.agric_area_ha - prev_year_data.agric_area_ha,
                'percent': (current_year_data.agric_area_ha - prev_year_data.agric_area_ha) / prev_year_data.agric_area_ha * 100 if prev_year_data.agric_area_ha else 0
            },
            'avg_duration_hours': {
                'value': current_year_data.avg_duration_hours - prev_year_data.avg_duration_hours,
                'percent': (current_year_data.avg_duration_hours - prev_year_data.avg_duration_hours) / prev_year_data.avg_duration_hours * 100 if prev_year_data.avg_duration_hours else 0
            },
            'fires_over_24h': {
                'value': current_year_data.fires_over_24h - prev_year_data.fires_over_24h,
                'percent': (current_year_data.fires_over_24h - prev_year_data.fires_over_24h) / prev_year_data.fires_over_24h * 100 if prev_year_data.fires_over_24h else 0
            },
            'max_fire_size_ha': {
                'value': current_year_data.max_fire_size_ha - prev_year_data.max_fire_size_ha,
                'percent': (current_year_data.max_fire_size_ha - prev_year_data.max_fire_size_ha) / prev_year_data.max_fire_size_ha * 100 if prev_year_data.max_fire_size_ha else 0
            },
        }
    
    # Generate historical trend charts using Polars and the utility function
    historical_charts = {}
    
    if yearly_data.exists():
        # Convert to list of dicts for easier manipulation with Polars
        yearly_data_list = list(yearly_data.values('year', 'total_fires', 'total_area_ha', 
                                                  'forest_area_ha', 'shrub_area_ha', 
                                                  'agric_area_ha', 'avg_duration_hours',
                                                  'fires_over_24h', 'max_fire_size_ha'))
        
        # Create Polars DataFrame
        df = pl.DataFrame(yearly_data_list)
        
        # Generate charts
        if not df.is_empty():
            # Total fires over years chart
            # Total fires over years chart
            fires_df = df.select(['year', 'total_fires']).rename({'year': 'timestamp', 'total_fires': df.columns[1]})
            fires_chart = generate_line_chart(
                df=fires_df,
                title=f"Total Fires in {selected_concelho.name} by Year",
                x_axis="Year",
                y_axis="Number of Fires"
            )
            # Ensure we're not double-encoding JSON
            historical_charts['total_fires'] = fires_chart
            
            # Total area burned over years chart
            area_df = df.select(['year', 'total_area_ha']).rename({'year': 'timestamp', 'total_area_ha': df.columns[1]})
            area_chart = generate_line_chart(
                df=area_df,
                title=f"Total Area Burned in {selected_concelho.name} by Year",
                x_axis="Year",
                y_axis="Area (ha)"
            )
            historical_charts['total_area'] = area_chart
            
            # Fire duration over years chart
            duration_df = df.select(['year', 'avg_duration_hours']).rename({'year': 'timestamp', 'avg_duration_hours': df.columns[1]})
            duration_chart = generate_line_chart(
                df=duration_df,
                title=f"Average Fire Duration in {selected_concelho.name} by Year",
                x_axis="Year",
                y_axis="Duration (hours)"
            )
            historical_charts['avg_duration'] = duration_chart
    
    # Get nationwide totals for comparison
    nationwide_stats = {}
    for year in range(current_year - 5, current_year + 1):
        yearly_totals = YearlyWildfireSummary.objects.filter(year=year).aggregate(
            total_fires=Sum('total_fires'),
            total_area=Sum('total_area_ha'),
            avg_duration=Avg('avg_duration_hours'),
            max_fire=Max('max_fire_size_ha')
        )
        nationwide_stats[year] = yearly_totals
    
    # Prepare context for template
    context = {
        'selected_concelho': selected_concelho,
        'all_concelhos': all_concelhos,
        'yearly_data': yearly_data,
        'current_year_data': current_year_data,
        'prev_year_data': prev_year_data,
        'comparison': comparison,
        'historical_charts': historical_charts,
        'nationwide_stats': nationwide_stats,
        'current_year': current_year,
    }
    
    # Return full template or just the content for HTMX requests
    if request.headers.get('HX-Request') == 'true':
        return render(request, 'wildfires/dashboard_content.html', context)
    else:
        return render(request, 'wildfires/dashboard.html', context)


def wildfire_risk_map(request):
    """
    View for displaying the wildfire risk map of Portugal
    """
    try:
        # Get the current date
        current_date = timezone.now().date()
        
        # Get fire risk data for today and tomorrow
        today_risks = FireRisk.objects.filter(
            forecast_day=0  # Today's forecast
        ).select_related('concelho')
        
        tomorrow_risks = FireRisk.objects.filter(
            forecast_day=1  # Tomorrow's forecast
        ).select_related('concelho')
        
        # Get all districts and concelhos
        all_distritos = Distrito.objects.all()
        all_concelhos = Concelho.objects.all()
        
        # Create a mapping of concelho dico_code to distrito district_code
        concelho_to_distrito = {}
        for concelho in all_concelhos:
            try:
                # Use the string representation of district_code to avoid type issues
                distrito_code = concelho.distrito.district_code
                concelho_to_distrito[concelho.dico_code] = distrito_code
            except Exception as e:
                # Log any issues with the relationship
                print(f"Error mapping concelho {concelho.dico_code} to distrito: {e}")
        
        # Initialize risk distribution counters
        risk_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        # Prepare data structures for today and tomorrow
        distritos_data = {}
        tomorrow_distritos_data = {}
        
        # Initialize data for all districts
        for distrito in all_distritos:
            distritos_data[distrito.district_code] = {
                'name': distrito.name,
                'risk_level': 1,  # Default to low risk
                'concelho_risks': []
            }
            tomorrow_distritos_data[distrito.district_code] = {
                'name': distrito.name,
                'risk_level': 1,  # Default to low risk
                'concelho_risks': []
            }
        
        # Process today's risks
        for risk in today_risks:
            concelho = risk.concelho
            distrito_id = concelho_to_distrito.get(concelho.dico_code)
            
            if distrito_id:
                # Add concelho risk info
                distritos_data[distrito_id]['concelho_risks'].append({
                    'concelho': concelho.name,
                    'risk_level': risk.risk_level,
                    'dico_code': concelho.dico_code
                })
                
                # Update risk distribution count
                risk_level = int(risk.risk_level)  # Ensure it's an integer
                risk_distribution[risk_level] = risk_distribution.get(risk_level, 0) + 1
                
                # Update max risk level for the distrito
                if risk.risk_level > distritos_data[distrito_id]['risk_level']:
                    distritos_data[distrito_id]['risk_level'] = risk.risk_level
        
        # Process tomorrow's risks
        for risk in tomorrow_risks:
            concelho = risk.concelho
            distrito_id = concelho_to_distrito.get(concelho.dico_code)
            
            if distrito_id:
                # Add concelho risk info
                tomorrow_distritos_data[distrito_id]['concelho_risks'].append({
                    'concelho': concelho.name,
                    'risk_level': risk.risk_level,
                    'dico_code': concelho.dico_code
                })
                
                # Update max risk level for the distrito
                if risk.risk_level > tomorrow_distritos_data[distrito_id]['risk_level']:
                    tomorrow_distritos_data[distrito_id]['risk_level'] = risk.risk_level
        
        # Get highest risk municipalities (those with level 4 or 5)
        high_risk_concelhos = []
        for risk in today_risks:
            if risk.risk_level >= 4:
                # Get distrito name safely
                distrito_name = "Unknown"
                try:
                    distrito_id = concelho_to_distrito.get(risk.concelho.dico_code)
                    if distrito_id in distritos_data:
                        distrito_name = distritos_data[distrito_id]['name']
                except Exception:
                    pass
                
                high_risk_concelhos.append({
                    'name': risk.concelho.name,
                    'distrito': distrito_name,
                    'risk_level': risk.risk_level
                })
        
        # Count active wildfires (this would connect to a real data source in production)
        # Placeholder data for demonstration
        active_wildfires_count = 12
        
        # Get total area burned statistics (placeholder data)
        total_area_burned = 3450.7  # hectares
        
        # Weather conditions (placeholder data)
        weather_conditions = {
            'avg_temp': 25.7,
            'avg_humidity': 45,
            'avg_wind_speed': 15,
            'precipitation_7days': 0.5
        }
        
        # Convert distrito data to JSON for JavaScript
        district_risk_json = json.dumps(distritos_data)
        tomorrow_district_risk_json = json.dumps(tomorrow_distritos_data)
        
        # Generate the risk distribution pie chart
        risk_labels = ['Reduced Risk', 'Moderate Risk', 'High Risk', 'Very High Risk', 'Maximum Risk']
        risk_colors = ['#28a745', '#ffc107', '#fd7e14', '#dc3545', '#990000']
        risk_values = [risk_distribution[1], risk_distribution[2], risk_distribution[3], risk_distribution[4], risk_distribution[5]]
        
        # Prepare data for the pie chart
        pie_data = {
            'labels': risk_labels,
            'values': risk_values,
            'colors': risk_colors
        }
        
        # Generate the pie chart using the utility function
        risk_distribution_chart = generate_pie_chart(
            data=pie_data,
            title='Municipality Risk Distribution',
            height=250
        )
        
        # Prepare context for template
        context = {
            'distritos_data': distritos_data,
            'district_risk_json': district_risk_json,
            'tomorrow_district_risk_json': tomorrow_district_risk_json,
            'current_date': current_date,
            'active_wildfires': active_wildfires_count,
            'total_area_burned': total_area_burned,
            'high_risk_concelhos': high_risk_concelhos,
            'risk_distribution': risk_distribution,
            'weather_conditions': weather_conditions,
            'risk_distribution_chart': risk_distribution_chart,  # Add the chart to the context
        }
        
        return render(request, 'wildfires/risk_map.html', context)
        
    except Exception as e:
        # Log the error and return a simple error page
        print(f"Error in wildfire_risk_map view: {e}")
        error_context = {
            'error_message': "There was an error loading the wildfire risk map. Please try again later.",
            'details': str(e) if settings.DEBUG else ""
        }
        return render(request, 'wildfires/risk_map_error.html', error_context, status=500)
    
    
    
def district_detail(request, district_code):
    """
    Detailed view for a specific district, showing wildfire risk information
    """
    # Get the distrito or return 404
    distrito = get_object_or_404(Distrito, district_code=district_code)
    
    # Get current date
    current_date = timezone.now().date()
    
    # Get all concelhos in this distrito
    concelhos = Concelho.objects.filter(distrito=distrito).order_by('name')
    
    # Get current fire risks for all concelhos in this distrito
    fire_risks = FireRisk.objects.filter(
        concelho__distrito=distrito,
        forecast_day=0  # Today's forecast
    ).select_related('concelho')
    
    # Get tomorrow's fire risks
    tomorrow_risks = FireRisk.objects.filter(
        concelho__distrito=distrito,
        forecast_day=1  # Tomorrow's forecast
    ).select_related('concelho')
    
    # Calculate distrito-level risk (highest risk among its concelhos)
    distrito_risk = 1  # Default to low risk
    for risk in fire_risks:
        if risk.risk_level > distrito_risk:
            distrito_risk = risk.risk_level
    
    # Calculate tomorrow's distrito-level risk
    tomorrow_distrito_risk = 1  # Default to low risk
    for risk in tomorrow_risks:
        if risk.risk_level > tomorrow_distrito_risk:
            tomorrow_distrito_risk = risk.risk_level
    
    # Calculate risk distribution
    risk_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for risk in fire_risks:
        risk_level = int(risk.risk_level)
        risk_distribution[risk_level] = risk_distribution.get(risk_level, 0) + 1
    

    
    # Get weather stations in this district
    weather_stations = WeatherStation.objects.filter(concelho__distrito=distrito)
    
    # Calculate time range for recent observations
    now = timezone.now()
    day_ago = now - timedelta(hours=24)
    
    # Get recent observations for these stations
    recent_observations = StationObservation.objects.filter(
        station__in=weather_stations,
        timestamp__gte=day_ago,
        temperature__gt=-90  # Filter out invalid readings
    ).exclude(
        humidity=-99.0
    ).exclude(
        wind_speed_kmh=-99.0
    )
    
    # Initialize default weather conditions
    weather_conditions = {
        'temperature': 22,
        'humidity': 45,
        'wind_speed': 8,
        'wind_direction': 'NE',
        'precipitation_chance': 5,
        'last_rainfall': current_date - timedelta(days=7),
    }
    
    # If we have observations, use real data
    if recent_observations.exists():
        # Calculate average weather conditions
        weather_stats = recent_observations.aggregate(
            avg_temp=Avg('temperature'),
            avg_humidity=Avg('humidity'),
            avg_wind_speed=Avg('wind_speed_kmh')
        )
        
        # Get most recent observation for current conditions
        latest_observation = recent_observations.order_by('-timestamp').first()
        
        # Direction mapping for human-readable output
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
        
        # Get observations with precipitation
        week_ago = now - timedelta(days=7)
        precipitation_observations = StationObservation.objects.filter(
            station__in=weather_stations,
            timestamp__gte=week_ago,
            precipitation__gt=0
        ).order_by('-timestamp')
        
        # Find last rainfall date
        last_rainfall = precipitation_observations.first()
        
        # Calculate precipitation chance based on humidity
        precipitation_chance = 5  # Default value
        if latest_observation and latest_observation.humidity:
            if latest_observation.humidity > 80:
                precipitation_chance = 45
            elif latest_observation.humidity > 70:
                precipitation_chance = 25
            elif latest_observation.humidity > 60:
                precipitation_chance = 10
        
        # Update weather conditions with real data
        weather_conditions = {
            'temperature': round(weather_stats['avg_temp'], 1) if weather_stats['avg_temp'] else 22,
            'humidity': round(weather_stats['avg_humidity']) if weather_stats['avg_humidity'] else 45,
            'wind_speed': round(weather_stats['avg_wind_speed']) if weather_stats['avg_wind_speed'] else 8,
            'wind_direction': direction_map.get(latest_observation.wind_direction if latest_observation else 0, 'Variable'),
            'precipitation_chance': precipitation_chance,
            'last_rainfall': last_rainfall.timestamp.date() if last_rainfall else current_date - timedelta(days=7),
        }
    
    # Mock active wildfires - keep this for demonstration
    active_wildfires = []
    if distrito_risk >= 4:  # Only show mock active wildfires for high risk districts
        active_wildfires = [
            {'location': 'Vale de Cambra', 'start_time': timezone.now() - timedelta(hours=5), 'status': 'Active', 'area_ha': 12.5},
            {'location': 'Serra da Freita', 'start_time': timezone.now() - timedelta(hours=8), 'status': 'Contained', 'area_ha': 8.2},
        ]
    
    # Historical wildfires (Mock data for now)
    historical_wildfires = [
        {'date': '2023-08-12', 'location': 'Serra de Santa Justa', 'area_ha': 145.8, 'duration_hours': 48},
        {'date': '2023-07-24', 'location': 'Parque Natural do Alvão', 'area_ha': 78.2, 'duration_hours': 36},
        {'date': '2023-06-30', 'location': 'Serra da Freita', 'area_ha': 210.5, 'duration_hours': 72},
        {'date': '2022-08-05', 'location': 'Vale de Cambra', 'area_ha': 320.7, 'duration_hours': 96},
        {'date': '2022-07-17', 'location': 'Serra do Marão', 'area_ha': 185.3, 'duration_hours': 60},
    ]
    
    # Prepare context for template
    context = {
        'distrito': distrito,
        'current_date': current_date,
        'distrito_risk': distrito_risk,
        'tomorrow_distrito_risk': tomorrow_distrito_risk,
        'risk_distribution': risk_distribution,
        'historical_wildfires': historical_wildfires,
        'active_wildfires': active_wildfires,
        'weather_conditions': weather_conditions,
        'concelhos': concelhos,
        'concelho_risks': {risk.concelho.dico_code: risk.risk_level for risk in fire_risks},
        'tomorrow_concelho_risks': {risk.concelho.dico_code: risk.risk_level for risk in tomorrow_risks},
    }
    
    return render(request, 'wildfires/district_detail.html', context)