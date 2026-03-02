from django.contrib import admin
from .models import Medicine, MedicineReminder, MedicineRefillRequest


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ['name', 'member', 'dosage', 'frequency', 'quantity_remaining', 'is_active', 'expiry_date']
    list_filter = ['is_active', 'frequency', 'member__family']
    search_fields = ['name', 'member__name']
    date_hierarchy = 'start_date'


@admin.register(MedicineReminder)
class MedicineReminderAdmin(admin.ModelAdmin):
    list_display = ['medicine', 'scheduled_time', 'status', 'taken_at']
    list_filter = ['status']


@admin.register(MedicineRefillRequest)
class MedicineRefillRequestAdmin(admin.ModelAdmin):
    list_display = ['medicine', 'quantity_requested', 'requested_at', 'fulfilled']
