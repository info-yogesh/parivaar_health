"""vault/forms.py"""
from django import forms
from .models import Report, EmergencyShareLink


class ReportUploadForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ["member", "report_type", "title", "report_date",
                  "doctor", "hospital_lab", "file", "notes"]
        widgets = {
            "member":       forms.Select(attrs={"class": "form-select"}),
            "report_type":  forms.Select(attrs={"class": "form-select"}),
            "title":        forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., CBC Report - Jan 2025"}),
            "report_date":  forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "doctor":       forms.TextInput(attrs={"class": "form-control", "placeholder": "Referring Doctor"}),
            "hospital_lab": forms.TextInput(attrs={"class": "form-control", "placeholder": "Hospital or Lab Name"}),
            "file":         forms.FileInput(attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png"}),
            "notes":        forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, family=None, **kwargs):
        super().__init__(*args, **kwargs)
        if family:
            self.fields["member"].queryset = family.members.all()


class ReportFilterForm(forms.Form):
    member      = forms.ChoiceField(required=False, widget=forms.Select(attrs={"class": "form-select"}))
    report_type = forms.ChoiceField(required=False, widget=forms.Select(attrs={"class": "form-select"}))
    date_from   = forms.DateField(required=False, widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}))
    date_to     = forms.DateField(required=False, widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}))

    def __init__(self, *args, family=None, **kwargs):
        super().__init__(*args, **kwargs)
        member_choices = [("", "All Members")]
        if family:
            for m in family.members.all():
                member_choices.append((str(m.id), m.name))
        self.fields["member"].choices = member_choices
        self.fields["report_type"].choices = [("", "All Types")] + list(Report.REPORT_TYPE_CHOICES)


# ---------------------------------------------------------------------------
# Emergency Share Link forms
# ---------------------------------------------------------------------------

class EmergencyShareLinkCreateForm(forms.Form):
    """
    Caregiver creates a share link.
    We don't use ModelForm because password needs special handling
    (hash on save, never round-trip plain text).
    """
    label = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. Dr. Mehta, Apollo Hospital",
        }),
        help_text="Optional — helps you remember who you shared with.",
    )
    member = forms.ModelChoiceField(
        queryset=None,       # set in __init__
        required=False,
        empty_label="All family members",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Leave blank to share all members.",
    )
    password = forms.CharField(
        min_length=6,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Set a password for the doctor",
            "autocomplete": "new-password",
        }),
        help_text="Minimum 6 characters. Share this password separately with the doctor.",
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Confirm password",
            "autocomplete": "new-password",
        }),
    )

    def __init__(self, *args, family=None, **kwargs):
        super().__init__(*args, **kwargs)
        if family:
            self.fields["member"].queryset = family.members.all()

    def clean(self):
        cleaned = super().clean()
        pw  = cleaned.get("password")
        cpw = cleaned.get("confirm_password")
        if pw and cpw and pw != cpw:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned


class EmergencySharePasswordForm(forms.Form):
    """
    Doctor enters the password to access the shared emergency link.
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "Enter access password",
            "autofocus": True,
            "autocomplete": "current-password",
        }),
    )