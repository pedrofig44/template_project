from django.contrib import admin
from django.utils.html import format_html
from .models import MLModel


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