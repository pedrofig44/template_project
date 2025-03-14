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
        forecasts_unchanged = 0
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
                
                # Get update time for all forecasts in this response
                update_date = parse_datetime(forecast_data['dataUpdate'])
                
                # Process each day's forecast
                for daily_data in forecast_data['data']:
                    # Convert date string to datetime
                    forecast_date = datetime.strptime(daily_data['forecastDate'], '%Y-%m-%d').date()
                    
                    # Extract forecast details
                    t_min = float(daily_data.get('tMin', 0))
                    t_max = float(daily_data.get('tMax', 0))
                    precipita_prob = float(daily_data.get('precipitaProb', 0))
                    wind_dir = daily_data.get('predWindDir', 'N')
                    wind_speed_class = int(daily_data.get('classWindSpeed', 0))
                    weather_type = int(daily_data.get('idWeatherType', 0))
                    latitude = float(daily_data.get('latitude', city.latitude))
                    longitude = float(daily_data.get('longitude', city.longitude))
                    
                    # Check if we already have a forecast for this date
                    existing_forecast = DailyForecast.objects.filter(
                        city=city,
                        forecast_date=forecast_date
                    ).order_by('-update_date').first()
                    
                    if existing_forecast:
                        # Check if the forecast has changed
                        if (existing_forecast.t_min != t_min or 
                            existing_forecast.t_max != t_max or
                            existing_forecast.precipita_prob != precipita_prob or
                            existing_forecast.wind_dir != wind_dir or
                            existing_forecast.wind_speed_class != wind_speed_class or
                            existing_forecast.weather_type != weather_type):
                            
                            # Update the existing forecast instead of creating a new one
                            existing_forecast.update_date = update_date
                            existing_forecast.t_min = t_min
                            existing_forecast.t_max = t_max
                            existing_forecast.precipita_prob = precipita_prob
                            existing_forecast.wind_dir = wind_dir
                            existing_forecast.wind_speed_class = wind_speed_class
                            existing_forecast.weather_type = weather_type
                            existing_forecast.latitude = latitude
                            existing_forecast.longitude = longitude
                            existing_forecast.save()
                            
                            forecasts_updated += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'Updated forecast for {city.name}, date {forecast_date}')
                            )
                        else:
                            # Forecast hasn't changed
                            forecasts_unchanged += 1
                    else:
                        # No existing forecast, create a new one
                        DailyForecast.objects.create(
                            city=city,
                            forecast_date=forecast_date,
                            update_date=update_date,
                            t_min=t_min,
                            t_max=t_max,
                            precipita_prob=precipita_prob,
                            wind_dir=wind_dir,
                            wind_speed_class=wind_speed_class,
                            weather_type=weather_type,
                            latitude=latitude,
                            longitude=longitude
                        )
                        forecasts_created += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'Created new forecast for {city.name}, date {forecast_date}')
                        )
                
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
                f'- New forecasts created: {forecasts_created}\n'
                f'- Forecasts updated: {forecasts_updated}\n'
                f'- Forecasts unchanged: {forecasts_unchanged}\n'
                f'- Errors: {errors}\n'
            )
        )