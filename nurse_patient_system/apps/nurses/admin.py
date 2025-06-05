# apps/nurses/admin.py

from django.contrib import admin
from .models import Nurse

@admin.register(Nurse)
class NurseAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'employee_id')
    list_filter = ('status',)
    search_fields = ('user__username', 'employee_id')
    raw_id_fields = ('user',)