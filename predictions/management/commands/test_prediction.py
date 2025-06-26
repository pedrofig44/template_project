# predictions/management/commands/test_prediction.py

from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from datetime import date, datetime
from location.models import Concelho
from predictions.services import WildfireFeatureAssembler
from predictions.models import MLModel


class Command(BaseCommand):
    help = 'Test wildfire prediction feature assembly'

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
            self.style.SUCCESS('🔥 Testing Wildfire Prediction Feature Assembly')
        )
        
        # Get test parameters with proper None handling
        concelho_name = options.get('concelho')
        date_str = options.get('date')
        if not date_str:  # Handle None or empty string
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
            except Concelho.MultipleObjectsReturned:
                self.stdout.write(
                    self.style.ERROR(f'Multiple concelhos found with name: {concelho_name}')
                )
                return
        else:
            concelho = Concelho.objects.first()
            if not concelho:
                self.stdout.write(
                    self.style.ERROR('No concelhos found in database')
                )
                return
        
        self.stdout.write(f'📍 Testing with: {concelho.name}')
        self.stdout.write(f'📅 Date: {test_date}')
        
        # Check if we have an active model
        active_model = MLModel.objects.filter(is_active=True).first()
        if active_model:
            self.stdout.write(f'🤖 Active model: {active_model.name} v{active_model.version}')
        else:
            self.stdout.write(
                self.style.WARNING('⚠️  No active model found (upload one in admin first)')
            )
        
        # Test feature assembly
        try:
            self.stdout.write('\\n🔧 Assembling features...')
            
            features = WildfireFeatureAssembler.get_features_for_prediction(
                concelho, test_date
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Successfully assembled {len(features)} features')
            )
            
            # Show features in correct order
            self.stdout.write('\\n📋 Features in model order:')
            self.stdout.write('-' * 60)
            
            for i, feature_name in enumerate(WildfireFeatureAssembler.FEATURE_ORDER):
                value = features.get(feature_name, 'MISSING')
                if value == 'MISSING':
                    status = self.style.ERROR('MISSING')
                else:
                    status = f'{value:>12.6f}' if isinstance(value, (int, float)) else str(value)
                
                self.stdout.write(f'{i:2d}. {feature_name:<40} = {status}')
            
            # Convert to array
            feature_array = WildfireFeatureAssembler.features_dict_to_array(features)
            self.stdout.write(f'\\n📊 Feature array shape: {feature_array.shape}')
            
            # Show some statistics
            self.stdout.write('\\n📈 Feature statistics:')
            self.stdout.write(f'   Min value: {feature_array.min():.6f}')
            self.stdout.write(f'   Max value: {feature_array.max():.6f}')
            self.stdout.write(f'   Mean value: {feature_array.mean():.6f}')
            
            # Check for potential issues
            issues = []
            if (feature_array == 0).sum() > 5:
                issues.append(f'{(feature_array == 0).sum()} features are zero')
            if feature_array.max() > 1000:
                issues.append('Some features have very large values (>1000)')
            if feature_array.min() < -100:
                issues.append('Some features have very negative values (<-100)')
            
            if issues:
                self.stdout.write('\\n⚠️  Potential issues:')
                for issue in issues:
                    self.stdout.write(f'   - {issue}')
            
            self.stdout.write(
                self.style.SUCCESS('\\n✅ Feature assembly test completed successfully!')
            )
            
        except ValidationError as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Feature assembly failed: {e}')
            )
            
            # Show what data is missing
            self.stdout.write('\\n🔍 Debugging info:')
            self._check_data_availability(concelho, test_date)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Unexpected error: {e}')
            )
    
    def _check_data_availability(self, concelho, test_date):
        """Check what data is available for debugging"""
        
        # Check land occupation
        try:
            land_occ = concelho.land_occupation.get()
            self.stdout.write('✅ Land occupation data: Available')
        except:
            self.stdout.write('❌ Land occupation data: Missing')
        
        # Check risk analytics
        try:
            risk = concelho.risk_analytics.get() 
            self.stdout.write('✅ Risk analytics data: Available')
        except:
            self.stdout.write('❌ Risk analytics data: Missing')
        
        # Check spatial features
        try:
            spatial = concelho.spatial_features
            self.stdout.write('✅ Spatial features: Available')
        except:
            self.stdout.write('❌ Spatial features: Missing')
        
        # Check wildfire recovery
        recovery_count = concelho.wildfire_recovery.filter(data_date=test_date).count()
        if recovery_count > 0:
            self.stdout.write(f'✅ Recovery data for {test_date}: Available')
        else:
            self.stdout.write(f'⚠️  Recovery data for {test_date}: Missing (will use default)')
        
        # Check temporal features
        from predictions.models import ConcelhoTemporalFeatures
        try:
            temporal = ConcelhoTemporalFeatures.objects.get(feature_date=test_date)
            self.stdout.write(f'✅ Temporal features for {test_date}: Available')
        except:
            self.stdout.write(f'⚠️  Temporal features for {test_date}: Missing (will create)')
        
        # Check fire risk
        from climate.models import FireRisk
        fire_risk_count = FireRisk.objects.filter(
            concelho=concelho, forecast_date=test_date
        ).count()
        if fire_risk_count > 0:
            self.stdout.write(f'✅ Fire risk for {test_date}: Available')
        else:
            self.stdout.write(f'⚠️  Fire risk for {test_date}: Missing (will use default)')