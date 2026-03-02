from django.contrib import admin
from .models import Report, VaultAccessLog

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'member', 'report_type', 'report_date', 'doctor']
    list_filter = ['report_type', 'family']
    search_fields = ['title', 'member__name', 'doctor']
    date_hierarchy = 'report_date'

@admin.register(VaultAccessLog)
class VaultAccessLogAdmin(admin.ModelAdmin):
    list_display = ['report', 'accessed_by', 'action', 'accessed_at']
