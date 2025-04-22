from django.core.management.base import BaseCommand
from django.utils import timezone
from floods.models import WaterStation, WaterReading
import requests
from datetime import datetime, timedelta
import time
import logging

# Set up logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetch water level and flow data for all active water stations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Number of hours to fetch data for (default: 24)'
        )

    def handle(self, *args, **options):
        hours = options['hours']
        
        # Get end time (now) and start time (24 hours ago or as specified)
        end_time = timezone.now()
        start_time = end_time - timedelta(hours=hours)
        
        self.stdout.write(f"Fetching water readings from {start_time} to {end_time}")
        
        # Get all active water stations
        stations = WaterStation.objects.filter(is_active=True)
        
        if not stations.exists():
            self.stdout.write(self.style.WARNING("No active water stations found"))
            return
        
        # Count statistics
        total_stations = stations.count()
        processed_stations = 0
        successful_stations = 0
        failed_stations = 0
        total_readings = 0
        
        # Process each station
        for station in stations:
            processed_stations += 1
            station_success = False
            
            try:
                self.stdout.write(f"Processing station {processed_stations}/{total_stations}: {station.name} ({station.station_id})")
                
                # Get readings for this station
                readings = self.fetch_station_readings(station, start_time, end_time)
                
                if readings:
                    station_success = True
                    total_readings += len(readings)
                    self.stdout.write(self.style.SUCCESS(f"  Successfully fetched {len(readings)} readings"))
                else:
                    self.stdout.write(self.style.WARNING(f"  No readings obtained for this station"))
            
            except Exception as e:
                failed_stations += 1
                self.stdout.write(self.style.ERROR(f"  Error processing station {station.name}: {str(e)}"))
                logger.error(f"Error processing station {station.station_id}: {str(e)}")
                continue
            
            if station_success:
                successful_stations += 1
            
            # Add a delay to avoid overwhelming the API
            time.sleep(2)
        
        # Print summary
        self.stdout.write(self.style.SUCCESS(
            f"\nWater readings fetch completed:\n"
            f"- Stations processed: {processed_stations}/{total_stations}\n"
            f"- Successful stations: {successful_stations}\n"
            f"- Failed stations: {failed_stations}\n"
            f"- Total readings collected: {total_readings}\n"
        ))

    def fetch_station_readings(self, station, start_time, end_time):
        """Fetch readings for a specific station and timeframe"""
        all_readings = []
        
        # Format dates for API
        start_date_str = start_time.strftime('%Y-%m-%d')
        end_date_str = end_time.strftime('%Y-%m-%d')
        
        # Fetch water level data if station has level capability
        if station.has_level_capability() and station.level_channel_id:
            level_readings = self.fetch_channel_data(
                station.level_channel_id,
                start_date_str,
                end_date_str,
                'level'
            )
            
            if level_readings:
                self.stdout.write(f"  Fetched {len(level_readings)} level readings")
                all_readings.extend(level_readings)
        
        # Fetch flow rate data if station has flow capability
        if station.has_flow_capability() and station.flow_channel_id:
            flow_readings = self.fetch_channel_data(
                station.flow_channel_id,
                start_date_str,
                end_date_str,
                'flow'
            )
            
            if flow_readings:
                self.stdout.write(f"  Fetched {len(flow_readings)} flow readings")
                all_readings.extend(flow_readings)
        
        # Process and save readings
        readings_saved = self.process_and_save_readings(station, all_readings)
        return readings_saved

    def fetch_channel_data(self, channel_id, start_date, end_date, data_type):
        """Fetch data for a specific channel from the API"""
        # Base URL and parameters
        base_url = "https://redehidro.ambiente.azores.gov.pt/chart.ashx"
        params = {
            's': 'c',
            'source': '1',
            'can_id': channel_id,
            'sdate': start_date,
            'edate': end_date,
            'time': '10m',
            'rnd': '0.123456789'  # Random value to prevent caching
        }
        
        self.stdout.write(f"  Fetching {data_type} data from channel {channel_id}")
        
        try:
            # Make the request
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            
            # Parse the data
            content = response.content.decode('utf-8')
            readings = self.parse_api_response(content, data_type)
            
            return readings
            
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f"  Error fetching data from API: {str(e)}"))
            return []
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Error processing data: {str(e)}"))
            return []

    def parse_api_response(self, content, data_type):
        """Parse the API response content into readings data"""
        try:
            # Clean up the content
            content = content.replace("\r\n", "").replace(" ", "").replace("'", "\"")
            
            # Find the data array
            start_index = content.find('[[')
            end_index = content.rfind(']]') + 2
            
            if start_index == -1 or end_index <= 1:
                self.stdout.write(self.style.WARNING("  No data array found in response"))
                return []
                
            data_str = content[start_index:end_index]
            
            # Split into entries
            entries = data_str[1:-1].split("],[")
            readings = []
            
            for entry in entries:
                # Split timestamp and value
                parts = entry.replace("[", "").replace("]", "").split(",")
                if len(parts) < 2:
                    continue
                    
                try:
                    # Parse timestamp and value
                    timestamp = datetime.utcfromtimestamp(int(parts[0]) / 1000)
                    value = float(parts[1])
                    
                    # Skip invalid readings (-99.0 is often used as a "no data" indicator)
                    if value != -99.0:
                        readings.append({
                            'timestamp': timestamp,
                            'value': value,
                            'type': data_type
                        })
                except (ValueError, IndexError) as e:
                    self.stdout.write(self.style.WARNING(f"  Error parsing entry '{entry}': {str(e)}"))
                    continue
            
            return readings
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Error parsing response: {str(e)}"))
            return []

    def process_and_save_readings(self, station, readings):
        """Process and save readings to database"""
        if not readings:
            return []
        
        # Group readings by timestamp
        readings_by_timestamp = {}
        for reading in readings:
            timestamp = reading['timestamp']
            if timestamp not in readings_by_timestamp:
                readings_by_timestamp[timestamp] = {'level': None, 'flow': None}
            
            if reading['type'] == 'level':
                readings_by_timestamp[timestamp]['level'] = reading['value']
            elif reading['type'] == 'flow':
                readings_by_timestamp[timestamp]['flow'] = reading['value']
        
        # Sort timestamps
        sorted_timestamps = sorted(readings_by_timestamp.keys())
        
        # Get previous readings for this station to calculate changes
        prev_level_reading = None
        prev_flow_reading = None
        
        try:
            latest_db_reading = WaterReading.objects.filter(
                station=station
            ).order_by('-timestamp').first()
            
            if latest_db_reading:
                prev_level_reading = latest_db_reading.water_level
                prev_flow_reading = latest_db_reading.flow_rate
        except Exception:
            # If there's an error, just proceed without previous readings
            pass
        
        # Process each reading
        saved_readings = []
        
        for timestamp in sorted_timestamps:
            reading_data = readings_by_timestamp[timestamp]
            level = reading_data['level']
            flow = reading_data['flow']
            
            # Calculate changes
            level_change = None
            flow_change = None
            
            if level is not None and prev_level_reading is not None:
                level_change = level - prev_level_reading
            
            if flow is not None and prev_flow_reading is not None:
                flow_change = flow - prev_flow_reading
            
            # Update previous values
            if level is not None:
                prev_level_reading = level
            
            if flow is not None:
                prev_flow_reading = flow
            
            # Create or update the reading
            try:
                reading, created = WaterReading.objects.update_or_create(
                    station=station,
                    timestamp=timestamp,
                    defaults={
                        'water_level': level,
                        'level_change': level_change,
                        'flow_rate': flow,
                        'flow_change': flow_change
                    }
                )
                
                saved_readings.append(reading)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error saving reading for {timestamp}: {str(e)}"))
        
        return saved_readings