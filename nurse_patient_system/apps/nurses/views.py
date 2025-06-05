# apps/nurses/views.py
from rest_framework import generics
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken # For JWT token generation

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from .serializers import NurseRegistrationSerializer, NurseLoginSerializer
from .models import Nurse

class NurseRegisterView(generics.CreateAPIView):
    queryset = Nurse.objects.all()
    serializer_class = NurseRegistrationSerializer
    permission_classes = (AllowAny,) # Allow anyone to register

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nurse = serializer.save()

        refresh = RefreshToken.for_user(nurse.user)
        return Response({
            "message": "Nurse registered successfully.",
            "user_id": nurse.user.id,
            "nurse_id": nurse.id,
            "username": nurse.user.username,
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh)
        }, status=status.HTTP_201_CREATED)

class NurseLoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = NurseLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        fcm_token = serializer.validated_data.get('fcm_token') # Optional FCM token on login

        user = authenticate(username=username, password=password)

        if user is not None:
            if hasattr(user, 'nurse_profile'): # Check if the user has a nurse profile
                nurse = user.nurse_profile
                # Set nurse status to FREE upon successful login
                nurse.status = 'FREE'
                # Update FCM token if provided
                if fcm_token:
                    nurse.fcm_token = fcm_token
                nurse.save()

                refresh = RefreshToken.for_user(user)

                return Response({
                    "message": "Nurse logged in successfully.",
                    "user_id": user.id,
                    "nurse_id": nurse.id,
                    "username": user.username,
                    "status": nurse.status,
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh)
                }, status=status.HTTP_200_OK)
            else:
                return Response({"detail": "User is not a nurse."}, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

class NurseLogoutView(APIView):
    permission_classes = (IsAuthenticated,) # Only authenticated users can log out

    def post(self, request, *args, **kwargs):
        # Ensure the logged-in user is a nurse
        if not hasattr(request.user, 'nurse_profile'):
            return Response({"detail": "Not a nurse."}, status=status.HTTP_403_FORBIDDEN)

        nurse = request.user.nurse_profile
        nurse.status = 'ON_BREAK' # Set status to ON_BREAK
        nurse.fcm_token = None # Clear FCM token on logout
        nurse.save()

        # You might also want to blacklist the refresh token if using Simple JWT
        # try:
        #     refresh_token = request.data["refresh_token"]
        #     token = RefreshToken(refresh_token)
        #     token.blacklist()
        # except Exception as e:
        #     return Response({"detail": "Refresh token not provided or invalid.", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Nurse logged out successfully. Status set to ON_BREAK."}, status=status.HTTP_200_OK)

class NurseStatusUpdateView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        if not hasattr(request.user, 'nurse_profile'):
            return Response({"detail": "Not a nurse."}, status=status.HTTP_403_FORBIDDEN)

        nurse = request.user.nurse_profile
        new_status = request.data.get('status')

        if new_status and new_status in dict(Nurse.STATUS_CHOICES).keys():
            nurse.status = new_status
            nurse.save()
            return Response({"message": f"Nurse status updated to {new_status}", "status": nurse.status}, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "Invalid or missing status."}, status=status.HTTP_400_BAD_REQUEST)
        

# apps/nurses/views.py
# ... (existing imports) ...
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from .serializers import NurseRegistrationSerializer, NurseLoginSerializer, NurseSerializer # Make sure NurseSerializer is imported
from .models import Nurse

# ... (NurseRegisterView, NurseLoginView, NurseLogoutView, NurseStatusUpdateView) ...

class FreeNurseListView(generics.ListAPIView):
    serializer_class = NurseSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Nurse.objects.filter(status='FREE').select_related('user')        