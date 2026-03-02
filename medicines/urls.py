from django.urls import path
from . import views

app_name = 'medicines'

urlpatterns = [
    path('', views.MedicineListView.as_view(), name='list'),
    path('add/', views.MedicineCreateView.as_view(), name='add'),
    path('<uuid:pk>/', views.MedicineDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.MedicineUpdateView.as_view(), name='edit'),
    path('<uuid:pk>/delete/', views.MedicineDeleteView.as_view(), name='delete'),
    path('<uuid:pk>/stock/', views.MedicineStockUpdateView.as_view(), name='stock_update'),
    path('reminders/today/', views.TodayRemindersView.as_view(), name='today_reminders'),
    path('reminders/<uuid:pk>/update/', views.ReminderUpdateView.as_view(), name='reminder_update'),
]
