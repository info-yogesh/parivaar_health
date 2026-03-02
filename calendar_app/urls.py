from django.urls import path
from . import views

app_name = 'calendar_app'

urlpatterns = [
    path('', views.AppointmentListView.as_view(), name='list'),
    path('view/', views.CalendarView.as_view(), name='calendar'),
    path('add/', views.AppointmentCreateView.as_view(), name='add'),
    path('<uuid:pk>/edit/', views.AppointmentUpdateView.as_view(), name='edit'),
    path('<uuid:pk>/delete/', views.AppointmentDeleteView.as_view(), name='delete'),
    path('<uuid:pk>/status/<str:status>/', views.AppointmentStatusView.as_view(), name='update_status'),
]
