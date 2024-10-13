import os
import django
import requests
import unicodedata
from decimal import Decimal

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django.setup()

from location.models import Coordinates, SensorInfo, Concelho, Distrito, Country
from accounts.models import Organization

# Function to normalize strings (remove accents and convert to lowercase)
def normalize_str(s):
    s = unicodedata.normalize('NFD', s)
    s = s.encode('ascii', 'ignore').decode('utf-8')
    return s.lower()

# Mapping of district capitals to location IDs (use unique 7-digit numbers)
districts = {
    'Aveiro': '1000001',
    'Beja': '1000002',
    'Braga': '1000003',
    'Braganca': '1000004',
    'Castelo Branco': '1000005',
    'Coimbra': '1000006',
    'Evora': '1000007',
    'Faro': '1000008',
    'Guarda': '1000009',
    'Leiria': '1000010',
    'Lisboa': '1000011',
    'Portalegre': '1000012',
    'Porto': '1000013',
    'Santarem': '1000014',
    'Setubal': '1000015',
    'Viana do Castelo': '1000016',
    'Vila Real': '1000017',
    'Viseu': '1000018',
    'Ponta Delgada': '1000019',
    'Funchal': '1000020',
}

# Normalize district capitals
normalized_capitals = {normalize_str(name): name for name in districts.keys()}

# Get or create the Country instance
country, _ = Country.objects.get_or_create(name='Portugal', code='PRT')

# Fetch data from the API
url = "https://api.ipma.pt/open-data/observation/meteorology/stations/stations.json"
response = requests.get(url)
data = response.json()

# Iterate over each station in the data
for station in data:
    local_estacao = station['properties']['localEstacao']
    id_estacao = station['properties']['idEstacao']
    coordinates = station['geometry']['coordinates']  # [longitude, latitude]
    longitude, latitude = coordinates
    normalized_local_estacao = normalize_str(local_estacao)
    
    # Check if the station is in a district capital
    for normalized_capital, capital in normalized_capitals.items():
        if normalized_capital in normalized_local_estacao:
            # Get or create Distrito instance
            distrito_name = capital
            location_id = districts[capital]
            distrito, _ = Distrito.objects.get_or_create(
                name=distrito_name,
                country=country,
                defaults={'location_id': location_id}
            )
            
            # Get or create Concelho instance
            concelho_name = capital
            concelho, _ = Concelho.objects.get_or_create(
                name=concelho_name,
                distrito=distrito
            )
            
            # Convert coordinates to Decimal
            latitude = Decimal(str(latitude))
            longitude = Decimal(str(longitude))
            
            # Get or create Coordinates instance
            coord, _ = Coordinates.objects.get_or_create(
                concelho=concelho,
                latitude=latitude,
                longitude=longitude
            )
            
            # Prepare sensor ID
            sensor_id = str(id_estacao).zfill(8)
            
            # Check if SensorInfo with this sensor_id already exists
            if SensorInfo.objects.filter(sensor_id=sensor_id).exists():
                print(f"SensorInfo with sensor_id {sensor_id} already exists.")
                continue
            
            # Create SensorInfo instance
            sensor_info = SensorInfo.objects.create(
                sensor_id=sensor_id,
                coordinates=coord,
                manufacturer='',  # Manufacturer not provided
                model=local_estacao,
                organization=None  # Organization is optional
            )
            
            print(f"Created SensorInfo for {local_estacao}")
            break  # Exit the loop after finding a matching capital
