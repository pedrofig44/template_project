# predictions/management/commands/generate_batch_predictions.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import date, timedelta
import time

from location.models import Concelho
from predictions.models import WildfirePrediction, MLModel
from predictions.services import WildfirePredictionService


class Command(BaseCommand):
    help = 'Generate batch wildfire predictions for today and tomorrow'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration even if predictions already exist',
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Specific date to process (YYYY-MM-DD format, default: today)',
        )
        parser.add_argument(
            '--concelhos',
            type=str,
            nargs='+',
            help='Specific concelhos to process (default: all)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔥 Starting Batch Wildfire Prediction Generation')
        )
        
        start_time = time.time()
        
        # Get processing date
        if options['date']:
            try:
                from datetime import datetime
                base_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(
                    self.style.ERROR(f'Invalid date format: {options["date"]}. Use YYYY-MM-DD')
                )
                return
        else:
            base_date = timezone.now().date()
        
        today = base_date
        tomorrow = base_date + timedelta(days=1)
        
        self.stdout.write(f'📅 Processing dates: {today} (today), {tomorrow} (tomorrow)')
        
        # Get active model
        ml_model = MLModel.objects.filter(is_active=True).first()
        if not ml_model:
            self.stdout.write(
                self.style.ERROR('❌ No active ML model found. Please activate a model in admin.')
            )
            return
        
        self.stdout.write(f'🤖 Using model: {ml_model.name} v{ml_model.version}')
        
        # Get concelhos to process - ONLY those in training data
        if options['concelhos']:
            concelhos = Concelho.objects.filter(
                name__in=options['concelhos'],
                in_wildfire_training=True  # Only training concelhos
            )
            if not concelhos.exists():
                self.stdout.write(
                    self.style.ERROR(f'No training concelhos found matching: {options["concelhos"]}')
                )
                return
        else:
            # Get all concelhos that were in training data
            concelhos = Concelho.objects.filter(in_wildfire_training=True)
        
        total_concelhos = concelhos.count()
        total_available = Concelho.objects.count()
        training_count = Concelho.objects.filter(in_wildfire_training=True).count()
        
        self.stdout.write(f'📍 Processing {total_concelhos} concelhos (training data only)')
        self.stdout.write(f'ℹ️  Training concelhos: {training_count}/{total_available} total concelhos')
        
        if total_concelhos == 0:
            self.stdout.write(
                self.style.ERROR('❌ No concelhos marked as in_wildfire_training=True!')
            )
            self.stdout.write('💡 Use: python manage.py mark_training_concelhos --help')
            return
        
        # Check for existing predictions
        force = options['force']
        existing_today = WildfirePrediction.objects.filter(
            prediction_date=today,
            prediction_type='today',
            concelho__in=concelhos
        ).count()
        existing_tomorrow = WildfirePrediction.objects.filter(
            prediction_date=tomorrow,
            prediction_type='tomorrow',
            concelho__in=concelhos
        ).count()
        
        if existing_today > 0 or existing_tomorrow > 0:
            if force:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Found {existing_today} today + {existing_tomorrow} tomorrow predictions. Forcing regeneration...')
                )
                # Delete existing predictions
                WildfirePrediction.objects.filter(
                    prediction_date__in=[today, tomorrow],
                    concelho__in=concelhos
                ).delete()
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Found {existing_today} today + {existing_tomorrow} tomorrow predictions. Use --force to regenerate.')
                )
                return
        
        # Initialize prediction service
        try:
            predictor = WildfirePredictionService()
            self.stdout.write('✅ Prediction service initialized')
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to initialize prediction service: {e}')
            )
            return
        
        # Process predictions
        self._process_batch_predictions(predictor, concelhos, today, tomorrow, ml_model)
        
        # Summary
        total_time = time.time() - start_time
        self.stdout.write('\\n' + '='*60)
        self.stdout.write('📊 BATCH PREDICTION SUMMARY')
        self.stdout.write('='*60)
        
        # Count final results
        today_count = WildfirePrediction.objects.filter(
            prediction_date=today,
            prediction_type='today',
            concelho__in=concelhos
        ).count()
        tomorrow_count = WildfirePrediction.objects.filter(
            prediction_date=tomorrow,
            prediction_type='tomorrow',
            concelho__in=concelhos
        ).count()
        
        self.stdout.write(f'✅ Today predictions: {today_count}/{total_concelhos}')
        self.stdout.write(f'✅ Tomorrow predictions: {tomorrow_count}/{total_concelhos}')
        self.stdout.write(f'⏱️  Total processing time: {total_time:.1f} seconds')
        self.stdout.write(f'⚡ Average time per concelho: {total_time/(total_concelhos*2):.2f} seconds')
        
        # High risk alerts
        high_risk_today = WildfirePrediction.objects.filter(
            prediction_date=today,
            prediction_type='today',
            prediction=True,
            probability__gte=0.6
        ).count()
        high_risk_tomorrow = WildfirePrediction.objects.filter(
            prediction_date=tomorrow,
            prediction_type='tomorrow',
            prediction=True,
            probability__gte=0.6
        ).count()
        
        if high_risk_today > 0 or high_risk_tomorrow > 0:
            self.stdout.write('\\n🚨 HIGH RISK ALERTS:')
            self.stdout.write(f'   Today: {high_risk_today} concelhos')
            self.stdout.write(f'   Tomorrow: {high_risk_tomorrow} concelhos')
        
        self.stdout.write('\\n✅ Batch prediction generation completed!')
    
    def _process_batch_predictions(self, predictor, concelhos, today, tomorrow, ml_model):
        """Process predictions for all concelhos and both dates"""
        
        success_count = 0
        error_count = 0
        
        for i, concelho in enumerate(concelhos, 1):
            self.stdout.write(f'\\n📍 Processing {i}/{concelhos.count()}: {concelho.name}')
            
            # Process today's prediction
            try:
                self._generate_single_prediction(
                    predictor, concelho, today, 'today', ml_model
                )
                success_count += 1
                self.stdout.write(f'   ✅ Today: Success')
            except Exception as e:
                error_count += 1
                self.stdout.write(f'   ❌ Today: {str(e)[:100]}...')
            
            # Process tomorrow's prediction
            try:
                self._generate_single_prediction(
                    predictor, concelho, tomorrow, 'tomorrow', ml_model
                )
                success_count += 1
                self.stdout.write(f'   ✅ Tomorrow: Success')
            except Exception as e:
                error_count += 1
                self.stdout.write(f'   ❌ Tomorrow: {str(e)[:100]}...')
        
        self.stdout.write(f'\\n📈 Processing results: {success_count} success, {error_count} errors')
    
    def _generate_single_prediction(self, predictor, concelho, prediction_date, prediction_type, ml_model):
        """Generate and store a single prediction"""
        start_time = time.time()
        
        # Make prediction
        result = predictor.predict(concelho, prediction_date)
        
        processing_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
        
        # Extract key features for storage
        features = result.get('features_used', {})
        
        # Determine data quality
        has_real_fwi = True  # We'll enhance this logic later
        data_quality = 1.0   # We'll enhance this logic later
        
        # Store prediction
        with transaction.atomic():
            prediction_obj, created = WildfirePrediction.objects.update_or_create(
                concelho=concelho,
                prediction_date=prediction_date,
                prediction_type=prediction_type,
                defaults={
                    'ml_model': ml_model,
                    'probability': result['probability'],
                    'prediction': result['prediction'],
                    'confidence': result['confidence'],
                    'risk_level': result['risk_level'],
                    'threshold_used': result['threshold_used'],
                    'fire_season': result.get('fire_season', True),
                    'fire_season_message': result.get('fire_season_message', ''),
                    'fwi': features.get('fwi', 0),
                    'forest_percentage': features.get('Florestas', 0),
                    'risk_mean': features.get('risk_mean', 0),
                    'day_of_season': features.get('day_of_season', 0),
                    'has_real_fwi': has_real_fwi,
                    'data_quality_score': data_quality,
                    'processing_time_ms': processing_time,
                }
            )
        
        return prediction_obj
    
    def _update_today_from_yesterday_tomorrow(self, base_date):
        """
        Update today's predictions from yesterday's tomorrow predictions
        This maintains consistency when new fire risk data comes in
        """
        yesterday = base_date - timedelta(days=1)
        
        # Get yesterday's tomorrow predictions
        yesterday_tomorrow = WildfirePrediction.objects.filter(
            prediction_date=base_date,
            prediction_type='tomorrow'
        )
        
        if not yesterday_tomorrow.exists():
            self.stdout.write('ℹ️  No yesterday tomorrow predictions to update from')
            return
        
        updated_count = 0
        for pred in yesterday_tomorrow:
            # Update to today's prediction
            WildfirePrediction.objects.update_or_create(
                concelho=pred.concelho,
                prediction_date=pred.prediction_date,
                prediction_type='today',
                defaults={
                    'ml_model': pred.ml_model,
                    'probability': pred.probability,
                    'prediction': pred.prediction,
                    'confidence': pred.confidence,
                    'risk_level': pred.risk_level,
                    'threshold_used': pred.threshold_used,
                    'fire_season': pred.fire_season,
                    'fire_season_message': pred.fire_season_message,
                    'fwi': pred.fwi,
                    'forest_percentage': pred.forest_percentage,
                    'risk_mean': pred.risk_mean,
                    'day_of_season': pred.day_of_season,
                    'has_real_fwi': pred.has_real_fwi,
                    'data_quality_score': pred.data_quality_score,
                    'processing_time_ms': pred.processing_time_ms,
                }
            )
            updated_count += 1
        
        self.stdout.write(f"🔄 Updated {updated_count} today predictions from yesterday's tomorrow predictions")