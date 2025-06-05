# apps/service_requests/models.py

from django.db import models
from apps.patients.models import Patient
from apps.nurses.models import Nurse

class ServiceRequest(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='service_requests')
    nurse = models.ForeignKey(Nurse, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_requests',
                              help_text="The nurse assigned to this request. Can be null if not yet assigned or nurse deleted.")

    # Details of the service request
    need = models.CharField(max_length=255, help_text="What the patient needs, e.g., 'water', 'medication check'.")
    patient_bed_number_snapshot = models.CharField(max_length=10, blank=True, null=True,
                                                   help_text="Patient's bed number at time of request (for historical record).")
    patient_name_snapshot = models.CharField(max_length=255, blank=True, null=True,
                                             help_text="Patient's name at time of request (for historical record).")

    # Request status
    STATUS_CHOICES = [
        ('PENDING_ACCEPTANCE', 'Pending Acceptance'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('REJECTED', 'Rejected'), # If nurse rejects it
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING_ACCEPTANCE',
        help_text="Current status of the service request."
    )

    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Request for {self.patient.user.username} - {self.need} ({self.status})"

    class Meta:
        verbose_name = "Service Request"
        verbose_name_plural = "Service Requests"
        ordering = ['-requested_at'] # Order by most recent requests first