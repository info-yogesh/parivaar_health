from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from accounts.models import Family, FamilyMember
from .models import Medicine, MedicineReminder, MedicineRefillRequest
from .forms import MedicineForm, MedicineReminderUpdateForm, StockUpdateForm


class MedicineListView(LoginRequiredMixin, ListView):
    model = Medicine
    template_name = 'medicines/medicine_list.html'
    context_object_name = 'medicines'

    def get_family(self):
        return get_object_or_404(Family, admin=self.request.user)

    def get_queryset(self):
        family = self.get_family()
        member_filter = self.request.GET.get('member')
        qs = Medicine.objects.filter(member__family=family)
        if member_filter:
            qs = qs.filter(member__id=member_filter)
        return qs.select_related('member')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        family = self.get_family()
        ctx['family'] = family
        ctx['members'] = family.members.all()
        ctx['selected_member'] = self.request.GET.get('member', '')

        # Alerts
        all_meds = Medicine.objects.filter(member__family=family, is_active=True)
        ctx['low_stock_count'] = sum(1 for m in all_meds if m.is_low_stock())
        ctx['expiry_soon_count'] = sum(1 for m in all_meds if m.expiry_soon())
        return ctx


class MedicineCreateView(LoginRequiredMixin, CreateView):
    model = Medicine
    form_class = MedicineForm
    template_name = 'medicines/medicine_form.html'
    success_url = reverse_lazy('medicines:list')

    def get_family(self):
        return get_object_or_404(Family, admin=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['family'] = self.get_family()
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add Medicine'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'Medicine "{form.instance.name}" added!')
        return super().form_valid(form)


class MedicineUpdateView(LoginRequiredMixin, UpdateView):
    model = Medicine
    form_class = MedicineForm
    template_name = 'medicines/medicine_form.html'
    success_url = reverse_lazy('medicines:list')

    def get_family(self):
        return get_object_or_404(Family, admin=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['family'] = self.get_family()
        return kwargs

    def get_queryset(self):
        return Medicine.objects.filter(member__family__admin=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Edit Medicine'
        return ctx


class MedicineDeleteView(LoginRequiredMixin, DeleteView):
    model = Medicine
    template_name = 'medicines/medicine_confirm_delete.html'
    success_url = reverse_lazy('medicines:list')

    def get_queryset(self):
        return Medicine.objects.filter(member__family__admin=self.request.user)


class MedicineDetailView(LoginRequiredMixin, DetailView):
    model = Medicine
    template_name = 'medicines/medicine_detail.html'
    context_object_name = 'medicine'

    def get_queryset(self):
        return Medicine.objects.filter(member__family__admin=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        medicine = self.get_object()
        ctx['reminders'] = medicine.reminders.order_by('-scheduled_time')[:10]
        ctx['stock_form'] = StockUpdateForm()
        return ctx


class MedicineStockUpdateView(LoginRequiredMixin, FormView):
    form_class = StockUpdateForm
    template_name = 'medicines/stock_update.html'

    def get_medicine(self):
        return get_object_or_404(Medicine, pk=self.kwargs['pk'], member__family__admin=self.request.user)

    def form_valid(self, form):
        medicine = self.get_medicine()
        qty = form.cleaned_data['quantity_to_add']
        medicine.quantity_remaining += qty
        medicine.quantity_purchased += qty
        medicine.save()
        messages.success(self.request, f'Stock updated! {medicine.name} now has {medicine.quantity_remaining} units.')
        return redirect('medicines:detail', pk=medicine.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['medicine'] = self.get_medicine()
        return ctx


class TodayRemindersView(LoginRequiredMixin, ListView):
    template_name = 'medicines/today_reminders.html'
    context_object_name = 'reminders'

    def get_queryset(self):
        family = get_object_or_404(Family, admin=self.request.user)
        today_start = timezone.now().replace(hour=0, minute=0, second=0)
        today_end = timezone.now().replace(hour=23, minute=59, second=59)
        return MedicineReminder.objects.filter(
            medicine__member__family=family,
            scheduled_time__range=(today_start, today_end)
        ).select_related('medicine', 'medicine__member').order_by('scheduled_time')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['family'] = get_object_or_404(Family, admin=self.request.user)
        return ctx


class ReminderUpdateView(LoginRequiredMixin, UpdateView):
    model = MedicineReminder
    form_class = MedicineReminderUpdateForm
    template_name = 'medicines/reminder_update.html'
    success_url = reverse_lazy('medicines:today_reminders')

    def get_queryset(self):
        return MedicineReminder.objects.filter(medicine__member__family__admin=self.request.user)

    def form_valid(self, form):
        if form.cleaned_data['status'] == 'taken':
            form.instance.taken_at = timezone.now()
            # Deduct from stock
            med = form.instance.medicine
            if med.quantity_remaining > 0:
                med.quantity_remaining -= 1
                med.save()
        return super().form_valid(form)
