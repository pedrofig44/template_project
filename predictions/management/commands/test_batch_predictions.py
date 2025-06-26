# predictions/management/commands/test_batch_predictions.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta

from location.models import Concelho
from predictions.models import WildfirePrediction


class Command(BaseCommand):
    help = 'Test the batch prediction system with a small sample'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sample-size',
            type=int,
            default=3,
            help='Number of concelhos to test (default: 3)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🧪 Testing Batch Prediction System')
        )
        
        sample_size = options['sample_size']
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)
        
        # Get sample concelhos (ones that worked before)
        test_concelhos = ['Águeda', 'Pedrógão Grande', 'Coimbra', 'Faro', 'Aveiro']
        concelhos = Concelho.objects.filter(name__in=test_concelhos)[:sample_size]
        
        if not concelhos.exists():
            self.stdout.write(
                self.style.ERROR('❌ No test concelhos found')
            )
            return
        
        self.stdout.write(f'📍 Testing with {concelhos.count()} concelhos:')
        for concelho in concelhos:
            self.stdout.write(f'   - {concelho.name}')
        
        # Run batch prediction
        self.stdout.write(f'\\n🚀 Running batch prediction...')
        
        from django.core.management import call_command
        call_command(
            'generate_batch_predictions',
            force=True,
            concelhos=[c.name for c in concelhos],
            verbosity=0  # Reduce output for cleaner test
        )
        
        # Check results
        self.stdout.write('\\n📊 Checking results...')
        
        today_predictions = WildfirePrediction.objects.filter(
            prediction_date=today,
            prediction_type='today',
            concelho__in=concelhos
        )
        
        tomorrow_predictions = WildfirePrediction.objects.filter(
            prediction_date=tomorrow,
            prediction_type='tomorrow',
            concelho__in=concelhos
        )
        
        self.stdout.write(f'✅ Today predictions: {today_predictions.count()}/{concelhos.count()}')
        self.stdout.write(f'✅ Tomorrow predictions: {tomorrow_predictions.count()}/{concelhos.count()}')
        
        # Show sample results
        self.stdout.write('\\n📋 Sample Results:')
        for pred in today_predictions[:3]:
            risk_symbol = pred.risk_emoji
            self.stdout.write(
                f'   {risk_symbol} {pred.concelho.name}: {pred.probability:.3f} ({pred.risk_level})'
            )
        
        # Test high-risk detection
        high_risk = WildfirePrediction.objects.filter(
            prediction_date__in=[today, tomorrow],
            concelho__in=concelhos,
            prediction=True,
            probability__gte=0.6
        )
        
        if high_risk.exists():
            self.stdout.write(f'\\n🚨 High-risk alerts: {high_risk.count()}')
            for pred in high_risk:
                self.stdout.write(
                    f'   🔥 {pred.concelho.name} ({pred.prediction_type}): {pred.probability:.3f}'
                )
        else:
            self.stdout.write('\\n✅ No high-risk alerts in test sample')
        
        # Test retrieval methods
        self.stdout.write('\\n🔍 Testing retrieval methods...')
        
        latest_today = WildfirePrediction.get_latest_predictions('today')
        latest_tomorrow = WildfirePrediction.get_latest_predictions('tomorrow')
        
        self.stdout.write(f'📅 Latest today predictions: {latest_today.count()}')
        self.stdout.write(f'📅 Latest tomorrow predictions: {latest_tomorrow.count()}')
        
        # Test API format
        if today_predictions.exists():
            sample_pred = today_predictions.first()
            api_data = sample_pred.to_dict()
            self.stdout.write(f'\\n📡 API format test:')
            self.stdout.write(f'   Concelho: {api_data["concelho_name"]}')
            self.stdout.write(f'   Probability: {api_data["probability"]}')
            self.stdout.write(f'   Risk Color: {api_data["risk_color"]}')
            self.stdout.write(f'   Risk Emoji: {api_data["risk_emoji"]}')
        
        self.stdout.write('\\n✅ Batch prediction system test completed!')
        self.stdout.write('\\nℹ️  You can view stored predictions in Django admin under "Wildfire Predictions"')