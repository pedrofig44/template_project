import polars as pl
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from data_source.models import SensorDataDummy
from location.models import SensorLocation
from .utils import generate_line_chart

@login_required
def main_dashboard_view(request):
    # Get the logged-in user's organization
    user_organization = request.user.organization

    # Find the sensor with the lowest ID for this organization
    sensor = SensorLocation.objects.filter(organization=user_organization).order_by('id').first()

    print(sensor)

    if sensor is None:
        # Handle the case where there are no sensors for this organization
        return render(request, 'dashboard/main_dashboard.html', {
            'error': 'No sensors available for your organization.'
        })

    # Query sensor data for the selected sensor
    sensor_data_queryset = SensorDataDummy.objects.filter(sensor=sensor).values('timestamp', 'temperature', 'humidity', 'precipitation')

    # Convert QuerySet to list of dictionaries and then to Polars DataFrame
    sensor_data_list = list(sensor_data_queryset)
    df = pl.DataFrame(sensor_data_list)

    # Generate the line charts for temperature, humidity, and precipitation
    temperature_chart = generate_line_chart(
        df.select(['timestamp', 'temperature']), 
        title="Temperature Over Time", 
        x_axis="Timestamp", 
        y_axis="Temperature (°C)"
    )

    humidity_chart = generate_line_chart(
        df.select(['timestamp', 'humidity']), 
        title="Humidity Over Time", 
        x_axis="Timestamp", 
        y_axis="Humidity (%)"
    )

    precipitation_chart = generate_line_chart(
        df.select(['timestamp', 'precipitation']), 
        title="Precipitation Over Time", 
        x_axis="Timestamp", 
        y_axis="Precipitation (mm)"
    )

    # Pass the charts to the template context
    context = {
        'temperature_chart': temperature_chart,
        'humidity_chart': humidity_chart,
        'precipitation_chart': precipitation_chart,
        'sensor_name': sensor.name  # Include the sensor name for display
    }

    return render(request, 'dashboard/main_dashboard.html', context)
