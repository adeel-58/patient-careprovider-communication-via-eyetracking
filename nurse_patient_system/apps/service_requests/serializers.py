# apps/service_requests/serializers.py

from rest_framework import serializers
from .models import ServiceRequest
from apps.patients.models import Patient
from apps.nurses.models import Nurse

# apps/service_requests/serializers.py

from rest_framework import serializers
from .models import ServiceRequest
# No need to import Patient or Nurse directly in serializer,
# as they are linked via ServiceRequest model fields.

class ServiceRequestCreateSerializer(serializers.ModelSerializer):
    # These are the fields expected from the incoming request payload
    # They are write-only as they don't directly map to model fields in ServiceRequest
    # (they are used to populate snapshot fields)
    patient_bed_number = serializers.CharField(write_only=True)
    patient_name = serializers.CharField(write_only=True)
    selected_nurse_id = serializers.IntegerField(write_only=True, required=False) # Optional for direct assignment

    class Meta:
        model = ServiceRequest
        # These are the fields the serializer expects for input/output.
        # Note: We use the *input* names here, not the snapshot names for the direct fields.
        fields = ('need', 'patient_bed_number', 'patient_name', 'selected_nurse_id')
        # We don't need read_only_fields here because we're overriding create().
        # The fields patient, nurse, status, timestamps are handled by the view/model defaults.


    def create(self, validated_data):
        # Extract the fields that are meant for the snapshots
        patient_bed_number_data = validated_data.pop('patient_bed_number')
        patient_name_data = validated_data.pop('patient_name')

        # Extract selected_nurse_id (if present) as it's not a direct model field for create
        selected_nurse_id_data = validated_data.pop('selected_nurse_id', None)
        # Note: The actual patient and nurse instances will be passed by the view's .save() call

        # Create the ServiceRequest instance using the correct model field names
        service_request = ServiceRequest.objects.create(
            # Pass remaining validated_data (like 'need') directly
            **validated_data,
            # Assign the snapshot data to the correct model fields
            patient_bed_number_snapshot=patient_bed_number_data,
            patient_name_snapshot=patient_name_data,
            # patient and nurse fields will be provided by the view's serializer.save() call
            # e.g., serializer.save(patient=patient_instance, nurse=nurse_instance)
        )
        return service_request
    
class ServiceRequestActionSerializer(serializers.Serializer):
    """
    A simple serializer to acknowledge actions like accept or complete.
    The service_request_id will typically come from the URL.
    """
    # No fields here, as the ID comes from the URL, and action is implied by endpoint.
    # You could add fields like 'comment' if nurses could add notes.
    pass

class NurseServiceRequestListSerializer(serializers.ModelSerializer):
    patient_username = serializers.CharField(source='patient.user.username', read_only=True)
    nurse_username = serializers.CharField(source='nurse.user.username', read_only=True)

    class Meta:
        model = ServiceRequest
        fields = (
            'id', 'patient_username', 'nurse_username', 'patient_name_snapshot',
            'patient_bed_number_snapshot', 'need', 'status',
            'requested_at', 'accepted_at', 'completed_at'
        )
        read_only_fields = fields # All fields are read-only for listing    