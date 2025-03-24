from django.core.management.base import BaseCommand
from django.utils import timezone
from location.models import WeatherStation
from climate.models import StationObservation
import requests
from datetime import datetime
import time

class Command(BaseCommand):
    help = 'Fetch last 3 hours of meteorological observations from IPMA API'

    def handle(self, *args, **kwargs):
        total_created = 0
        total_updated = 0
        total_errors = 0
        no_data_count = 0
        missing_stations = set()

        try:
            # Fetch observations data
            url = "https://api.ipma.pt/open-data/observation/meteorology/stations/obs-surface.geojson"
            self.stdout.write("Fetching recent observations data...")
            
            response = requests.get(url)
            response.raise_for_status()
            geojson_data = response.json()

            # Get all existing station IDs for validation
            existing_station_ids = set(WeatherStation.objects.values_list('station_id', flat=True))
            self.stdout.write(f"Found {len(existing_station_ids)} stations in database")

            # Process each feature (station observation)
            for feature in geojson_data['features']:
                properties = feature.get('properties', {})
                if not properties:
                    continue

                station_id = str(properties.get('idEstacao'))
                timestamp_str = properties.get('time')

                try:
                    # Skip if station doesn't exist in our database
                    if station_id not in existing_station_ids:
                        if station_id not in missing_stations:
                            missing_stations.add(station_id)
                            self.stdout.write(
                                self.style.WARNING(f'Weather station with ID {station_id} ({properties.get("localEstacao", "Unknown")}) not found in database')
                            )
                        continue

                    # Convert timestamp to timezone-aware datetime
                    timestamp = timezone.make_aware(datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S'))

                    # Check if all primary values are -99.0 (no data)
                    values_to_check = [
                        properties.get('temperatura'),
                        properties.get('humidade'),
                        properties.get('intensidadeVentoKM'),
                        properties.get('intensidadeVento'),
                        properties.get('precAcumulada')
                    ]
                    
                    if all(v == -99.0 for v in values_to_check if v is not None):
                        no_data_count += 1
                        continue
                    
                    # Get the station
                    station = WeatherStation.objects.get(station_id=station_id)
                    
                    # Create or update observation
                    observation, created = StationObservation.objects.update_or_create(
                        station=station,
                        timestamp=timestamp,
                        defaults={
                            'temperature': properties.get('temperatura', -99.0),
                            'humidity': properties.get('humidade', -99.0),
                            'wind_speed_kmh': properties.get('intensidadeVentoKM', -99.0),
                            'wind_speed_ms': properties.get('intensidadeVento', -99.0),
                            'wind_direction': properties.get('idDireccVento', 0),
                            'precipitation': properties.get('precAcumulada', -99.0),
                            'pressure': None if properties.get('pressao', -99.0) == -99.0 else properties['pressao'],
                            'radiation': None if properties.get('radiacao', -99.0) == -99.0 else properties['radiacao']
                        }
                    )
                    
                    if created:
                        total_created += 1
                    else:
                        total_updated += 1
                        
                except Exception as e:
                    total_errors += 1
                    self.stdout.write(
                        self.style.ERROR(f'Error processing observation for station {station_id} at {timestamp_str}: {str(e)}')
                    )
            
        except requests.RequestException as e:
            self.stdout.write(
                self.style.ERROR(f'Error fetching observations data: {str(e)}')
            )
            total_errors += 1
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error processing observations: {str(e)}')
            )
            total_errors += 1
        
        # Print final summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\nRecent observations processing completed:\n'
                f'- Created: {total_created}\n'
                f'- Updated: {total_updated}\n'
                f'- No Data entries skipped: {no_data_count}\n'
                f'- Errors: {total_errors}\n'
                f'- Missing stations: {len(missing_stations)}\n'
                f'\nMissing station IDs:\n{", ".join(sorted(missing_stations))}'
            )
        )