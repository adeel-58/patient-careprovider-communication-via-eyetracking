# apps/patients/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Patient

class PatientRegistrationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = Patient
        fields = ('username', 'password', 'password2', 'phone_number', 'address', 'bed_number')
        extra_kwargs = {
            'phone_number': {'required': False},
            'address': {'required': False},
            'bed_number': {'required': False},
        }

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        # Remove password2 as it's not part of the User model
        validated_data.pop('password2')
        phone_number = validated_data.pop('phone_number', None)
        address = validated_data.pop('address', None)
        bed_number = validated_data.pop('bed_number', None)

        # Create the User instance
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password']
        )
        user.save()

        # Create the Patient profile linked to the User
        patient = Patient.objects.create(
            user=user,
            phone_number=phone_number,
            address=address,
            bed_number=bed_number
        )
        return patient

class PatientLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'})