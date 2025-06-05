# apps/nurses/urls.py
from .views import FreeNurseListView
from django.urls import path
from .views import NurseRegisterView, NurseLoginView, NurseLogoutView, NurseStatusUpdateView

urlpatterns = [
    path('register/', NurseRegisterView.as_view(), name='nurse-register'),
    path('login/', NurseLoginView.as_view(), name='nurse-login'),
    path('logout/', NurseLogoutView.as_view(), name='nurse-logout'),
    path('status/', NurseStatusUpdateView.as_view(), name='nurse-status-update'),
    path('available/', FreeNurseListView.as_view(), name='free-nurses-list'), # New endpoint
]