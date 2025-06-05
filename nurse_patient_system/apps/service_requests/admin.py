# apps/service_requests/admin.py

from django.contrib import admin
from .models import ServiceRequest

@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ('patient', 'nurse', 'need', 'status', 'requested_at')
    list_filter = ('status', 'requested_at', 'nurse')
    search_fields = ('patient__user__username', 'nurse__user__username', 'need')
    raw_id_fields = ('patient', 'nurse') # Allows searching for patient/nurse by ID
    readonly_fields = ('requested_at', 'accepted_at', 'completed_at') # Timestamps usually set automatically