"""
vault/views.py

Views:
  Standard vault:
    ReportListView, ReportUploadView, ReportDetailView,
    ReportUpdateView, ReportDeleteView, ReportExtractionStatusView

  Caregiver emergency (login required):
    EmergencyViewView          GET  /vault/emergency/
    ShareLinkCreateView        POST /vault/emergency/share/create/
    ShareLinkRevokeView        POST /vault/emergency/share/<token>/revoke/
    ShareLinkDeleteView        POST /vault/emergency/share/<token>/delete/

  Doctor shared view (no login required):
    SharedEmergencyPasswordView  GET/POST /vault/emergency/share/<token>/
    SharedEmergencyView          GET      /vault/emergency/share/<token>/view/
"""

import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    DeleteView, DetailView, ListView,
    CreateView, TemplateView, UpdateView, View,
)

from accounts.models import Family
from .forms import (
    EmergencyShareLinkCreateForm,
    EmergencySharePasswordForm,
    ReportFilterForm,
    ReportUploadForm,
)
from .models import EmergencyShareLink, Report, ReportExtraction, VaultAccessLog

logger = logging.getLogger(__name__)

_SESSION_AUTH_KEY     = "emg_auth_{token}"
_SESSION_ATTEMPT_KEY  = "emg_attempts_{token}"
_MAX_PASSWORD_ATTEMPTS = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FamilyOwnedMixin(LoginRequiredMixin):
    def get_family(self) -> Family:
        return get_object_or_404(Family, admin=self.request.user)


def _build_members_data(family, member_filter=None) -> list:
    """
    Build members_data list for both caregiver and shared emergency views.
    Each member dict contains: report_items (report + extraction pairs),
    active_medicines, upcoming_appointments, chronic_conditions.
    """
    members_qs = family.members.all()
    if member_filter:
        members_qs = members_qs.filter(pk=member_filter.pk)

    members_data = []
    for member in members_qs:
        reports = list(
            member.reports
            .filter(is_deleted=False)
            .select_related()
            .order_by("-report_date")
        )
        report_items = []
        for report in reports:
            try:
                extraction = report.extraction
            except ReportExtraction.DoesNotExist:
                extraction = None
            report_items.append({"report": report, "extraction": extraction})

        members_data.append({
            "member":                member,
            "report_items":          report_items,
            "active_medicines":      member.medicines.filter(is_active=True),
            "upcoming_appointments": member.appointments.filter(
                status="scheduled").order_by("date_time")[:3],
            "chronic_conditions":    member.chronic_conditions.all(),
        })
    return members_data


# ---------------------------------------------------------------------------
# Standard vault CRUD
# ---------------------------------------------------------------------------

class ReportListView(FamilyOwnedMixin, ListView):
    model = Report
    template_name = "vault/report_list.html"
    context_object_name = "reports"
    paginate_by = 12

    def get_queryset(self):
        family = self.get_family()
        qs = Report.objects.filter(family=family, is_deleted=False).select_related("member")
        if m := self.request.GET.get("member"):      qs = qs.filter(member__id=m)
        if t := self.request.GET.get("report_type"): qs = qs.filter(report_type=t)
        if d := self.request.GET.get("date_from"):   qs = qs.filter(report_date__gte=d)
        if d := self.request.GET.get("date_to"):     qs = qs.filter(report_date__lte=d)
        if s := self.request.GET.get("search"):
            qs = qs.filter(title__icontains=s) | qs.filter(doctor__icontains=s)
        return qs.order_by("-report_date")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        family = self.get_family()
        ctx.update({
            "family": family,
            "filter_form": ReportFilterForm(self.request.GET, family=family),
            "members": family.members.all(),
            "total_reports": Report.objects.filter(family=family, is_deleted=False).count(),
        })
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
            messages.success(self.request,
                f'Report "{self.object.title}" uploaded. Extracting health parameters in background...')
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
            family__admin=self.request.user, is_deleted=False).select_related("member")

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        try:
            member = self.get_family().members.filter(user=request.user).first()
            if member:
                VaultAccessLog.objects.create(
                    family=self.object.family, report=self.object,
                    accessed_by=member, action="view")
        except Exception:
            pass
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            ctx["extraction"] = self.object.extraction
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
        return Report.objects.filter(family__admin=self.request.user, is_deleted=False)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Edit Report"
        return ctx


class ReportDeleteView(FamilyOwnedMixin, DeleteView):
    model = Report
    template_name = "vault/report_confirm_delete.html"
    success_url = reverse_lazy("vault:list")

    def get_queryset(self):
        return Report.objects.filter(family__admin=self.request.user, is_deleted=False)

    def form_valid(self, form):
        report = self.get_object()
        report.soft_delete()
        messages.success(self.request, f'Report "{report.title}" deleted.')
        return redirect(self.success_url)


class ReportExtractionStatusView(FamilyOwnedMixin, View):
    def get(self, request, pk):
        report = get_object_or_404(
            Report, pk=pk, family__admin=request.user, is_deleted=False)
        try:
            e = report.extraction
            return JsonResponse({
                "status": e.status, "is_completed": e.is_completed(),
                "is_processing": e.is_processing(), "error": e.error_message or None,
            })
        except ReportExtraction.DoesNotExist:
            return JsonResponse({
                "status": "pending", "is_completed": False,
                "is_processing": True, "error": None,
            })


# ---------------------------------------------------------------------------
# Caregiver Emergency View (login required)
# ---------------------------------------------------------------------------

class EmergencyViewView(FamilyOwnedMixin, TemplateView):
    """
    Caregiver's own emergency view.
    Report list per member — parameters expandable per report.
    Share link management panel below.
    """
    template_name = "vault/emergency_view.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        family = self.get_family()
        ctx["family"]       = family
        ctx["members_data"] = _build_members_data(family)
        ctx["share_links"]  = EmergencyShareLink.objects.filter(
            family=family).order_by("-created_at")
        ctx["share_form"]   = EmergencyShareLinkCreateForm(family=family)
        return ctx


class ShareLinkCreateView(FamilyOwnedMixin, View):
    """POST — caregiver creates a new EmergencyShareLink."""

    def post(self, request):
        family = self.get_family()
        form = EmergencyShareLinkCreateForm(request.POST, family=family)
        if form.is_valid():
            link = EmergencyShareLink(family=family)
            link.label  = form.cleaned_data.get("label", "")
            link.member = form.cleaned_data.get("member")
            link.set_password(form.cleaned_data["password"])
            link.save()
            share_url = request.build_absolute_uri(
                reverse("vault:shared_emergency_password", args=[link.token])
            )
            messages.success(
                request,
                f'Share link created. Send this URL to the doctor: {share_url}',
            )
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f"{err}")
        return redirect("vault:emergency")


class ShareLinkRevokeView(FamilyOwnedMixin, View):
    """POST — revoke (deactivate) a share link."""

    def post(self, request, token):
        family = self.get_family()
        link = get_object_or_404(EmergencyShareLink, token=token, family=family)
        link.revoke()
        messages.success(request, "Link revoked. The doctor can no longer access it.")
        return redirect("vault:emergency")


class ShareLinkDeleteView(FamilyOwnedMixin, View):
    """POST — permanently delete a share link record."""

    def post(self, request, token):
        family = self.get_family()
        link = get_object_or_404(EmergencyShareLink, token=token, family=family)
        link.delete()
        messages.success(request, "Share link deleted.")
        return redirect("vault:emergency")


# ---------------------------------------------------------------------------
# Doctor shared view (no Django login required)
# ---------------------------------------------------------------------------

class SharedEmergencyPasswordView(View):
    """
    GET  — show password entry form to doctor
    POST — validate password → set session key → redirect to SharedEmergencyView

    Rate limiting: after _MAX_PASSWORD_ATTEMPTS failures, session is locked.
    """
    template_name = "vault/shared_emergency_password.html"

    def _get_link(self, token):
        return get_object_or_404(EmergencyShareLink, token=token, is_active=True)

    def get(self, request, token):
        link = self._get_link(token)
        auth_key = _SESSION_AUTH_KEY.format(token=token)
        if request.session.get(auth_key):
            return redirect("vault:shared_emergency_view", token=token)
        attempts = request.session.get(_SESSION_ATTEMPT_KEY.format(token=token), 0)
        return render(request, self.template_name, {
            "form": EmergencySharePasswordForm(), "link": link,
            "locked": attempts >= _MAX_PASSWORD_ATTEMPTS,
            "attempts": attempts, "max": _MAX_PASSWORD_ATTEMPTS,
        })

    def post(self, request, token):
        link        = self._get_link(token)
        attempt_key = _SESSION_ATTEMPT_KEY.format(token=token)
        auth_key    = _SESSION_AUTH_KEY.format(token=token)
        attempts    = request.session.get(attempt_key, 0)

        if attempts >= _MAX_PASSWORD_ATTEMPTS:
            return render(request, self.template_name, {
                "form": EmergencySharePasswordForm(), "link": link,
                "locked": True, "attempts": attempts, "max": _MAX_PASSWORD_ATTEMPTS,
            })

        form = EmergencySharePasswordForm(request.POST)
        if form.is_valid():
            if link.check_password(form.cleaned_data["password"]):
                request.session[auth_key] = True
                request.session.pop(attempt_key, None)
                link.record_access()
                return redirect("vault:shared_emergency_view", token=token)
            else:
                attempts += 1
                request.session[attempt_key] = attempts
                remaining = _MAX_PASSWORD_ATTEMPTS - attempts
                form.add_error(
                    "password",
                    f"Incorrect password. {remaining} attempt{'s' if remaining != 1 else ''} remaining.",
                )

        return render(request, self.template_name, {
            "form": form, "link": link, "locked": False,
            "attempts": attempts, "max": _MAX_PASSWORD_ATTEMPTS,
        })


class SharedEmergencyView(View):
    """
    Read-only emergency view for doctors. No Django login needed.
    Authenticated via session key set by SharedEmergencyPasswordView.

    Security:
      - Token must exist and is_active=True
      - Session must have emg_auth_<token> = True
      - All data read-only — no edit/delete actions exposed
    """
    template_name = "vault/shared_emergency_view.html"

    def get(self, request, token):
        link = get_object_or_404(EmergencyShareLink, token=token, is_active=True)

        # Enforce session auth
        auth_key = _SESSION_AUTH_KEY.format(token=token)
        if not request.session.get(auth_key):
            return redirect("vault:shared_emergency_password", token=token)

        members_data = _build_members_data(link.family, member_filter=link.member)

        return render(request, self.template_name, {
            "link":         link,
            "family":       link.family,
            "members_data": members_data,
        })