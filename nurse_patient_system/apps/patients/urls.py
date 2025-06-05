# apps/patients/urls.py

from django.urls import path
from .views import PatientRegisterView, PatientLoginView

urlpatterns = [
    path('register/', PatientRegisterView.as_view(), name='patient-register'),
    path('login/', PatientLoginView.as_view(), name='patient-login'),
]