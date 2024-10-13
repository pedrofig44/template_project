# api/management/commands/fetch_weather_data.py
from django.core.management.base import BaseCommand, CommandError
from api.utils import fetch_and_load_weather_data

class Command(BaseCommand):
    help = 'Fetches and stores weather prediction data'

    def handle(self, *args, **options):
        try:
            fetch_and_load_weather_data()
            self.stdout.write(self.style.SUCCESS('Successfully fetched and stored weather prediction data'))
        except Exception as e:
            raise CommandError('Error fetching and storing weather prediction data: %s' % e)
