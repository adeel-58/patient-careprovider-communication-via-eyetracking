

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    # API Endpoints
    path('api/patients/', include('apps.patients.urls')),
    path('api/nurses/', include('apps.nurses.urls')),
    path('api/service-requests/', include('apps.service_requests.urls')), # New include
    # JWT authentication endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]