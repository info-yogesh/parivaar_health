"""vault/urls.py"""
from django.urls import path
from . import views

app_name = "vault"

urlpatterns = [
    path("", views.ReportListView.as_view(), name="list"),
    path("upload/", views.ReportUploadView.as_view(), name="upload"),
    path("<uuid:pk>/", views.ReportDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", views.ReportUpdateView.as_view(), name="edit"),
    path("<uuid:pk>/delete/", views.ReportDeleteView.as_view(), name="delete"),
    path(
        "<uuid:pk>/extraction-status/",
        views.ReportExtractionStatusView.as_view(),
        name="extraction_status",
    ),
    path("emergency/", views.EmergencyViewView.as_view(), name="emergency"),
]