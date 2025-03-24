from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Organization

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role', 'organization')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role', 'organization')}),
    )
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'organization', 'is_staff']
    list_filter = ['role', 'organization', 'is_staff', 'is_superuser', 'is_active']

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Organization)
