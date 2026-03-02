from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = 'core'

urlpatterns = [
    path('', lambda request: redirect('core:dashboard'), name='home'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('family-summary/', views.FamilySummaryView.as_view(), name='family_summary'),
]
