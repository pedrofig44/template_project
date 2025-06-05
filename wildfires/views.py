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
from django.contrib.auth.decorators import login_required

@login_required
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

def _dedupe_risks(risks):
    """Return only the first FireRisk per concelho.dico_code to avoid duplicates."""
    seen = set()
    unique = []
    for r in risks:
        code = r.concelho.dico_code
        if code not in seen:
            seen.add(code)
            unique.append(r)
    return unique


@login_required
def wildfire_risk_map(request):
    """
    View for displaying the wildfire risk map of Portugal, without duplicate municipality entries.
    """
    # Current date
    current_date = timezone.now().date()

    # Raw risk QuerySets
    today_raw = FireRisk.objects.filter(forecast_day=0).select_related('concelho')
    tomorrow_raw = FireRisk.objects.filter(forecast_day=1).select_related('concelho')

    # Deduplicate by concelho
    today_risks = _dedupe_risks(today_raw)
    tomorrow_risks = _dedupe_risks(tomorrow_raw)

    # Load all districts and concelhos
    all_distritos = Distrito.objects.all()
    all_concelhos = Concelho.objects.all()

    # Map concelho code → distrito code
    concelho_to_distrito = {}
    for conc in all_concelhos:
        try:
            code = str(conc.dico_code)
            distrito_code = str(conc.distrito.district_code)
            concelho_to_distrito[code] = distrito_code
        except Exception as e:
            print(f"Mapping error for {conc}: {e}")

    # Initialize counters and structures
    risk_distribution = {i: 0 for i in range(1, 6)}
    distritos_data = {}
    tomorrow_data = {}
    for dist in all_distritos:
        key = str(dist.district_code)
        distritos_data[key] = {'name': dist.name, 'risk_level': 1, 'concelho_risks': []}
        tomorrow_data[key] = {'name': dist.name, 'risk_level': 1, 'concelho_risks': []}

    # Helper function to validate and convert risk level
    def get_valid_risk_level(risk_obj):
        """Convert risk_level to valid integer between 1-5, return None if invalid"""
        try:
            if risk_obj.risk_level is None:
                print(f"Warning: FireRisk {risk_obj.id} has null risk_level")
                return None
            
            level = int(risk_obj.risk_level)
            if level < 1 or level > 5:
                print(f"Warning: FireRisk {risk_obj.id} has invalid risk_level: {level}")
                return None
                
            return level
        except (ValueError, TypeError) as e:
            print(f"Warning: FireRisk {risk_obj.id} has non-numeric risk_level: {risk_obj.risk_level} - {e}")
            return None

    # Process today's unique risks with error handling
    for risk in today_risks:
        try:
            # Validate concelho exists
            if not risk.concelho:
                print(f"Warning: FireRisk {risk.id} has no concelho")
                continue
            
            # Validate risk level
            lvl = get_valid_risk_level(risk)
            if lvl is None:
                continue  # Skip invalid risk levels
            
            code = str(risk.concelho.dico_code)
            dist_key = concelho_to_distrito.get(code)
            if not dist_key:
                print(f"Warning: No distrito mapping for concelho {code}")
                continue

            # Safely access distrito data
            if dist_key not in distritos_data:
                print(f"Warning: Distrito {dist_key} not found in distritos_data")
                continue

            dataslot = distritos_data[dist_key]
            dataslot['concelho_risks'].append({
                'concelho': risk.concelho.name,
                'risk_level': lvl,  # Use validated level
                'dico_code': code
            })
            
            # Safely update risk distribution
            if lvl in risk_distribution:
                risk_distribution[lvl] += 1
            else:
                print(f"Warning: Unexpected risk level {lvl} not in distribution dict")
            
            # Update distrito max risk level
            if lvl > dataslot['risk_level']:
                dataslot['risk_level'] = lvl
                
        except Exception as e:
            print(f"Error processing today's risk {getattr(risk, 'id', 'unknown')}: {e}")
            continue

    # Process tomorrow's unique risks with error handling
    for risk in tomorrow_risks:
        try:
            # Validate concelho exists
            if not risk.concelho:
                print(f"Warning: Tomorrow FireRisk {risk.id} has no concelho")
                continue
            
            # Validate risk level
            lvl = get_valid_risk_level(risk)
            if lvl is None:
                continue  # Skip invalid risk levels
            
            code = str(risk.concelho.dico_code)
            dist_key = concelho_to_distrito.get(code)
            if not dist_key:
                continue

            # Safely access distrito data
            if dist_key not in tomorrow_data:
                print(f"Warning: Distrito {dist_key} not found in tomorrow_data")
                continue

            slot = tomorrow_data[dist_key]
            slot['concelho_risks'].append({
                'concelho': risk.concelho.name,
                'risk_level': lvl,  # Use validated level
                'dico_code': code
            })
            
            # Update distrito max risk level
            if lvl > slot['risk_level']:
                slot['risk_level'] = lvl
                
        except Exception as e:
            print(f"Error processing tomorrow's risk {getattr(risk, 'id', 'unknown')}: {e}")
            continue

    # High-risk concelhos (unique list) with error handling
    high_risk = []
    for r in today_risks:
        try:
            # Validate risk level for high-risk filtering
            lvl = get_valid_risk_level(r)
            if lvl is None or lvl < 4:
                continue
            
            if not r.concelho:
                continue
                
            code = str(r.concelho.dico_code)
            dist_key = concelho_to_distrito.get(code)
            distrito_name = "Unknown"
            
            if dist_key and dist_key in distritos_data:
                distrito_name = distritos_data[dist_key].get('name', 'Unknown')
            
            high_risk.append({
                'name': r.concelho.name,
                'distrito': distrito_name,
                'risk_level': lvl
            })
            
        except Exception as e:
            print(f"Error processing high-risk concelho for risk {getattr(r, 'id', 'unknown')}: {e}")
            continue

    # Placeholder stats
    active_count = 12
    total_area = 3450.7
    weather = {'avg_temp': 25.7, 'avg_humidity': 45, 'avg_wind_speed': 15, 'precipitation_7days': 0.5}

    # JSON for JS - with error handling
    try:
        district_risk_json = json.dumps(distritos_data)
        tomorrow_json = json.dumps(tomorrow_data)
    except (TypeError, ValueError) as e:
        print(f"Error serializing district data to JSON: {e}")
        # Fallback to empty data
        district_risk_json = json.dumps({})
        tomorrow_json = json.dumps({})

    # Pie chart - with error handling
    try:
        labels = ['Reduced Risk','Moderate Risk','High Risk','Very High','Maximum']
        values = [risk_distribution[i] for i in range(1,6)]
        pie_data = {
            'labels': labels, 
            'values': values, 
            'colors': ['#28a745','#ffc107','#fd7e14','#dc3545','#990000']
        }
        pie = generate_pie_chart(pie_data, title='Municipality Risk Distribution', height=250)
    except Exception as e:
        print(f"Error generating pie chart: {e}")
        # Fallback to simple chart data
        pie = json.dumps({'data': [], 'layout': {}})

    context = {
        'distritos_data': distritos_data,
        'district_risk_json': district_risk_json,
        'tomorrow_district_risk_json': tomorrow_json,
        'current_date': current_date,
        'active_wildfires': active_count,
        'total_area_burned': total_area,
        'high_risk_concelhos': high_risk,
        'risk_distribution': risk_distribution,
        'weather_conditions': weather,
        'risk_distribution_chart': pie,
    }
    return render(request, 'wildfires/risk_map.html', context)


@login_required
def district_detail(request, district_code):
    """
    Detailed view for a specific district, without duplicate municipality entries.
    """
    distrito = get_object_or_404(Distrito, district_code=district_code)
    current_date = timezone.now().date()

    # Raw risks and dedupe
    raw_today = FireRisk.objects.filter(concelho__distrito=distrito, forecast_day=0).select_related('concelho')
    raw_tomorrow = FireRisk.objects.filter(concelho__distrito=distrito, forecast_day=1).select_related('concelho')
    fire_risks = _dedupe_risks(raw_today)
    tomorrow_risks = _dedupe_risks(raw_tomorrow)

    # Distrito-level risk
    distrito_risk = max((r.risk_level for r in fire_risks), default=1)
    tomorrow_risk = max((r.risk_level for r in tomorrow_risks), default=1)

    # Risk distribution
    risk_dist = {i: 0 for i in range(1,6)}
    for r in fire_risks:
        risk_dist[int(r.risk_level)] += 1

    # Weather stations & observations
    stations = WeatherStation.objects.filter(concelho__distrito=distrito)
    now = timezone.now()
    obs_24h = StationObservation.objects.filter(
        station__in=stations,
        timestamp__gte=now - timedelta(hours=24)
    ).exclude(humidity=-99.0).exclude(wind_speed_kmh=-99.0)

    # Default weather
    weather = {'temperature':22,'humidity':45,'wind_speed':8,'wind_direction':'NE','precipitation_chance':5,'last_rainfall':current_date - timedelta(days=7)}
    if obs_24h.exists():
        stats = obs_24h.aggregate(avg_temp=Avg('temperature'), avg_humidity=Avg('humidity'), avg_wind_speed=Avg('wind_speed_kmh'))
        latest = obs_24h.order_by('-timestamp').first()
        dir_map = {1:'North',2:'Northeast',3:'East',4:'Southeast',5:'South',6:'Southwest',7:'West',8:'Northwest'}
        rain_obs = StationObservation.objects.filter(
            station__in=stations,
            timestamp__gte=now - timedelta(days=7),
            precipitation__gt=0
        ).order_by('-timestamp')
        last_rain = rain_obs.first()
        precip_chance = 5
        if latest.humidity > 80: precip_chance = 45
        elif latest.humidity > 70: precip_chance = 25
        elif latest.humidity > 60: precip_chance = 10
        weather = {
            'temperature': round(stats['avg_temp'],1),
            'humidity': round(stats['avg_humidity']),
            'wind_speed': round(stats['avg_wind_speed']),
            'wind_direction': dir_map.get(latest.wind_direction, 'Variable'),
            'precipitation_chance': precip_chance,
            'last_rainfall': last_rain.timestamp.date() if last_rain else current_date - timedelta(days=7)
        }

    # Context concelho risks as dict (unique)
    concelho_risks = {r.concelho.dico_code: r.risk_level for r in fire_risks}
    tomorrow_concelho_risks = {r.concelho.dico_code: r.risk_level for r in tomorrow_risks}

    # Mock data (unchanged)
    active_wildfires = []
    if distrito_risk >= 4:
        active_wildfires = [
            {'location': 'Vale de Cambra', 'start_time': now - timedelta(hours=5), 'status': 'Active', 'area_ha': 12.5},
            {'location': 'Serra da Freita', 'start_time': now - timedelta(hours=8), 'status': 'Contained', 'area_ha': 8.2},
        ]
    historical_wildfires = [
        {'date': '2023-08-12','location': 'Serra de Santa Justa','area_ha': 145.8,'duration_hours': 48},
        # ... etc.
    ]

    context = {
        'distrito': distrito,
        'current_date': current_date,
        'distrito_risk': distrito_risk,
        'tomorrow_distrito_risk': tomorrow_risk,
        'risk_distribution': risk_dist,
        'historical_wildfires': historical_wildfires,
        'active_wildfires': active_wildfires,
        'weather_conditions': weather,
        'concelhos': Concelho.objects.filter(distrito=distrito).order_by('name'),
        'concelho_risks': concelho_risks,
        'tomorrow_concelho_risks': tomorrow_concelho_risks,
    }
    return render(request, 'wildfires/district_detail.html', context)
