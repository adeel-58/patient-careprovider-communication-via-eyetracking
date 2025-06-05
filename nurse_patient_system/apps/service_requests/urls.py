# apps/service_requests/urls.py

from django.urls import path
from .views import ServiceRequestCreateView, NurseAcceptServiceRequestView, NurseServiceRequestListView, NurseCompleteServiceRequestView # Import new view

urlpatterns = [
    path('create/', ServiceRequestCreateView.as_view(), name='service-request-create'),
    path('<int:pk>/accept/', NurseAcceptServiceRequestView.as_view(), name='service-request-accept'),
    path('<int:pk>/complete/', NurseCompleteServiceRequestView.as_view(), name='service-request-complete'), # New: Complete by ID
    path('nurse/my-requests/', NurseServiceRequestListView.as_view(), name='nurse-my-requests'),
]