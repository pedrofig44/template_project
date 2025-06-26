import math
from django.db import models
from location.models import Concelho
from climate.models import FireRisk

class FWIConverter:
    """
    Service to convert IPMA risk levels (1-5) to FWI values
    for ML model predictions
    """
    
    # Standard FWI classification ranges (based on Canadian/European systems)
    FWI_RANGES = {
        1: (0, 8),      # Reduced Risk: 0-8 FWI
        2: (9, 16),     # Moderate Risk: 9-16 FWI  
        3: (17, 24),    # High Risk: 17-24 FWI
        4: (25, 33),    # Very High Risk: 25-33 FWI
        5: (34, 50),    # Maximum Risk: 34+ FWI
    }
    
    @classmethod
    def risk_level_to_fwi(cls, risk_level, method='midpoint'):
        """
        Convert IPMA risk level (1-5) to FWI value
        
        Args:
            risk_level (int): IPMA risk level (1-5)
            method (str): Conversion method
                - 'midpoint': Use middle of FWI range
                - 'lower': Use lower bound + 1
                - 'upper': Use upper bound - 1
                
        Returns:
            float: FWI value
        """
        if risk_level not in cls.FWI_RANGES:
            raise ValueError(f"Invalid risk level: {risk_level}. Must be 1-5.")
        
        min_fwi, max_fwi = cls.FWI_RANGES[risk_level]
        
        if method == 'midpoint':
            return (min_fwi + max_fwi) / 2
        elif method == 'lower':
            return min_fwi + 1
        elif method == 'upper':  
            return max_fwi - 1
        else:
            raise ValueError(f"Invalid method: {method}")
    
    @classmethod
    def get_fwi_for_prediction(cls, fire_risk_obj):
        """
        Get FWI value from FireRisk object for ML prediction
        
        Args:
            fire_risk_obj: FireRisk model instance
            
        Returns:
            float: FWI value
        """
        if fire_risk_obj is None:
            # Default to moderate risk if no data
            return cls.risk_level_to_fwi(2, method='midpoint')
        
        try:
            return cls.risk_level_to_fwi(fire_risk_obj.risk_level, method='midpoint')
        except (ValueError, AttributeError):
            # Fallback to moderate risk
            return cls.risk_level_to_fwi(2, method='midpoint')
    
    @classmethod
    def get_mapping_info(cls):
        """Return mapping information for debugging/validation"""
        mapping = {}
        for level in range(1, 6):
            fwi_range = cls.FWI_RANGES[level]
            midpoint = cls.risk_level_to_fwi(level, 'midpoint')
            mapping[level] = {
                'range': fwi_range,
                'midpoint': midpoint,
                'description': {
                    1: 'Reduced Risk',
                    2: 'Moderate Risk', 
                    3: 'High Risk',
                    4: 'Very High Risk',
                    5: 'Maximum Risk'
                }[level]
            }
        return mapping


# Example usage in your feature assembly:
def get_fwi_for_concelho_date(concelho, prediction_date):
    """
    Get FWI value for a specific concelho and date
    """
    from climate.models import FireRisk
    
    # Try to get fire risk data for the date
    fire_risk = FireRisk.objects.filter(
        concelho=concelho,
        forecast_date=prediction_date
    ).first()
    
    # Convert to FWI using the converter
    fwi_value = FWIConverter.get_fwi_for_prediction(fire_risk)
    
    return fwi_value


# Test the mapping
if __name__ == "__main__":
    print("FWI Risk Level Mapping:")
    print("=" * 40)
    
    mapping = FWIConverter.get_mapping_info()
    for level, info in mapping.items():
        print(f"Level {level} ({info['description']}):")
        print(f"  FWI Range: {info['range'][0]}-{info['range'][1]}")
        print(f"  Midpoint: {info['midpoint']}")
        print()
    
    # Test conversion
    print("Test conversions:")
    for level in range(1, 6):
        fwi = FWIConverter.risk_level_to_fwi(level)
        print(f"Risk Level {level} → FWI {fwi}")