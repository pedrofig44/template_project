from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from climate.models import WeatherWarning
from location.models import City
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
            warnings_updated = 0
            warnings_unchanged = 0
            
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
                
                # Get key identifiers for the warning
                awareness_type = warning['awarenessTypeName']
                area_code = warning['idAreaAviso']
                awareness_level = warning['awarenessLevelID']
                description = warning.get('text', '')
                
                # Check if a similar warning already exists
                existing_warning = WeatherWarning.objects.filter(
                    awareness_type=awareness_type,
                    area_code=area_code,
                    start_time=start_time,
                    end_time=end_time
                ).first()
                
                # Try to find a matching city for this area code
                matching_city = None
                try:
                    matching_city = City.objects.filter(ipma_area_code=area_code).first()
                except Exception:
                    # If any error occurs, continue without setting the city
                    pass
                
                if existing_warning:
                    # Check if the warning has changed
                    if (existing_warning.awareness_level != awareness_level or 
                        existing_warning.description != description):
                        
                        # Create a new record to track the change
                        new_warning = WeatherWarning.objects.create(
                            awareness_type=awareness_type,
                            area_code=area_code,
                            start_time=start_time,
                            end_time=end_time,
                            awareness_level=awareness_level,
                            description=description,
                            city=matching_city
                        )
                        warnings_updated += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'Updated warning: {awareness_type} for {area_code}')
                        )
                    else:
                        warnings_unchanged += 1
                else:
                    # Create a new warning
                    new_warning = WeatherWarning.objects.create(
                        awareness_type=awareness_type,
                        area_code=area_code,
                        start_time=start_time,
                        end_time=end_time,
                        awareness_level=awareness_level,
                        description=description,
                        city=matching_city
                    )
                    warnings_created += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Created new warning: {awareness_type} for {area_code}')
                    )
            
            # Print summary
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully processed warnings:\n'
                    f'- New warnings created: {warnings_created}\n'
                    f'- Warnings updated: {warnings_updated}\n'
                    f'- Warnings unchanged: {warnings_unchanged}\n'
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