"""vault/admin.py"""
from django.contrib import admin
from .models import Report, ReportExtraction, VaultAccessLog


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["title", "member", "report_type", "report_date", "doctor", "is_deleted"]
    list_filter = ["report_type", "family", "is_deleted"]
    search_fields = ["title", "member__name", "doctor"]
    date_hierarchy = "report_date"
    readonly_fields = ["created_at", "updated_at", "deleted_at"]


@admin.register(ReportExtraction)
class ReportExtractionAdmin(admin.ModelAdmin):
    list_display = ["report", "status", "extracted_at", "created_at"]
    list_filter = ["status"]
    search_fields = ["report__title", "report__member__name"]
    readonly_fields = ["created_at", "updated_at", "extracted_at", "raw_data"]
    ordering = ["-created_at"]


@admin.register(VaultAccessLog)
class VaultAccessLogAdmin(admin.ModelAdmin):
    list_display = ["report", "accessed_by", "action", "accessed_at"]
    readonly_fields = ["accessed_at"]