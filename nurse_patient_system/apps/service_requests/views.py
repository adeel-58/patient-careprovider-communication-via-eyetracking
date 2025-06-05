# apps/service_requests/views.py

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
import random
from firebase_admin import messaging
from apps.patients.models import Patient

from .serializers import ServiceRequestCreateSerializer
from .models import ServiceRequest
from apps.nurses.models import Nurse
from apps.notifications.utils import get_fcm_messaging, get_firestore_db

import random # Assuming random is imported elsewhere for nurse selection
from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

# Assuming these models and serializers are defined elsewhere in your Django project
# from .models import ServiceRequest, Nurse
# from .serializers import ServiceRequestCreateSerializer

# Removed Firebase imports (firebase_admin, messaging)
# Removed Firebase utility functions (get_fcm_messaging, get_firestore_db)

class ServiceRequestCreateView(generics.CreateAPIView):
    queryset = ServiceRequest.objects.all()
    serializer_class = ServiceRequestCreateSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not hasattr(request.user, 'patient_profile'):
            return Response({"detail": "User is not a patient."}, status=status.HTTP_403_FORBIDDEN)
        patient = request.user.patient_profile

        assigned_nurse = None
        
        # Removed Firebase service initialization and checks
        # fcm = get_fcm_messaging()
        # firestore_db = get_firestore_db()
        # if not fcm or not firestore_db:
        #     return Response({"detail": "Firebase services not initialized. Check backend logs."},
        #                     status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            with transaction.atomic():
                # Logic to assign a nurse (either selected or a random free one)
                if selected_nurse_id_from_payload := serializer.validated_data.get('selected_nurse_id'):
                    try:
                        # Ensure Nurse model is correctly imported and available
                        nurse_candidates = Nurse.objects.select_for_update().filter(
                            id=selected_nurse_id_from_payload, status='FREE'
                        )
                        if nurse_candidates.exists():
                            assigned_nurse = nurse_candidates.first()
                        else:
                            return Response({"detail": "Selected nurse is not free or does not exist."},
                                            status=status.HTTP_400_BAD_REQUEST)
                    except Nurse.DoesNotExist:
                        return Response({"detail": "Selected nurse does not exist."},
                                        status=status.HTTP_404_NOT_FOUND)
                else:
                    # Ensure Nurse model is correctly imported and available
                    free_nurses = list(Nurse.objects.select_for_update().filter(status='FREE'))
                    if not free_nurses:
                        return Response({"detail": "No free nurses available at this moment."},
                                        status=status.HTTP_404_NOT_FOUND)
                    assigned_nurse = random.choice(free_nurses)

                # Update nurse status to BUSY
                assigned_nurse.status = 'BUSY'
                assigned_nurse.save()

                # Create the ServiceRequest instance
                service_request = serializer.save(
                    patient=patient,
                    nurse=assigned_nurse,
                    status='PENDING_ACCEPTANCE' # Pass status here
                )

                # Removed FCM notification logic entirely
                # if assigned_nurse.fcm_token:
                #     message = messaging.Message(...)
                #     try:
                #         response = fcm.send(message)
                #         print(f"FCM message sent to nurse {assigned_nurse.user.username}: {response}")
                #     except Exception as e:
                #         print(f"Error sending FCM to nurse {assigned_nurse.user.username}: {e}")
                # else:
                #     print(f"No FCM token for nurse {assigned_nurse.user.username}. Cannot send FCM notification.")

                return Response({
                    "message": "Service request created and assigned.",
                    "request_id": service_request.id,
                    "assigned_nurse_id": assigned_nurse.id,
                    "assigned_nurse_name": assigned_nurse.user.username,
                    "status": service_request.status
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"Error in ServiceRequestCreateView: {e}")
            return Response({"detail": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

     

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView # Needed for non-generics class
from django.db import transaction
from django.utils import timezone # For setting datetime fields
import random
from firebase_admin import messaging, firestore # Explicitly import firestore
from apps.patients.models import Patient
from apps.nurses.models import Nurse

from .serializers import ServiceRequestCreateSerializer, ServiceRequestActionSerializer, NurseServiceRequestListSerializer # Import new serializers
from .models import ServiceRequest

from apps.notifications.utils import get_fcm_messaging, get_firestore_db

class NurseAcceptServiceRequestView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk, *args, **kwargs): # pk is the service_request_id from URL
        fcm = get_fcm_messaging()
        firestore_db = get_firestore_db()

        if not fcm or not firestore_db:
            return Response({"detail": "Firebase services not initialized. Check backend logs."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            with transaction.atomic():
                # 1. Verify Nurse
                if not hasattr(request.user, 'nurse_profile'):
                    return Response({"detail": "User is not a nurse."}, status=status.HTTP_403_FORBIDDEN)
                nurse = request.user.nurse_profile

                # 2. Retrieve Service Request and Lock for Update
                try:
                    service_request = ServiceRequest.objects.select_for_update().get(pk=pk)
                except ServiceRequest.DoesNotExist:
                    return Response({"detail": "Service Request not found."}, status=status.HTTP_404_NOT_FOUND)

                # 3. Validate Request State and Assignment
                if service_request.nurse != nurse:
                    return Response({"detail": "You are not assigned to this service request."},
                                    status=status.HTTP_403_FORBIDDEN)
                if service_request.status != 'PENDING_ACCEPTANCE':
                    return Response({"detail": f"Service Request is not in PENDING_ACCEPTANCE status. Current status: {service_request.status}"},
                                    status=status.HTTP_400_BAD_REQUEST)

                # 4. Update Service Request Status
                service_request.status = 'IN_PROGRESS'
                service_request.accepted_at = timezone.now()
                service_request.save()

                # 5. Notify Patient via Firestore
                # Path: user_notifications/{patient_id}/{service_request_id}
                patient_id = service_request.patient.id
                request_id_str = str(service_request.id)

                doc_ref = firestore_db.collection('user_notifications').document(str(patient_id)).collection('requests').document(request_id_str)
                doc_ref.set({
                    'status': 'accepted',
                    'message': f"Nurse {nurse.user.username} has accepted your request for '{service_request.need}' and is coming.",
                    'nurse_name': nurse.user.username,
                    'timestamp': firestore.SERVER_TIMESTAMP # Use server timestamp for accuracy
                })
                print(f"Firestore update sent to patient {patient_id} for request {request_id_str}: Nurse Accepted.")

                return Response({
                    "message": "Service Request accepted successfully.",
                    "request_id": service_request.id,
                    "status": service_request.status,
                    "accepted_at": service_request.accepted_at
                }, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Error in NurseAcceptServiceRequestView: {e}")
            return Response({"detail": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NurseServiceRequestListView(generics.ListAPIView):
    serializer_class = NurseServiceRequestListSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        # Ensure the logged-in user is a nurse
        if not hasattr(self.request.user, 'nurse_profile'):
            # Return an empty queryset or raise an exception as appropriate
            return ServiceRequest.objects.none()

        nurse = self.request.user.nurse_profile
        # Fetch requests assigned to this nurse that are not yet completed or cancelled
        return ServiceRequest.objects.filter(
            nurse=nurse
        ).exclude(
            status__in=['COMPLETED', 'CANCELLED', 'REJECTED']
        ).order_by(
            'requested_at' # Order by oldest requests first for task management
        ).select_related('patient__user', 'nurse__user') # Optimize related lookups
    

class NurseCompleteServiceRequestView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk, *args, **kwargs): # pk is the service_request_id from URL
        firestore_db = get_firestore_db()

        if not firestore_db:
            return Response({"detail": "Firebase Firestore not initialized. Check backend logs."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            with transaction.atomic():
                # 1. Verify Nurse
                if not hasattr(request.user, 'nurse_profile'):
                    return Response({"detail": "User is not a nurse."}, status=status.HTTP_403_FORBIDDEN)
                nurse = request.user.nurse_profile

                # 2. Retrieve Service Request and Lock for Update
                try:
                    service_request = ServiceRequest.objects.select_for_update().get(pk=pk)
                except ServiceRequest.DoesNotExist:
                    return Response({"detail": "Service Request not found."}, status=status.HTTP_404_NOT_FOUND)

                # 3. Validate Request State and Assignment
                if service_request.nurse != nurse:
                    return Response({"detail": "You are not assigned to this service request."},
                                    status=status.HTTP_403_FORBIDDEN)
                if service_request.status != 'IN_PROGRESS':
                    return Response({"detail": f"Service Request is not in IN_PROGRESS status. Current status: {service_request.status}"},
                                    status=status.HTTP_400_BAD_REQUEST)

                # 4. Update Service Request Status to COMPLETED
                service_request.status = 'COMPLETED'
                service_request.completed_at = timezone.now()
                service_request.save()

                # 5. Check if Nurse has other active requests and update status if not
                has_other_active_requests = ServiceRequest.objects.filter(
                    nurse=nurse
                ).exclude(
                    status__in=['COMPLETED', 'CANCELLED', 'REJECTED']
                ).exists()

                if not has_other_active_requests:
                    nurse.status = 'FREE' # Set nurse back to FREE if no other pending tasks
                    nurse.save()
                    print(f"Nurse {nurse.user.username} status set to FREE as all tasks are completed.")
                else:
                    print(f"Nurse {nurse.user.username} still has other active tasks, remaining BUSY.")


                # 6. (Optional) Notify Patient via Firestore about task completion
                patient_id = service_request.patient.id
                request_id_str = str(service_request.id)

                doc_ref = firestore_db.collection('user_notifications').document(str(patient_id)).collection('requests').document(request_id_str)
                doc_ref.set({
                    'status': 'completed',
                    'message': f"Nurse {nurse.user.username} has completed your request for '{service_request.need}'.",
                    'nurse_name': nurse.user.username,
                    'timestamp': firestore.SERVER_TIMESTAMP
                }, merge=True) # Use merge=True to update existing document rather than overwrite
                print(f"Firestore update sent to patient {patient_id} for request {request_id_str}: Task Completed.")

                return Response({
                    "message": "Service Request completed successfully.",
                    "request_id": service_request.id,
                    "status": service_request.status,
                    "completed_at": service_request.completed_at,
                    "nurse_status_after_completion": nurse.status
                }, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Error in NurseCompleteServiceRequestView: {e}")
            return Response({"detail": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    