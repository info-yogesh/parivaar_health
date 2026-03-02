from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from datetime import timedelta, date
from accounts.models import Family, FamilyMember
from medicines.models import Medicine, MedicineReminder
from calendar_app.models import Appointment
from vault.models import Report


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            try:
                request.user.admin_family
            except Family.DoesNotExist:
                return redirect('accounts:create_family')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        family = get_object_or_404(Family, admin=self.request.user)
        now = timezone.now()
        today = date.today()

        # --- TODAY'S DUE ITEMS ---
        today_start = now.replace(hour=0, minute=0, second=0)
        today_end = now.replace(hour=23, minute=59, second=59)

        today_reminders = MedicineReminder.objects.filter(
            medicine__member__family=family,
            scheduled_time__range=(today_start, today_end),
            status='pending'
        ).select_related('medicine', 'medicine__member')

        today_appointments = Appointment.objects.filter(
            family=family,
            date_time__date=today,
            status='scheduled'
        ).select_related('member')

        # --- ALERTS ---
        active_medicines = Medicine.objects.filter(member__family=family, is_active=True)
        low_stock_medicines = [m for m in active_medicines if m.is_low_stock()]
        expiry_soon_medicines = [m for m in active_medicines if m.expiry_soon()]

        # Members with no recent reports
        thirty_days_ago = today - timedelta(days=30)
        members_no_reports = []
        for member in family.members.all():
            if not member.reports.filter(report_date__gte=thirty_days_ago).exists():
                members_no_reports.append(member)

        # --- MONTHLY SNAPSHOT ---
        month_start = today.replace(day=1)
        uploads_this_month = Report.objects.filter(
            family=family,
            created_at__date__gte=month_start
        ).count()
        completed_reminders = MedicineReminder.objects.filter(
            medicine__member__family=family,
            scheduled_time__date__gte=month_start,
            status='taken'
        ).count()
        missed_reminders = MedicineReminder.objects.filter(
            medicine__member__family=family,
            scheduled_time__date__gte=month_start,
            status='missed'
        ).count()
        appointments_completed = Appointment.objects.filter(
            family=family,
            date_time__date__gte=month_start,
            status='completed'
        ).count()

        # Upcoming appointments (next 7 days)
        upcoming_appointments = Appointment.objects.filter(
            family=family,
            date_time__range=(now, now + timedelta(days=7)),
            status='scheduled'
        ).select_related('member').order_by('date_time')[:5]

        ctx.update({
            'family': family,
            'members': family.members.all(),
            'today_reminders': today_reminders,
            'today_appointments': today_appointments,
            'low_stock_medicines': low_stock_medicines,
            'expiry_soon_medicines': expiry_soon_medicines,
            'members_no_reports': members_no_reports[:3],
            'uploads_this_month': uploads_this_month,
            'completed_reminders': completed_reminders,
            'missed_reminders': missed_reminders,
            'appointments_completed': appointments_completed,
            'upcoming_appointments': upcoming_appointments,
            'total_members': family.members.count(),
            'active_medicines_count': active_medicines.count(),
        })
        return ctx


class FamilySummaryView(LoginRequiredMixin, TemplateView):
    template_name = 'core/family_summary.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        family = get_object_or_404(Family, admin=self.request.user)
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)
        month_start = today.replace(day=1)

        # Aggregate insights
        insights = []

        # Reports this month
        reports_count = Report.objects.filter(family=family, created_at__date__gte=month_start).count()
        if reports_count:
            insights.append({
                'icon': '📄',
                'text': f'{reports_count} report{"s" if reports_count > 1 else ""} uploaded this month',
                'type': 'info'
            })

        # Members with active BP medicines
        bp_members = FamilyMember.objects.filter(
            family=family,
            medicines__name__icontains='bp'
        ).distinct()
        if not bp_members.exists():
            bp_members = FamilyMember.objects.filter(
                family=family,
                medicines__name__icontains='amlodipin'
            ).distinct()

        active_bp_count = Medicine.objects.filter(
            member__family=family,
            is_active=True,
            name__icontains='amlodipin'
        ).count()
        if active_bp_count:
            insights.append({
                'icon': '💊',
                'text': f'{active_bp_count} member{"s" if active_bp_count > 1 else ""} on active BP medication',
                'type': 'info'
            })

        # Missed medicines last 30 days
        missed = MedicineReminder.objects.filter(
            medicine__member__family=family,
            scheduled_time__date__gte=thirty_days_ago,
            status='missed'
        ).count()
        if missed:
            insights.append({
                'icon': '⚠️',
                'text': f'{missed} medicine dose{"s" if missed > 1 else ""} missed in the last 30 days',
                'type': 'warning'
            })

        # Upcoming appointments
        upcoming = Appointment.objects.filter(
            family=family,
            status='scheduled',
            date_time__date__gte=today
        ).count()
        if upcoming:
            insights.append({
                'icon': '📅',
                'text': f'{upcoming} appointment{"s" if upcoming > 1 else ""} coming up',
                'type': 'info'
            })

        # Low stock
        low_stock = sum(1 for m in Medicine.objects.filter(member__family=family, is_active=True) if m.is_low_stock())
        if low_stock:
            insights.append({
                'icon': '🔴',
                'text': f'{low_stock} medicine{"s" if low_stock > 1 else ""} running low on stock',
                'type': 'danger'
            })

        # Per-member summary
        members_summary = []
        for member in family.members.all():
            member_reports = member.reports.filter(report_date__gte=thirty_days_ago).count()
            member_medicines = member.medicines.filter(is_active=True).count()
            member_appointments = member.appointments.filter(
                status='scheduled', date_time__date__gte=today
            ).count()
            members_summary.append({
                'member': member,
                'reports_this_month': member_reports,
                'active_medicines': member_medicines,
                'upcoming_appointments': member_appointments,
                'chronic_conditions': member.chronic_conditions.all(),
            })

        ctx.update({
            'family': family,
            'insights': insights,
            'members_summary': members_summary,
            'disclaimer': 'This summary is for informational purposes only and is not a medical diagnosis or medical advice.'
        })
        return ctx
