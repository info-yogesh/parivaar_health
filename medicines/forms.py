from django import forms
from .models import Medicine, MedicineReminder


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = [
            'member', 'name', 'dosage', 'frequency', 'start_date', 'end_date',
            'quantity_purchased', 'quantity_remaining', 'expiry_date',
            'low_stock_threshold', 'instructions', 'photo', 'prescribed_by', 'is_active'
        ]
        widgets = {
            'member': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Metformin 500mg'}),
            'dosage': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1 tablet'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'quantity_purchased': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantity_remaining': forms.NumberInput(attrs={'class': 'form-control'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'low_stock_threshold': forms.NumberInput(attrs={'class': 'form-control'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'prescribed_by': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Doctor name'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, family=None, **kwargs):
        super().__init__(*args, **kwargs)
        if family:
            self.fields['member'].queryset = family.members.all()


class MedicineReminderUpdateForm(forms.ModelForm):
    class Meta:
        model = MedicineReminder
        fields = ['status', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class StockUpdateForm(forms.Form):
    quantity_to_add = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Units to add'})
    )
