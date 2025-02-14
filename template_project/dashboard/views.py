# dashboard/views.py
import polars as pl
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from data_source.models import SensorDataDummy
from location.models import SensorInfo
from .utils import generate_line_chart
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import user_passes_test

def always_false(user):
    return False


@user_passes_test(always_false)
@login_required
def main_dashboard_view(request):
    # Get the logged-in user's organization
    user_organization = request.user.organization

    # Find the sensor with the lowest ID for this organization
    sensor = SensorInfo.objects.filter(organization=user_organization).order_by('id').first()

    if sensor is None:
        return render(request, 'dashboard/main_dashboard.html', {
            'error': 'No sensors available for your organization.'
        })

    # Get the time range from GET parameters
    time_range = request.GET.get('time_range', 'all')

    # Determine the time filter
    if time_range == 'last_week':
        start_date = timezone.now() - timedelta(weeks=365)
    elif time_range == 'last_month':
        start_date = timezone.now() - timedelta(days=465)
    elif time_range == 'last_year':
        start_date = timezone.now() - timedelta(days=565)
    else:
        start_date = None  # No time filter applied

    # Query sensor data for the selected sensor and time range
    sensor_data_queryset = SensorDataDummy.objects.filter(sensor=sensor)
    if start_date:
        sensor_data_queryset = sensor_data_queryset.filter(timestamp__gte=start_date)

    # Convert QuerySet to list of dictionaries and then to Polars DataFrame
    sensor_data_list = list(sensor_data_queryset.values('timestamp', 'temperature', 'humidity', 'precipitation'))
    df = pl.DataFrame(sensor_data_list)

     # Determine background color based on cookie (or default)
    bg_color = '#191C24' if request.COOKIES.get('nightMode') == 'enabled' else '#f8f9fa'

    # Generate the line charts
    temperature_chart = generate_line_chart(
        df.select(['timestamp', 'temperature']),
        title="Temperature Over Time",
        x_axis="Timestamp",
        y_axis="Temperature (°C)",
        bg_color=bg_color
    )

    humidity_chart = generate_line_chart(
        df.select(['timestamp', 'humidity']),
        title="Humidity Over Time",
        x_axis="Timestamp",
        y_axis="Humidity (%)",
        bg_color=bg_color
    )

    precipitation_chart = generate_line_chart(
        df.select(['timestamp', 'precipitation']),
        title="Precipitation Over Time",
        x_axis="Timestamp",
        y_axis="Precipitation (mm)",
        bg_color=bg_color
    )

    # Prepare context
    context = {
        'temperature_chart': temperature_chart,
        'humidity_chart': humidity_chart,
        'precipitation_chart': precipitation_chart,
        'sensor_name': sensor.model,
        'time_range': time_range,
    }

    # Check if the request is an HTMX request
    if request.headers.get('HX-Request') == 'true':
        # Return the partial template with updated charts
        return render(request, 'dashboard/charts_partial.html', context)
    else:
        # Render the full page
        return render(request, 'dashboard/main_dashboard.html', context)
    

def index_dashboard_view(request):
     return render(request, 'dashboard/index_dashboard.html')
