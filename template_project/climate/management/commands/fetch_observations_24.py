from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from location.models import WeatherStation
from climate.models import StationObservation
import requests
from datetime import datetime
import time

class Command(BaseCommand):
    help = 'Fetch meteorological observations from IPMA API'

    def handle(self, *args, **kwargs):
        total_created = 0
        total_updated = 0
        total_errors = 0
        no_data_count = 0
        missing_stations = set()  # Track unique missing stations

        try:
            # Fetch observations data
            url = "https://api.ipma.pt/open-data/observation/meteorology/stations/observations.json"
            self.stdout.write("Fetching observations data...")
            
            response = requests.get(url)
            response.raise_for_status()
            observations_data = response.json()

            # Get all existing station IDs for validation
            existing_station_ids = set(WeatherStation.objects.values_list('station_id', flat=True))
            self.stdout.write(f"Found {len(existing_station_ids)} stations in database")

            # Process each timestamp
            for timestamp_str, stations_data in observations_data.items():
                # Convert timestamp to timezone-aware datetime
                timestamp = timezone.make_aware(parse_datetime(timestamp_str))
                
                # Process each station
                for station_id, obs_data in stations_data.items():
                    try:
                        # Skip if station doesn't exist in our database
                        if station_id not in existing_station_ids:
                            if station_id not in missing_stations:
                                missing_stations.add(station_id)
                                self.stdout.write(
                                    self.style.WARNING(f'Weather station with ID {station_id} not found in database')
                                )
                            continue

                        # Skip if obs_data is None or empty
                        if not obs_data:
                            self.stdout.write(
                                self.style.WARNING(f'No observation data for station {station_id} at {timestamp_str}')
                            )
                            continue

                        # Check if all values are -99.0 (no data)
                        values_to_check = [
                            obs_data.get('temperatura'),
                            obs_data.get('humidade'),
                            obs_data.get('intensidadeVentoKM'),
                            obs_data.get('intensidadeVento'),
                            obs_data.get('precAcumulada')
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
                                'temperature': obs_data.get('temperatura', -99.0),
                                'humidity': obs_data.get('humidade', -99.0),
                                'wind_speed_kmh': obs_data.get('intensidadeVentoKM', -99.0),
                                'wind_speed_ms': obs_data.get('intensidadeVento', -99.0),
                                'wind_direction': obs_data.get('idDireccVento', 0),
                                'precipitation': obs_data.get('precAcumulada', -99.0),
                                'pressure': None if obs_data.get('pressao', -99.0) == -99.0 else obs_data['pressao'],
                                'radiation': None if obs_data.get('radiacao', -99.0) == -99.0 else obs_data['radiacao']
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
                f'\nObservations processing completed:\n'
                f'- Created: {total_created}\n'
                f'- Updated: {total_updated}\n'
                f'- No Data entries skipped: {no_data_count}\n'
                f'- Errors: {total_errors}\n'
                f'- Missing stations: {len(missing_stations)}\n'
                f'\nMissing station IDs:\n{", ".join(sorted(missing_stations))}'
            )
        )