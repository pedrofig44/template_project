from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from location.models import City
from climate.models import HighPrecisionForecast
import requests
from datetime import datetime
import time

class Command(BaseCommand):
   help = 'Fetch high precision weather forecasts from IPMA API'

   def handle(self, *args, **kwargs):
       # Number of days to fetch (0 to 2)
       days = range(3)
       total_created = 0
       total_updated = 0
       total_errors = 0

       for day in days:
           try:
               # Construct URL for this day
               url = f"https://api.ipma.pt/open-data/forecast/meteorology/cities/daily/hp-daily-forecast-day{day}.json"
               
               self.stdout.write(f"Fetching high precision forecast for day {day}...")
               response = requests.get(url)
               response.raise_for_status()
               forecast_data = response.json()
               
               # Parse the common dates
               forecast_date = datetime.strptime(forecast_data['forecastDate'], '%Y-%m-%d').date()
               update_date = parse_datetime(forecast_data['dataUpdate'])
               
               # Process each city's forecast
               for city_forecast in forecast_data['data']:
                   try:
                       # Get the city from database
                       global_id = str(city_forecast['globalIdLocal'])
                       city = City.objects.get(global_id=global_id)
                       
                       # Create or update forecast
                       forecast, created = HighPrecisionForecast.objects.update_or_create(
                           city=city,
                           forecast_day=day,
                           defaults={
                               'forecast_date': forecast_date,
                               'update_date': update_date,
                               't_min': float(city_forecast.get('tMin', 0)),
                               't_max': float(city_forecast.get('tMax', 0)),
                               'precipita_prob': float(city_forecast.get('precipitaProb', 0)),
                               'wind_dir': city_forecast.get('predWindDir', 'N'),
                               'wind_speed_class': int(city_forecast.get('classWindSpeed', 0)),
                               'precip_intensity_class': int(city_forecast.get('classPrecInt', 0)),
                               'weather_type': int(city_forecast.get('idWeatherType', 0))
                           }
                       )
                       
                       if created:
                           total_created += 1
                       else:
                           total_updated += 1
                           
                   except City.DoesNotExist:
                       self.stdout.write(
                           self.style.WARNING(f'City with global_id {global_id} not found in database')
                       )
                       total_errors += 1
                   except Exception as e:
                       self.stdout.write(
                           self.style.ERROR(f'Error processing forecast for city {global_id}: {str(e)}')
                       )
                       total_errors += 1
               
               # Add a small delay between day requests
               time.sleep(1)
               
           except requests.RequestException as e:
               self.stdout.write(
                   self.style.ERROR(f'Error fetching data for day {day}: {str(e)}')
               )
               total_errors += 1
           except Exception as e:
               self.stdout.write(
                   self.style.ERROR(f'Error processing day {day}: {str(e)}')
               )
               total_errors += 1
       
       # Print final summary
       self.stdout.write(
           self.style.SUCCESS(
               f'High precision forecast processing completed:\n'
               f'- Created: {total_created}\n'
               f'- Updated: {total_updated}\n'
               f'- Errors: {total_errors}\n'
           )
       )