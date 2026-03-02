from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Family, FamilyMember, ChronicCondition


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=False)
    phone = forms.CharField(max_length=15, required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class FamilyForm(forms.ModelForm):
    class Meta:
        model = Family
        fields = ['name', 'city']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Sharma Family'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Mumbai'}),
        }


class FamilyMemberForm(forms.ModelForm):
    chronic_conditions = forms.MultipleChoiceField(
        choices=FamilyMember.CHRONIC_CONDITION_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = FamilyMember
        fields = ['name', 'date_of_birth', 'gender', 'relationship', 'role', 'phone', 'profile_photo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'relationship': forms.Select(attrs={'class': 'form-select'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_photo': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        member = super().save(commit=commit)
        if commit:
            selected_conditions = self.cleaned_data.get('chronic_conditions', [])
            member.chronic_conditions.all().delete()
            for condition in selected_conditions:
                ChronicCondition.objects.create(member=member, condition=condition)
        return member
