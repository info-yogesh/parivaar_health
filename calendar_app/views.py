from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from accounts.models import Family
from .models import Appointment
from .forms import AppointmentForm, AppointmentRescheduleForm


class AppointmentListView(LoginRequiredMixin, ListView):
    model = Appointment
    template_name = 'calendar_app/appointment_list.html'
    context_object_name = 'appointments'

    def get_family(self):
        return get_object_or_404(Family, admin=self.request.user)

    def get_queryset(self):
        family = self.get_family()
        view_mode = self.request.GET.get('view', 'upcoming')
        qs = Appointment.objects.filter(family=family).select_related('member')

        if view_mode == 'upcoming':
            qs = qs.filter(date_time__gte=timezone.now(), status='scheduled')
        elif view_mode == 'past':
            qs = qs.filter(date_time__lt=timezone.now())
        elif view_mode == 'this_month':
            now = timezone.now()
            qs = qs.filter(date_time__year=now.year, date_time__month=now.month)

        member = self.request.GET.get('member')
        if member:
            qs = qs.filter(member__id=member)

        return qs.order_by('date_time')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        family = self.get_family()
        ctx['family'] = family
        ctx['members'] = family.members.all()
        ctx['view_mode'] = self.request.GET.get('view', 'upcoming')
        ctx['selected_member'] = self.request.GET.get('member', '')
        return ctx


class AppointmentCreateView(LoginRequiredMixin, CreateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = 'calendar_app/appointment_form.html'
    success_url = reverse_lazy('calendar_app:list')

    def get_family(self):
        return get_object_or_404(Family, admin=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['family'] = self.get_family()
        return kwargs

    def form_valid(self, form):
        form.instance.family = self.get_family()
        messages.success(self.request, 'Appointment scheduled!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add Appointment'
        return ctx


class AppointmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = 'calendar_app/appointment_form.html'
    success_url = reverse_lazy('calendar_app:list')

    def get_family(self):
        return get_object_or_404(Family, admin=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['family'] = self.get_family()
        return kwargs

    def get_queryset(self):
        return Appointment.objects.filter(family__admin=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Edit Appointment'
        return ctx


class AppointmentDeleteView(LoginRequiredMixin, DeleteView):
    model = Appointment
    template_name = 'calendar_app/appointment_confirm_delete.html'
    success_url = reverse_lazy('calendar_app:list')

    def get_queryset(self):
        return Appointment.objects.filter(family__admin=self.request.user)


class AppointmentStatusView(LoginRequiredMixin, View):
    def post(self, request, pk, status):
        appointment = get_object_or_404(Appointment, pk=pk, family__admin=request.user)
        if status in ['completed', 'cancelled', 'rescheduled']:
            appointment.status = status
            appointment.save()
            messages.success(request, f'Appointment marked as {status}.')
        return redirect('calendar_app:list')


class CalendarView(LoginRequiredMixin, ListView):
    template_name = 'calendar_app/calendar_view.html'
    context_object_name = 'appointments'

    def get_family(self):
        return get_object_or_404(Family, admin=self.request.user)

    def get_queryset(self):
        family = self.get_family()
        now = timezone.now()
        start = now.replace(day=1, hour=0, minute=0, second=0)
        # Get 6 weeks of data
        end = start + timedelta(days=42)
        return Appointment.objects.filter(
            family=family,
            date_time__range=(start, end)
        ).select_related('member')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        import calendar
        from datetime import date
        now = timezone.now()
        ctx['family'] = self.get_family()
        ctx['current_month'] = now.strftime('%B %Y')
        ctx['month_days'] = calendar.monthcalendar(now.year, now.month)
        ctx['today'] = date.today()
        return ctx
