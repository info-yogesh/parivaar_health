from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.contrib import messages
from accounts.models import Family
from .models import Report, VaultAccessLog
from .forms import ReportUploadForm, ReportFilterForm


class ReportListView(LoginRequiredMixin, ListView):
    model = Report
    template_name = 'vault/report_list.html'
    context_object_name = 'reports'
    paginate_by = 12

    def get_family(self):
        return get_object_or_404(Family, admin=self.request.user)

    def get_queryset(self):
        family = self.get_family()
        qs = Report.objects.filter(family=family).select_related('member')

        member = self.request.GET.get('member')
        report_type = self.request.GET.get('report_type')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        search = self.request.GET.get('search')

        if member:
            qs = qs.filter(member__id=member)
        if report_type:
            qs = qs.filter(report_type=report_type)
        if date_from:
            qs = qs.filter(report_date__gte=date_from)
        if date_to:
            qs = qs.filter(report_date__lte=date_to)
        if search:
            qs = qs.filter(title__icontains=search) | qs.filter(doctor__icontains=search)

        return qs.order_by('-report_date')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        family = self.get_family()
        ctx['family'] = family
        ctx['filter_form'] = ReportFilterForm(self.request.GET, family=family)
        ctx['members'] = family.members.all()
        ctx['total_reports'] = Report.objects.filter(family=family).count()
        return ctx


class ReportUploadView(LoginRequiredMixin, CreateView):
    model = Report
    form_class = ReportUploadForm
    template_name = 'vault/report_form.html'
    success_url = reverse_lazy('vault:list')

    def get_family(self):
        return get_object_or_404(Family, admin=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['family'] = self.get_family()
        return kwargs

    def form_valid(self, form):
        form.instance.family = self.get_family()
        messages.success(self.request, f'Report "{form.instance.title}" uploaded successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Upload Report'
        return ctx


class ReportDetailView(LoginRequiredMixin, DetailView):
    model = Report
    template_name = 'vault/report_detail.html'
    context_object_name = 'report'

    def get_queryset(self):
        return Report.objects.filter(family__admin=self.request.user)

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        # Log access
        report = self.get_object()
        try:
            member = request.user.family_member
            VaultAccessLog.objects.create(
                family=report.family,
                report=report,
                accessed_by=member,
                action='view'
            )
        except Exception:
            pass
        return response


class ReportUpdateView(LoginRequiredMixin, UpdateView):
    model = Report
    form_class = ReportUploadForm
    template_name = 'vault/report_form.html'
    success_url = reverse_lazy('vault:list')

    def get_family(self):
        return get_object_or_404(Family, admin=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['family'] = self.get_family()
        return kwargs

    def get_queryset(self):
        return Report.objects.filter(family__admin=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Edit Report'
        return ctx


class ReportDeleteView(LoginRequiredMixin, DeleteView):
    model = Report
    template_name = 'vault/report_confirm_delete.html'
    success_url = reverse_lazy('vault:list')

    def get_queryset(self):
        return Report.objects.filter(family__admin=self.request.user)


class EmergencyViewView(LoginRequiredMixin, TemplateView):
    template_name = 'vault/emergency_view.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        family = get_object_or_404(Family, admin=self.request.user)
        ctx['family'] = family
        members_data = []
        for member in family.members.all():
            members_data.append({
                'member': member,
                'latest_reports': member.reports.order_by('-report_date')[:3],
                'active_medicines': member.medicines.filter(is_active=True)[:5],
                'upcoming_appointments': member.appointments.filter(status='scheduled').order_by('date_time')[:2],
                'chronic_conditions': member.chronic_conditions.all(),
            })
        ctx['members_data'] = members_data
        return ctx
