from django import forms
from .models import Appointment


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = [
            'member', 'doctor_name', 'clinic_hospital', 'appointment_type',
            'date_time', 'duration_minutes', 'notes', 'send_whatsapp_reminder'
        ]
        widgets = {
            'member': forms.Select(attrs={'class': 'form-select'}),
            'doctor_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dr. Name'}),
            'clinic_hospital': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Clinic or Hospital'}),
            'appointment_type': forms.Select(attrs={'class': 'form-select'}),
            'date_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'send_whatsapp_reminder': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, family=None, **kwargs):
        super().__init__(*args, **kwargs)
        if family:
            self.fields['member'].queryset = family.members.all()


class AppointmentRescheduleForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['date_time', 'notes']
        widgets = {
            'date_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
