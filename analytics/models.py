from django.db import models
from location.models import Concelho


class ConcelhoRiskAnalytics(models.Model):
    """
    Risk analytics data for each concelho
    Based on training data risk features
    """
    concelho = models.ForeignKey(
        Concelho, 
        on_delete=models.CASCADE, 
        related_name='risk_analytics'
    )
    
    # Risk metrics (from training data)
    risk_mean = models.DecimalField(
        max_digits=8, decimal_places=4,
        help_text="Mean risk value"
    )
    risk_median = models.IntegerField(
        help_text="Median risk value"
    )
    risk_minority = models.IntegerField(
        help_text="Minority risk value"
    )
    risk_majority = models.IntegerField(
        help_text="Majority risk value"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['concelho']
        ordering = ['concelho']
        verbose_name = "Concelho Risk Analytics"
        verbose_name_plural = "Concelho Risk Analytics"
        indexes = [
            models.Index(fields=['concelho']),
            models.Index(fields=['risk_mean']),
        ]
    
    def __str__(self):
        return f"Risk analytics for {self.concelho.name}"
    
    def get_risk_analytics_dict(self):
        """Return risk analytics data as dictionary for ML model input"""
        return {
            'risk_mean': float(self.risk_mean),
            'risk_median': int(self.risk_median),
            'risk_minority': int(self.risk_minority),
            'risk_majority': int(self.risk_majority),
        }
    
    @property
    def risk_category(self):
        """Categorize overall risk based on mean value"""
        if self.risk_mean >= 4.0:
            return "Very High"
        elif self.risk_mean >= 3.0:
            return "High"
        elif self.risk_mean >= 2.0:
            return "Medium"
        elif self.risk_mean >= 1.0:
            return "Low"
        else:
            return "Very Low"
        
        
        
class ConcelhoWildfireRecovery(models.Model):
    """
    Wildfire recovery data for each concelho by date
    Tracks significant burn recovery indicator over time
    """
    concelho = models.ForeignKey(
        Concelho, 
        on_delete=models.CASCADE, 
        related_name='wildfire_recovery'
    )
    
    # Date for this recovery data
    data_date = models.DateField(help_text="Date for this recovery data")
    
    # Recovery indicator (0 or 1)
    significant_burn_recovery = models.IntegerField(
        choices=[(0, 'No significant burn recovery'), (1, 'Significant burn recovery')],
        help_text="Indicator if region had significant wildfire recovery (0 or 1)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['concelho', 'data_date']
        ordering = ['-data_date', 'concelho']
        verbose_name = "Concelho Wildfire Recovery"
        verbose_name_plural = "Concelho Wildfire Recovery"
        indexes = [
            models.Index(fields=['data_date']),
            models.Index(fields=['concelho', 'data_date']),
            models.Index(fields=['significant_burn_recovery']),
        ]
    
    def __str__(self):
        recovery_status = "with recovery" if self.significant_burn_recovery else "no recovery"
        return f"Wildfire recovery for {self.concelho.name} on {self.data_date} ({recovery_status})"
    
    def get_wildfire_recovery_dict(self):
        """Return wildfire recovery data as dictionary for ML model input"""
        return {
            'significant_burn_recovery': int(self.significant_burn_recovery),
        }
    
    @property
    def recovery_status(self):
        """Human-readable recovery status"""
        return "Significant burn recovery" if self.significant_burn_recovery else "No significant burn recovery"