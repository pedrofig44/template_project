from django.contrib import admin
from django.utils.html import format_html
from .models import MLModel, WildfirePrediction


@admin.register(MLModel)
class MLModelAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'version', 'model_type', 'status', 'is_active', 
        'f1_score', 'created_at', 'file_status'
    ]
    list_filter = ['status', 'is_active', 'model_type', 'created_at']
    search_fields = ['name', 'version', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ('name', 'version', 'model_type', 'description')
        }),
        ('Model Files', {
            'fields': ('model_file', 'scaler_file', 'threshold_file'),
            'description': 'Upload your .keras model file, scaler .pkl file, and threshold .pkl file'
        }),
        ('Performance Metrics (Optional)', {
            'fields': ('accuracy', 'precision', 'recall', 'f1_score', 'roc_auc', 'optimal_threshold'),
            'classes': ['collapse']
        }),
        ('Status', {
            'fields': ('status', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ['collapse']
        })
    ]
    
    actions = ['activate_model', 'deactivate_model']
    
    def file_status(self, obj):
        """Show status of uploaded files"""
        files = []
        if obj.model_file:
            files.append('<span style="color: green;">✓ Model</span>')
        else:
            files.append('<span style="color: red;">✗ Model</span>')
            
        if obj.scaler_file:
            files.append('<span style="color: green;">✓ Scaler</span>')
        else:
            files.append('<span style="color: red;">✗ Scaler</span>')
            
        if obj.threshold_file:
            files.append('<span style="color: green;">✓ Threshold</span>')
        else:
            files.append('<span style="color: red;">✗ Threshold</span>')
            
        return format_html(' | '.join(files))
    
    file_status.short_description = 'Files Status'
    
    def activate_model(self, request, queryset):
        """Activate selected models"""
        activated_count = 0
        for model in queryset:
            # Check if all files are uploaded
            if not all([model.model_file, model.scaler_file, model.threshold_file]):
                self.message_user(request, f"Cannot activate {model.name} v{model.version}: Missing required files.", level='ERROR')
                continue
            
            model.is_active = True
            model.status = 'active'
            model.save()
            activated_count += 1
        
        if activated_count > 0:
            self.message_user(request, f"Activated {activated_count} model(s) successfully.")
    
    activate_model.short_description = "Activate selected models"
    
    def deactivate_model(self, request, queryset):
        """Deactivate selected models"""
        count = queryset.update(is_active=False, status='inactive')
        self.message_user(request, f"Deactivated {count} model(s).")
    
    deactivate_model.short_description = "Deactivate selected models"
    
    
@admin.register(WildfirePrediction)
class WildfirePredictionAdmin(admin.ModelAdmin):
    list_display = [
        'concelho_name', 'prediction_date', 'prediction_type', 
        'risk_display', 'probability_display', 'confidence_display',
        'fire_season', 'has_real_fwi', 'created_at'
    ]
    list_filter = [
        'prediction_type', 'prediction', 'fire_season', 
        'has_real_fwi', 'prediction_date', 'ml_model'
    ]
    search_fields = ['concelho__name', 'concelho__dico_code']
    readonly_fields = [
        'created_at', 'updated_at', 'processing_time_ms', 
        'risk_color', 'risk_emoji'
    ]
    date_hierarchy = 'prediction_date'
    
    fieldsets = [
        ('Location & Time', {
            'fields': ('concelho', 'prediction_date', 'prediction_type')
        }),
        ('Prediction Results', {
            'fields': (
                'probability', 'prediction', 'confidence', 'risk_level', 
                'threshold_used', 'risk_color', 'risk_emoji'
            )
        }),
        ('Key Features', {
            'fields': ('fwi', 'forest_percentage', 'risk_mean', 'day_of_season'),
            'classes': ['collapse']
        }),
        ('Fire Season Info', {
            'fields': ('fire_season', 'fire_season_message'),
            'classes': ['collapse']
        }),
        ('Data Quality', {
            'fields': ('has_real_fwi', 'data_quality_score', 'ml_model'),
            'classes': ['collapse']
        }),
        ('Processing Info', {
            'fields': ('processing_time_ms', 'created_at', 'updated_at'),
            'classes': ['collapse']
        })
    ]
    
    actions = ['export_high_risk', 'delete_old_predictions']
    
    def concelho_name(self, obj):
        return obj.concelho.name
    concelho_name.short_description = 'Concelho'
    concelho_name.admin_order_field = 'concelho__name'
    
    def risk_display(self, obj):
        """Display risk with emoji and color"""
        try:
            color = str(obj.risk_color)  # Ensure color is string
            emoji = str(obj.risk_emoji)  # Ensure emoji is string
            risk_level = str(obj.risk_level or 'Unknown')  # Ensure risk_level is string
            
            return format_html(
                '<span style="color: {}; font-weight: bold;">{} {}</span>',
                color, emoji, risk_level
            )
        except Exception as e:
            return f"Error: {e}"
    risk_display.short_description = 'Risk Level'
    risk_display.admin_order_field = 'probability'
    
    def probability_display(self, obj):
        """Display probability with color coding"""
        try:
            color = str(obj.risk_color)  # Ensure color is string
            probability = float(obj.probability)  # Convert Decimal to float
            
            # Format probability as string first, then use format_html
            prob_str = f"{probability:.3f}"
            
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, prob_str
            )
        except Exception as e:
            return f"Error: {e}"
    probability_display.short_description = 'Probability'
    probability_display.admin_order_field = 'probability'
    
    def confidence_display(self, obj):
        """Display confidence as decimal"""
        try:
            confidence = float(obj.confidence)  # Convert Decimal to float
            return f"{confidence:.3f}"
        except Exception as e:
            return f"Error: {e}"
    confidence_display.short_description = 'Confidence'
    confidence_display.admin_order_field = 'confidence'
    
    def export_high_risk(self, request, queryset):
        """Export high-risk predictions"""
        high_risk = queryset.filter(prediction=True, probability__gte=0.6)
        count = high_risk.count()
        self.message_user(
            request, 
            f"Found {count} high-risk predictions. Export functionality can be added here."
        )
    export_high_risk.short_description = "Export high-risk predictions"
    
    def delete_old_predictions(self, request, queryset):
        """Delete predictions older than 30 days"""
        from datetime import date, timedelta
        old_date = date.today() - timedelta(days=30)
        old_predictions = queryset.filter(prediction_date__lt=old_date)
        count = old_predictions.count()
        old_predictions.delete()
        self.message_user(
            request,
            f"Deleted {count} predictions older than {old_date}"
        )
    delete_old_predictions.short_description = "Delete old predictions"