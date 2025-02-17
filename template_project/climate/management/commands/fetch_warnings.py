from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from climate.models import WeatherWarning
import requests
from datetime import datetime
import pytz

class Command(BaseCommand):
    help = 'Fetch weather warnings from IPMA API and store them in the database'

    def handle(self, *args, **kwargs):
        # API endpoint
        url = "https://api.ipma.pt/open-data/forecast/warnings/warnings_www.json"
        
        try:
            # Fetch data from API
            self.stdout.write("Fetching weather warnings from IPMA...")
            response = requests.get(url)
            response.raise_for_status()
            warnings_data = response.json()
            
            # Counter for new and updated warnings
            warnings_created = 0
            
            # Process each warning
            for warning in warnings_data:
                # Convert timestamps to datetime objects with timezone
                start_time = parse_datetime(warning['startTime'])
                end_time = parse_datetime(warning['endTime'])
                
                # Ensure timestamps are timezone-aware
                if start_time.tzinfo is None:
                    start_time = pytz.UTC.localize(start_time)
                if end_time.tzinfo is None:
                    end_time = pytz.UTC.localize(end_time)
                
                # Create or update warning
                warning_obj, created = WeatherWarning.objects.update_or_create(
                    awareness_type=warning['awarenessTypeName'],
                    area_code=warning['idAreaAviso'],
                    start_time=start_time,
                    end_time=end_time,
                    defaults={
                        'awareness_level': warning['awarenessLevelID'],
                        'description': warning.get('text', '')
                    }
                )
                
                if created:
                    warnings_created += 1
            
            # Print summary
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully processed warnings. Created {warnings_created} new warnings.'
                )
            )
            
        except requests.RequestException as e:
            self.stdout.write(
                self.style.ERROR(f'Error fetching data from API: {str(e)}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error processing warnings: {str(e)}')
            )