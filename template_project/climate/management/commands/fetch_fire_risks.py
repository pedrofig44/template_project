from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from location.models import Concelho
from climate.models import FireRisk
from datetime import datetime
import requests
import time

class Command(BaseCommand):
   help = 'Fetch fire risk forecasts from IPMA API'

   def handle(self, *args, **kwargs):
       # Fetch for today (0) and tomorrow (1)
       days = range(2)
       total_created = 0
       total_updated = 0
       total_errors = 0

       for day in days:
           try:
               # Construct URL for this day
               url = f"https://api.ipma.pt/open-data/forecast/meteorology/rcm/rcm-d{day}.json"
               
               self.stdout.write(f"Fetching fire risk forecast for day {day}...")
               response = requests.get(url)
               response.raise_for_status()
               risk_data = response.json()
               
               # Parse common dates
               forecast_date = datetime.strptime(risk_data['dataPrev'], '%Y-%m-%d').date()
               model_run_date = datetime.strptime(risk_data['dataRun'], '%Y-%m-%d').date()
               update_date = datetime.strptime(risk_data['fileDate'], '%Y-%m-%d %H:%M:%S')
               
               # Process each concelho's risk data
               for dico_code, data in risk_data['local'].items():
                   try:
                       # Ensure dico_code is in correct format (4 digits)
                       dico_code = dico_code.zfill(4)
                       
                       # Get the concelho from database
                       concelho = Concelho.objects.get(dico_code=dico_code)
                       
                       # Create or update risk forecast
                       risk, created = FireRisk.objects.update_or_create(
                           concelho=concelho,
                           forecast_day=day,
                           defaults={
                               'forecast_date': forecast_date,
                               'model_run_date': model_run_date,
                               'update_date': update_date,
                               'risk_level': data['data']['rcm']
                           }
                       )
                       
                       if created:
                           total_created += 1
                       else:
                           total_updated += 1
                           
                   except Concelho.DoesNotExist:
                       self.stdout.write(
                           self.style.WARNING(f'Concelho with DICO code {dico_code} not found in database')
                       )
                       total_errors += 1
                   except Exception as e:
                       self.stdout.write(
                           self.style.ERROR(f'Error processing fire risk for concelho {dico_code}: {str(e)}')
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
               f'Fire risk forecast processing completed:\n'
               f'- Created: {total_created}\n'
               f'- Updated: {total_updated}\n'
               f'- Errors: {total_errors}\n'
           )
       )