# predictions/services.py

import os
import numpy as np
import pickle
from datetime import date
from django.core.exceptions import ValidationError

from location.models import Concelho
from analytics.models import ConcelhoRiskAnalytics, ConcelhoWildfireRecovery
from predictions.models import ConcelhoSpatialFeatures, ConcelhoTemporalFeatures, MLModel
from climate.models import FireRisk
from climate.services import FWIConverter


import keras
import tensorflow as tf
from django.core.exceptions import ValidationError


class WildfireFeatureAssembler:
    """
    Service to assemble all 28 features for wildfire prediction
    
    CRITICAL: The feature order must match your training data exactly!
    """
    
    # CORRECT feature order from training data (X.info())
    FEATURE_ORDER = [
        'fwi',                                         # 0
        'year',                                        # 1  
        'area_ha',                                     # 2
        'risk_mean',                                   # 3
        'risk_median',                                 # 4
        'risk_minority',                               # 5
        'risk_majority',                               # 6
        'Territórios artificializados',                # 7
        'Pastagens',                                   # 8
        'Florestas',                                   # 9
        'Massas de água superficiais',                 # 10
        'Matos',                                       # 11
        'Superfícies agroflorestais (SAF)',            # 12
        'Espaços descobertos ou com pouca vegetação',  # 13
        'Agricultura',                                 # 14
        'Zonas húmidas',                               # 15
        'significant_burn_recovery',                   # 16
        'north_south',                                 # 17
        'east_west',                                   # 18
        'year_norm',                                   # 19
        'day_of_year',                                 # 20
        'day_of_season',                               # 21
        'day_of_season_norm',                          # 22
        'day_sin',                                     # 23
        'day_cos',                                     # 24
        'month',                                       # 25
        'month_sin',                                   # 26
        'month_cos',                                   # 27
    ]
    
    @classmethod
    def get_features_for_prediction(cls, concelho, prediction_date):
        """
        Assemble all 28 features for a given concelho and date
        
        Args:
            concelho: Concelho instance
            prediction_date: date object
            
        Returns:
            dict: Dictionary with all features
            
        Raises:
            ValidationError: If any required data is missing
        """
        features = {}
        missing_data = []
        
        try:
            # 1. Land Occupation Features (10)
            try:
                land_occ = concelho.land_occupation.get()
                features.update(land_occ.get_land_occupation_dict())
            except Exception as e:
                missing_data.append(f"Land occupation: {e}")
            
            # 2. Risk Analytics (4) 
            try:
                risk_analytics = concelho.risk_analytics.get()
                features.update(risk_analytics.get_risk_analytics_dict())
            except Exception as e:
                missing_data.append(f"Risk analytics: {e}")
            
            # 3. Wildfire Recovery (1)
            try:
                recovery = concelho.wildfire_recovery.filter(
                    data_date=prediction_date
                ).first()
                if recovery:
                    features.update(recovery.get_wildfire_recovery_dict())
                else:
                    # Default to 0 if no recovery data for this date
                    features['significant_burn_recovery'] = 0
            except Exception as e:
                missing_data.append(f"Recovery data: {e}")
            
            # 4. Spatial Features (2)
            try:
                spatial = concelho.spatial_features
                features.update(spatial.get_spatial_features_dict())
            except Exception as e:
                missing_data.append(f"Spatial features: {e}")
            
            # 5. Temporal Features (10)
            try:
                temporal = ConcelhoTemporalFeatures.objects.get(feature_date=prediction_date)
                features.update(temporal.get_temporal_features_dict())
            except ConcelhoTemporalFeatures.DoesNotExist:
                # Create temporal features on-the-fly if missing
                temporal = ConcelhoTemporalFeatures(feature_date=prediction_date)
                temporal.save()
                features.update(temporal.get_temporal_features_dict())
            except Exception as e:
                missing_data.append(f"Temporal features: {e}")
            
            # 6. Fire Weather Index (1)
            try:
                fire_risk = FireRisk.objects.filter(
                    concelho=concelho,
                    forecast_date=prediction_date
                ).first()
                
                fwi_value = FWIConverter.get_fwi_for_prediction(fire_risk)
                features['fwi'] = fwi_value
                
            except Exception as e:
                missing_data.append(f"FWI data: {e}")
            
            # Validate we have all expected features
            missing_features = [f for f in cls.FEATURE_ORDER if f not in features]
            if missing_features:
                missing_data.append(f"Missing features: {missing_features}")
            
            if missing_data:
                raise ValidationError(f"Missing data for prediction: {'; '.join(missing_data)}")
            
            return features
            
        except Exception as e:
            raise ValidationError(f"Error assembling features: {e}")
    
    @classmethod
    def features_dict_to_array(cls, features_dict):
        """
        Convert features dictionary to numpy array in correct order
        
        Args:
            features_dict: Dictionary of features
            
        Returns:
            np.array: Features in correct order for model input
        """
        try:
            feature_array = []
            for feature_name in cls.FEATURE_ORDER:
                if feature_name not in features_dict:
                    raise ValueError(f"Missing feature: {feature_name}")
                feature_array.append(float(features_dict[feature_name]))
            
            return np.array(feature_array).reshape(1, -1)  # Shape (1, 28) for single prediction
            
        except Exception as e:
            raise ValueError(f"Error converting features to array: {e}")
    
    @classmethod
    def validate_feature_order(cls, scaler_path=None):
        """
        Validate that our feature order matches the training data
        
        Args:
            scaler_path: Path to scaler.pkl file to inspect feature names
            
        Returns:
            bool: True if order is correct, False otherwise
        """
        if scaler_path:
            try:
                with open(scaler_path, 'rb') as f:
                    scaler = pickle.load(f)
                
                # Check if scaler has feature names
                if hasattr(scaler, 'feature_names_in_'):
                    training_features = list(scaler.feature_names_in_)
                    print("Training feature order:")
                    for i, feature in enumerate(training_features):
                        print(f"{i}: {feature}")
                    
                    print("\\nCurrent feature order:")
                    for i, feature in enumerate(cls.FEATURE_ORDER):
                        print(f"{i}: {feature}")
                    
                    return training_features == cls.FEATURE_ORDER
                else:
                    print("Scaler doesn't contain feature names")
                    return False
                    
            except Exception as e:
                print(f"Error validating feature order: {e}")
                return False
        
        print("No scaler path provided for validation")
        return False


# Test function
def test_feature_assembly():
    """
    Test feature assembly with a sample concelho and date
    """
    try:
        # Get a test concelho
        concelho = Concelho.objects.first()
        if not concelho:
            print("No concelho found for testing")
            return
        
        test_date = date(2024, 7, 15)  # Summer date
        
        print(f"Testing feature assembly for {concelho.name} on {test_date}")
        
        # Assemble features
        features = WildfireFeatureAssembler.get_features_for_prediction(concelho, test_date)
        
        print(f"\\nAssembled {len(features)} features:")
        for feature, value in features.items():
            print(f"  {feature}: {value}")
        
        # Convert to array
        feature_array = WildfireFeatureAssembler.features_dict_to_array(features)
        print(f"\\nFeature array shape: {feature_array.shape}")
        print(f"Feature array: {feature_array}")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        return False


if __name__ == "__main__":
    test_feature_assembly()
    

@keras.saving.register_keras_serializable()
class FocalLoss(keras.losses.Loss):
    """
    Focal Loss for binary classification
    Used to handle class imbalance in wildfire prediction
    """
    def __init__(self, alpha=0.25, gamma=2.0, reduction='sum_over_batch_size', name='focal_loss'):
        super().__init__(reduction=reduction, name=name)
        self.alpha = alpha
        self.gamma = gamma

    def call(self, y_true, y_pred):
        """
        Compute focal loss
        """
        # Clip predictions to prevent log(0)
        epsilon = tf.keras.backend.epsilon()
        y_pred = tf.clip_by_value(y_pred, epsilon, 1.0 - epsilon)
        
        # Compute focal loss
        alpha_t = y_true * self.alpha + (1 - y_true) * (1 - self.alpha)
        p_t = y_true * y_pred + (1 - y_true) * (1 - y_pred)
        focal_loss = alpha_t * tf.pow((1 - p_t), self.gamma) * tf.keras.backend.binary_crossentropy(y_true, y_pred)
        
        return focal_loss

    def get_config(self):
        config = super().get_config()
        config.update({
            'alpha': self.alpha,
            'gamma': self.gamma,
        })
        return config


class WildfirePredictionService:
    """
    Service to make wildfire predictions using the trained ML model
    """
    
    def __init__(self, model_id=None):
        """
        Initialize with a specific model or use the active one
        
        Args:
            model_id: Specific MLModel ID, or None to use active model
        """
        if model_id:
            self.ml_model = MLModel.objects.get(id=model_id, is_active=True)
        else:
            self.ml_model = MLModel.objects.filter(is_active=True).first()
            
        if not self.ml_model:
            raise ValidationError("No active ML model found")
            
        # Don't load model components yet - load lazily when needed
        self.keras_model = None
        self.scaler = None
        self.threshold = None
        self._model_loaded = False
    
    def _load_model_components(self):
        """Lazy load keras model, scaler, and threshold from files"""
        if self._model_loaded:
            return
            
        try:
            print("🔍 Starting model component loading...")
            
            # Since we rolled back to TensorFlow 2.16.1, use tensorflow.keras
            from tensorflow import keras as keras_module
            print("✅ Using TensorFlow Keras")
            
            # Load Keras model with custom objects
            print(f"📁 Loading model from: {self.ml_model.model_file_path}")
            if not os.path.exists(self.ml_model.model_file_path):
                raise FileNotFoundError(f"Model file not found: {self.ml_model.model_file_path}")
            
            # Define custom objects for model loading
            custom_objects = {
                'FocalLoss': FocalLoss,
                'focal_loss': FocalLoss,  # Alternative name
            }
            
            self.keras_model = keras_module.models.load_model(
                self.ml_model.model_file_path,
                custom_objects=custom_objects
            )
            print(f"✅ Loaded Keras model with FocalLoss: {self.ml_model.name}")
            
            # Load scaler
            print(f"📁 Loading scaler from: {self.ml_model.scaler_file_path}")
            if not os.path.exists(self.ml_model.scaler_file_path):
                raise FileNotFoundError(f"Scaler file not found: {self.ml_model.scaler_file_path}")
                
            with open(self.ml_model.scaler_file_path, 'rb') as f:
                self.scaler = pickle.load(f)
            print(f"✅ Loaded scaler (type: {type(self.scaler)})")
            
            # Load threshold
            print(f"📁 Loading threshold from: {self.ml_model.threshold_file_path}")
            if not os.path.exists(self.ml_model.threshold_file_path):
                raise FileNotFoundError(f"Threshold file not found: {self.ml_model.threshold_file_path}")
                
            with open(self.ml_model.threshold_file_path, 'rb') as f:
                threshold_raw = pickle.load(f)
            
            print(f"🔍 Raw threshold loaded: {threshold_raw} (type: {type(threshold_raw)})")
            
            # Process threshold value
            if threshold_raw is None:
                print("⚠️  Warning: Threshold is None! Using default value 0.1027")
                self.threshold = 0.1027  # Use your model's optimal threshold
            elif isinstance(threshold_raw, (int, float)):
                self.threshold = float(threshold_raw)
                print(f"✅ Threshold is a number: {self.threshold}")
            elif hasattr(threshold_raw, '__getitem__') and len(threshold_raw) > 0:
                # Handle case where threshold is in an array/list
                self.threshold = float(threshold_raw[0])
                print(f"✅ Extracted threshold from container: {self.threshold}")
            else:
                print(f"⚠️  Warning: Unexpected threshold type: {type(threshold_raw)}, value: {threshold_raw}")
                print("⚠️  Using default optimal threshold: 0.1027")
                self.threshold = 0.1027  # Your model's optimal threshold
            
            print(f"✅ Final threshold value: {self.threshold}")
            
            self._model_loaded = True
            print("✅ All model components loaded successfully!")
            
        except Exception as e:
            print(f"❌ Error in _load_model_components: {e}")
            import traceback
            traceback.print_exc()
            raise ValidationError(f"Error loading model components: {e}")
    
    def predict(self, concelho, prediction_date):
        """
        Make wildfire prediction for a specific concelho and date
        
        Args:
            concelho: Concelho instance
            prediction_date: date object
            
        Returns:
            dict: {
                'probability': float,      # Raw prediction probability (0-1)
                'prediction': bool,        # Binary prediction (True/False)
                'confidence': float,       # Confidence score
                'risk_level': str,         # Human-readable risk level
                'features_used': dict,     # Features used for debugging
                'model_info': dict         # Model metadata
            }
        """
        try:
            # CRITICAL: Validate fire season (May 1 - October 31)
            month = prediction_date.month
            day = prediction_date.day
            
            print(f"🔍 Fire season check: Date {prediction_date}, Month {month}, Day {day}")
            
            # Define fire season boundaries
            fire_season_start = (5, 1)   # May 1
            fire_season_end = (10, 31)   # October 31
            
            is_fire_season = False
            
            # Check if month is within fire season range
            if month >= fire_season_start[0] and month <= fire_season_end[0]:
                if month == fire_season_start[0]:  # May
                    is_fire_season = day >= fire_season_start[1]
                    print(f"🔍 May check: day {day} >= {fire_season_start[1]} = {is_fire_season}")
                elif month == fire_season_end[0]:  # October
                    is_fire_season = day <= fire_season_end[1]
                    print(f"🔍 October check: day {day} <= {fire_season_end[1]} = {is_fire_season}")
                else:  # June, July, August, September
                    is_fire_season = True
                    print(f"🔍 Middle month check: {month} is in fire season = {is_fire_season}")
            else:
                print(f"🔍 Month {month} is outside fire season range (5-10)")
            
            print(f"🔍 Final fire season result: {is_fire_season}")
            
            if not is_fire_season:
                print(f"🚫 BLOCKING prediction for out-of-season date: {prediction_date}")
                # Return safe prediction for out-of-season dates
                return {
                    'probability': 0.0,
                    'prediction': False,
                    'confidence': 1.0,
                    'risk_level': 'No Risk (Out of Season)',
                    'threshold_used': float(self.threshold) if self.threshold is not None else 0.1027,
                    'fire_season': False,
                    'fire_season_message': f'Date {prediction_date} is outside fire season (May 1 - October 31). No wildfire risk during winter months.',
                    'features_used': {'fire_season_check': 'OUTSIDE_SEASON'},
                    'model_info': {
                        'name': self.ml_model.name,
                        'version': self.ml_model.version,
                        'f1_score': float(self.ml_model.f1_score) if self.ml_model.f1_score else None,
                        'roc_auc': float(self.ml_model.roc_auc) if self.ml_model.roc_auc else None,
                    }
                }
            
            print(f"✅ Date {prediction_date} is within fire season - proceeding with prediction")
            
            # Lazy load model components only when prediction is requested
            self._load_model_components()
            
            # Step 1: Assemble features
            features_dict = WildfireFeatureAssembler.get_features_for_prediction(
                concelho, prediction_date
            )
            
            # Step 2: Convert to array in correct order
            feature_array = WildfireFeatureAssembler.features_dict_to_array(features_dict)
            
            # Step 3: Scale features
            scaled_features = self.scaler.transform(feature_array)
            
            # Step 4: Make prediction
            print(f"🔮 Making prediction with scaled features shape: {scaled_features.shape}")
            prediction_result = self.keras_model.predict(scaled_features, verbose=0)
            print(f"📊 Raw prediction result: {prediction_result} (type: {type(prediction_result)})")
            
            if prediction_result is None:
                raise ValueError("Model returned None prediction")
            
            raw_probability = float(prediction_result[0][0])
            print(f"📈 Extracted probability: {raw_probability}")
            
            # Step 5: Apply threshold for binary prediction
            print(f"⚖️  Applying threshold: {self.threshold}")
            binary_prediction = raw_probability > self.threshold
            
            # Step 6: Calculate confidence (distance from threshold)
            confidence = abs(raw_probability - self.threshold)
            
            # Step 7: Determine risk level
            risk_level = self._get_risk_level(raw_probability)
            
            return {
                'probability': round(raw_probability, 6),
                'prediction': binary_prediction,
                'confidence': round(confidence, 6),
                'risk_level': risk_level,
                'threshold_used': float(self.threshold) if self.threshold is not None else 0.5,
                'fire_season': True,
                'fire_season_message': f'Prediction made for fire season date {prediction_date}',
                'features_used': features_dict,
                'model_info': {
                    'name': self.ml_model.name,
                    'version': self.ml_model.version,
                    'f1_score': float(self.ml_model.f1_score) if self.ml_model.f1_score else None,
                    'roc_auc': float(self.ml_model.roc_auc) if self.ml_model.roc_auc else None,
                }
            }
            
        except Exception as e:
            raise ValidationError(f"Prediction failed: {e}")
    
    def _get_risk_level(self, probability):
        """Convert probability to human-readable risk level"""
        if probability >= 0.8:
            return "Very High Risk"
        elif probability >= 0.6:
            return "High Risk"
        elif probability >= 0.4:
            return "Moderate Risk"
        elif probability >= 0.2:
            return "Low Risk"
        else:
            return "Very Low Risk"
    
    def predict_batch(self, concelho_date_pairs):
        """
        Make predictions for multiple concelho/date combinations
        
        Args:
            concelho_date_pairs: List of (concelho, date) tuples
            
        Returns:
            list: List of prediction results
        """
        results = []
        
        for concelho, prediction_date in concelho_date_pairs:
            try:
                result = self.predict(concelho, prediction_date)
                result['concelho_name'] = concelho.name
                result['prediction_date'] = prediction_date.isoformat()
                result['success'] = True
                results.append(result)
                
            except Exception as e:
                results.append({
                    'concelho_name': concelho.name,
                    'prediction_date': prediction_date.isoformat(),
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def get_model_info(self):
        """Get information about the loaded model"""
        # Make sure model is loaded first
        self._load_model_components()
        
        return {
            'model_name': self.ml_model.name,
            'version': self.ml_model.version,
            'model_type': self.ml_model.get_model_type_display(),
            'f1_score': float(self.ml_model.f1_score) if self.ml_model.f1_score else None,
            'roc_auc': float(self.ml_model.roc_auc) if self.ml_model.roc_auc else None,
            'optimal_threshold': float(self.ml_model.optimal_threshold) if self.ml_model.optimal_threshold else None,
            'threshold_file_value': float(self.threshold) if self.threshold is not None else None,
            'status': self.ml_model.status,
            'created_at': self.ml_model.created_at.isoformat(),
        }


# Quick test function
def test_single_prediction():
    """
    Test function to make a single prediction
    """
    try:
        from location.models import Concelho
        from datetime import date
        
        # Get test data
        concelho = Concelho.objects.first()
        test_date = date(2024, 7, 15)
        
        # Initialize prediction service
        predictor = WildfirePredictionService()
        
        print(f"🔥 Testing prediction for {concelho.name} on {test_date}")
        print(f"🤖 Using model: {predictor.ml_model.name} v{predictor.ml_model.version}")
        
        # Make prediction
        result = predictor.predict(concelho, test_date)
        
        # Show results
        print(f"\\n📊 PREDICTION RESULTS:")
        print(f"   Probability: {result['probability']:.6f}")
        print(f"   Binary Prediction: {'🔥 FIRE RISK' if result['prediction'] else '✅ NO FIRE'}")
        print(f"   Risk Level: {result['risk_level']}")
        print(f"   Confidence: {result['confidence']:.6f}")
        print(f"   Threshold Used: {result['threshold_used']:.6f}")
        
        return result
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return None