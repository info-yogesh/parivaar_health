from django.views.generic import CreateView, UpdateView, DeleteView, ListView, DetailView, FormView, TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Family, FamilyMember, ChronicCondition
from .forms import UserRegistrationForm, FamilyForm, FamilyMemberForm


class RegisterView(CreateView):
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:create_family')

    def form_valid(self, form):
        response = super().form_valid(form)
        from django.contrib.auth import login
        login(self.request, self.object)
        messages.success(self.request, 'Account created! Now set up your family profile.')
        return response

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs['class'] = 'form-control'
        return form


class FamilyCreateView(LoginRequiredMixin, CreateView):
    model = Family
    form_class = FamilyForm
    template_name = 'accounts/family_create.html'
    success_url = reverse_lazy('accounts:add_member')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            try:
                request.user.admin_family
                return redirect('core:dashboard')
            except Family.DoesNotExist:
                pass
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.admin = self.request.user
        response = super().form_valid(form)
        # Auto-create admin as first family member
        FamilyMember.objects.create(
            family=self.object,
            user=self.request.user,
            name=self.request.user.get_full_name() or self.request.user.username,
            relationship='self',
            role='admin',
            gender='other',
        )
        messages.success(self.request, f'Family "{self.object.name}" created!')
        return response


class FamilyUpdateView(LoginRequiredMixin, UpdateView):
    model = Family
    form_class = FamilyForm
    template_name = 'accounts/family_edit.html'
    success_url = reverse_lazy('core:dashboard')

    def get_object(self):
        return get_object_or_404(Family, admin=self.request.user)


class FamilyMemberListView(LoginRequiredMixin, ListView):
    model = FamilyMember
    template_name = 'accounts/member_list.html'
    context_object_name = 'members'

    def get_queryset(self):
        family = get_object_or_404(Family, admin=self.request.user)
        return FamilyMember.objects.filter(family=family).order_by('name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['family'] = get_object_or_404(Family, admin=self.request.user)
        return ctx


class FamilyMemberCreateView(LoginRequiredMixin, CreateView):
    model = FamilyMember
    form_class = FamilyMemberForm
    template_name = 'accounts/member_form.html'
    success_url = reverse_lazy('accounts:member_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add Family Member'
        return ctx

    def form_valid(self, form):
        try:
            family = self.request.user.admin_family
        except Family.DoesNotExist:
            messages.error(self.request, 'Please create a family first.')
            return redirect('accounts:create_family')
        form.instance.family = family
        messages.success(self.request, f'Member "{form.instance.name}" added!')
        return super().form_valid(form)


class FamilyMemberUpdateView(LoginRequiredMixin, UpdateView):
    model = FamilyMember
    form_class = FamilyMemberForm
    template_name = 'accounts/member_form.html'
    success_url = reverse_lazy('accounts:member_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Edit Family Member'
        return ctx

    def get_queryset(self):
        family = get_object_or_404(Family, admin=self.request.user)
        return FamilyMember.objects.filter(family=family)


class FamilyMemberDeleteView(LoginRequiredMixin, DeleteView):
    model = FamilyMember
    template_name = 'accounts/member_confirm_delete.html'
    success_url = reverse_lazy('accounts:member_list')

    def get_queryset(self):
        family = get_object_or_404(Family, admin=self.request.user)
        return FamilyMember.objects.filter(family=family)


class FamilyMemberDetailView(LoginRequiredMixin, DetailView):
    model = FamilyMember
    template_name = 'accounts/member_detail.html'
    context_object_name = 'member'

    def get_queryset(self):
        family = get_object_or_404(Family, admin=self.request.user)
        return FamilyMember.objects.filter(family=family)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        member = self.get_object()
        ctx['medicines'] = member.medicines.filter(is_active=True)
        ctx['appointments'] = member.appointments.order_by('-date_time')[:5]
        ctx['reports'] = member.reports.order_by('-report_date')[:5]
        return ctx
