from django.contrib import admin
from .models import Appointment

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['member', 'appointment_type', 'date_time', 'doctor_name', 'status']
    list_filter = ['status', 'appointment_type', 'family']
    search_fields = ['member__name', 'doctor_name', 'clinic_hospital']
    date_hierarchy = 'date_time'
