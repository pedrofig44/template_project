from django.db import models
from location.models import Concelho
from django.core.validators import FileExtensionValidator
import os
import math

def model_file_upload_path(instance, filename):
    """Generate upload path for model files"""
    return f'models/{instance.name}_{instance.version}/{filename}'


class MLModel(models.Model):
    """
    Simple model for storing uploaded neural network models
    """
    MODEL_TYPES = [
        ('residual_network', 'Residual Network'),
        ('wide_deep', 'Wide and Deep'),
        ('pyramid', 'Pyramid Network'),
        ('ensemble', 'Ensemble Model'),
    ]
    
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    # Basic Information
    name = models.CharField(max_length=100, help_text="Model name")
    version = models.CharField(max_length=20, help_text="Version (e.g., v1.0.0)")
    model_type = models.CharField(max_length=50, choices=MODEL_TYPES, default='residual_network')
    description = models.TextField(blank=True, help_text="Model description")
    
    # File uploads
    model_file = models.FileField(
        upload_to=model_file_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['keras', 'h5'])],
        help_text="Upload .keras or .h5 model file"
    )
    scaler_file = models.FileField(
        upload_to=model_file_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['pkl'])],
        help_text="Upload scaler .pkl file"
    )
    threshold_file = models.FileField(
        upload_to=model_file_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['pkl'])],
        help_text="Upload threshold .pkl file"
    )
    
    # Performance metrics (optional)
    accuracy = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    precision = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    recall = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    f1_score = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    roc_auc = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    optimal_threshold = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    is_active = models.BooleanField(default=False, help_text="Is this model currently active?")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['name', 'version']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} v{self.version} ({self.get_model_type_display()})"
    
    def save(self, *args, **kwargs):
        # Set status based on activation state
        if self.is_active:
            self.status = 'active'
        super().save(*args, **kwargs)
    
    @property
    def model_file_path(self):
        """Get the full path to the model file"""
        if self.model_file:
            return self.model_file.path
        return None
    
    @property
    def scaler_file_path(self):
        """Get the full path to the scaler file"""
        if self.scaler_file:
            return self.scaler_file.path
        return None
    
    @property
    def threshold_file_path(self):
        """Get the full path to the threshold file"""
        if self.threshold_file:
            return self.threshold_file.path
        return None
    
    
class ConcelhoTemporalFeatures(models.Model):
    """
    Temporal features for predictions based on date
    Auto-calculates cyclical and normalized time features
    No concelho relationship - temporal data is universal
    """
    # Date for which these temporal features apply
    feature_date = models.DateField(unique=True, help_text="Date for which these temporal features apply")
    
    # Temporal features (some auto-calculated from feature_date)
    year = models.IntegerField(help_text="Year")
    year_norm = models.DecimalField(
        max_digits=8, decimal_places=6,
        help_text="Normalized year"
    )
    day_of_year = models.IntegerField(help_text="Day of year (1-365/366)")
    day_of_season = models.IntegerField(help_text="Day of season")
    day_of_season_norm = models.DecimalField(
        max_digits=8, decimal_places=6,
        help_text="Normalized day of season"
    )
    
    # Cyclical time features (auto-calculated)
    day_sin = models.DecimalField(
        max_digits=8, decimal_places=6,
        help_text="Sine of day of year (cyclical)"
    )
    day_cos = models.DecimalField(
        max_digits=8, decimal_places=6,
        help_text="Cosine of day of year (cyclical)"
    )
    month = models.IntegerField(help_text="Month (1-12)")
    month_sin = models.DecimalField(
        max_digits=8, decimal_places=6,
        help_text="Sine of month (cyclical)"
    )
    month_cos = models.DecimalField(
        max_digits=8, decimal_places=6,
        help_text="Cosine of month (cyclical)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['feature_date']
        verbose_name = "Temporal Features"
        verbose_name_plural = "Temporal Features"
        indexes = [
            models.Index(fields=['feature_date']),
            models.Index(fields=['day_of_year']),
            models.Index(fields=['month']),
        ]
    
    def __str__(self):
        return f"Temporal features for {self.feature_date}"
    
    def save(self, *args, **kwargs):
        """Auto-calculate temporal features from feature_date"""
        if self.feature_date:
            # Calculate temporal features
            self.year = self.feature_date.year
            self.month = self.feature_date.month
            self.day_of_year = self.feature_date.timetuple().tm_yday
            
            # Calculate cyclical features using correct formulas
            day_angle = math.pi * (self.day_of_year - 135) / 77
            self.day_sin = math.sin(day_angle)
            self.day_cos = math.cos(day_angle)
            
            month_angle = (self.month - 1) * math.pi / 6
            self.month_sin = math.sin(month_angle)
            self.month_cos = math.cos(month_angle)
            
        super().save(*args, **kwargs)
    
    def get_temporal_features_dict(self):
        """Return temporal features data as dictionary for ML model input"""
        return {
            'year': int(self.year),
            'year_norm': float(self.year_norm),
            'day_of_year': int(self.day_of_year),
            'day_of_season': int(self.day_of_season),
            'day_of_season_norm': float(self.day_of_season_norm),
            'day_sin': float(self.day_sin),
            'day_cos': float(self.day_cos),
            'month': int(self.month),
            'month_sin': float(self.month_sin),
            'month_cos': float(self.month_cos),
        }



class ConcelhoSpatialFeatures(models.Model):
    """
    Spatial/geographic features for each concelho
    Derived from concelho coordinates - usually static
    """
    concelho = models.OneToOneField(
        Concelho, 
        on_delete=models.CASCADE, 
        related_name='spatial_features'
    )
    
    # Geographic position features (derived from concelho coordinates)
    north_south = models.DecimalField(
        max_digits=10, decimal_places=6,
        help_text="North-South geographic position"
    )
    east_west = models.DecimalField(
        max_digits=10, decimal_places=6,
        help_text="East-West geographic position"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['concelho']
        verbose_name = "Concelho Spatial Features"
        verbose_name_plural = "Concelho Spatial Features"
        indexes = [
            models.Index(fields=['north_south']),
            models.Index(fields=['east_west']),
        ]
    
    def __str__(self):
        return f"Spatial features for {self.concelho.name}"
    
    def get_spatial_features_dict(self):
        """Return spatial features data as dictionary for ML model input"""
        return {
            'north_south': float(self.north_south),
            'east_west': float(self.east_west),
        }