# apps/patients/views.py

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken # For JWT token generation

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from .serializers import PatientRegistrationSerializer, PatientLoginSerializer
from .models import Patient

class PatientRegisterView(generics.CreateAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientRegistrationSerializer
    permission_classes = (AllowAny,) # Allow anyone to register

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = serializer.save() # This calls the create method in the serializer

        # You might want to return tokens immediately after registration
        refresh = RefreshToken.for_user(patient.user)
        return Response({
            "message": "Patient registered successfully.",
            "user_id": patient.user.id,
            "patient_id": patient.id,
            "username": patient.user.username,
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh)
        }, status=status.HTTP_201_CREATED)

class PatientLoginView(APIView):
    permission_classes = (AllowAny,) # Allow any user to attempt login

    def post(self, request, *args, **kwargs):
        serializer = PatientLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        user = authenticate(username=username, password=password)

        if user is not None:
            if hasattr(user, 'patient_profile'): # Check if the user has a patient profile
                patient = user.patient_profile
                refresh = RefreshToken.for_user(user) # Generate JWT tokens

                return Response({
                    "message": "Patient logged in successfully.",
                    "user_id": user.id,
                    "patient_id": patient.id,
                    "username": user.username,
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh)
                }, status=status.HTTP_200_OK)
            else:
                return Response({"detail": "User is not a patient."}, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)