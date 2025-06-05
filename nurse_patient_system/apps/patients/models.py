# apps/patients/models.py

from django.db import models
from django.contrib.auth.models import User # Import Django's built-in User model

class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    # Use OneToOneField to link to Django's User model for authentication.
    # related_name allows you to access Patient from a User instance, e.g., user.patient_profile

    # Additional patient-specific fields
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    bed_number = models.CharField(max_length=10, blank=True, null=True, help_text="Bed number in the facility")

    # You can add more fields as needed, e.g., medical history, emergency contact

    def __str__(self):
        return f"Patient: {self.user.username} ({self.bed_number or 'N/A'})"

    class Meta:
        verbose_name = "Patient"
        verbose_name_plural = "Patients"