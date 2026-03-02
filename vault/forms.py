from django import forms
from .models import Report


class ReportUploadForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['member', 'report_type', 'title', 'report_date', 'doctor', 'hospital_lab', 'file', 'notes']
        widgets = {
            'member': forms.Select(attrs={'class': 'form-select'}),
            'report_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., CBC Report - Jan 2025'}),
            'report_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'doctor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Referring Doctor'}),
            'hospital_lab': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Hospital or Lab Name'}),
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, family=None, **kwargs):
        super().__init__(*args, **kwargs)
        if family:
            self.fields['member'].queryset = family.members.all()


class ReportFilterForm(forms.Form):
    member = forms.ChoiceField(required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    report_type = forms.ChoiceField(required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))

    def __init__(self, *args, family=None, **kwargs):
        super().__init__(*args, **kwargs)
        member_choices = [('', 'All Members')]
        if family:
            for m in family.members.all():
                member_choices.append((str(m.id), m.name))
        self.fields['member'].choices = member_choices
        self.fields['report_type'].choices = [('', 'All Types')] + list(Report.REPORT_TYPE_CHOICES)
