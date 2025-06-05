# apps/nurses/models.py

from django.db import models
from django.contrib.auth.models import User

class Nurse(models.Model):
    # Link to Django's built-in User model
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='nurse_profile')

    # Nurse availability status
    STATUS_CHOICES = [
        ('FREE', 'Free'),
        ('BUSY', 'Busy'),
        ('ON_BREAK', 'On Break'),
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='ON_BREAK', # Default to on break until they log in
        help_text="Current availability status of the nurse."
    )

    # Firebase Cloud Messaging (FCM) device registration token
    # This token is unique to the nurse's Flutter app instance and device
    fcm_token = models.CharField(max_length=255, blank=True, null=True,
                                 help_text="Firebase Cloud Messaging device token for push notifications.")

    # Additional nurse-specific fields (optional)
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    specialty = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Nurse: {self.user.username} ({self.status})"

    class Meta:
        verbose_name = "Nurse"
        verbose_name_plural = "Nurses"