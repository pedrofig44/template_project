# utils.py
import requests
from decimal import Decimal
from datetime import datetime
from data_source.models import WeatherForecast
from location.models import Distrito

def fetch_and_load_weather_data():
    # List of location IDs (globalIdLocal) that correspond to your Distrito.location_id
    location_ids = [
        "1010500", "1020500", "1030300", "1040200", "1050200",
        "1060300", "1070500", "1080500", "1090700", "1100900",
        "1110600", "1121400", "1131200", "1141600", "1151200",
        "1160900", "1171400", "1182300", "2310300", "3420300"
    ]

    
    base_url = 'https://api.ipma.pt/open-data/forecast/meteorology/cities/daily/'

    for location_id in location_ids:
        url = f'{base_url}{location_id}.json'
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()

            # Try to get the Distrito instance with this location_id
            try:
                distrito = Distrito.objects.get(location_id=location_id)
            except Distrito.DoesNotExist:
                print(f'Distrito with location_id {location_id} does not exist.')
                continue

            data_update_str = data.get('dataUpdate')
            data_update = datetime.strptime(data_update_str, '%Y-%m-%dT%H:%M:%S')

            for entry in data['data']:
                forecast_date = datetime.strptime(entry['forecastDate'], '%Y-%m-%d').date()

                # Update or create the WeatherForecast object
                WeatherForecast.objects.update_or_create(
                    distrito=distrito,
                    forecast_date=forecast_date,
                    defaults={
                        'data_update': data_update,
                        'temperature_min': Decimal(str(entry.get('tMin', 0))),
                        'temperature_max': Decimal(str(entry.get('tMax', 0))),
                        'precipitation_probability': Decimal(str(entry.get('precipitaProb', 0))),
                        'predominant_wind_direction': entry.get('predWindDir', ''),
                        'id_weather_type': entry.get('idWeatherType', 0),
                        'wind_speed_class': entry.get('classWindSpeed', 0),
                        'precipitation_intensity_class': entry.get('classPrecInt'),
                        'latitude': Decimal(str(entry.get('latitude', 0))),
                        'longitude': Decimal(str(entry.get('longitude', 0))),
                    }
                )
            print(f'Successfully loaded weather forecast data for location {location_id}')
        else:
            print(f'Failed to fetch data for location {location_id}, status code: {response.status_code}')
