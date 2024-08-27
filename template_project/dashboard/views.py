import polars as pl
from django.shortcuts import render
from data_source.models import SensorData
from .utils import generate_line_chart

def main_dashboard_view(request):
    # Query sensor data for sensor_id = 2
    sensor_data_queryset = SensorData.objects.filter(sensor_id=2).values('timestamp', 'temperature', 'humidity', 'precipitation')

    # Convert QuerySet to list of dictionaries
    sensor_data_list = list(sensor_data_queryset)

    # Convert query result to Polars DataFrame
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

    context = {
        'temperature_chart': temperature_chart,
        'humidity_chart': humidity_chart,
        'precipitation_chart': precipitation_chart,
    }

    return render(request, 'dashboard/main_dashboard.html', context)
