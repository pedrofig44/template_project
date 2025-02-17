from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from location.models import City
from climate.models import DailyForecast
import requests
from datetime import datetime
import time

class Command(BaseCommand):
    help = 'Fetch daily weather forecasts from IPMA API for all cities'

    def handle(self, *args, **kwargs):
        # Get all cities
        cities = City.objects.all()
        total_cities = cities.count()
        
        self.stdout.write(f"Starting to fetch forecasts for {total_cities} cities...")
        
        forecasts_created = 0
        forecasts_updated = 0
        errors = 0

        for index, city in enumerate(cities, 1):
            try:
                # Construct URL using city's global_id
                url = f"https://api.ipma.pt/open-data/forecast/meteorology/cities/daily/{city.global_id}.json"
                
                # Fetch data from API
                self.stdout.write(f"Fetching forecast for {city.name} ({index}/{total_cities})")
                response = requests.get(url)
                response.raise_for_status()
                forecast_data = response.json()
                
                # Process each day's forecast
                for daily_data in forecast_data['data']:
                    # Convert date string to datetime
                    forecast_date = datetime.strptime(daily_data['forecastDate'], '%Y-%m-%d').date()
                    update_date = parse_datetime(forecast_data['dataUpdate'])
                    
                    # Create or update forecast
                    forecast, created = DailyForecast.objects.update_or_create(
                        city=city,
                        forecast_date=forecast_date,
                        defaults={
                            'update_date': update_date,
                            't_min': float(daily_data.get('tMin', 0)),
                            't_max': float(daily_data.get('tMax', 0)),
                            'precipita_prob': float(daily_data.get('precipitaProb', 0)),
                            'wind_dir': daily_data.get('predWindDir', 'N'),
                            'wind_speed_class': int(daily_data.get('classWindSpeed', 0)),
                            'weather_type': int(daily_data.get('idWeatherType', 0)),
                            'latitude': float(daily_data.get('latitude', city.latitude)),
                            'longitude': float(daily_data.get('longitude', city.longitude))
                        }
                    )
                    
                    if created:
                        forecasts_created += 1
                    else:
                        forecasts_updated += 1
                
                # Add a small delay to avoid overwhelming the API
                time.sleep(0.5)
                
            except requests.RequestException as e:
                self.stdout.write(
                    self.style.ERROR(f'Error fetching data for {city.name}: {str(e)}')
                )
                errors += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing forecast for {city.name}: {str(e)}')
                )
                errors += 1
        
        # Print summary
        self.stdout.write(
            self.style.SUCCESS(
                f'Forecast processing completed:\n'
                f'- Created: {forecasts_created}\n'
                f'- Updated: {forecasts_updated}\n'
                f'- Errors: {errors}\n'
            )
        )