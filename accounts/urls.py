from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('family/create/', views.FamilyCreateView.as_view(), name='create_family'),
    path('family/edit/', views.FamilyUpdateView.as_view(), name='edit_family'),
    path('members/', views.FamilyMemberListView.as_view(), name='member_list'),
    path('members/add/', views.FamilyMemberCreateView.as_view(), name='add_member'),
    path('members/<uuid:pk>/', views.FamilyMemberDetailView.as_view(), name='member_detail'),
    path('members/<uuid:pk>/edit/', views.FamilyMemberUpdateView.as_view(), name='edit_member'),
    path('members/<uuid:pk>/delete/', views.FamilyMemberDeleteView.as_view(), name='delete_member'),
]
