# wildfires/views.py
from django.shortcuts import render, get_object_or_404
from .models import YearlyWildfireSummary
from location.models import Concelho
from django.db.models import Sum, Avg, Max
from django.utils import timezone
import polars as pl
import json
from dashboard.utils import generate_line_chart
from location.models import Distrito, Concelho
from climate.models import FireRisk

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
    # Get the current date
    current_date = timezone.now().date()
    
    # Get fire risk data for all concelhos
    fire_risks = FireRisk.objects.filter(
        forecast_day=0  # Today's forecast
    ).select_related('concelho')
    
    # For tomorrow's data if needed
    tomorrow_risks = FireRisk.objects.filter(
        forecast_day=1  # Tomorrow's forecast
    ).select_related('concelho')
    
    # Count active wildfires (this would connect to a real data source in production)
    # Placeholder data for demonstration
    active_wildfires_count = 12
    
    # Get total area burned statistics (placeholder data)
    total_area_burned = 3450.7  # hectares
    
    # Organize data by distrito for the map
    distritos_data = {}
    risk_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}  # Count municipalities in each risk level
    
    for distrito in Distrito.objects.all():
        # Find the highest risk level in this distrito's concelhos
        max_risk_level = 1  # Default to low risk
        concelho_risks = []
        
        for fire_risk in fire_risks:
            if fire_risk.concelho.distrito.district_code == distrito.district_code:
                concelho_risks.append({
                    'concelho': fire_risk.concelho.name,
                    'risk_level': fire_risk.risk_level,
                    'dico_code': fire_risk.concelho.dico_code
                })
                
                # Update risk distribution count
                risk_distribution[fire_risk.risk_level] = risk_distribution.get(fire_risk.risk_level, 0) + 1
                
                if fire_risk.risk_level > max_risk_level:
                    max_risk_level = fire_risk.risk_level
        
        distritos_data[distrito.district_code] = {
            'name': distrito.name,
            'risk_level': max_risk_level,
            'concelho_risks': concelho_risks
        }
    
    # Get highest risk municipalities (those with level 4 or 5)
    high_risk_concelhos = []
    for risk in fire_risks:
        if risk.risk_level >= 4:
            high_risk_concelhos.append({
                'name': risk.concelho.name,
                'distrito': risk.concelho.distrito.name,
                'risk_level': risk.risk_level
            })
    
    # Weather conditions (placeholder data)
    weather_conditions = {
        'avg_temp': 25.7,
        'avg_humidity': 45,
        'avg_wind_speed': 15,
        'precipitation_7days': 0.5
    }
    
    # Prepare context for template
    context = {
        'distritos_data': distritos_data,
        'current_date': current_date,
        'active_wildfires': active_wildfires_count,
        'total_area_burned': total_area_burned,
        'high_risk_concelhos': high_risk_concelhos,
        'risk_distribution': risk_distribution,
        'weather_conditions': weather_conditions,
    }
    
    return render(request, 'wildfires/risk_map.html', context)