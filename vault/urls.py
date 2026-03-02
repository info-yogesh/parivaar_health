"""vault/urls.py"""
from django.urls import path
from . import views

app_name = "vault"

urlpatterns = [
    # ── Vault CRUD ────────────────────────────────────────────────────────
    path("",                        views.ReportListView.as_view(),            name="list"),
    path("upload/",                 views.ReportUploadView.as_view(),          name="upload"),
    path("<uuid:pk>/",              views.ReportDetailView.as_view(),          name="detail"),
    path("<uuid:pk>/edit/",         views.ReportUpdateView.as_view(),          name="edit"),
    path("<uuid:pk>/delete/",       views.ReportDeleteView.as_view(),          name="delete"),
    path("<uuid:pk>/extraction-status/",
                                    views.ReportExtractionStatusView.as_view(),name="extraction_status"),

    # ── Caregiver emergency (login required) ──────────────────────────────
    path("emergency/",              views.EmergencyViewView.as_view(),         name="emergency"),
    path("emergency/share/create/", views.ShareLinkCreateView.as_view(),       name="share_link_create"),
    path("emergency/share/<uuid:token>/revoke/",
                                    views.ShareLinkRevokeView.as_view(),       name="share_link_revoke"),
    path("emergency/share/<uuid:token>/delete/",
                                    views.ShareLinkDeleteView.as_view(),       name="share_link_delete"),

    # ── Doctor shared view (no login required) ────────────────────────────
    path("emergency/share/<uuid:token>/",
                                    views.SharedEmergencyPasswordView.as_view(),name="shared_emergency_password"),
    path("emergency/share/<uuid:token>/view/",
                                    views.SharedEmergencyView.as_view(),        name="shared_emergency_view"),
]