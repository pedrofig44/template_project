# predictions/management/commands/test_prediction_service.py

from django.core.management.base import BaseCommand
from datetime import date, datetime
from location.models import Concelho
from predictions.services import WildfirePredictionService


class Command(BaseCommand):
    help = 'Test wildfire prediction service with actual ML model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--concelho',
            type=str,
            help='Concelho name to test (default: first available)',
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Date to test (YYYY-MM-DD format, default: 2024-07-15)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔥 Testing Wildfire Prediction Service')
        )
        
        # Get test parameters
        concelho_name = options.get('concelho')
        date_str = options.get('date')
        if not date_str:
            date_str = '2024-07-15'
        
        try:
            test_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            self.stdout.write(
                self.style.ERROR(f'Invalid date format: {date_str}. Use YYYY-MM-DD')
            )
            return
        
        # Get concelho
        if concelho_name:
            try:
                concelho = Concelho.objects.get(name__icontains=concelho_name)
            except Concelho.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Concelho not found: {concelho_name}')
                )
                return
        else:
            concelho = Concelho.objects.first()
        
        self.stdout.write(f'📍 Testing prediction for: {concelho.name}')
        self.stdout.write(f'📅 Date: {test_date}')
        
        try:
            # Initialize prediction service
            self.stdout.write('\\n🤖 Loading ML model...')
            predictor = WildfirePredictionService()
            
            # Show model info
            model_info = predictor.get_model_info()
            self.stdout.write(f'✅ Model: {model_info["model_name"]} v{model_info["version"]}')
            self.stdout.write(f'📊 F1-Score: {model_info["f1_score"]}')
            self.stdout.write(f'📊 ROC-AUC: {model_info["roc_auc"]}') 
            self.stdout.write(f'🎯 Threshold: {model_info["threshold_file_value"]:.6f}')
            
            # Make prediction
            self.stdout.write('\\n🔮 Making prediction...')
            result = predictor.predict(concelho, test_date)
            
            # Display results
            self.stdout.write('\\n' + '='*60)
            self.stdout.write('🎯 WILDFIRE PREDICTION RESULTS')
            self.stdout.write('='*60)
            
            # Check if out of fire season
            if not result.get('fire_season', True):
                self.stdout.write(f'🗓️  FIRE SEASON STATUS: {self.style.WARNING("OUT OF SEASON")}')
                self.stdout.write(f'📅 {result["fire_season_message"]}')
                self.stdout.write(f'🚨 PREDICTION: {self.style.SUCCESS("✅ NO FIRE RISK (WINTER)")}')
                self.stdout.write(f'💡 INTERPRETATION: Winter months have no wildfire activity in Portugal.')
                self.stdout.write('='*60)
                self.stdout.write(self.style.SUCCESS('✅ Out-of-season prediction completed!'))
                return
            
            # In-season prediction display
            self.stdout.write(f'🗓️  FIRE SEASON STATUS: {self.style.SUCCESS("ACTIVE SEASON")}')
            
            # Main prediction
            prediction_symbol = '🔥 FIRE RISK' if result['prediction'] else '✅ NO FIRE RISK'
            self.stdout.write(f'🚨 PREDICTION: {prediction_symbol}')
            
            # Probability details
            prob_color = self.style.ERROR if result['probability'] > 0.5 else self.style.SUCCESS
            self.stdout.write(f'📊 Probability: {prob_color(f"{result["probability"]:.6f}")}')
            self.stdout.write(f'📈 Risk Level: {result["risk_level"]}')
            self.stdout.write(f'🎯 Confidence: {result["confidence"]:.6f}')
            self.stdout.write(f'⚖️  Threshold: {result["threshold_used"]:.6f}')
            
            # Key features that influenced prediction
            self.stdout.write('\\n📋 Key Features:')
            key_features = ['fwi', 'Florestas', 'risk_mean', 'day_of_season', 'month']
            for feature in key_features:
                if feature in result['features_used']:
                    value = result['features_used'][feature]
                    self.stdout.write(f'   {feature}: {value}')
            
            # Risk interpretation
            self.stdout.write('\\n💡 INTERPRETATION:')
            if result['probability'] > 0.8:
                self.stdout.write(self.style.ERROR('   ⚠️  VERY HIGH RISK - Immediate attention required'))
            elif result['probability'] > 0.6:
                self.stdout.write(self.style.WARNING('   🔶 HIGH RISK - Monitor closely'))
            elif result['probability'] > 0.4:
                self.stdout.write(self.style.WARNING('   🔸 MODERATE RISK - Normal monitoring'))
            elif result['probability'] > 0.2:
                self.stdout.write(self.style.SUCCESS('   🔹 LOW RISK - Standard precautions'))
            else:
                self.stdout.write(self.style.SUCCESS('   ✅ VERY LOW RISK - Minimal concern'))
            
            # Show detailed breakdown if verbose
            if result['probability'] > 0.5:
                self.stdout.write('\\n🔍 HIGH RISK FACTORS:')
                features = result['features_used']
                
                if features.get('fwi', 0) > 20:
                    self.stdout.write('   🌡️  High Fire Weather Index')
                if features.get('Florestas', 0) > 60:
                    self.stdout.write('   🌲 High forest coverage')
                if features.get('risk_mean', 0) > 3:
                    self.stdout.write('   📊 High historical risk')
                if 150 <= features.get('day_of_year', 0) <= 280:
                    self.stdout.write('   📅 Peak fire season')
            
            self.stdout.write('\\n' + '='*60)
            self.stdout.write(
                self.style.SUCCESS('✅ Prediction completed successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Prediction failed: {e}')
            )
            
            # Debug info
            self.stdout.write('\\n🔍 Troubleshooting:')
            self.stdout.write('   1. Check that model files are uploaded and accessible')
            self.stdout.write('   2. Verify all required data is available for the concelho/date')
            self.stdout.write('   3. Check the previous test_prediction command worked')