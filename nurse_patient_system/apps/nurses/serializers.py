# apps/nurses/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Nurse

class NurseRegistrationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = Nurse
        fields = ('username', 'password', 'password2', 'employee_id', 'specialty', 'fcm_token')
        extra_kwargs = {
            'employee_id': {'required': False},
            'specialty': {'required': False},
            'fcm_token': {'required': False}, # FCM token might be sent later
        }

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        employee_id = validated_data.pop('employee_id', None)
        specialty = validated_data.pop('specialty', None)
        fcm_token = validated_data.pop('fcm_token', None)

        # Create the User instance
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password']
        )
        user.save()

        # Create the Nurse profile linked to the User
        nurse = Nurse.objects.create(
            user=user,
            employee_id=employee_id,
            specialty=specialty,
            fcm_token=fcm_token,
            status='ON_BREAK' # Default to ON_BREAK upon registration
        )
        return nurse

class NurseLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'})
    fcm_token = serializers.CharField(required=False) # Allow sending FCM token on login

class NurseSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True) # Access username from related User model

    class Meta:
        model = Nurse
        fields = ('id', 'username', 'employee_id', 'specialty', 'status')
        read_only_fields = ('id', 'username', 'employee_id', 'specialty', 'status') # These fields are read-only    