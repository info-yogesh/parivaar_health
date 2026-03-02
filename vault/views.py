"""
vault/views.py

Updated views:
  - All querysets filter is_deleted=False
  - ReportDeleteView: soft delete via report.soft_delete()
  - ReportDetailView: passes extraction to template via context
  - ReportExtractionStatusView: AJAX polling endpoint (GET, returns JSON)
  - EmergencyViewView: enhanced with extraction data per member

Security notes:
  - Every queryset scoped to family__admin=request.user (IDOR prevention)
  - ReportExtractionStatusView also scoped — cannot poll other family's reports
  - CSRF not required on GET-only AJAX endpoint
"""

import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView, View,
)

from accounts.models import Family
from .forms import ReportUploadForm, ReportFilterForm
from .models import Report, ReportExtraction, VaultAccessLog

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper mixin — DRY family ownership guard
# ---------------------------------------------------------------------------

class FamilyOwnedMixin(LoginRequiredMixin):
    """
    Provides get_family() scoped to request.user.
    All vault views inherit this instead of duplicating the guard.
    """

    def get_family(self) -> Family:
        return get_object_or_404(Family, admin=self.request.user)


# ---------------------------------------------------------------------------
# Report CRUD
# ---------------------------------------------------------------------------

class ReportListView(FamilyOwnedMixin, ListView):
    model = Report
    template_name = "vault/report_list.html"
    context_object_name = "reports"
    paginate_by = 12

    def get_queryset(self):
        family = self.get_family()
        qs = (
            Report.objects
            .filter(family=family, is_deleted=False)
            .select_related("member")
        )
        member = self.request.GET.get("member")
        report_type = self.request.GET.get("report_type")
        date_from = self.request.GET.get("date_from")
        date_to = self.request.GET.get("date_to")
        search = self.request.GET.get("search")

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

        return qs.order_by("-report_date")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        family = self.get_family()
        ctx["family"] = family
        ctx["filter_form"] = ReportFilterForm(self.request.GET, family=family)
        ctx["members"] = family.members.all()
        ctx["total_reports"] = Report.objects.filter(family=family, is_deleted=False).count()
        return ctx


class ReportUploadView(FamilyOwnedMixin, CreateView):
    model = Report
    form_class = ReportUploadForm
    template_name = "vault/report_form.html"
    success_url = reverse_lazy("vault:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["family"] = self.get_family()
        return kwargs

    def form_valid(self, form):
        form.instance.family = self.get_family()
        response = super().form_valid(form)
        if self.object.file:
            messages.success(
                self.request,
                f'Report "{self.object.title}" uploaded. '
                f'Extracting health parameters in the background...',
            )
        else:
            messages.success(self.request, f'Report "{self.object.title}" saved.')
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Upload Report"
        return ctx


class ReportDetailView(FamilyOwnedMixin, DetailView):
    model = Report
    template_name = "vault/report_detail.html"
    context_object_name = "report"

    def get_queryset(self):
        return Report.objects.filter(
            family__admin=self.request.user,
            is_deleted=False,
        ).select_related("member")

    def get(self, request, *args, **kwargs):
        # Log access
        response = super().get(request, *args, **kwargs)
        report = self.object
        try:
            member = self.get_family().members.filter(user=request.user).first()
            if member:
                VaultAccessLog.objects.create(
                    family=report.family,
                    report=report,
                    accessed_by=member,
                    action="view",
                )
        except Exception:
            pass
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        report = self.object
        # Attach extraction if it exists
        try:
            ctx["extraction"] = report.extraction
        except ReportExtraction.DoesNotExist:
            ctx["extraction"] = None
        return ctx


class ReportUpdateView(FamilyOwnedMixin, UpdateView):
    model = Report
    form_class = ReportUploadForm
    template_name = "vault/report_form.html"
    success_url = reverse_lazy("vault:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["family"] = self.get_family()
        return kwargs

    def get_queryset(self):
        return Report.objects.filter(
            family__admin=self.request.user,
            is_deleted=False,
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Edit Report"
        return ctx


class ReportDeleteView(FamilyOwnedMixin, DeleteView):
    """
    Soft delete only. Sets is_deleted=True, records deleted_at.
    Does NOT remove the DB row, file, or extraction data.
    """
    model = Report
    template_name = "vault/report_confirm_delete.html"
    success_url = reverse_lazy("vault:list")

    def get_queryset(self):
        return Report.objects.filter(
            family__admin=self.request.user,
            is_deleted=False,
        )

    def form_valid(self, form):
        report = self.get_object()
        report.soft_delete()
        messages.success(self.request, f'Report "{report.title}" deleted.')
        return redirect(self.success_url)


# ---------------------------------------------------------------------------
# Extraction status AJAX endpoint
# ---------------------------------------------------------------------------

class ReportExtractionStatusView(FamilyOwnedMixin, View):
    """
    GET /vault/<uuid:pk>/extraction-status/

    AJAX polling endpoint used by report_detail.html to check extraction progress.
    Returns JSON — never a full page response.

    Security: scoped to family__admin=request.user (IDOR safe).

    Response schema:
        {
            "status": "pending" | "processing" | "completed" | "failed",
            "is_completed": bool,
            "is_processing": bool,
            "error": "string or null"
        }
    """

    def get(self, request, pk):
        report = get_object_or_404(
            Report,
            pk=pk,
            family__admin=request.user,
            is_deleted=False,
        )
        try:
            extraction = report.extraction
            return JsonResponse({
                "status": extraction.status,
                "is_completed": extraction.is_completed(),
                "is_processing": extraction.is_processing(),
                "error": extraction.error_message or None,
            })
        except ReportExtraction.DoesNotExist:
            return JsonResponse({
                "status": "pending",
                "is_completed": False,
                "is_processing": True,
                "error": None,
            })


# ---------------------------------------------------------------------------
# Emergency View
# ---------------------------------------------------------------------------

class EmergencyViewView(FamilyOwnedMixin, TemplateView):
    """
    Printable emergency health summary for all family members.

    For each member, resolves the latest Report that has a completed extraction
    and surfaces its key clinical sections (CBC, biochemistry, LFT, KFT).

    Falls back gracefully to report list if no extraction is available.
    """
    template_name = "vault/emergency_view.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        family = self.get_family()
        ctx["family"] = family

        members_data = []
        for member in family.members.all():
            latest_reports = list(
                member.reports
                .filter(is_deleted=False)
                .select_related()
                .order_by("-report_date")[:5]
            )

            # Find latest report with completed extraction
            latest_extraction = None
            for report in latest_reports:
                try:
                    if report.extraction.is_completed():
                        latest_extraction = report.extraction
                        break
                except ReportExtraction.DoesNotExist:
                    continue

            members_data.append({
                "member": member,
                "latest_reports": latest_reports[:3],
                "active_medicines": member.medicines.filter(is_active=True)[:5],
                "upcoming_appointments": (
                    member.appointments
                    .filter(status="scheduled")
                    .order_by("date_time")[:2]
                ),
                "chronic_conditions": member.chronic_conditions.all(),
                # Extraction data (None if no completed extraction)
                "extraction": latest_extraction,
            })

        ctx["members_data"] = members_data
        return ctx