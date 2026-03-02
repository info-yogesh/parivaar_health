from django.contrib import admin
from .models import Family, FamilyMember, ChronicCondition, ConsentLog


class FamilyMemberInline(admin.TabularInline):
    model = FamilyMember
    extra = 0
    fields = ['name', 'relationship', 'role', 'gender', 'date_of_birth']


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'admin', 'get_member_count', 'created_at']
    search_fields = ['name', 'city', 'admin__username']
    inlines = [FamilyMemberInline]


@admin.register(FamilyMember)
class FamilyMemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'family', 'relationship', 'role', 'gender', 'get_age']
    list_filter = ['role', 'gender', 'relationship', 'family']
    search_fields = ['name', 'family__name', 'phone']


@admin.register(ChronicCondition)
class ChronicConditionAdmin(admin.ModelAdmin):
    list_display = ['member', 'condition', 'diagnosed_date']


@admin.register(ConsentLog)
class ConsentLogAdmin(admin.ModelAdmin):
    list_display = ['member', 'action', 'consented', 'timestamp']
    list_filter = ['action', 'consented']
