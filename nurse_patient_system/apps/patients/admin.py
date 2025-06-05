# apps/patients/admin.py

from django.contrib import admin
from .models import Patient

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'bed_number')
    search_fields = ('user__username', 'phone_number', 'bed_number')
    raw_id_fields = ('user',) # Allows searching for user by ID